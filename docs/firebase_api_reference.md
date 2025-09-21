# Firebase API Reference - PestControl99

## Quick Reference for Firebase Integration

### Base URL
```
https://pestcontrol-backend-production.up.railway.app/api/v1
```

## Device Token Management

### Register Device Token
```http
POST /device-tokens/register
Content-Type: application/json

{
    "token": "firebase_device_token_here",
    "device_type": "android|ios|web",
    "user_agent": "optional_user_agent"
}
```

### Unregister Device Token
```http
POST /device-tokens/unregister
Content-Type: application/json

{
    "token": "firebase_device_token_here"
}
```

### Get Device Token Statistics
```http
GET /device-tokens/statistics
Authorization: Bearer your_jwt_token
```

## Notification Sending

### Send Push Notification
```http
POST /notifications/send
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "title": "Notification Title",
    "body": "Notification message body",
    "device_tokens": ["token1", "token2"],
    "data": {
        "key": "value",
        "action": "open_screen"
    },
    "image_url": "https://example.com/image.jpg",
    "click_action": "OPEN_ACTION"
}
```

### Send Topic Notification
```http
POST /notifications/send
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "title": "Topic Notification",
    "body": "Message for all subscribers",
    "topic": "topic_name",
    "data": {
        "type": "broadcast"
    }
}
```

### Send Bulk Notification
```http
POST /notifications/send-bulk
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "title": "Bulk Notification",
    "body": "Message for multiple devices",
    "target_type": "all|android|ios|web|topic",
    "target_value": "topic_name_if_applicable",
    "data": {
        "type": "bulk"
    }
}
```

## Topic Management

### Subscribe to Topic
```http
POST /notifications/subscribe-topic
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "device_tokens": ["token1", "token2"],
    "topic": "topic_name"
}
```

### Unsubscribe from Topic
```http
POST /notifications/unsubscribe-topic
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "device_tokens": ["token1", "token2"],
    "topic": "topic_name"
}
```

## Monitoring & Statistics

### Get Notification Statistics
```http
GET /notifications/statistics
Authorization: Bearer your_jwt_token
```

### Get Active Device Tokens
```http
GET /notifications/active-tokens?device_type=android
Authorization: Bearer your_jwt_token
```

### Get Topic Subscribers
```http
GET /notifications/topic-subscribers?topic=topic_name
Authorization: Bearer your_jwt_token
```

### Firebase Health Check
```http
GET /firebase/health/
```

## Response Examples

### Successful Token Registration
```json
{
    "id": 1,
    "token": "firebase_device_token_here",
    "device_type": "android",
    "user_agent": null,
    "is_active": true,
    "last_used": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### Successful Notification Send
```json
{
    "success": true,
    "notification_log_id": 123,
    "status": "sent",
    "success_count": 2,
    "failure_count": 0,
    "error_message": null
}
```

### Notification Statistics
```json
{
    "device_tokens": {
        "total": 150,
        "active": 145,
        "by_type": {
            "android": 120,
            "ios": 25
        }
    },
    "notifications": {
        "total": 500,
        "successful": 480,
        "failed": 20,
        "success_rate": 96.0
    },
    "subscriptions": {
        "total": 300,
        "topics_count": 5
    }
}
```

## Error Responses

### Validation Error
```json
{
    "error": "Validation failed",
    "details": {
        "token": ["Device token is required and cannot be empty."]
    }
}
```

### Authentication Error
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### Firebase Error
```json
{
    "success": false,
    "error": "Firebase error: Invalid registration token"
}
```

## Common Use Cases

### 1. App Launch - Register Token
```javascript
// When app starts, register the FCM token
const token = await messaging().getToken();
await fetch('/api/v1/device-tokens/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        token: token,
        device_type: 'android' // or 'ios'
    })
});
```

### 2. Send Job Card Notification
```javascript
// When a new job card is created
await fetch('/api/v1/notifications/send', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + jwtToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'New Job Card Created',
        body: `Job card ${jobCardCode} has been created`,
        device_tokens: [clientToken],
        data: {
            type: 'job_card',
            job_card_id: jobCardId,
            action: 'view_job_card'
        }
    })
});
```

### 3. Send Service Reminder
```javascript
// Send reminder to all subscribers
await fetch('/api/v1/notifications/send', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + jwtToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'Service Reminder',
        body: 'Your pest control service is due tomorrow',
        topic: 'service_reminders',
        data: {
            type: 'reminder',
            service_date: '2024-01-16'
        }
    })
});
```

### 4. Subscribe to Notifications
```javascript
// Subscribe user to specific topics
await fetch('/api/v1/notifications/subscribe-topic', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer ' + jwtToken,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        device_tokens: [userToken],
        topic: 'service_reminders'
    })
});
```

## Environment Variables for Backend

```bash
# Required Firebase Configuration
FIREBASE_PROJECT_ID=pestcontrol99-notifications
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@pestcontrol99-notifications.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40pestcontrol99-notifications.iam.gserviceaccount.com

# Optional
FCM_SERVER_KEY=your_fcm_server_key
```

## Testing Commands

### Test Token Registration
```bash
curl -X POST https://pestcontrol-backend-production.up.railway.app/api/v1/device-tokens/register \
  -H "Content-Type: application/json" \
  -d '{"token": "test_token_123", "device_type": "android"}'
```

### Test Notification Send
```bash
curl -X POST https://pestcontrol-backend-production.up.railway.app/api/v1/notifications/send \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Test message", "device_tokens": ["test_token_123"]}'
```

### Test Firebase Health
```bash
curl https://pestcontrol-backend-production.up.railway.app/api/v1/firebase/health/
```
