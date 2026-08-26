from django.test import TestCase
from rest_framework.test import APIClient

from core.customer_app_version import CustomerAppVersionConfig
from core.partner_app_version import PartnerAppVersionConfig
from core.version_utils import compare_versions, is_version_below


class VersionUtilsTests(TestCase):
    def test_compare_versions(self):
        self.assertEqual(compare_versions('2.0.7', '2.0.8'), -1)
        self.assertEqual(compare_versions('2.0.8', '2.0.8'), 0)
        self.assertEqual(compare_versions('2.0.9', '2.0.8'), 1)
        self.assertTrue(is_version_below('2.0.7+9', '2.0.8'))
        self.assertFalse(is_version_below('2.0.8+10', '2.0.8'))


class PartnerAppVersionAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        PartnerAppVersionConfig.objects.filter(pk=1).delete()
        PartnerAppVersionConfig.objects.create(
            pk=1,
            latest_version='2.0.9',
            minimum_supported_version='2.0.9',
            force_update=True,
            update_title='Please update the app.',
            update_message='Please update the app.',
        )
        CustomerAppVersionConfig.objects.filter(pk=1).delete()
        CustomerAppVersionConfig.objects.create(
            pk=1,
            latest_version='1.0.4',
            minimum_supported_version='1.0.4',
            force_update=True,
            update_title='Update required',
            update_message='Please update Pest Control 99 to continue.',
        )

    def test_public_version_endpoint_defaults_to_partner(self):
        response = self.client.get('/api/app/version/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('app'), 'partner')
        self.assertTrue(data['force_update'])
        self.assertEqual(data['minimum_supported_version'], '2.0.9')
        self.assertEqual(data['latest_version'], '2.0.9')
        self.assertIn('play.google.com', data['store_url'])
        self.assertIn('com.pestcontrol99.partner', data['store_url'])

    def test_public_customer_version_endpoint(self):
        response = self.client.get('/api/app/version/?app=customer')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('app'), 'customer')
        self.assertTrue(data['force_update'])
        self.assertEqual(data['latest_version'], '1.0.4')
        self.assertIn('pest_99_customer_app', data['store_url'])
