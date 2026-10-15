"""DeepCleaning99 master rates: public catalog and CRM add / update / delete."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import DeepCleaningRate


class DeepCleaningRateMasterTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='dc-rates',
            password='pass12345',
            is_staff=True,
        )

    def test_public_catalog_matches_launch_sheet(self):
        res = self.client.get('/api/deepcleaning-rates/catalog/')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        rates = {row['id']: row for row in res.data['rates']}
        self.assertEqual(len(rates), 46)
        self.assertEqual(rates['R2']['base'], 3499)
        self.assertEqual(rates['R2']['package'], 'Furnished 1BHK up to 600 sq ft')
        self.assertEqual(rates['C17']['base'], 21000)
        amc = {row['id']: row for row in res.data['amc']}
        self.assertEqual(amc['R2']['annual'], 6648)
        self.assertEqual(amc['R2']['perVisit'], 3324)
        self.assertEqual(amc['C2']['visits'], 12)
        self.assertIn('Full Home Deep Cleaning', res.data['services'])

    def test_anonymous_cannot_change_rates(self):
        res = self.client.post(
            '/api/deepcleaning-rates/',
            {'code': 'R99', 'segment': 'Residential', 'service': 'Sofa Cleaning', 'package_name': 'Extra seat'},
            format='json',
        )
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_staff_can_add_update_and_delete(self):
        self.client.force_authenticate(user=self.staff)
        created = self.client.post(
            '/api/deepcleaning-rates/',
            {
                'code': 'r99',
                'segment': 'Residential',
                'service': 'Sofa Cleaning',
                'package_name': 'Loose cushion',
                'billing_unit': 'cushion',
                'example_qty': 1,
                'rate_per_unit': 199,
                'min_charge': 199,
                'job_amount': 199,
                'technicians': 1,
                'on_site_hours': '0.5',
                'scope_note': 'One loose cushion',
                'amc_visits': 2,
                'amc_discount': '0.0500',
                'amc_per_visit': 189,
                'amc_annual': 378,
                'amc_interval': 'Every 6 months',
                'is_active': True,
                'sort_order': 99,
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data['code'], 'R99')
        rate_id = created.data['id']

        updated = self.client.patch(
            f'/api/deepcleaning-rates/{rate_id}/',
            {'job_amount': 249, 'is_active': False},
            format='json',
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertEqual(str(updated.data['job_amount']), '249.00')

        catalog = self.client.get('/api/deepcleaning-rates/catalog/')
        codes = [row['id'] for row in catalog.data['rates']]
        self.assertNotIn('R99', codes)

        deleted = self.client.delete(f'/api/deepcleaning-rates/{rate_id}/')
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeepCleaningRate.objects.filter(code='R99').exists())
        self.assertEqual(DeepCleaningRate.objects.filter(code='R2').count(), 1)
