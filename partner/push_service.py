"""
Firebase Cloud Messaging for Pest 99 Partner app.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_init_error: str | None = None


def get_fcm_config_status() -> dict[str, Any]:
    """
    Diagnose partner FCM setup (no secrets). Used by health check and CRM warnings.
    """
    project_id = getattr(settings, 'PARTNER_FIREBASE_PROJECT_ID', 'pest-99-partner-app')
    sa_json = (getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', '') or '').strip()
    private_key = (getattr(settings, 'FIREBASE_PRIVATE_KEY', '') or '').strip()
    client_email = (getattr(settings, 'FIREBASE_CLIENT_EMAIL', '') or '').strip()
    cred_path = (getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or '').strip()

    has_json = bool(sa_json)
    has_split = bool(private_key and client_email)
    has_file = bool(cred_path)

    if not has_json and not has_split and not has_file:
        return {
            'configured': False,
            'project_id': project_id,
            'reason': (
                'Missing Firebase credentials on the server. On Railway set '
                'FIREBASE_SERVICE_ACCOUNT_JSON (recommended) or FIREBASE_CLIENT_EMAIL + '
                'FIREBASE_PRIVATE_KEY from Firebase project pest-99-partner-app.'
            ),
            'has_service_account_json': False,
            'has_client_email': bool(client_email),
            'has_private_key': bool(private_key),
        }

    if _firebase_init_error:
        return {
            'configured': False,
            'project_id': project_id,
            'reason': f'Firebase credentials present but invalid: {_firebase_init_error}',
            'has_service_account_json': has_json,
            'has_client_email': has_split,
        }

    app = _get_firebase_app()
    if app is None:
        return {
            'configured': False,
            'project_id': project_id,
            'reason': _firebase_init_error or 'Firebase Admin failed to initialize',
            'has_service_account_json': has_json,
            'has_client_email': has_split,
        }

    return {
        'configured': True,
        'project_id': project_id,
        'reason': 'ok',
        'has_service_account_json': has_json,
        'has_client_email': has_split,
    }


def _get_firebase_app():
    global _firebase_app, _firebase_init_error
    if _firebase_app is not None:
        return _firebase_app

    import firebase_admin
    from firebase_admin import credentials

    project_id = getattr(settings, 'PARTNER_FIREBASE_PROJECT_ID', 'pest-99-partner-app')
    sa_json = (getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_JSON', '') or '').strip()
    private_key = (getattr(settings, 'FIREBASE_PRIVATE_KEY', '') or '').strip()
    client_email = (getattr(settings, 'FIREBASE_CLIENT_EMAIL', '') or '').strip()
    private_key_id = (getattr(settings, 'FIREBASE_PRIVATE_KEY_ID', '') or '').strip()

    try:
        if sa_json:
            cred_dict = json.loads(sa_json)
            if isinstance(cred_dict.get('private_key'), str) and '\\n' in cred_dict['private_key']:
                cred_dict['private_key'] = cred_dict['private_key'].replace('\\n', '\n')
            cred = credentials.Certificate(cred_dict)
            project_id = cred_dict.get('project_id') or project_id
            try:
                _firebase_app = firebase_admin.get_app('partner-fcm')
            except ValueError:
                _firebase_app = firebase_admin.initialize_app(
                    cred, {'projectId': project_id}, name='partner-fcm'
                )
            logger.info('Firebase Admin ready for partner FCM (JSON, project=%s)', project_id)
            _firebase_init_error = None
            return _firebase_app
    except json.JSONDecodeError as exc:
        _firebase_init_error = f'FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}'
        logger.error(_firebase_init_error)
        return None
    except Exception as exc:
        _firebase_init_error = str(exc)
        logger.exception('Firebase JSON credentials failed: %s', exc)
        return None

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
        _firebase_init_error = None
        return _firebase_app

    cred_path = (getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or '').strip()
    if cred_path:
        try:
            cred = credentials.Certificate(cred_path)
            try:
                _firebase_app = firebase_admin.get_app('partner-fcm')
            except ValueError:
                _firebase_app = firebase_admin.initialize_app(
                    cred, {'projectId': project_id}, name='partner-fcm'
                )
            _firebase_init_error = None
            return _firebase_app
        except Exception as exc:
            _firebase_init_error = str(exc)
            logger.exception('Firebase file credentials failed: %s', exc)
            return None

    _firebase_init_error = 'No Firebase credentials configured'
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
    channel_id: str = 'pest99_bookings',
    sound: str | None = None,
    data_only: bool = False,
) -> dict[str, int]:
    """
    Send FCM. For new bookings use data_only=True so the app shows a high-priority local
    notification with the correct channel + custom sound (avoids silent system tray).
    """
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

    android_config = messaging.AndroidConfig(
        priority='high',
        collapse_key=collapse_key,
    )
    if not data_only:
        android_notification = messaging.AndroidNotification(
            channel_id=channel_id,
            sound=sound or 'default',
            priority=messaging.AndroidNotificationPriority.HIGH,
            tag=collapse_key or payload_data.get('booking_id'),
            visibility='public',
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
            if data_only:
                message = messaging.MulticastMessage(
                    data=payload_data,
                    tokens=batch,
                    android=android_config,
                )
            else:
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
    return get_fcm_config_status().get('configured') is True
