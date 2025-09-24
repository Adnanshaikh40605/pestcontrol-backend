"""
Simplified notification service for basic push notification functionality.
Only includes what's needed for simple inquiry notifications.
"""

import logging
from typing import List, Dict, Any, Optional
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import DeviceToken, NotificationLog
from .firebase_service import FirebaseService

logger = logging.getLogger(__name__)


class NotificationService:
    """Simplified service class for notification operations."""
    
    @staticmethod
    def register_device_token(token: str, device_name: Optional[str] = None) -> DeviceToken:
        """
        Register or update a device token.
        
        Args:
            token: Firebase device token
            device_name: Optional name to identify the device
            
        Returns:
            DeviceToken instance
        """
        try:
            # Try to get existing token
            device_token, created = DeviceToken.objects.get_or_create(
                token=token,
                defaults={
                    'device_name': device_name,
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing token
                device_token.device_name = device_name
                device_token.is_active = True
                device_token.save()
            
            logger.info(f"Device token {'registered' if created else 'updated'}: {device_name or 'Unknown'}")
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
        device_tokens: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to devices.
        
        Args:
            title: Notification title
            body: Notification body
            device_tokens: List of device tokens (if None, sends to all active tokens)
            
        Returns:
            Dict containing notification results
        """
        try:
            # If no device tokens provided, get all active tokens
            if not device_tokens:
                device_tokens = list(DeviceToken.objects.filter(is_active=True).values_list('token', flat=True))
            
            if not device_tokens:
                return {
                    'success': False,
                    'error': 'No active device tokens found'
                }
            
            # Create notification log entry
            notification_log = NotificationLog.objects.create(
                title=title,
                body=body,
                status=NotificationLog.Status.SENT
            )
            
            # Send notification via Firebase
            result = FirebaseService.send_notification(
                device_tokens=device_tokens,
                title=title,
                body=body
            )
            
            # Update notification log with results
            if result.get('success'):
                notification_log.status = NotificationLog.Status.SENT
            else:
                notification_log.status = NotificationLog.Status.FAILED
                notification_log.error_message = result.get('error', 'Unknown error')
            
            notification_log.save()
            
            logger.info(f"Notification sent: {title} - Status: {notification_log.status}")
            
            return {
                'success': result.get('success', False),
                'notification_log_id': notification_log.id,
                'status': notification_log.status,
                'error_message': notification_log.error_message
            }
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def send_inquiry_notification(inquiry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send notification when a new inquiry is submitted.
        
        Args:
            inquiry_data: Dictionary containing inquiry information
            
        Returns:
            Dict containing notification results
        """
        try:
            customer_name = inquiry_data.get('name', 'Customer')
            customer_phone = inquiry_data.get('mobile', 'No phone')
            service_type = inquiry_data.get('service_type', 'General Service')
            
            title = "New Inquiry Received"
            body = f"New inquiry from {customer_name} ({customer_phone}) for {service_type}"
            
            return NotificationService.send_notification(title=title, body=body)
            
        except Exception as e:
            logger.error(f"Error sending inquiry notification: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_active_device_tokens() -> List[str]:
        """
        Get list of all active device tokens.
        
        Returns:
            List of active device tokens
        """
        try:
            return list(DeviceToken.objects.filter(is_active=True).values_list('token', flat=True))
        except Exception as e:
            logger.error(f"Error getting active device tokens: {e}")
            return []
    
    @staticmethod
    def get_notification_statistics() -> Dict[str, Any]:
        """
        Get basic notification statistics.
        
        Returns:
            Dict containing notification statistics
        """
        try:
            total_tokens = DeviceToken.objects.count()
            active_tokens = DeviceToken.objects.filter(is_active=True).count()
            total_notifications = NotificationLog.objects.count()
            successful_notifications = NotificationLog.objects.filter(
                status=NotificationLog.Status.SENT
            ).count()
            failed_notifications = NotificationLog.objects.filter(
                status=NotificationLog.Status.FAILED
            ).count()
            
            return {
                'device_tokens': {
                    'total': total_tokens,
                    'active': active_tokens
                },
                'notifications': {
                    'total': total_notifications,
                    'successful': successful_notifications,
                    'failed': failed_notifications,
                    'success_rate': (successful_notifications / total_notifications * 100) if total_notifications > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting notification statistics: {e}")
            return {
                'error': str(e)
            }
