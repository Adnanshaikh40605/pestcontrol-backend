#!/usr/bin/env python
"""
Test script to verify the inquiry conversion fix.
Run this after starting your Django server to test the fix.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api"
INQUIRY_ID = 3  # The inquiry ID from your error

def test_client_exists_check():
    """Test the new check_client_exists endpoint."""
    print("Testing client existence check...")
    
    url = f"{BASE_URL}/inquiries/{INQUIRY_ID}/check_client_exists/"
    response = requests.get(url)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def test_inquiry_conversion():
    """Test the inquiry conversion with the fix."""
    print("\nTesting inquiry conversion...")
    
    url = f"{BASE_URL}/inquiries/{INQUIRY_ID}/convert/"
    data = {
        "schedule_date": "2025-01-15",
        "technician_name": "Test Technician",
        "price_subtotal": 500.00,
        "tax_percent": 18
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Success! Job card created: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_with_existing_client():
    """Test conversion by specifying an existing client ID."""
    print("\nTesting conversion with existing client...")
    
    # First, get the inquiry to see its mobile number
    inquiry_url = f"{BASE_URL}/inquiries/{INQUIRY_ID}/"
    inquiry_response = requests.get(inquiry_url)
    
    if inquiry_response.status_code != 200:
        print(f"Could not get inquiry: {inquiry_response.text}")
        return False
    
    inquiry_data = inquiry_response.json()
    mobile = inquiry_data.get('mobile')
    
    # Find existing client with this mobile
    clients_url = f"{BASE_URL}/clients/"
    clients_response = requests.get(clients_url, params={'search': mobile})
    
    if clients_response.status_code != 200:
        print(f"Could not search clients: {clients_response.text}")
        return False
    
    clients_data = clients_response.json()
    if clients_data.get('results'):
        existing_client = clients_data['results'][0]
        client_id = existing_client['id']
        
        print(f"Found existing client: {existing_client['full_name']} (ID: {client_id})")
        
        # Try conversion with existing client
        url = f"{BASE_URL}/inquiries/{INQUIRY_ID}/convert/"
        data = {
            "client_id": client_id,
            "schedule_date": "2025-01-15",
            "technician_name": "Test Technician",
            "price_subtotal": 500.00,
            "tax_percent": 18
        }
        
        response = requests.post(url, json=data)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"Success! Job card created with existing client: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
    else:
        print("No existing client found with this mobile number")
        return False

if __name__ == "__main__":
    print("Testing Inquiry Conversion Fix")
    print("=" * 40)
    
    # Test 1: Check if client exists
    test_client_exists_check()
    
    # Test 2: Try normal conversion
    test_inquiry_conversion()
    
    # Test 3: Try conversion with existing client
    test_with_existing_client()
    
    print("\nTest completed!")
