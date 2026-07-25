from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.ecard_tracking import detect_device_type, detect_traffic_source
from core.models import ECardVisit


class ECardTrackingHelpersTests(TestCase):
    def test_device_detection(self):
        self.assertEqual(detect_device_type('Mozilla/5.0 (iPhone; CPU iPhone OS)'), 'Mobile')
        self.assertEqual(detect_device_type('Mozilla/5.0 (iPad; CPU OS)'), 'Tablet')
        self.assertEqual(detect_device_type('Mozilla/5.0 (Windows NT 10.0) Chrome'), 'Desktop')

    def test_traffic_sources(self):
        self.assertEqual(detect_traffic_source('https://wa.me/91', '', ''), 'WhatsApp')
        self.assertEqual(detect_traffic_source('', 'instagram', ''), 'Instagram')
        self.assertEqual(detect_traffic_source('https://www.google.com/', '', ''), 'Google Search')
        self.assertEqual(detect_traffic_source('', '', ''), 'Direct Link')
        self.assertEqual(
            detect_traffic_source('https://example.com/page', '', ''),
            'Another Website (Referral)',
        )


class ECardTrackingAPITests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user('ecardcrm', password='pass', is_staff=True)

    def test_public_track_and_crm_list(self):
        track = self.api.post(
            '/api/e-card/track/',
            {
                'referrer': 'https://l.facebook.com/',
                'landing_url': 'https://www.pestcontrol99.com/e-card/',
                'user_agent': 'Mozilla/5.0 (iPhone)',
            },
            format='json',
        )
        self.assertEqual(track.status_code, 201, track.data)
        self.assertEqual(track.data['device_type'], 'Mobile')
        self.assertEqual(track.data['traffic_source'], 'Facebook')
        self.assertIn('visited_at', track.data)
        self.assertEqual(ECardVisit.objects.count(), 1)

        denied = self.api.get('/api/e-card/tracking/')
        self.assertIn(denied.status_code, (401, 403))

        self.api.force_authenticate(user=self.user)
        listing = self.api.get('/api/e-card/tracking/')
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data['total_visitors'], 1)
        self.assertEqual(listing.data['today_visitors'], 1)
        self.assertEqual(len(listing.data['results']), 1)
        row = listing.data['results'][0]
        self.assertEqual(set(row.keys()), {'city', 'device_type', 'traffic_source', 'visited_at'})
