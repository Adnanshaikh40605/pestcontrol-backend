"""Auto-send CRM bookings into the Partner App open pool."""

from datetime import datetime, timezone as dt_timezone

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.services import JobCardService
from partner.models import Partner
from partner.services import (
    auto_send_new_booking_to_partner_app,
    broadcast_pending_filter,
)
from partner.utils import generate_partner_tokens


@override_settings(REVENUE_MODEL_V2=True)
class AutoSendBookingToPartnerAppTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='crm_auto', password='pass1234', is_staff=True)
        self.schedule = datetime(2026, 8, 20, 10, 0, tzinfo=dt_timezone.utc)
        self.client_record = Client.objects.create(full_name='Auto Send Client', mobile='9888877777')
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Auto')
        city, _ = City.objects.get_or_create(state=state, name='Pune Auto')
        norm = Location.normalize_text('Auto Send Area')
        self.location, _ = Location.objects.get_or_create(
            city=city,
            normalized_name=norm,
            defaults={'name': 'Auto Send Area'},
        )

        self.tech = Technician.objects.create(
            name='Auto Pool Tech',
            mobile='9000099999',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Auto Pool Tech',
            mobile='9000099999',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        tokens = generate_partner_tokens(self.partner)
        self.partner_api = APIClient()
        self.partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        self.crm = APIClient()
        self.crm.force_authenticate(user=self.user)

    def test_create_jobcard_service_auto_sends_to_partner_pool(self):
        with self.captureOnCommitCallbacks(execute=True):
            job = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'General Pest Control',
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '1999',
                    'reference': 'Poster',
                    'status': JobCard.JobStatus.PENDING,
                    'master_location': self.location.id,
                },
                user=self.user,
            )
        job.refresh_from_db()
        self.assertIsNotNone(job.sent_to_app_at)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.PENDING)
        self.assertIsNone(job.partner_id)
        self.assertTrue(JobCard.objects.filter(broadcast_pending_filter(), pk=job.pk).exists())

        available = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(available.status_code, 200, available.data)
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(job.id, ids)

    def test_create_via_api_auto_sends(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.crm.post(
                '/api/v1/jobcards/',
                {
                    'client_data': {
                        'full_name': 'API Auto Client',
                        'mobile': '9777766666',
                    },
                    'service_type': 'Bed Bugs',
                    'service_category': 'One-Time Service',
                    'schedule_datetime': self.schedule.isoformat(),
                    'price': '3000',
                    'reference': 'Poster',
                    'status': 'Pending',
                    'master_location': self.location.id,
                },
                format='json',
            )
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(id=response.data['id'])
        self.assertIsNotNone(job.sent_to_app_at)

        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(job.id, ids)

    def test_auto_send_is_idempotent_no_duplicate_pool_entry(self):
        with self.captureOnCommitCallbacks(execute=True):
            job = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Cockroach / Ants',
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '1500',
                    'reference': 'Poster',
                    'status': JobCard.JobStatus.PENDING,
                },
                user=self.user,
            )
        job.refresh_from_db()
        first_sent_at = job.sent_to_app_at
        self.assertIsNotNone(first_sent_at)

        sent_again = auto_send_new_booking_to_partner_app(job, sent_by_user=self.user)
        self.assertFalse(sent_again)
        job.refresh_from_db()
        self.assertEqual(job.sent_to_app_at, first_sent_at)

        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertEqual(ids.count(job.id), 1)

    def test_manual_send_to_app_still_works_as_refloat(self):
        with self.captureOnCommitCallbacks(execute=True):
            job = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Termite',
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '5000',
                    'reference': 'Poster',
                    'status': JobCard.JobStatus.PENDING,
                },
                user=self.user,
            )
        send = self.crm.post(f'/api/v1/jobcards/{job.id}/send-to-app/', {}, format='json')
        self.assertEqual(send.status_code, 200, send.data)
        self.assertTrue(send.data['success'])
        self.assertTrue(send.data.get('refloated'))
