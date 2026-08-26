from django.test import TestCase
from rest_framework.test import APIClient

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

    def test_public_version_endpoint(self):
        response = self.client.get('/api/app/version/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['force_update'])
        self.assertEqual(data['minimum_supported_version'], '2.0.9')
        self.assertEqual(data['latest_version'], '2.0.9')
        self.assertIn('play.google.com', data['store_url'])
        self.assertIn('com.pestcontrol99.partner', data['store_url'])
