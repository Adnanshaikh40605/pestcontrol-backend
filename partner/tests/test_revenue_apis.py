"""
Phase 4 partner app APIs: presence, leave, suspended accept gate, earnings extras.
"""
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from core.models import Client, JobCard, Technician, TechnicianSettlement
from partner.models import Partner, PartnerEarning, PartnerLeaveRequest
from partner.utils import generate_partner_tokens


def _selfie_file():
    buf = BytesIO()
    Image.new('RGB', (40, 40), color=(10, 20, 30)).save(buf, format='JPEG')
    return SimpleUploadedFile('selfie.jpg', buf.getvalue(), content_type='image/jpeg')


@override_settings(REVENUE_MODEL_V2=True)
class PartnerRevenueApiTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(full_name='P4 Client', mobile='9444444444')
        self.tech = Technician.objects.create(
            name='P4 Tech',
            mobile='9555555555',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
        )
        self.partner = Partner.objects.create(
            full_name='P4 Tech',
            mobile='9555555555',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        tokens = generate_partner_tokens(self.partner)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_get_presence(self):
        res = self.api.get('/api/partner/presence/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['presence_status'], 'online')
        self.assertFalse(res.data['is_suspended'])
        self.assertTrue(res.data['technician_linked'])

    def test_set_presence_online_offline(self):
        res = self.api.post('/api/partner/presence/', {'presence_status': 'offline'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.OFFLINE)

        res = self.api.post('/api/partner/presence/', {'presence_status': 'online'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.ONLINE)

    def test_cannot_self_set_while_busy(self):
        self.tech.presence_status = Technician.PresenceStatus.BUSY
        self.tech.save(update_fields=['presence_status', 'updated_at'])
        res = self.api.post('/api/partner/presence/', {'presence_status': 'offline'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['code'], 'presence_locked')

    def test_pool_booking_detail_visible(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            sent_to_app_at=timezone.now(),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.get(f'/api/partner/bookings/{job.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['id'], job.id)

    def test_suspended_cannot_change_presence(self):
        self.tech.presence_status = Technician.PresenceStatus.SUSPENDED
        self.tech.suspend_reason = 'Policy breach'
        self.tech.save(update_fields=['presence_status', 'suspend_reason', 'updated_at'])
        res = self.api.post('/api/partner/presence/', {'presence_status': 'online'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(res.data['code'], 'suspended')

    def test_suspended_blocks_accept(self):
        self.tech.presence_status = Technician.PresenceStatus.SUSPENDED
        self.tech.suspend_reason = 'Docs pending'
        self.tech.save(update_fields=['presence_status', 'suspend_reason', 'updated_at'])
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            sent_to_app_at=timezone.now(),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.post(f'/api/partner/bookings/{job.id}/accept/')
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data.get('code'), 'suspended')

    def test_leave_request_create_list_cancel(self):
        start = date.today() + timedelta(days=2)
        end = start + timedelta(days=3)
        create = self.api.post(
            '/api/partner/leave-requests/',
            {'start_date': str(start), 'end_date': str(end), 'reason': 'Family'},
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.data)
        leave_id = create.data['id']
        self.assertEqual(create.data['status'], 'pending')

        listed = self.api.get('/api/partner/leave-requests/')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data['results']), 1)

        cancel = self.api.post(f'/api/partner/leave-requests/{leave_id}/cancel/')
        self.assertEqual(cancel.status_code, 200, cancel.data)
        self.assertEqual(cancel.data['status'], 'cancelled')

    def test_leave_rejects_inverted_dates(self):
        start = date.today() + timedelta(days=5)
        end = start - timedelta(days=1)
        res = self.api.post(
            '/api/partner/leave-requests/',
            {'start_date': str(start), 'end_date': str(end)},
            format='json',
        )
        self.assertEqual(res.status_code, 400)

    def test_earnings_include_settlement_fields(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            technician=self.tech,
            partner=self.partner,
            status=JobCard.JobStatus.DONE,
            partner_status=JobCard.PartnerStatus.COMPLETED,
            completed_at=timezone.now(),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.PENDING,
            visit_payout_amount=Decimal('400.00'),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        PartnerEarning.objects.create(
            partner=self.partner,
            job=job,
            amount=Decimal('400.00'),
            is_approved=True,
        )
        res = self.api.get('/api/partner/earnings/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('approved_earnings', res.data)
        row = res.data['results'][0]
        self.assertEqual(row['payout_status'], JobCard.PayoutStatus.PENDING)
        self.assertEqual(Decimal(row['visit_payout_amount']), Decimal('400.00'))
        self.assertIsNone(row['settlement_status'])

    def test_settlements_list_approved_only(self):
        TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            status=TechnicianSettlement.Status.DRAFT,
            net_amount=Decimal('100.00'),
        )
        paid = TechnicianSettlement.objects.create(
            technician=self.tech,
            partner=self.partner,
            period_start=date.today() - timedelta(days=14),
            period_end=date.today() - timedelta(days=8),
            status=TechnicianSettlement.Status.PAID,
            net_amount=Decimal('500.00'),
        )
        res = self.api.get('/api/partner/settlements/')
        self.assertEqual(res.status_code, 200, res.data)
        ids = [r['id'] for r in res.data['results']]
        self.assertIn(paid.id, ids)
        self.assertEqual(len(ids), 1)

    def test_accept_sets_busy_presence(self):
        job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            sent_to_app_at=timezone.now(),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.post(f'/api/partner/bookings/{job.id}/accept/')
        self.assertEqual(res.status_code, 200, res.data)
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.BUSY)

    def test_suspended_available_bookings_empty(self):
        self.tech.presence_status = Technician.PresenceStatus.SUSPENDED
        self.tech.suspend_reason = 'KYC incomplete'
        self.tech.save(update_fields=['presence_status', 'suspend_reason', 'updated_at'])
        JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            sent_to_app_at=timezone.now(),
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        res = self.api.get('/api/partner/bookings/available/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['is_suspended'])
        self.assertEqual(res.data['count'], 0)
        self.assertEqual(res.data['results'], [])
        self.assertIn('KYC', res.data.get('suspend_reason', ''))
