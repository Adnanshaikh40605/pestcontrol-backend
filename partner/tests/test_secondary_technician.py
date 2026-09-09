"""Secondary technicians: manual assignment only, but paid like a partner.

A secondary technician must never see the open booking broadcast or get the
pool push — desk staff hand them each job. Their money, however, works exactly
like a partner's: they earn from the 40% pool and their earnings settle.
"""

from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.services import JobCardService
from partner.models import Partner
from partner.services import PartnerBookingError, partner_accept_booking
from partner.utils import generate_partner_tokens


@override_settings(REVENUE_MODEL_V2=True)
class SecondaryTechnicianDispatchTests(TestCase):
    def setUp(self):
        self.schedule = timezone.localtime(
            timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        )
        self.client_record = Client.objects.create(
            full_name='Secondary Client', mobile='9888822222'
        )
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Sec')
        self.city, _ = City.objects.get_or_create(state=state, name='Mumbai Sec')
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=Location.normalize_text('Andheri'),
            defaults={'name': 'Andheri'},
        )

        self.partner_tech, self.partner_api, self.partner_row = self._make_tech(
            'Broadcast Tech', '9000022221', Technician.TechnicianType.PARTNER
        )
        self.secondary_tech, self.secondary_api, self.secondary_row = self._make_tech(
            'Secondary Tech', '9000022222', Technician.TechnicianType.SECONDARY
        )

    def _make_tech(self, name, mobile, technician_type):
        tech = Technician.objects.create(
            name=name,
            mobile=mobile,
            technician_type=technician_type,
            presence_status=Technician.PresenceStatus.ACTIVE,
            is_active=True,
        )
        tech.service_cities.add(self.city)
        partner = Partner.objects.create(
            full_name=name,
            mobile=mobile,
            password='x',
            core_technician=tech,
            is_app_approved=True,
            is_active=True,
        )
        partner.set_password('testpass')
        partner.save()
        tokens = generate_partner_tokens(partner)
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tech, api, partner

    def _broadcast_booking(self):
        with self.captureOnCommitCallbacks(execute=True):
            return JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Bed Bugs',
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '5000',
                    'total_amount': Decimal('5000'),
                    'status': JobCard.JobStatus.PENDING,
                    'master_location': self.location.id,
                    'master_city': self.city.id,
                },
                user=None,
            )

    def test_broadcast_hidden_from_secondary_but_visible_to_partner(self):
        job = self._broadcast_booking()

        partner_view = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(partner_view.status_code, 200, partner_view.data)
        self.assertIn(job.id, [r['id'] for r in partner_view.data['results']])
        self.assertFalse(partner_view.data['manual_assign_only'])

        secondary_view = self.secondary_api.get('/api/partner/bookings/available/')
        self.assertEqual(secondary_view.status_code, 200, secondary_view.data)
        self.assertEqual(secondary_view.data['results'], [])
        self.assertTrue(secondary_view.data['manual_assign_only'])
        self.assertTrue(secondary_view.data['message'])

    def test_badge_count_excludes_broadcast_for_secondary(self):
        self._broadcast_booking()

        partner_counts = self.partner_api.get('/api/partner/bookings/counts/')
        self.assertEqual(partner_counts.data['available'], 1)

        secondary_counts = self.secondary_api.get('/api/partner/bookings/counts/')
        self.assertEqual(secondary_counts.data['available'], 0)

    def test_secondary_cannot_accept_a_broadcast_booking(self):
        job = self._broadcast_booking()
        with self.assertRaises(PartnerBookingError) as ctx:
            partner_accept_booking(job, self.secondary_row)
        self.assertEqual(ctx.exception.code, 'manual_assign_only')

        job.refresh_from_db()
        self.assertIsNone(job.partner_id)
        self.assertEqual(job.status, JobCard.JobStatus.PENDING)

    def test_secondary_sees_and_accepts_a_job_assigned_by_staff(self):
        job = self._broadcast_booking()
        # Desk staff hand this one to the secondary technician.
        job.partner = self.secondary_row
        job.partner_status = JobCard.PartnerStatus.PENDING
        job.save(update_fields=['partner', 'partner_status'])

        view = self.secondary_api.get('/api/partner/bookings/available/')
        self.assertEqual([r['id'] for r in view.data['results']], [job.id])

        partner_accept_booking(job, self.secondary_row)
        job.refresh_from_db()
        self.assertEqual(job.partner_id, self.secondary_row.id)
        self.assertEqual(job.status, JobCard.JobStatus.ON_PROCESS)

    def test_pool_push_skips_secondary_technicians(self):
        from partner.notification_service import approved_partner_ids

        broadcast_ids = approved_partner_ids()
        self.assertIn(self.partner_row.id, broadcast_ids)
        self.assertNotIn(self.secondary_row.id, broadcast_ids)

        # A directed notification (staff picked this technician) still reaches them.
        directed = approved_partner_ids(technician_id=self.secondary_tech.id)
        self.assertEqual(directed, [self.secondary_row.id])

    def test_partner_and_salaried_dispatch_behaviour_is_unchanged(self):
        """Only the new type is gated; salaried keeps seeing the pool as before."""
        from partner.notification_service import approved_partner_ids

        job = self._broadcast_booking()
        _tech, salaried_api, salaried_row = self._make_tech(
            'Salaried Tech', '9000022223', Technician.TechnicianType.SALARIED
        )

        view = salaried_api.get('/api/partner/bookings/available/')
        self.assertIn(job.id, [r['id'] for r in view.data['results']])
        self.assertFalse(view.data['manual_assign_only'])
        self.assertIn(salaried_row.id, approved_partner_ids())
