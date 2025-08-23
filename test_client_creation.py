#!/usr/bin/env python
"""
Test script to verify the client creation fix.
Run this after starting your Django server to test the fix.
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000/api"

def test_create_client():
    """Test creating a new client."""
    print("Testing client creation...")
    
    url = f"{BASE_URL}/clients/"
    data = {
        "full_name": "Test User",
        "mobile": "9876543210",
        "email": "test@example.com",
        "city": "Mumbai"
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"Success! Client created: {json.dumps(data, indent=2)}")
        return data.get('id')
    else:
        print(f"Error: {response.text}")
        return None

def test_create_duplicate_client():
    """Test creating a client with the same mobile number."""
    print("\nTesting duplicate client creation...")
    
    url = f"{BASE_URL}/clients/"
    data = {
        "full_name": "Another Test User",
        "mobile": "9876543210",  # Same mobile as above
        "email": "another@example.com",
        "city": "Delhi"
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"Expected error (duplicate mobile): {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Unexpected response: {response.text}")
        return False

def test_create_or_get_client():
    """Test the new create_or_get endpoint."""
    print("\nTesting create_or_get client endpoint...")
    
    url = f"{BASE_URL}/clients/create_or_get/"
    data = {
        "full_name": "Test User 2",
        "mobile": "9876543210",  # Same mobile as above
        "email": "test2@example.com",
        "city": "Bangalore"
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Success! Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_create_new_client_with_create_or_get():
    """Test creating a new client with create_or_get."""
    print("\nTesting create_or_get with new mobile number...")
    
    url = f"{BASE_URL}/clients/create_or_get/"
    data = {
        "full_name": "New Test User",
        "mobile": "1234567890",  # New mobile number
        "email": "new@example.com",
        "city": "Chennai"
    }
    
    response = requests.post(url, json=data)
    
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        data = response.json()
        print(f"Success! Response: {json.dumps(data, indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

if __name__ == "__main__":
    print("Testing Client Creation Fix")
    print("=" * 40)
    
    # Test 1: Create a new client
    client_id = test_create_client()
    
    # Test 2: Try to create duplicate client (should fail)
    test_create_duplicate_client()
    
    # Test 3: Use create_or_get with existing mobile (should return existing client)
    test_create_or_get_client()
    
    # Test 4: Use create_or_get with new mobile (should create new client)
    test_create_new_client_with_create_or_get()
    
    print("\nTest completed!")
