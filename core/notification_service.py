"""
Notification service for handling Firebase Cloud Messaging operations.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import DeviceToken, NotificationLog, NotificationSubscription
from .firebase_service import FirebaseService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for notification operations."""
    
    @staticmethod
    def register_device_token(
        token: str,
        device_type: str = 'android',
        user_agent: Optional[str] = None
    ) -> DeviceToken:
        """
        Register or update a device token.
        
        Args:
            token: Firebase device token
            device_type: Type of device (android, ios, web)
            user_agent: User agent string for web devices
            
        Returns:
            DeviceToken instance
        """
        try:
            # Try to get existing token
            device_token, created = DeviceToken.objects.get_or_create(
                token=token,
                defaults={
                    'device_type': device_type,
                    'user_agent': user_agent,
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing token
                device_token.device_type = device_type
                device_token.user_agent = user_agent
                device_token.is_active = True
                device_token.last_used = timezone.now()
                device_token.save()
            
            logger.info(f"Device token {'registered' if created else 'updated'}: {device_type}")
            return device_token
            
        except Exception as e:
            logger.error(f"Error registering device token: {e}")
            raise ValidationError(f"Failed to register device token: {e}")
    
    @staticmethod
    def unregister_device_token(token: str) -> bool:
        """
        Unregister a device token.
        
        Args:
            token: Firebase device token
            
        Returns:
            Boolean indicating success
        """
        try:
            device_token = DeviceToken.objects.get(token=token)
            device_token.is_active = False
            device_token.save()
            
            logger.info(f"Device token unregistered: {token[:20]}...")
            return True
            
        except DeviceToken.DoesNotExist:
            logger.warning(f"Device token not found for unregistration: {token[:20]}...")
            return False
        except Exception as e:
            logger.error(f"Error unregistering device token: {e}")
            return False
    
    @staticmethod
    def send_notification(
        title: str,
        body: str,
        device_tokens: Optional[List[str]] = None,
        topic: Optional[str] = None,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to devices or topic.
        
        Args:
            title: Notification title
            body: Notification body
            device_tokens: List of device tokens (for direct notifications)
            topic: Topic name (for topic notifications)
            data: Additional data payload
            image_url: URL of notification image
            click_action: Action to perform when notification is clicked
            
        Returns:
            Dict containing notification results
        """
        try:
            # Create notification log entry
            notification_log = NotificationLog.objects.create(
                title=title,
                body=body,
                notification_type=NotificationLog.NotificationType.TOPIC if topic else NotificationLog.NotificationType.PUSH,
                target_tokens=device_tokens or [],
                topic=topic,
                data_payload=data or {},
                status=NotificationLog.Status.PENDING
            )
            
            # Send notification via Firebase
            if topic:
                result = FirebaseService.send_topic_notification(
                    topic=topic,
                    title=title,
                    body=body,
                    data=data,
                    image_url=image_url
                )
            else:
                result = FirebaseService.send_notification(
                    device_tokens=device_tokens or [],
                    title=title,
                    body=body,
                    data=data,
                    image_url=image_url,
                    click_action=click_action
                )
            
            # Update notification log with results
            if result.get('success'):
                notification_log.status = NotificationLog.Status.SENT
                notification_log.success_count = result.get('success_count', 1)
                notification_log.failure_count = result.get('failure_count', 0)
                notification_log.firebase_message_id = result.get('message_id', '')
                
                # If there were failures, mark as partial
                if result.get('failure_count', 0) > 0:
                    notification_log.status = NotificationLog.Status.PARTIAL
            else:
                notification_log.status = NotificationLog.Status.FAILED
                notification_log.error_message = result.get('error', 'Unknown error')
                notification_log.failure_count = len(device_tokens) if device_tokens else 1
            
            notification_log.save()
            
            logger.info(f"Notification sent: {title} - Status: {notification_log.status}")
            
            return {
                'success': result.get('success', False),
                'notification_log_id': notification_log.id,
                'status': notification_log.status,
                'success_count': notification_log.success_count,
                'failure_count': notification_log.failure_count,
                'error_message': notification_log.error_message
            }
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def subscribe_to_topic(device_tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Subscribe device tokens to a topic.
        
        Args:
            device_tokens: List of device tokens
            topic: Topic name
            
        Returns:
            Dict containing subscription results
        """
        try:
            # Subscribe via Firebase
            result = FirebaseService.subscribe_to_topic(device_tokens, topic)
            
            if result.get('success'):
                # Create subscription records in database
                subscriptions_created = 0
                for token in device_tokens:
                    try:
                        device_token = DeviceToken.objects.get(token=token, is_active=True)
                        subscription, created = NotificationSubscription.objects.get_or_create(
                            device_token=device_token,
                            topic=topic,
                            defaults={'is_active': True}
                        )
                        if created:
                            subscriptions_created += 1
                        else:
                            # Update existing subscription
                            subscription.is_active = True
                            subscription.save()
                    except DeviceToken.DoesNotExist:
                        logger.warning(f"Device token not found for subscription: {token[:20]}...")
                        continue
                
                logger.info(f"Subscribed {subscriptions_created} devices to topic '{topic}'")
                
                return {
                    'success': True,
                    'subscriptions_created': subscriptions_created,
                    'firebase_success_count': result.get('success_count', 0),
                    'firebase_failure_count': result.get('failure_count', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def unsubscribe_from_topic(device_tokens: List[str], topic: str) -> Dict[str, Any]:
        """
        Unsubscribe device tokens from a topic.
        
        Args:
            device_tokens: List of device tokens
            topic: Topic name
            
        Returns:
            Dict containing unsubscription results
        """
        try:
            # Unsubscribe via Firebase
            result = FirebaseService.unsubscribe_from_topic(device_tokens, topic)
            
            if result.get('success'):
                # Update subscription records in database
                subscriptions_deactivated = 0
                for token in device_tokens:
                    try:
                        device_token = DeviceToken.objects.get(token=token, is_active=True)
                        try:
                            subscription = NotificationSubscription.objects.get(
                                device_token=device_token,
                                topic=topic
                            )
                            subscription.is_active = False
                            subscription.save()
                            subscriptions_deactivated += 1
                        except NotificationSubscription.DoesNotExist:
                            logger.warning(f"Subscription not found: {token[:20]}... -> {topic}")
                            continue
                    except DeviceToken.DoesNotExist:
                        logger.warning(f"Device token not found for unsubscription: {token[:20]}...")
                        continue
                
                logger.info(f"Unsubscribed {subscriptions_deactivated} devices from topic '{topic}'")
                
                return {
                    'success': True,
                    'subscriptions_deactivated': subscriptions_deactivated,
                    'firebase_success_count': result.get('success_count', 0),
                    'firebase_failure_count': result.get('failure_count', 0)
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_active_device_tokens(device_type: Optional[str] = None) -> List[str]:
        """
        Get list of active device tokens.
        
        Args:
            device_type: Optional device type filter
            
        Returns:
            List of active device tokens
        """
        try:
            queryset = DeviceToken.objects.filter(is_active=True)
            if device_type:
                queryset = queryset.filter(device_type=device_type)
            
            return list(queryset.values_list('token', flat=True))
            
        except Exception as e:
            logger.error(f"Error getting active device tokens: {e}")
            return []
    
    @staticmethod
    def get_topic_subscribers(topic: str) -> List[str]:
        """
        Get list of device tokens subscribed to a topic.
        
        Args:
            topic: Topic name
            
        Returns:
            List of subscribed device tokens
        """
        try:
            subscriptions = NotificationSubscription.objects.filter(
                topic=topic,
                is_active=True,
                device_token__is_active=True
            ).select_related('device_token')
            
            return [sub.device_token.token for sub in subscriptions]
            
        except Exception as e:
            logger.error(f"Error getting topic subscribers: {e}")
            return []
    
    @staticmethod
    def send_bulk_notification(
        title: str,
        body: str,
        target_type: str = 'all',  # 'all', 'android', 'ios', 'web', 'topic'
        target_value: Optional[str] = None,  # topic name if target_type is 'topic'
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send bulk notification to multiple devices.
        
        Args:
            title: Notification title
            body: Notification body
            target_type: Type of target ('all', 'android', 'ios', 'web', 'topic')
            target_value: Topic name if target_type is 'topic'
            data: Additional data payload
            image_url: URL of notification image
            
        Returns:
            Dict containing bulk notification results
        """
        try:
            if target_type == 'topic':
                if not target_value:
                    raise ValidationError("Topic name is required when target_type is 'topic'")
                
                return NotificationService.send_notification(
                    title=title,
                    body=body,
                    topic=target_value,
                    data=data,
                    image_url=image_url
                )
            else:
                # Get device tokens based on target type
                device_tokens = NotificationService.get_active_device_tokens(
                    device_type=target_type if target_type != 'all' else None
                )
                
                if not device_tokens:
                    return {
                        'success': False,
                        'error': f'No active device tokens found for target type: {target_type}'
                    }
                
                return NotificationService.send_notification(
                    title=title,
                    body=body,
                    device_tokens=device_tokens,
                    data=data,
                    image_url=image_url
                )
                
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_notification_statistics() -> Dict[str, Any]:
        """
        Get notification statistics.
        
        Returns:
            Dict containing notification statistics
        """
        try:
            from django.db.models import Count, Q
            
            # Device token statistics
            total_tokens = DeviceToken.objects.count()
            active_tokens = DeviceToken.objects.filter(is_active=True).count()
            tokens_by_type = DeviceToken.objects.filter(is_active=True).values('device_type').annotate(
                count=Count('device_type')
            )
            
            # Notification log statistics
            total_notifications = NotificationLog.objects.count()
            successful_notifications = NotificationLog.objects.filter(
                status__in=[NotificationLog.Status.SENT, NotificationLog.Status.PARTIAL]
            ).count()
            failed_notifications = NotificationLog.objects.filter(
                status=NotificationLog.Status.FAILED
            ).count()
            
            # Subscription statistics
            total_subscriptions = NotificationSubscription.objects.filter(is_active=True).count()
            topics_count = NotificationSubscription.objects.filter(is_active=True).values('topic').distinct().count()
            
            return {
                'device_tokens': {
                    'total': total_tokens,
                    'active': active_tokens,
                    'by_type': {item['device_type']: item['count'] for item in tokens_by_type}
                },
                'notifications': {
                    'total': total_notifications,
                    'successful': successful_notifications,
                    'failed': failed_notifications,
                    'success_rate': (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0
                },
                'subscriptions': {
                    'total': total_subscriptions,
                    'topics_count': topics_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return {
                'error': str(e)
            }
