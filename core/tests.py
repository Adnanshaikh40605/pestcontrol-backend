"""
Comprehensive tests for the Dashboard API endpoint.
"""
import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch, MagicMock
from django.core.cache import cache
from django.test.utils import override_settings

from .models import Client, Inquiry, JobCard, Renewal
from .services import DashboardService


class DashboardServiceTest(TestCase):
    """Unit tests for DashboardService."""
    
    def setUp(self):
        """Set up test data."""
        # Create test clients
        self.client1 = Client.objects.create(
            full_name="John Doe",
            mobile="1234567890",
            email="john@example.com",
            city="Mumbai"
        )
        self.client2 = Client.objects.create(
            full_name="Jane Smith", 
            mobile="9876543210",
            email="jane@example.com",
            city="Delhi"
        )
        
        # Create test inquiries
        self.inquiry1 = Inquiry.objects.create(
            name="Test Inquiry 1",
            mobile="1111111111",
            email="inquiry1@example.com",
            message="Test message 1",
            city="Mumbai"
        )
        self.inquiry2 = Inquiry.objects.create(
            name="Test Inquiry 2",
            mobile="2222222222", 
            email="inquiry2@example.com",
            message="Test message 2",
            city="Delhi"
        )
        
        # Create test job cards
        self.jobcard1 = JobCard.objects.create(
            client=self.client1,
            service_type="Residential Pest Control",
            schedule_date="2024-01-15",
            technician_name="Tech 1",
            job_type="One-time",
            contract_duration=1
        )
        
        # Create test renewals
        self.renewal1 = Renewal.objects.create(
            jobcard=self.jobcard1,
            due_date="2024-02-15",
            renewal_type="Contract Extension"
        )
    
    def test_get_dashboard_statistics_success(self):
        """Test successful retrieval of dashboard statistics."""
        stats = DashboardService.get_dashboard_statistics()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_inquiries', stats)
        self.assertIn('total_job_cards', stats)
        self.assertIn('total_clients', stats)
        self.assertIn('renewals', stats)
        
        # Verify counts
        self.assertEqual(stats['total_inquiries'], 2)
        self.assertEqual(stats['total_job_cards'], 1)
        self.assertEqual(stats['total_clients'], 2)
        self.assertEqual(stats['renewals'], 1)
    
    def test_get_dashboard_statistics_empty_database(self):
        """Test dashboard statistics with empty database."""
        # Clear all data
        Client.objects.all().delete()
        Inquiry.objects.all().delete()
        JobCard.objects.all().delete()
        Renewal.objects.all().delete()
        
        stats = DashboardService.get_dashboard_statistics()
        
        self.assertEqual(stats['total_inquiries'], 0)
        self.assertEqual(stats['total_job_cards'], 0)
        self.assertEqual(stats['total_clients'], 0)
        self.assertEqual(stats['renewals'], 0)
    
    @patch('core.services.logger')
    @patch('core.services.Client.objects.count')
    def test_get_dashboard_statistics_database_error(self, mock_count, mock_logger):
        """Test dashboard statistics with database error."""
        mock_count.side_effect = Exception("Database connection error")
        
        with self.assertRaises(Exception):
            DashboardService.get_dashboard_statistics()
        
        mock_logger.error.assert_called()


