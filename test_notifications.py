#!/usr/bin/env python3
"""
Test script for web push notifications.
Run this script to test your notification system.
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.notification_service import NotificationService
from core.firebase_service import FirebaseService
from core.models import DeviceToken, NotificationLog


def test_firebase_connection():
    """Test Firebase connection."""
    print("🔍 Testing Firebase connection...")
    try:
        app = FirebaseService.get_app()
        print("✅ Firebase connection successful!")
        print(f"   Project ID: {app.project_id}")
        return True
    except Exception as e:
        print(f"❌ Firebase connection failed: {e}")
        return False


def test_device_token_registration():
    """Test device token registration."""
    print("\n📱 Testing device token registration...")
    
    # Create a test token
    test_token = "test_token_" + str(int(datetime.now().timestamp()))
    
    try:
        device_token = NotificationService.register_device_token(
            token=test_token,
            device_name="Test Device"
        )
        print("✅ Device token registered successfully!")
        print(f"   Token ID: {device_token.id}")
        print(f"   Token: {device_token.token[:20]}...")
        return test_token
    except Exception as e:
        print(f"❌ Device token registration failed: {e}")
        return None


def test_notification_sending(test_token):
    """Test notification sending."""
    print("\n📤 Testing notification sending...")
    
    try:
        result = NotificationService.send_notification(
            title="Test Notification",
            body="This is a test notification from your backend",
            device_tokens=[test_token] if test_token else None
        )
        
        if result.get('success'):
            print("✅ Notification sent successfully!")
            print(f"   Status: {result.get('status')}")
            print(f"   Log ID: {result.get('notification_log_id')}")
        else:
            print(f"❌ Notification sending failed: {result.get('error')}")
        
        return result
    except Exception as e:
        print(f"❌ Notification sending failed: {e}")
        return None


def test_inquiry_notification():
    """Test inquiry notification."""
    print("\n📋 Testing inquiry notification...")
    
    try:
        inquiry_data = {
            'name': 'Test Customer',
            'mobile': '9876543210',
            'service_type': 'Pest Control'
        }
        
        result = NotificationService.send_inquiry_notification(inquiry_data)
        
        if result.get('success'):
            print("✅ Inquiry notification sent successfully!")
            print(f"   Status: {result.get('status')}")
        else:
            print(f"❌ Inquiry notification failed: {result.get('error')}")
        
        return result
    except Exception as e:
        print(f"❌ Inquiry notification failed: {e}")
        return None


def test_statistics():
    """Test notification statistics."""
    print("\n📊 Testing notification statistics...")
    
    try:
        stats = NotificationService.get_notification_statistics()
        
        print("✅ Statistics retrieved successfully!")
        print(f"   Total device tokens: {stats['device_tokens']['total']}")
        print(f"   Active device tokens: {stats['device_tokens']['active']}")
        print(f"   Total notifications: {stats['notifications']['total']}")
        print(f"   Successful notifications: {stats['notifications']['successful']}")
        print(f"   Success rate: {stats['notifications']['success_rate']:.1f}%")
        
        return stats
    except Exception as e:
        print(f"❌ Statistics retrieval failed: {e}")
        return None


def test_api_endpoints():
    """Test API endpoints."""
    print("\n🌐 Testing API endpoints...")
    
    # You'll need to update this with your actual backend URL
    base_url = "http://localhost:8000"  # Change this to your backend URL
    
    endpoints = [
        "/api/v1/health/",
        "/api/v1/firebase/health/",
        "/api/v1/notifications/statistics/"
    ]
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"❌ {endpoint} - Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {e}")


def cleanup_test_data(test_token):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        if test_token:
            NotificationService.unregister_device_token(test_token)
            print("✅ Test device token unregistered")
        
        # Clean up test notification logs
        test_logs = NotificationLog.objects.filter(
            title="Test Notification"
        )
        count = test_logs.count()
        test_logs.delete()
        print(f"✅ Cleaned up {count} test notification logs")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


def main():
    """Main test function."""
    print("🚀 Starting Web Push Notification Tests")
    print("=" * 50)
    
    # Test Firebase connection
    if not test_firebase_connection():
        print("\n❌ Firebase connection failed. Please check your credentials.")
        return
    
    # Test device token registration
    test_token = test_device_token_registration()
    
    # Test notification sending
    test_notification_sending(test_token)
    
    # Test inquiry notification
    test_inquiry_notification()
    
    # Test statistics
    test_statistics()
    
    # Test API endpoints (optional - requires running server)
    # test_api_endpoints()
    
    # Cleanup
    cleanup_test_data(test_token)
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    print("\nNext steps:")
    print("1. Add your Firebase credentials to environment variables")
    print("2. Test with real device tokens from your frontend")
    print("3. Integrate with your business logic")


if __name__ == "__main__":
    main()
