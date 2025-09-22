"""
Notification views for Firebase Cloud Messaging operations.
"""

import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status, response, decorators
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle

from .models import DeviceToken, NotificationLog, NotificationSubscription
from .serializers import (
    DeviceTokenSerializer, NotificationLogSerializer, NotificationSubscriptionSerializer,
    SendNotificationSerializer, SubscribeToTopicSerializer
)
from .notification_service import NotificationService
from .views import BaseModelViewSet

logger = logging.getLogger(__name__)


class DeviceTokenViewSet(BaseModelViewSet):
    """
    API endpoint that allows device tokens to be viewed, created, updated, or deleted.
    
    This endpoint provides full CRUD operations for device token management including:
    - List all device tokens with filtering and search capabilities
    - Register new device tokens (public endpoint - no authentication required)
    - Update device token information
    - Unregister device tokens
    - Manage device token lifecycle
    
    Filtering options:
    - device_type: Filter by device type (android, ios, web)
    - is_active: Filter by active status
    
    Search fields:
    - token: Search by device token
    - user_agent: Search by user agent string
    
    Ordering options:
    - created_at, updated_at, last_used, device_type
    """
    queryset = DeviceToken.objects.all()
    serializer_class = DeviceTokenSerializer
    filterset_fields = ['device_type', 'is_active']
    search_fields = ['token', 'user_agent']
    ordering_fields = ['created_at', 'updated_at', 'last_used', 'device_type']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]  # Allow unauthenticated access for all actions
    
    
    def create(self, request, *args, **kwargs):
        """Register a new device token."""
        try:
            token = request.data.get('token')
            device_type = request.data.get('device_type', 'android')
            user_agent = request.data.get('user_agent')
            
            if not token:
                return response.Response(
                    {'error': 'Device token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            device_token = NotificationService.register_device_token(
                token=token,
                device_type=device_type,
                user_agent=user_agent
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
    
    @decorators.action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get device token statistics."""
        try:
            stats = NotificationService.get_notification_statistics()
            return response.Response(stats)
        except Exception as e:
            logger.error(f"Error getting device token statistics: {e}")
            return response.Response(
                {'error': 'Failed to get statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationLogViewSet(BaseModelViewSet):
    """
    API endpoint that allows notification logs to be viewed and managed.
    
    This endpoint provides operations for notification log management including:
    - List all notification logs with filtering and search capabilities
    - View notification delivery status and details
    - Track notification history and performance
    - Monitor notification success/failure rates
    
    Filtering options:
    - status: Filter by notification status (sent, delivered, failed)
    - notification_type: Filter by notification type
    - created_at: Filter by creation date
    
    Search fields:
    - title: Search by notification title
    - body: Search by notification body
    - device_token: Search by device token
    
    Ordering options:
    - created_at, updated_at, status, notification_type
    """
    queryset = NotificationLog.objects.all()
    serializer_class = NotificationLogSerializer
    filterset_fields = ['status', 'notification_type', 'topic']
    search_fields = ['title', 'body']
    ordering_fields = ['created_at', 'updated_at', 'status', 'success_count', 'failure_count']
    ordering = ['-created_at']
    
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


class NotificationSubscriptionViewSet(BaseModelViewSet):
    """
    API endpoint that allows notification subscriptions to be viewed and managed.
    
    This endpoint provides operations for notification subscription management including:
    - List all notification subscriptions with filtering and search capabilities
    - Create new topic subscriptions for device tokens
    - Update subscription status and preferences
    - Get available topics for subscription
    - Manage topic-based notification subscriptions
    
    Filtering options:
    - topic: Filter by subscription topic
    - is_active: Filter by active status
    - device_token__device_type: Filter by device type
    
    Search fields:
    - topic: Search by topic name
    - device_token__token: Search by device token
    
    Ordering options:
    - created_at, updated_at, topic
    """
    queryset = NotificationSubscription.objects.select_related('device_token').all()
    serializer_class = NotificationSubscriptionSerializer
    filterset_fields = ['topic', 'is_active', 'device_token__device_type']
    search_fields = ['topic', 'device_token__token']
    ordering_fields = ['created_at', 'updated_at', 'topic']
    ordering = ['-created_at']
    
    @decorators.action(detail=False, methods=['get'])
    def topics(self, request):
        """Get list of available topics."""
        try:
            topics = NotificationSubscription.objects.filter(is_active=True).values_list(
                'topic', flat=True
            ).distinct().order_by('topic')
            
            return response.Response({
                'topics': list(topics),
                'count': len(topics)
            })
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return response.Response(
                {'error': 'Failed to get topics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationViewSet(viewsets.ViewSet):
    """
    API endpoint for notification operations and management.
    
    This endpoint provides operations for sending and managing push notifications including:
    - Send push notifications to specific device tokens or topics
    - Subscribe devices to notification topics
    - Unsubscribe devices from notification topics
    - Get notification statistics and performance metrics
    - Test notification delivery and Firebase connectivity
    
    Authentication: Required for all operations
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
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
                device_tokens=data.get('device_tokens'),
                topic=data.get('topic'),
                data=data.get('data'),
                image_url=data.get('image_url'),
                click_action=data.get('click_action')
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
    
    @decorators.action(detail=False, methods=['post'], url_path='send-bulk')
    def send_bulk_notification(self, request):
        """Send bulk notification."""
        try:
            title = request.data.get('title')
            body = request.data.get('body')
            target_type = request.data.get('target_type', 'all')
            target_value = request.data.get('target_value')
            data = request.data.get('data')
            image_url = request.data.get('image_url')
            
            if not title or not body:
                return response.Response(
                    {'error': 'Title and body are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = NotificationService.send_bulk_notification(
                title=title,
                body=body,
                target_type=target_type,
                target_value=target_value,
                data=data,
                image_url=image_url
            )
            
            if result.get('success'):
                return response.Response(result, status=status.HTTP_200_OK)
            else:
                return response.Response(
                    {'error': result.get('error', 'Failed to send bulk notification')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
            return response.Response(
                {'error': 'Failed to send bulk notification'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['post'], url_path='subscribe-topic')
    def subscribe_topic(self, request):
        """Subscribe device tokens to a topic."""
        try:
            serializer = SubscribeToTopicSerializer(data=request.data)
            if not serializer.is_valid():
                return response.Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            
            result = NotificationService.subscribe_to_topic(
                device_tokens=data['device_tokens'],
                topic=data['topic']
            )
            
            if result.get('success'):
                return response.Response(result, status=status.HTTP_200_OK)
            else:
                return response.Response(
                    {'error': result.get('error', 'Failed to subscribe to topic')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return response.Response(
                {'error': 'Failed to subscribe to topic'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['post'], url_path='unsubscribe-topic')
    def unsubscribe_topic(self, request):
        """Unsubscribe device tokens from a topic."""
        try:
            serializer = SubscribeToTopicSerializer(data=request.data)
            if not serializer.is_valid():
                return response.Response(
                    {'error': 'Validation failed', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            data = serializer.validated_data
            
            result = NotificationService.unsubscribe_from_topic(
                device_tokens=data['device_tokens'],
                topic=data['topic']
            )
            
            if result.get('success'):
                return response.Response(result, status=status.HTTP_200_OK)
            else:
                return response.Response(
                    {'error': result.get('error', 'Failed to unsubscribe from topic')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return response.Response(
                {'error': 'Failed to unsubscribe from topic'},
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
    
    @decorators.action(detail=False, methods=['get'])
    def active_tokens(self, request):
        """Get active device tokens."""
        try:
            device_type = request.query_params.get('device_type')
            tokens = NotificationService.get_active_device_tokens(device_type)
            
            return response.Response({
                'tokens': tokens,
                'count': len(tokens),
                'device_type': device_type or 'all'
            })
        except Exception as e:
            logger.error(f"Error getting active tokens: {e}")
            return response.Response(
                {'error': 'Failed to get active tokens'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['get'])
    def topic_subscribers(self, request):
        """Get subscribers for a topic."""
        try:
            topic = request.query_params.get('topic')
            
            if not topic:
                return response.Response(
                    {'error': 'Topic parameter is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tokens = NotificationService.get_topic_subscribers(topic)
            
            return response.Response({
                'topic': topic,
                'subscribers': tokens,
                'count': len(tokens)
            })
        except Exception as e:
            logger.error(f"Error getting topic subscribers: {e}")
            return response.Response(
                {'error': 'Failed to get topic subscribers'},
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
