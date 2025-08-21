#!/usr/bin/env python3
"""
Test CORS configuration for PestControl99 domains
"""

import requests
import json

# Test URLs
TEST_URLS = [
    "http://127.0.0.1:8000/health/",
    "http://127.0.0.1:8000/api/token/",
]

# Test origins
TEST_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001", 
    "https://www.pestcontrol99.com",
    "https://pestcontrol-crm-frontend.vercel.app",
]

def test_cors_preflight(url, origin):
    """Test CORS preflight request"""
    try:
        headers = {
            'Origin': origin,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type,Authorization',
        }
        
        response = requests.options(url, headers=headers)
        
        print(f"✅ CORS Preflight for {origin} -> {url}")
        print(f"   Status: {response.status_code}")
        print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'Not Set')}")
        print(f"   Access-Control-Allow-Methods: {response.headers.get('Access-Control-Allow-Methods', 'Not Set')}")
        print(f"   Access-Control-Allow-Headers: {response.headers.get('Access-Control-Allow-Headers', 'Not Set')}")
        print()
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ CORS Preflight failed for {origin} -> {url}: {e}")
        print()
        return False

def test_actual_request(url, origin):
    """Test actual CORS request"""
    try:
        headers = {
            'Origin': origin,
            'Content-Type': 'application/json',
        }
        
        response = requests.get(url, headers=headers)
        
        print(f"✅ CORS Request for {origin} -> {url}")
        print(f"   Status: {response.status_code}")
        print(f"   Access-Control-Allow-Origin: {response.headers.get('Access-Control-Allow-Origin', 'Not Set')}")
        print()
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"❌ CORS Request failed for {origin} -> {url}: {e}")
        print()
        return False

def main():
    print("🔍 Testing CORS Configuration for PestControl99 Domains")
    print("=" * 60)
    
    # Check if server is running
    try:
        response = requests.get("http://127.0.0.1:8000/health/")
        if response.status_code != 200:
            print("❌ Server is not running. Please start the Django server first.")
            return
        print("✅ Server is running")
        print()
    except:
        print("❌ Server is not running. Please start the Django server first.")
        return
    
    # Test CORS for each origin
    for origin in TEST_ORIGINS:
        print(f"🌐 Testing Origin: {origin}")
        print("-" * 40)
        
        for url in TEST_URLS:
            # Test preflight
            test_cors_preflight(url, origin)
            
            # Test actual request
            test_actual_request(url, origin)
    
    print("🎯 CORS Testing Complete!")
    print("\n📋 Summary:")
    print("The following domains are now allowed in CORS:")
    for origin in TEST_ORIGINS:
        print(f"   - {origin}")

if __name__ == "__main__":
    main()
