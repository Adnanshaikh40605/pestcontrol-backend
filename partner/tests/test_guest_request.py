"""Partner guest-request / refer-client API."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import CRMInquiry, Technician
from partner.models import Partner, PartnerReferral
from partner.utils import generate_partner_tokens


@override_settings(REVENUE_MODEL_V2=True)
class GuestRequestAPITests(TestCase):
    def setUp(self):
        self.tech = Technician.objects.create(
            name='Guest Tech',
            mobile='9333000001',
            technician_type=Technician.TechnicianType.PARTNER,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Guest Tech',
            mobile='9333000001',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        tokens = generate_partner_tokens(self.partner)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def test_guest_request_path_defaults_to_guest(self):
        res = self.api.post(
            '/api/partner/guest-request/',
            {
                'client_name': 'Walk-in Guest',
                'mobile': '9888777666',
                'area': 'Andheri',
                'service_type': 'Bed Bug Control',
                'preferred_date': '2026-09-25',
                'notes': 'Evening preferred',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['request_type'], 'guest_request')
        self.assertIn('Guest request', res.data['message'])
        inquiry = CRMInquiry.objects.get(mobile='9888777666')
        self.assertEqual(inquiry.pest_type, 'Bed Bug Control')
        self.assertIn('Guest request', inquiry.remark)
        self.assertTrue(PartnerReferral.objects.filter(mobile='9888777666').exists())

    def test_refer_client_still_defaults_to_referral(self):
        res = self.api.post(
            '/api/partner/refer-client/',
            {
                'client_name': 'Referral Client',
                'mobile': '9888777555',
                'area': 'Bandra',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['request_type'], 'referral')
        inquiry = CRMInquiry.objects.get(mobile='9888777555')
        self.assertEqual(inquiry.pest_type, 'Partner Referral')
