# Firebase Integration Guide for PestControl99 App

This guide provides comprehensive instructions for implementing Firebase Cloud Messaging (FCM) in your mobile app to work with the PestControl99 backend.

## Table of Contents

1. [Overview](#overview)
2. [Backend Setup](#backend-setup)
3. [Android Implementation](#android-implementation)
4. [iOS Implementation](#ios-implementation)
5. [API Endpoints](#api-endpoints)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## Overview

The PestControl99 backend now supports Firebase Cloud Messaging for push notifications. The system includes:

- Device token registration and management
- Push notification sending (individual and bulk)
- Topic-based notifications
- Notification logging and tracking
- Admin panel for notification management

## Backend Setup

### Environment Variables

Add these environment variables to your backend configuration:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=pestcontrol99-notifications
FIREBASE_PRIVATE_KEY_ID=your_private_key_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@pestcontrol99-notifications.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your_client_id
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxxxx%40pestcontrol99-notifications.iam.gserviceaccount.com

# Optional: FCM Server Key (for legacy support)
FCM_SERVER_KEY=your_fcm_server_key
```

### Firebase Service Account

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project: `pestcontrol99-notifications`
3. Go to Project Settings > Service Accounts
4. Generate a new private key
5. Use the downloaded JSON file to extract the required environment variables

## Android Implementation

### 1. Add Firebase to your Android project

In your `build.gradle` (Project level):
```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.3'
    }
}
```

In your `build.gradle` (App level):
```gradle
plugins {
    id 'com.android.application'
    id 'com.google.gms.google-services'
}

dependencies {
    // Import the Firebase BoM
    implementation platform('com.google.firebase:firebase-bom:34.3.0')
    
    // Firebase Cloud Messaging
    implementation 'com.google.firebase:firebase-messaging'
    
    // Optional: Firebase Analytics
    implementation 'com.google.firebase:firebase-analytics'
}
```

### 2. Add google-services.json

Place the `google-services.json` file in your `app/` directory.

### 3. Create Firebase Messaging Service

Create `MyFirebaseMessagingService.java`:

```java
package com.pestcontrol99.app;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import androidx.core.app.NotificationCompat;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;
import java.util.Map;

public class MyFirebaseMessagingService extends FirebaseMessagingService {
    
    private static final String CHANNEL_ID = "pestcontrol_notifications";
    private static final String CHANNEL_NAME = "PestControl Notifications";
    private static final String CHANNEL_DESCRIPTION = "Notifications from PestControl99";
    
    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }
    
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        // Handle data payload
        Map<String, String> data = remoteMessage.getData();
        
        // Handle notification payload
        if (remoteMessage.getNotification() != null) {
            sendNotification(
                remoteMessage.getNotification().getTitle(),
                remoteMessage.getNotification().getBody(),
                data
            );
        }
    }
    
    @Override
    public void onNewToken(String token) {
        // Send token to your backend
        sendTokenToServer(token);
    }
    
    private void sendNotification(String title, String messageBody, Map<String, String> data) {
        Intent intent = new Intent(this, MainActivity.class);
        
        // Add data payload to intent
        if (data != null) {
            for (Map.Entry<String, String> entry : data.entrySet()) {
                intent.putExtra(entry.getKey(), entry.getValue());
            }
        }
        
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_ONE_SHOT | PendingIntent.FLAG_IMMUTABLE
        );
        
        Uri defaultSoundUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION);
        
        NotificationCompat.Builder notificationBuilder = new NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification) // Use your app icon
            .setContentTitle(title)
            .setContentText(messageBody)
            .setAutoCancel(true)
            .setSound(defaultSoundUri)
            .setContentIntent(pendingIntent)
            .setColor(getResources().getColor(R.color.notification_color)); // Optional: Set notification color
        
        NotificationManager notificationManager = 
            (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        
        notificationManager.notify(0, notificationBuilder.build());
    }
    
    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_DEFAULT
            );
            channel.setDescription(CHANNEL_DESCRIPTION);
            
            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            notificationManager.createNotificationChannel(channel);
        }
    }
    
    private void sendTokenToServer(String token) {
        // Implement API call to register token with your backend
        // Use the /api/v1/device-tokens/register endpoint
    }
}
```

### 4. Register the Service in AndroidManifest.xml

```xml
<service
    android:name=".MyFirebaseMessagingService"
    android:exported="false">
    <intent-filter>
        <action android:name="com.google.firebase.MESSAGING_EVENT" />
    </intent-filter>
</service>
```

### 5. Request Notification Permissions (Android 13+)

```java
// In your MainActivity or Application class
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
    if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) 
        != PackageManager.PERMISSION_GRANTED) {
        ActivityCompat.requestPermissions(this, 
            new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
    }
}
```

## iOS Implementation

### 1. Add Firebase to your iOS project

Add Firebase to your `Podfile`:

```ruby
pod 'Firebase/Messaging'
pod 'Firebase/Analytics' # Optional
```

Run `pod install`.

### 2. Add GoogleService-Info.plist

Add the `GoogleService-Info.plist` file to your Xcode project.

### 3. Configure AppDelegate

```swift
import UIKit
import Firebase
import UserNotifications

@main
class AppDelegate: UIResponder, UIApplicationDelegate, UNUserNotificationCenterDelegate, MessagingDelegate {
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        
        // Configure Firebase
        FirebaseApp.configure()
        
        // Set messaging delegate
        Messaging.messaging().delegate = self
        
        // Request notification permissions
        UNUserNotificationCenter.current().delegate = self
        let authOptions: UNAuthorizationOptions = [.alert, .badge, .sound]
        UNUserNotificationCenter.current().requestAuthorization(
            options: authOptions,
            completionHandler: { _, _ in }
        )
        
