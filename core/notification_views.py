"""
Simplified notification views for basic push notification functionality.
Only includes what's needed for simple inquiry notifications.
"""

import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, response, decorators
from rest_framework.decorators import action

from .models import DeviceToken, NotificationLog
from .serializers import DeviceTokenSerializer, NotificationLogSerializer, SendNotificationSerializer
from .notification_service import NotificationService
from .views import BaseModelViewSet

logger = logging.getLogger(__name__)


class DeviceTokenViewSet(BaseModelViewSet):
    """
    Simplified API endpoint for device token management.
    
    Provides basic CRUD operations for device token management:
    - Register new device tokens (public endpoint - no authentication required)
    - List device tokens
    - Update device token information
    - Unregister device tokens
    """
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access for all actions
    
    def create(self, request, *args, **kwargs):
        """Register a new device token."""
        try:
            token = request.data.get('token')
            device_name = request.data.get('device_name')
            
            if not token:
                return response.Response(
                    {'error': 'Device token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            device_token = NotificationService.register_device_token(
                token=token,
                device_name=device_name
            )
            
            serializer = self.get_serializer(device_token)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return response.Response(
                {'error': 'Validation failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error registering device token: {e}")
            return response.Response(
                {'error': 'Failed to register device token'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['post'], url_path='register')
    def register(self, request):
        """Public endpoint to register device token."""
        return self.create(request)
    
    @decorators.action(detail=False, methods=['post'], url_path='unregister')
    def unregister(self, request):
        """Unregister a device token."""
        try:
            token = request.data.get('token')
            
            if not token:
                return response.Response(
                    {'error': 'Device token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            success = NotificationService.unregister_device_token(token)
            
            if success:
                return response.Response({'message': 'Device token unregistered successfully'})
            else:
                return response.Response(
                    {'error': 'Device token not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error unregistering device token: {e}")
            return response.Response(
                {'error': 'Failed to unregister device token'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationLogViewSet(BaseModelViewSet):
    """
    Simplified API endpoint for notification logs.
    
    Provides read-only access to notification logs for tracking sent notifications.
    """
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]  # Require authentication for logs


class NotificationViewSet(viewsets.ViewSet):
    """
    Simplified API endpoint for notification operations.
    
    Provides operations for sending push notifications:
    - Send push notifications to device tokens
    - Get notification statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @decorators.action(detail=False, methods=['post'], url_path='send')
    def send_notification(self, request):
        """Send push notification."""
        try:
            serializer = SendNotificationSerializer(data=request.data)
            if not serializer.is_valid():
                return response.Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            
            result = NotificationService.send_notification(
                title=data['title'],
                body=data['body'],
                device_tokens=data.get('device_tokens')
            )
            
            if result.get('success'):
                return response.Response(result, status=status.HTTP_200_OK)
            else:
                return response.Response(
                    {'error': result.get('error', 'Failed to send notification')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return response.Response(
                {'error': 'Failed to send notification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get notification statistics."""
        try:
            stats = NotificationService.get_notification_statistics()
            return response.Response(stats)
        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return response.Response(
                {'error': 'Failed to get statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def firebase_health_check(request):
    """Health check endpoint for Firebase service."""
    try:
        from .firebase_service import FirebaseService
        
        # Try to get Firebase app (this will initialize if not already done)
        app = FirebaseService.get_app()
        
        return JsonResponse({
            'status': 'ok',
            'service': 'firebase-fcm',
            'project_id': app.project_id if app else 'unknown',
            'message': 'Firebase service is operational'
        })
    except Exception as e:
        logger.error(f"Firebase health check failed: {e}")
        return JsonResponse({
            'status': 'error',
            'service': 'firebase-fcm',
            'error': str(e)
        }, status=500)
