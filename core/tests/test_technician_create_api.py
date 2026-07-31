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
                'presence_status': 'online',
                'security_deposit_status': 'collected',
                'security_deposit_amount': '2500',
                'aadhaar': '111122223333',
                'pan': 'ABCDE1234F',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['technician_type'], 'partner')
        self.assertEqual(res.data['presence_status'], 'online')
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
                'presence_status': 'offline',
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
                'presence_status': 'offline',
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
