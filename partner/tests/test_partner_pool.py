"""Partner App New Bookings pool — dedupe, filtering, amounts."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.services import JobCardService
from partner.models import Partner
from partner.services import (
    auto_send_new_booking_to_partner_app,
    filter_partner_pool_bookings,
    is_partner_pool_booking,
)
from partner.utils import generate_partner_tokens


@override_settings(REVENUE_MODEL_V2=True)
class PartnerPoolFilterTests(TestCase):
    def setUp(self):
        self.schedule = timezone.localtime(
            timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        )
        self.client_record = Client.objects.create(full_name='Pool Client', mobile='9888811111')
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Pool')
        city, _ = City.objects.get_or_create(state=state, name='Mumbai Pool')
        norm = Location.normalize_text('Malad')
        self.location, _ = Location.objects.get_or_create(
            city=city,
            normalized_name=norm,
            defaults={'name': 'Malad'},
        )

        self.tech = Technician.objects.create(
            name='Pool Tech',
            mobile='9000011111',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Pool Tech',
            mobile='9000011111',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        self.tech.service_cities.add(city)
        tokens = generate_partner_tokens(self.partner)
        self.partner_api = APIClient()
        self.partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def _pending_shell(self, **overrides):
        data = {
            'client': self.client_record.id,
            'service_type': 'Bed Bugs',
            'service_category': JobCard.ServiceCategory.ONE_TIME,
            'schedule_datetime': self.schedule,
            'price': '4000',
            'total_amount': Decimal('4000'),
            'status': JobCard.JobStatus.PENDING,
            'master_location': self.location.id,
            'master_city': self.location.city_id,
        }
        data.update(overrides)
        return JobCardService.create_jobcard(data, user=None)

    def test_old_service_call_excluded_from_available(self):
        with self.captureOnCommitCallbacks(execute=True):
            main = self._pending_shell()
        follow = JobCard.objects.create(
            client=self.client_record,
            service_type='Bed Bugs',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            schedule_datetime=self.schedule + timedelta(days=15),
            price='0',
            status=JobCard.JobStatus.UPCOMING,
            parent_job=main,
            service_cycle=2,
            is_followup_visit=True,
            is_service_call=True,
            sent_to_app_at=timezone.now(),
            partner_status=JobCard.PartnerStatus.PENDING,
            master_location=self.location,
        )
        self.assertFalse(is_partner_pool_booking(follow))

        available = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(available.status_code, 200, available.data)
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(main.id, ids)
        self.assertNotIn(follow.id, ids)
        self.assertEqual(ids.count(main.id), 1)

    def test_multi_service_day1_child_hidden_when_shell_in_pool(self):
        with self.captureOnCommitCallbacks(execute=True):
            shell = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Cockroach / Ants, Bed Bugs',
                    'service_items': [
                        {'service': 'Cockroach / Ants', 'plan': 'One-Time', 'area': '2 BHK', 'amount': '2000'},
                        {'service': 'Bed Bugs', 'plan': 'One-Time', 'area': '2 BHK', 'amount': '4000'},
                    ],
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '6000',
                    'total_amount': Decimal('6000'),
                    'status': JobCard.JobStatus.PENDING,
                    'master_location': self.location.id,
                },
                user=None,
            )
        shell.refresh_from_db()
        children = list(
            JobCard.objects.filter(parent_job=shell, service_cycle=1).order_by('id')
        )
        self.assertGreaterEqual(len(children), 2)

        # Simulate heal sending a day-1 child into the pool (legacy bug).
        child = children[0]
        child.sent_to_app_at = timezone.now()
        child.partner_status = JobCard.PartnerStatus.PENDING
        child.status = JobCard.JobStatus.PENDING
        child.is_service_call = False
        child.is_followup_visit = False
        child.save()

        filtered = filter_partner_pool_bookings([shell, child])
        self.assertEqual([j.id for j in filtered], [shell.id])

        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(shell.id, ids)
        self.assertNotIn(child.id, ids)

    def test_available_amount_uses_price_not_zero(self):
        with self.captureOnCommitCallbacks(execute=True):
            job = self._pending_shell(price='4000', total_amount=Decimal('4000'))

        available = self.partner_api.get('/api/partner/bookings/available/')
        row = next(r for r in available.data['results'] if r['id'] == job.id)
        self.assertEqual(row['total_booking_amount'], '4000.00')

    def test_counts_match_available_list(self):
        with self.captureOnCommitCallbacks(execute=True):
            self._pending_shell()

        available = self.partner_api.get('/api/partner/bookings/available/')
        counts = self.partner_api.get('/api/partner/bookings/counts/')
        self.assertEqual(counts.status_code, 200, counts.data)
        self.assertEqual(counts.data['available'], available.data['count'])

    def test_auto_send_skips_service_call_rows(self):
        job = JobCard.objects.create(
            client=self.client_record,
            service_type='Bed Bugs',
            service_category=JobCard.ServiceCategory.ONE_TIME,
            schedule_datetime=self.schedule,
            price='0',
            status=JobCard.JobStatus.PENDING,
            service_cycle=2,
            is_followup_visit=True,
            is_service_call=True,
            master_location=self.location,
        )
        sent = auto_send_new_booking_to_partner_app(job)
        self.assertFalse(sent)
        job.refresh_from_db()
        self.assertIsNone(job.sent_to_app_at)