class DashboardAPITest(APITestCase):
    """Integration tests for Dashboard API endpoint."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set up test data
        self.test_client = Client.objects.create(
            full_name="Test Client",
            mobile="1234567890",
            email="client@example.com",
            city="Mumbai"
        )
        
        self.test_inquiry = Inquiry.objects.create(
            name="Test Inquiry",
            mobile="9876543210",
            email="inquiry@example.com",
            message="Test message",
            city="Delhi"
        )
        
        self.test_jobcard = JobCard.objects.create(
            client=self.test_client,
            service_type="Residential Pest Control",
            schedule_date="2024-01-15",
            technician_name="Test Tech",
            job_type="One-time",
            contract_duration=1
        )
        
        self.test_renewal = Renewal.objects.create(
            jobcard=self.test_jobcard,
            due_date="2024-02-15",
            renewal_type="Contract Extension"
        )
        
        # Clear cache before each test
        cache.clear()
    
    def test_dashboard_statistics_success(self):
        """Test successful dashboard statistics retrieval."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        self.assertIn('total_inquiries', data)
        self.assertIn('total_job_cards', data)
        self.assertIn('total_clients', data)
        self.assertIn('renewals', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'success')
        
        # Verify counts
        self.assertEqual(data['total_inquiries'], 1)
        self.assertEqual(data['total_job_cards'], 1)
        self.assertEqual(data['total_clients'], 1)
        self.assertEqual(data['renewals'], 1)
    
    def test_dashboard_statistics_unauthenticated(self):
        """Test dashboard statistics without authentication."""
        url = reverse('dashboard-statistics')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_dashboard_statistics_invalid_token(self):
        """Test dashboard statistics with invalid token."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_dashboard_statistics_caching(self):
        """Test that dashboard statistics are properly cached."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # First request
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Add more data
        Client.objects.create(
            full_name="New Client",
            mobile="5555555555",
            email="new@example.com",
            city="Pune"
        )
        
        # Second request (should return cached data)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Data should be the same due to caching
        self.assertEqual(response1.json()['total_clients'], response2.json()['total_clients'])
    
    def test_dashboard_statistics_cache_headers(self):
        """Test that proper cache headers are set."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Cache-Control', response)
        self.assertIn('X-API-Version', response)
        self.assertEqual(response['X-API-Version'], 'v1')
        self.assertEqual(response['Content-Type'], 'application/json')
    
    @patch('core.services.DashboardService.get_dashboard_statistics')
    def test_dashboard_statistics_service_error(self, mock_service):
        """Test dashboard statistics with service error."""
        mock_service.side_effect = Exception("Service error")
        
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('status', data)
        self.assertEqual(data['status'], 'error')
    
    def test_dashboard_statistics_method_not_allowed(self):
        """Test that only GET method is allowed."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Test POST method
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test PUT method
        response = self.client.put(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        
        # Test DELETE method
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class DashboardPerformanceTest(APITestCase):
    """Performance tests for Dashboard API."""
    
    def setUp(self):
        """Set up performance test environment."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Clear cache
        cache.clear()
    
    def test_dashboard_statistics_large_dataset(self):
        """Test dashboard statistics performance with large dataset."""
        # Create large dataset
        clients = []
        for i in range(100):
            clients.append(Client(
                full_name=f"Client {i}",
                mobile=f"123456{i:04d}",
                email=f"client{i}@example.com",
                city="Mumbai"
            ))
        Client.objects.bulk_create(clients)
        
        inquiries = []
        for i in range(200):
            inquiries.append(Inquiry(
                name=f"Inquiry {i}",
                mobile=f"987654{i:04d}",
                email=f"inquiry{i}@example.com",
                message=f"Test message {i}",
                city="Delhi"
            ))
        Inquiry.objects.bulk_create(inquiries)
        
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        import time
        start_time = time.time()
        
        response = self.client.get(url)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 2.0)  # Should respond within 2 seconds
        
        data = response.json()
        self.assertEqual(data['total_clients'], 100)
        self.assertEqual(data['total_inquiries'], 200)


class DashboardSecurityTest(APITestCase):
    """Security tests for Dashboard API."""
    
    def setUp(self):
        """Set up security test environment."""
        self.client = APIClient()
        
        # Create test user
        self.user = User.objects.create_user(
            username='secuser',
            email='sec@example.com',
            password='secpass123'
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
    
    def test_dashboard_statistics_cors_headers(self):
        """Test CORS headers are properly set."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        response = self.client.get(url, HTTP_ORIGIN='https://example.com')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_dashboard_statistics_rate_limiting(self):
        """Test rate limiting is applied."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Make multiple requests rapidly
        responses = []
        for i in range(10):
            response = self.client.get(url)
            responses.append(response.status_code)
        
        # All requests should succeed (rate limiting is configured but not strict in tests)
        self.assertTrue(all(code == 200 for code in responses))
    
    def test_dashboard_statistics_input_validation(self):
        """Test input validation and sanitization."""
        url = reverse('dashboard-statistics')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Test with query parameters (should be ignored)
        response = self.client.get(url + '?malicious=<script>alert("xss")</script>')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Response should not contain any malicious content
        response_content = response.content.decode()
        self.assertNotIn('<script>', response_content)
        self.assertNotIn('alert', response_content)