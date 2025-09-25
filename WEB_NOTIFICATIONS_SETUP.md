# 🔔 Web Push Notifications Setup Guide

## 🎉 **Great News! Your Backend is Already Configured!**

Your Django backend already has a complete web push notification system implemented. Here's what you have:

## 📋 **Current Implementation Status**

### ✅ **Already Implemented:**
- **Firebase Admin SDK Integration** - Complete service class
- **Device Token Management** - Register/unregister tokens
- **Notification Sending** - Send to individual tokens or all devices
- **Notification Logging** - Track sent notifications
- **API Endpoints** - RESTful endpoints for all operations
- **Error Handling** - Comprehensive error handling and logging
- **Security** - Proper authentication and validation

### 🔧 **Backend Components:**

#### **1. Firebase Service (`core/firebase_service.py`)**
- Complete Firebase Admin SDK integration
- Send notifications to individual tokens or topics
- Subscribe/unsubscribe to topics
- Token validation
- Comprehensive error handling

#### **2. Notification Service (`core/notification_service.py`)**
- High-level notification operations
- Device token registration/unregistration
- Inquiry notification automation
- Statistics and monitoring

#### **3. Models (`core/models.py`)**
- `DeviceToken` - Store device tokens
- `NotificationLog` - Track notification history

#### **4. API Views (`core/notification_views.py`)**
- `DeviceTokenViewSet` - Token management
- `NotificationLogViewSet` - View notification history
- `NotificationViewSet` - Send notifications

## 🚀 **API Endpoints Available**

### **Device Token Management**
```
POST /api/v1/device-tokens/register/
POST /api/v1/device-tokens/unregister/
GET  /api/v1/device-tokens/
PUT  /api/v1/device-tokens/{id}/
```

### **Notification Operations**
```
POST /api/v1/notifications/send/
GET  /api/v1/notifications/statistics/
```

### **Notification Logs**
```
GET /api/v1/notification-logs/
```

### **Health Checks**
```
GET /api/v1/health/
GET /api/v1/firebase/health/
```

## 🔑 **Environment Variables Required**

Add these to your backend environment (Railway/Production):

```env
# Firebase Admin SDK Configuration
FIREBASE_PROJECT_ID=pestcontrol99-notifications
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@pestcontrol99-notifications.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_X509_CERT_URL=your_cert_url

# FCM Server Key (Alternative method)
FCM_SERVER_KEY=your_fcm_server_key
```

## 📱 **Frontend Integration**

Your React frontend needs to:

### **1. Register Device Token**
```javascript
// After getting permission and token from Firebase
const registerToken = async (token) => {
  try {
    const response = await fetch('/api/v1/device-tokens/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: token,
        device_name: 'Web Browser'
      })
    });
    
    if (response.ok) {
      console.log('Device token registered successfully');
    }
  } catch (error) {
    console.error('Failed to register device token:', error);
  }
};
```

### **2. Unregister Device Token**
```javascript
const unregisterToken = async (token) => {
  try {
    const response = await fetch('/api/v1/device-tokens/unregister/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        token: token
      })
    });
    
    if (response.ok) {
      console.log('Device token unregistered successfully');
    }
  } catch (error) {
    console.error('Failed to unregister device token:', error);
  }
};
```

## 🧪 **Testing Your Implementation**

### **1. Test Device Token Registration**
```bash
curl -X POST https://your-backend-url/api/v1/device-tokens/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your-device-token-here",
    "device_name": "Test Device"
  }'
```

### **2. Test Notification Sending**
```bash
curl -X POST https://your-backend-url/api/v1/notifications/send/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-jwt-token" \
  -d '{
    "title": "Test Notification",
    "body": "This is a test notification from your backend"
  }'
```

### **3. Check Firebase Health**
```bash
curl https://your-backend-url/api/v1/firebase/health/
```

## 🔧 **Backend Usage Examples**

### **Send Notification from Django Code**
```python
from core.notification_service import NotificationService

# Send to all registered devices
result = NotificationService.send_notification(
    title="New Inquiry",
    body="You have a new inquiry from John Doe"
)

# Send to specific devices
result = NotificationService.send_notification(
    title="New Inquiry",
    body="You have a new inquiry from John Doe",
    device_tokens=["token1", "token2"]
)
```

### **Send Inquiry Notification**
```python
# Automatically send when new inquiry is created
inquiry_data = {
    'name': 'John Doe',
    'mobile': '9876543210',
    'service_type': 'Pest Control'
}

result = NotificationService.send_inquiry_notification(inquiry_data)
```

## 📊 **Monitoring & Statistics**

### **Get Notification Statistics**
```python
stats = NotificationService.get_notification_statistics()
print(f"Active devices: {stats['device_tokens']['active']}")
print(f"Success rate: {stats['notifications']['success_rate']}%")
```

### **API Endpoint**
```bash
curl -H "Authorization: Bearer your-jwt-token" \
  https://your-backend-url/api/v1/notifications/statistics/
```

## 🚨 **Important Security Notes**

### ✅ **DO:**
- Store Firebase credentials in environment variables
- Use HTTPS in production
- Validate device tokens before sending
- Implement rate limiting
- Log all notification attempts

### ❌ **DON'T:**
- Expose Firebase Admin SDK credentials in frontend
- Commit credentials to version control
- Send notifications without proper validation
- Ignore error handling

## 🔄 **Integration with Existing Features**

### **Automatic Inquiry Notifications**
Your system can automatically send notifications when:
- New inquiries are submitted
- Job cards are created
- Renewals are due
- Status updates occur

### **Example Integration in Views**
```python
# In your inquiry creation view
def create_inquiry(request):
    # ... create inquiry logic ...
    
    # Send notification
    NotificationService.send_inquiry_notification({
        'name': inquiry.full_name,
        'mobile': inquiry.mobile,
        'service_type': inquiry.service_type
    })
    
    return response
```

## 🎯 **Next Steps**

1. **Add Firebase credentials** to your production environment
2. **Test the endpoints** using the provided examples
3. **Integrate with your frontend** using the registration code
4. **Set up automatic notifications** for your business logic
5. **Monitor the notification logs** for success rates

## 🆘 **Troubleshooting**

### **Common Issues:**

1. **Firebase not initialized**
   - Check environment variables
   - Verify credentials format
   - Check Firebase health endpoint

2. **Notifications not received**
   - Verify device token registration
   - Check browser notification permissions
   - Review notification logs

3. **Authentication errors**
   - Ensure JWT token is valid
   - Check permission classes
   - Verify user authentication

### **Debug Commands:**
```bash
# Check Django logs
tail -f logs/django.log

# Test Firebase connection
python manage.py shell
>>> from core.firebase_service import FirebaseService
>>> app = FirebaseService.get_app()
>>> print("Firebase initialized successfully")
```

## 📞 **Support**

If you encounter issues:
1. Check the Django logs in `logs/django.log`
2. Use the Firebase health check endpoint
3. Verify your environment variables
4. Test with the provided curl commands

---

**🎉 Your backend is ready for web push notifications! Just add the Firebase credentials and start testing!**
