"""
API tests for Revenue Model v2 Phase 2 endpoints:
feature flags, participants, payout recalculate / hold / approve.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Client, JobCard, JobCardTechnicianParticipation, Technician
from partner.models import Partner, PartnerEarning


@override_settings(REVENUE_MODEL_V2=True)
class RevenueModelApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='rev_admin', password='pass1234')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.client_obj = Client.objects.create(full_name='Rev Client', mobile='9111111111')
        self.tech = Technician.objects.create(
            name='Partner Tech',
            mobile='9222222222',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        self.partner = Partner.objects.create(
            full_name='Partner Tech',
            mobile='9222222222',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        self.job = JobCard.objects.create(
            client=self.client_obj,
            service_type='General Pest',
            price='1000',
            total_amount=Decimal('1000.00'),
            technician=self.tech,
            partner=self.partner,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            technician_share_percent=Decimal('40.00'),
            company_share_percent=Decimal('60.00'),
            status=JobCard.JobStatus.DONE,
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )

    def test_feature_flags_requires_auth(self):
        anon = APIClient()
        res = anon.get('/api/v1/feature-flags/')
        self.assertIn(res.status_code, (401, 403))

    def test_feature_flags_returns_revenue_flag(self):
        res = self.api.get('/api/v1/feature-flags/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertTrue(res.data['REVENUE_MODEL_V2'])

    @override_settings(REVENUE_MODEL_V2=False)
    def test_feature_flags_false_when_disabled(self):
        res = self.api.get('/api/v1/feature-flags/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data['REVENUE_MODEL_V2'])

    def test_participants_crud(self):
        crew = Technician.objects.create(
            name='Crew Tech',
            mobile='9333333333',
            technician_type=Technician.TechnicianType.PARTNER,
        )
        list_res = self.api.get(f'/api/v1/jobcards/{self.job.id}/participants/')
        self.assertEqual(list_res.status_code, 200)
        self.assertEqual(list_res.data, [])

        add_res = self.api.post(
            f'/api/v1/jobcards/{self.job.id}/participants/',
            {'technician_id': crew.id, 'role': 'crew'},
            format='json',
        )
        self.assertEqual(add_res.status_code, 201, add_res.data)
        participant_id = add_res.data['id']
        self.assertEqual(add_res.data['technician'], crew.id)

        patch_res = self.api.patch(
            f'/api/v1/jobcards/{self.job.id}/participants/{participant_id}/',
            {'attendance_status': 'completed'},
            format='json',
        )
        self.assertEqual(patch_res.status_code, 200, patch_res.data)
        self.assertEqual(patch_res.data['attendance_status'], 'completed')

        del_res = self.api.delete(
            f'/api/v1/jobcards/{self.job.id}/participants/{participant_id}/'
        )
        self.assertEqual(del_res.status_code, 204)
        self.assertFalse(
            JobCardTechnicianParticipation.objects.filter(id=participant_id).exists()
        )

    def test_payout_recalculate_and_approve(self):
        recalc = self.api.post(f'/api/v1/jobcards/{self.job.id}/payout-recalculate/')
        self.assertEqual(recalc.status_code, 200, recalc.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_status, JobCard.PayoutStatus.PENDING)
        self.assertEqual(self.job.technician_pool_amount, Decimal('400.00'))
        self.assertEqual(PartnerEarning.objects.filter(job=self.job).count(), 1)

        hold = self.api.post(f'/api/v1/jobcards/{self.job.id}/payout-hold/')
        self.assertEqual(hold.status_code, 200, hold.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_status, JobCard.PayoutStatus.HELD)

        approve = self.api.post(f'/api/v1/jobcards/{self.job.id}/payout-approve/')
        self.assertEqual(approve.status_code, 200, approve.data)
        self.job.refresh_from_db()
        self.assertEqual(self.job.payout_status, JobCard.PayoutStatus.APPROVED)
        self.assertTrue(PartnerEarning.objects.get(job=self.job).is_approved)

    def test_legacy_exempt_cannot_recalculate(self):
        self.job.payout_status = JobCard.PayoutStatus.LEGACY_EXEMPT
        self.job.save(update_fields=['payout_status'])
        res = self.api.post(f'/api/v1/jobcards/{self.job.id}/payout-recalculate/')
        self.assertEqual(res.status_code, 400)

    def test_jobcard_serializer_exposes_revenue_fields(self):
        res = self.api.get(f'/api/v1/jobcards/{self.job.id}/')
        self.assertEqual(res.status_code, 200)
        for key in (
            'package_tier',
            'payment_model',
            'technician_share_percent',
            'company_share_percent',
            'planned_visit_count',
            'payout_status',
            'visit_payout_amount',
            'discount_amount',
        ):
            self.assertIn(key, res.data)

    def test_technician_serializer_exposes_type(self):
        res = self.api.get(f'/api/v1/technicians/{self.tech.id}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['technician_type'], 'partner')
        self.assertIn('presence_status', res.data)
