"""
Firebase Cloud Messaging for Pest 99 Partner app.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    import firebase_admin
    from firebase_admin import credentials

    project_id = getattr(settings, 'PARTNER_FIREBASE_PROJECT_ID', 'pest-99-partner-app')
    private_key = getattr(settings, 'FIREBASE_PRIVATE_KEY', '') or ''
    client_email = getattr(settings, 'FIREBASE_CLIENT_EMAIL', '') or ''
    private_key_id = getattr(settings, 'FIREBASE_PRIVATE_KEY_ID', '') or ''

    if private_key and client_email:
        if '\\n' in private_key:
            private_key = private_key.replace('\\n', '\n')
        cred_dict = {
            'type': 'service_account',
            'project_id': project_id,
            'private_key': private_key,
            'client_email': client_email,
            'token_uri': 'https://oauth2.googleapis.com/token',
        }
        if private_key_id:
            cred_dict['private_key_id'] = private_key_id
        cred = credentials.Certificate(cred_dict)
        try:
            _firebase_app = firebase_admin.get_app('partner-fcm')
        except ValueError:
            _firebase_app = firebase_admin.initialize_app(cred, {'projectId': project_id}, name='partner-fcm')
        logger.info('Firebase Admin ready for partner FCM (project=%s)', project_id)
        return _firebase_app

    cred_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', None)
    if cred_path:
        cred = credentials.Certificate(cred_path)
        try:
            _firebase_app = firebase_admin.get_app('partner-fcm')
        except ValueError:
            _firebase_app = firebase_admin.initialize_app(cred, {'projectId': project_id}, name='partner-fcm')
        return _firebase_app

    logger.warning('Firebase credentials not configured — partner push disabled')
    return None


def _prune_invalid_tokens(batch: list[str], responses) -> None:
    """Deactivate device tokens rejected by FCM (unregistered / invalid)."""
    from partner.models import PartnerDeviceToken

    from firebase_admin import messaging

    for idx, resp in enumerate(responses):
        if resp.success:
            continue
        exc = resp.exception
        invalid_types = (messaging.UnregisteredError,)
        if not isinstance(exc, invalid_types):
            continue
        if idx >= len(batch):
            continue
        token = batch[idx]
        updated = PartnerDeviceToken.objects.filter(fcm_token=token, is_active=True).update(is_active=False)
        if updated:
            logger.info('Deactivated invalid FCM token (%s)', token[:16])


def push_dedupe_key(
    job_id: int,
    notification_type: str,
    *,
    technician_id: int | None = None,
    partner_id: int | None = None,
) -> str:
    if partner_id is not None:
        scope = f'p{partner_id}'
    elif technician_id is not None:
        scope = f'tech{technician_id}'
    else:
        scope = 'all'
    return f'partner_push:{job_id}:{notification_type}:{scope}'


def should_skip_duplicate_push(
    job_id: int,
    notification_type: str,
    technician_id: int | None = None,
    partner_id: int | None = None,
) -> bool:
    key = push_dedupe_key(job_id, notification_type, technician_id=technician_id, partner_id=partner_id)
    if cache.get(key):
        return True
    cache.set(key, True, timeout=90)
    return False


def send_push_to_tokens(
    tokens: list[str],
    *,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
    collapse_key: str | None = None,
) -> dict[str, int]:
    """Send FCM. Uses notification+data for killed/background; data includes booking_id for taps."""
    tokens = list(dict.fromkeys(t.strip() for t in tokens if t and t.strip()))
    if not tokens:
        return {'success': 0, 'failure': 0}

    app = _get_firebase_app()
    if app is None:
        logger.warning('Skipping FCM (not configured): %s', title)
        return {'success': 0, 'failure': len(tokens)}

    from firebase_admin import messaging

    payload_data = {str(k): str(v) for k, v in (data or {}).items()}
    payload_data['title'] = title
    payload_data['body'] = body
    payload_data.setdefault('click_action', 'FLUTTER_NOTIFICATION_CLICK')

    android_notification = messaging.AndroidNotification(
        channel_id='pest99_bookings',
        sound='default',
        priority=messaging.AndroidNotificationPriority.HIGH,
        tag=collapse_key or payload_data.get('booking_id'),
    )
    android_config = messaging.AndroidConfig(
        priority='high',
        collapse_key=collapse_key,
        notification=android_notification,
    )

    success = 0
    failure = 0
    batch_size = 500

    for i in range(0, len(tokens), batch_size):
        batch = tokens[i : i + batch_size]
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=payload_data,
                tokens=batch,
                android=android_config,
            )
            response = messaging.send_each_for_multicast(message, app=app)
            success += response.success_count
            failure += response.failure_count
            _prune_invalid_tokens(batch, response.responses)
            for idx, resp in enumerate(response.responses):
                if not resp.success and resp.exception:
                    logger.warning('FCM token error: %s', resp.exception)
        except Exception as exc:
            logger.exception('FCM multicast failed: %s', exc)
            failure += len(batch)

    logger.info('FCM "%s" → success=%s failure=%s tokens=%s', title, success, failure, len(tokens))
    return {'success': success, 'failure': failure}


def is_fcm_configured() -> bool:
    return _get_firebase_app() is not None
