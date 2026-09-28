"""Technician create/update API tests (Partner vs Salaried)."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Technician


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianCreateUpdateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tech_admin',
            password='pass1234',
            is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_create_partner_technician(self):
        res = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Partner Test Tech',
                'mobile': '9111000001',
                'age': 27,
                'service_area': 'Kothrud',
                'city': 'Pune',
                'is_active': True,
                'technician_type': 'partner',
                'branch': 'Pune HQ',
                'presence_status': 'active',
                'security_deposit_status': 'collected',
                'security_deposit_amount': '2500',
                'aadhaar': '111122223333',
                'pan': 'ABCDE1234F',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['technician_type'], 'partner')
        self.assertEqual(res.data['presence_status'], 'active')
        self.assertEqual(res.data['branch'], 'Pune HQ')
        self.assertEqual(res.data['mobile'], '9111000001')

        detail = self.api.get(f"/api/v1/technicians/{res.data['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['technician_type'], 'partner')
        self.assertEqual(detail.data['name'], 'Partner Test Tech')

    def test_create_salaried_technician(self):
        res = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Salaried Test Tech',
                'mobile': '9111000002',
                'city': 'Mumbai',
                'is_active': True,
                'technician_type': 'salaried',
                'presence_status': 'active',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['technician_type'], 'salaried')
        tech = Technician.objects.get(id=res.data['id'])
        self.assertEqual(tech.technician_type, Technician.TechnicianType.SALARIED)

    def test_update_technician_type_and_presence(self):
        create = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Switchable Tech',
                'mobile': '9111000003',
                'technician_type': 'partner',
                'presence_status': 'active',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.data)
        tech_id = create.data['id']

        patch = self.api.patch(
            f'/api/v1/technicians/{tech_id}/',
            {
                'technician_type': 'salaried',
                'presence_status': 'on_leave',
                'branch': 'Andheri',
            },
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        self.assertEqual(patch.data['technician_type'], 'salaried')
        self.assertEqual(patch.data['presence_status'], 'on_leave')
        self.assertEqual(patch.data['branch'], 'Andheri')

    def test_duplicate_mobile_rejected(self):
        first = self.api.post(
            '/api/v1/technicians/',
            {'name': 'One', 'mobile': '9111000004', 'is_active': True},
            format='json',
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.api.post(
            '/api/v1/technicians/',
            {'name': 'Two', 'mobile': '9111000004', 'is_active': True},
            format='json',
        )
        self.assertEqual(second.status_code, 400, second.data)

    def test_address_location_and_alt_mobile_persist(self):
        res = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Based Tech',
                'mobile': '9111000091',
                'alternative_mobile': '92220 00091',
                'address': '  Flat 4, Lane 2, Baner  ',
                'location': '  Baner, Pune  ',
                'accepts_one_time_jobs': True,
                'accepts_amc_jobs': False,
                'service_area': 'Kothrud',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['alternative_mobile'], '9222000091')
        self.assertEqual(res.data['address'], 'Flat 4, Lane 2, Baner')
        self.assertEqual(res.data['location'], 'Baner, Pune')
        self.assertEqual(res.data['service_area'], 'Kothrud')
        self.assertTrue(res.data['accepts_one_time_jobs'])
        self.assertFalse(res.data['accepts_amc_jobs'])
        self.assertTrue(res.data['accepts_standard_service'])
        self.assertTrue(res.data['accepts_premium_service'])

        tech = Technician.objects.get(id=res.data['id'])
        self.assertEqual(tech.address, 'Flat 4, Lane 2, Baner')
        self.assertEqual(tech.location, 'Baner, Pune')
        self.assertEqual(tech.alternative_mobile, '9222000091')

        patch = self.api.patch(
            f"/api/v1/technicians/{tech.id}/",
            {
                'address': 'Shop 12, FC Road',
                'location': 'Shivajinagar, Pune',
                'alternative_mobile': '',
            },
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        self.assertEqual(patch.data['address'], 'Shop 12, FC Road')
        self.assertEqual(patch.data['location'], 'Shivajinagar, Pune')
        self.assertIsNone(patch.data['alternative_mobile'])
        self.assertFalse(patch.data['accepts_amc_jobs'])
        self.assertEqual(patch.data['service_area'], 'Kothrud')
        self.assertEqual(patch.data['mobile'], '9111000091')

    def test_address_and_location_blank_by_default(self):
        res = self.api.post(
            '/api/v1/technicians/',
            {'name': 'No Address Tech', 'mobile': '9111000092', 'is_active': True},
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['address'], '')
        self.assertEqual(res.data['location'], '')
        self.assertIsNone(res.data['alternative_mobile'])
        self.assertTrue(res.data['accepts_one_time_jobs'])
        self.assertTrue(res.data['accepts_amc_jobs'])
        self.assertTrue(res.data['accepts_standard_service'])
        self.assertTrue(res.data['accepts_premium_service'])

        stored = Technician.objects.get(id=res.data['id'])
        self.assertEqual(stored.address, '')
        self.assertEqual(stored.location, '')

    def test_short_alternative_mobile_rejected(self):
        res = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Bad Alt',
                'mobile': '9111000093',
                'alternative_mobile': '12345',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertIn('alternative_mobile', res.data)