        application.registerForRemoteNotifications()
        
        return true
    }
    
    // Handle notification when app is in foreground
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                              willPresent notification: UNNotification,
                              withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([[.alert, .sound]])
    }
    
    // Handle notification tap
    func userNotificationCenter(_ center: UNUserNotificationCenter,
                              didReceive response: UNNotificationResponse,
                              withCompletionHandler completionHandler: @escaping () -> Void) {
        let userInfo = response.notification.request.content.userInfo
        // Handle notification data
        completionHandler()
    }
    
    // Handle FCM token refresh
    func messaging(_ messaging: Messaging, didReceiveRegistrationToken fcmToken: String?) {
        print("Firebase registration token: \(String(describing: fcmToken))")
        
        // Send token to your backend
        if let token = fcmToken {
            sendTokenToServer(token: token)
        }
    }
    
    private func sendTokenToServer(token: String) {
        // Implement API call to register token with your backend
        // Use the /api/v1/device-tokens/register endpoint
    }
}
```

## API Endpoints

### Base URL
```
https://pestcontrol-backend-production.up.railway.app/api/v1
```

### 1. Register Device Token

**Endpoint:** `POST /device-tokens/register`

**Request Body:**
```json
{
    "token": "your_firebase_device_token",
    "device_type": "android", // or "ios", "web"
    "user_agent": "optional_user_agent_string"
}
```

**Response:**
```json
{
    "id": 1,
    "token": "your_firebase_device_token",
    "device_type": "android",
    "user_agent": null,
    "is_active": true,
    "last_used": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### 2. Send Push Notification

**Endpoint:** `POST /notifications/send`

**Headers:**
```
Authorization: Bearer your_jwt_token
Content-Type: application/json
```

**Request Body:**
```json
{
    "title": "New Job Card Created",
    "body": "A new job card has been created for your service",
    "device_tokens": ["token1", "token2"],
    "data": {
        "type": "job_card",
        "job_card_id": "123",
        "action": "view_job_card"
    },
    "image_url": "https://example.com/image.jpg",
    "click_action": "OPEN_JOB_CARD"
}
```

### 3. Send Topic Notification

**Endpoint:** `POST /notifications/send`

**Request Body:**
```json
{
    "title": "Service Reminder",
    "body": "Your pest control service is due tomorrow",
    "topic": "service_reminders",
    "data": {
        "type": "reminder",
        "service_date": "2024-01-16"
    }
}
```

### 4. Subscribe to Topic

**Endpoint:** `POST /notifications/subscribe-topic`

**Request Body:**
```json
{
    "device_tokens": ["token1", "token2"],
    "topic": "service_reminders"
}
```

### 5. Get Notification Statistics

**Endpoint:** `GET /notifications/statistics`

**Response:**
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

## Testing

### 1. Test Device Token Registration

```bash
curl -X POST https://pestcontrol-backend-production.up.railway.app/api/v1/device-tokens/register \
  -H "Content-Type: application/json" \
  -d '{
    "token": "test_token_12345",
    "device_type": "android"
  }'
```

### 2. Test Push Notification

```bash
curl -X POST https://pestcontrol-backend-production.up.railway.app/api/v1/notifications/send \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Notification",
    "body": "This is a test notification",
    "device_tokens": ["test_token_12345"]
  }'
```

### 3. Test Firebase Health Check

```bash
curl https://pestcontrol-backend-production.up.railway.app/api/v1/firebase/health/
```

## Troubleshooting

### Common Issues

1. **Token Registration Fails**
   - Ensure the device token is valid and properly formatted
   - Check that the device has internet connectivity
   - Verify the API endpoint is accessible

2. **Notifications Not Received**
   - Check if notifications are enabled in device settings
   - Verify the app has notification permissions
   - Ensure the device token is active in the backend
   - Check Firebase console for delivery reports

3. **Firebase Initialization Errors**
   - Verify `google-services.json` (Android) or `GoogleService-Info.plist` (iOS) is properly added
   - Check that Firebase project configuration is correct
   - Ensure all required dependencies are installed

4. **Backend Authentication Errors**
   - Verify JWT token is valid and not expired
   - Check that the user has proper permissions
   - Ensure the Authorization header is correctly formatted

### Debug Steps

1. **Check Firebase Console**
   - Go to Firebase Console > Cloud Messaging
   - View message delivery reports
   - Check for any error messages

2. **Backend Logs**
   - Check Django logs for any Firebase-related errors
   - Verify environment variables are properly set
   - Test Firebase health endpoint

3. **Device Logs**
   - Check Android logcat or iOS console for FCM-related messages
   - Verify token generation and registration
   - Test notification handling in different app states

### Support

For technical support or questions about Firebase integration:

1. Check the [Firebase Documentation](https://firebase.google.com/docs/cloud-messaging)
2. Review the backend API documentation at `/api/schema/`
3. Contact the development team with specific error messages and logs

## Best Practices

1. **Token Management**
   - Always handle token refresh in your app
   - Implement retry logic for token registration
   - Clean up inactive tokens periodically

2. **Notification Handling**
   - Handle notifications when app is in foreground, background, and terminated
   - Implement proper deep linking for notification actions
   - Provide fallback behavior for notification data

3. **Error Handling**
   - Implement proper error handling for all API calls
   - Log errors for debugging purposes
   - Provide user feedback for critical failures

4. **Performance**
   - Batch token registrations when possible
   - Use topic subscriptions for broad notifications
   - Implement notification caching for offline scenarios

5. **Security**
   - Never expose Firebase credentials in client code
   - Validate all notification data on the client side
   - Use HTTPS for all API communications
