"""
Bug Condition Exploration Test for Technician Active Endpoint

This test is designed to FAIL on unfixed code to confirm the bug exists.
The bug: TechnicianViewSet.active() method is missing the required 'request' parameter.

**Validates: Requirements 1.1, 1.2, 1.3**
"""
import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Technician, JobCard


class TechnicianActiveEndpointBugConditionTest(TestCase):
    """
    Bug Condition Exploration Test - Property 1: Bug Condition
    
    This test MUST FAIL on unfixed code with TypeError about missing positional argument.
    When it fails, it confirms the bug exists.
    
    After the fix is implemented, this same test will pass, confirming the expected behavior.
    
    This uses a property-based testing approach by testing multiple scenarios with
    different combinations of active and inactive technicians.
    """
    
    def setUp(self):
        """Set up test environment with authentication."""
        self.client = APIClient()
        
        # Create test user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def _test_active_endpoint_with_technicians(self, num_active, num_inactive):
        """
        Helper method to test the active endpoint with different combinations of technicians.
        
        This implements property-based testing logic: for any combination of active and
        inactive technicians, the endpoint should return 200 OK with only active technicians.
        """
        # Clean up any existing technicians from previous test runs
        Technician.objects.all().delete()
        
        # Create active technicians
        active_technicians = []
        for i in range(num_active):
            tech = Technician.objects.create(
                name=f"Active Tech {i}",
                mobile=f"90000{i:05d}",
                age=25 + i,
                is_active=True
            )
            active_technicians.append(tech)
        
        # Create inactive technicians
        for i in range(num_inactive):
            Technician.objects.create(
                name=f"Inactive Tech {i}",
                mobile=f"80000{i:05d}",
                age=30 + i,
                is_active=False
            )
        
        # Make GET request to /api/technicians/active/
        url = reverse('technician-active')
        response = self.client.get(url)
        
        # ASSERTION 1: Status code should be 200 OK
        # On unfixed code, this will fail with 500 Internal Server Error
        self.assertEqual(
            response.status_code, 
            status.HTTP_200_OK,
            f"Expected 200 OK but got {response.status_code}. "
            f"On unfixed code, this fails with 500 due to missing 'request' parameter."
        )
        
        # ASSERTION 2: Response should be valid JSON array
        try:
            data = response.json()
            self.assertIsInstance(data, list, "Response should be a JSON array")
        except json.JSONDecodeError:
            self.fail("Response is not valid JSON")
        
        # ASSERTION 3: Response should contain only active technicians
        self.assertEqual(
            len(data), 
            num_active,
            f"Expected {num_active} active technicians but got {len(data)}"
        )
        
        # ASSERTION 4: All returned technicians should have is_active == True
        for tech_data in data:
            self.assertTrue(
                tech_data.get('is_active', False),
                f"Technician {tech_data.get('name')} should be active but is_active={tech_data.get('is_active')}"
            )
        
        # ASSERTION 5: Verify expected fields are present
        if num_active > 0:
            expected_fields = {'id', 'name', 'mobile', 'alternative_mobile', 'age', 'is_active', 'active_jobs'}
            actual_fields = set(data[0].keys())
            self.assertTrue(
                expected_fields.issubset(actual_fields),
                f"Response missing expected fields. Expected: {expected_fields}, Got: {actual_fields}"
            )
    
    def test_property_no_technicians(self):
        """Property test: 0 active, 0 inactive technicians"""
        self._test_active_endpoint_with_technicians(0, 0)
    
    def test_property_only_active_technicians(self):
        """Property test: Multiple active, 0 inactive technicians"""
        self._test_active_endpoint_with_technicians(5, 0)
    
    def test_property_only_inactive_technicians(self):
        """Property test: 0 active, multiple inactive technicians"""
        self._test_active_endpoint_with_technicians(0, 5)
    
    def test_property_mixed_technicians_small(self):
        """Property test: Small mix of active and inactive technicians"""
        self._test_active_endpoint_with_technicians(2, 3)
    
    def test_property_mixed_technicians_medium(self):
        """Property test: Medium mix of active and inactive technicians"""
        self._test_active_endpoint_with_technicians(5, 5)
    
    def test_property_mixed_technicians_large(self):
        """Property test: Large mix of active and inactive technicians"""
        self._test_active_endpoint_with_technicians(10, 10)
    
    def test_property_many_active_few_inactive(self):
        """Property test: Many active, few inactive technicians"""
        self._test_active_endpoint_with_technicians(10, 2)
    
    def test_property_few_active_many_inactive(self):
        """Property test: Few active, many inactive technicians"""
        self._test_active_endpoint_with_technicians(2, 10)


class TechnicianActiveEndpointUnitTest(TestCase):
    """
    Unit test for the active endpoint - simpler test cases for specific scenarios.
    """
    
    def setUp(self):
        """Set up test environment with authentication."""
        self.client = APIClient()
        
        # Create test user for authentication
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_active_endpoint_basic_request(self):
        """
        Basic test: GET request to /api/technicians/active/ should return 200 OK.
        
        **Validates: Requirements 1.1, 1.2**
        
        EXPECTED ON UNFIXED CODE: 500 Internal Server Error
        EXPECTED ON FIXED CODE: 200 OK
        """
        url = reverse('technician-active')
        response = self.client.get(url)
        
        # This assertion will fail on unfixed code with 500 error
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_active_endpoint_returns_empty_array_when_no_active_technicians(self):
        """
        Edge case: When no active technicians exist, should return empty array.
        
        **Validates: Requirements 2.1, 2.2**
        
        EXPECTED ON UNFIXED CODE: 500 Internal Server Error
        EXPECTED ON FIXED CODE: 200 OK with empty array []
        """
        # Ensure no active technicians exist
        Technician.objects.all().delete()
        
        url = reverse('technician-active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)
    
    def test_active_endpoint_filters_out_inactive_technicians(self):
        """
        Test that inactive technicians are not included in the response.
        
        **Validates: Requirements 2.2, 2.3**
        
        EXPECTED ON UNFIXED CODE: 500 Internal Server Error
        EXPECTED ON FIXED CODE: 200 OK with only active technicians
        """
        # Clean up
        Technician.objects.all().delete()
        
        # Create mix of active and inactive technicians
        active_tech = Technician.objects.create(
            name="Active Technician",
            mobile="9000000001",
            age=30,
            is_active=True
        )
        
        inactive_tech = Technician.objects.create(
            name="Inactive Technician",
            mobile="9000000002",
            age=35,
            is_active=False
        )
        
        url = reverse('technician-active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        # Should only return 1 technician (the active one)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], active_tech.id)
        self.assertTrue(data[0]['is_active'])
    
    def test_active_endpoint_includes_active_jobs_count(self):
        """
        Test that the response includes active_jobs count annotation.
        
        **Validates: Requirements 2.3**
        
        EXPECTED ON UNFIXED CODE: 500 Internal Server Error
        EXPECTED ON FIXED CODE: 200 OK with active_jobs field
        """
        # Clean up
        Technician.objects.all().delete()
        
        # Create active technician
        tech = Technician.objects.create(
            name="Test Technician",
            mobile="9000000001",
            age=30,
            is_active=True
        )
        
        url = reverse('technician-active')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        
        self.assertEqual(len(data), 1)
        self.assertIn('active_jobs', data[0])
        # Should be 0 since we haven't created any job cards
        self.assertEqual(data[0]['active_jobs'], 0)
