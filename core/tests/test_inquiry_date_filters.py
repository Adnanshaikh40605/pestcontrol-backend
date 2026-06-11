"""Tests for inquiry date filtering and status counts."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import CRMInquiry, Inquiry


class InquiryDateFilterAPITest(APITestCase):
    def setUp(self):
        self.api_client = APIClient()
        self.user = User.objects.create_superuser(
            username='filtertest',
            email='filter@test.com',
            password='testpass123',
        )
        refresh = RefreshToken.for_user(self.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_month = today - timedelta(days=40)

        Inquiry.objects.create(
            name='Today Lead',
            mobile='9000000001',
            message='Test',
            service_interest='Pest Control',
            status='New',
        )
        old_lead = Inquiry.objects.create(
            name='Old Lead',
            mobile='9000000002',
            message='Test',
            service_interest='Pest Control',
            status='Contacted',
        )
        Inquiry.objects.filter(pk=old_lead.pk).update(
            created_at=timezone.make_aware(
                timezone.datetime.combine(last_month, timezone.datetime.min.time())
            )
        )

        CRMInquiry.objects.create(
            name='CRM Today',
            mobile='9000000003',
            location='Lonavala',
            pest_type='Cockroach',
            status='New',
            inquiry_date=today,
        )
        CRMInquiry.objects.create(
            name='CRM Old',
            mobile='9000000004',
            location='Mumbai',
            pest_type='Ants',
            status='Closed',
            inquiry_date=last_month,
        )

    def test_website_leads_date_range_and_status_counts(self):
        today = timezone.now().date().isoformat()
        response = self.api_client.get(
            '/api/v1/inquiries/',
            {'from': today, 'to': today},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status_counts']['all'], 1)
        self.assertEqual(response.data['status_counts']['New'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Today Lead')

    def test_website_leads_tab_counts_respect_date_filter(self):
        today = timezone.now().date().isoformat()
        response = self.api_client.get('/api/v1/inquiries/', {'from': today, 'to': today})
        counts = response.data['status_counts']
        self.assertEqual(counts['Contacted'], 0)
        self.assertEqual(counts['all'], 1)

    def test_crm_inquiries_filter_by_inquiry_date(self):
        today = timezone.now().date().isoformat()
        response = self.api_client.get(
            '/api/v1/crm-inquiries/',
            {'from': today, 'to': today},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status_counts']['all'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'CRM Today')

    def test_crm_inquiries_status_filter_with_date(self):
        today = timezone.now().date().isoformat()
        response = self.api_client.get(
            '/api/v1/crm-inquiries/',
            {'from': today, 'to': today, 'status': 'Closed'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['status_counts']['all'], 1)
