"""
Firebase service module for handling Firebase Cloud Messaging (FCM) operations.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Union
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from firebase_admin import initialize_app, credentials, messaging
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)


class FirebaseService:
    """Service class for Firebase operations."""
    
    _app = None
    
    @classmethod
    def get_app(cls):
        """Get or initialize Firebase app."""
        if cls._app is None:
            try:
                # Check if Firebase is properly configured
                if not settings.FIREBASE_CONFIG.get('private_key'):
                    raise ImproperlyConfigured(
                        "Firebase private key not configured. Please set FIREBASE_PRIVATE_KEY in environment variables."
                    )
                
                # Create credentials from config
                cred = credentials.Certificate(settings.FIREBASE_CONFIG)
                
                # Initialize Firebase app
                cls._app = initialize_app(cred, name='pestcontrol-firebase')
                logger.info("Firebase app initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize Firebase app: {e}")
                raise ImproperlyConfigured(f"Firebase initialization failed: {e}")
        
        return cls._app
    
    @classmethod
    def send_notification(
        cls,
        device_tokens: Union[str, List[str]],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None,
        click_action: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send push notification to device(s).
        
        Args:
            device_tokens: Single token or list of tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: URL of notification image
            click_action: Action to perform when notification is clicked
            
        Returns:
            Dict containing success status and results
        """
        try:
            app = cls.get_app()
            
            # Ensure device_tokens is a list
            if isinstance(device_tokens, str):
                device_tokens = [device_tokens]
            
            if not device_tokens:
                return {
                    'success': False,
                    'error': 'No device tokens provided',
                    'results': []
                }
            
            # Prepare notification payload
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Prepare Android-specific configuration
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color=settings.NOTIFICATION_SETTINGS['DEFAULT_COLOR'],
                    sound=settings.NOTIFICATION_SETTINGS['DEFAULT_SOUND'],
                    click_action=click_action
                ),
                data=data or {}
            )
            
            # Prepare APNs-specific configuration
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=settings.NOTIFICATION_SETTINGS['DEFAULT_SOUND'],
                        badge=1
                    )
                )
            )
            
            # Send to each device individually (fixes the /batch endpoint issue)
            results = []
            success_count = 0
            failure_count = 0
            
            for token in device_tokens:
                try:
                    # Create individual message for each token
                    message = messaging.Message(
                        notification=notification,
                        data=data or {},
                        android=android_config,
                        apns=apns_config,
                        token=token
                    )
                    
                    # Send notification
                    response = messaging.send(message, app=app)
                    
                    success_count += 1
                    results.append({
                        'token': token,
                        'success': True,
                        'message_id': response
                    })
                    
                except Exception as e:
                    failure_count += 1
                    results.append({
                        'token': token,
                        'success': False,
                        'error': str(e)
                    })
            
            logger.info(f"Notification sent: {success_count} success, {failure_count} failures")
            
            return {
                'success': success_count > 0,
                'success_count': success_count,
                'failure_count': failure_count,
                'results': results
            }
            
        except FirebaseError as e:
            logger.error(f"Firebase error sending notification: {e}")
            return {
                'success': False,
                'error': f'Firebase error: {str(e)}',
                'results': []
            }
        except Exception as e:
            logger.error(f"Unexpected error sending notification: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'results': []
            }
    
    @classmethod
    def send_topic_notification(
        cls,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to a topic.
        
        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data payload
            image_url: URL of notification image
            
        Returns:
            Dict containing success status and message_id
        """
        try:
            app = cls.get_app()
            
            # Prepare notification payload
            notification = messaging.Notification(
                title=title,
                body=body,
                image=image_url
            )
            
            # Prepare Android-specific configuration
            android_config = messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    icon='ic_notification',
                    color=settings.NOTIFICATION_SETTINGS['DEFAULT_COLOR'],
                    sound=settings.NOTIFICATION_SETTINGS['DEFAULT_SOUND']
                ),
                data=data or {}
            )
            
            # Prepare APNs-specific configuration
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound=settings.NOTIFICATION_SETTINGS['DEFAULT_SOUND'],
                        badge=1
                    )
                )
            )
            
            # Create message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                android=android_config,
                apns=apns_config,
                topic=topic
            )
            
            # Send notification
            response = messaging.send(message, app=app)
            
            logger.info(f"Topic notification sent to '{topic}': {response}")
            
            return {
                'success': True,
                'message_id': response,
                'topic': topic
            }
            
        except FirebaseError as e:
            logger.error(f"Firebase error sending topic notification: {e}")
            return {
                'success': False,
                'error': f'Firebase error: {str(e)}',
                'topic': topic
            }
        except Exception as e:
            logger.error(f"Unexpected error sending topic notification: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'topic': topic
            }
    
    @classmethod
    def subscribe_to_topic(cls, device_tokens: Union[str, List[str]], topic: str) -> Dict[str, Any]:
        """
        Subscribe device(s) to a topic.
        
        Args:
            device_tokens: Single token or list of tokens
            topic: Topic name
            
        Returns:
            Dict containing success status and results
        """
        try:
            app = cls.get_app()
            
            # Ensure device_tokens is a list
            if isinstance(device_tokens, str):
                device_tokens = [device_tokens]
            
            if not device_tokens:
                return {
                    'success': False,
                    'error': 'No device tokens provided'
                }
            
            # Subscribe to topic
            response = messaging.subscribe_to_topic(device_tokens, topic, app=app)
            
            logger.info(f"Subscribed {len(device_tokens)} devices to topic '{topic}'")
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'errors': [str(error) for error in response.errors] if response.errors else []
            }
            
        except FirebaseError as e:
            logger.error(f"Firebase error subscribing to topic: {e}")
            return {
                'success': False,
                'error': f'Firebase error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error subscribing to topic: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @classmethod
    def unsubscribe_from_topic(cls, device_tokens: Union[str, List[str]], topic: str) -> Dict[str, Any]:
        """
        Unsubscribe device(s) from a topic.
        
        Args:
            device_tokens: Single token or list of tokens
            topic: Topic name
            
        Returns:
            Dict containing success status and results
        """
        try:
            app = cls.get_app()
            
            # Ensure device_tokens is a list
            if isinstance(device_tokens, str):
                device_tokens = [device_tokens]
            
            if not device_tokens:
                return {
                    'success': False,
                    'error': 'No device tokens provided'
                }
            
            # Unsubscribe from topic
            response = messaging.unsubscribe_from_topic(device_tokens, topic, app=app)
            
            logger.info(f"Unsubscribed {len(device_tokens)} devices from topic '{topic}'")
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'errors': [str(error) for error in response.errors] if response.errors else []
            }
            
        except FirebaseError as e:
            logger.error(f"Firebase error unsubscribing from topic: {e}")
            return {
                'success': False,
                'error': f'Firebase error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected error unsubscribing from topic: {e}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @classmethod
    def validate_token(cls, token: str) -> bool:
        """
        Validate if a device token is valid.
        
        Args:
            token: Device token to validate
            
        Returns:
            Boolean indicating if token is valid
        """
        try:
            # Try to send a test notification to validate the token
            result = cls.send_notification(
                device_tokens=[token],
                title="Test",
                body="Token validation",
                data={'type': 'validation'}
            )
            
            # Check if at least one notification was successful
            return result.get('success_count', 0) > 0
            
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
