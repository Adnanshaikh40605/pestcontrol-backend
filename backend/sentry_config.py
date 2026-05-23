"""
Sentry error monitoring for Django (pest99 organization).

Configure via settings: SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_initialized = False


def get_sentry_status() -> dict:
    from django.conf import settings

    dsn = (getattr(settings, 'SENTRY_DSN', None) or '').strip()
    return {
        'configured': bool(dsn) and _initialized,
        'dsn_present': bool(dsn),
        'environment': (getattr(settings, 'SENTRY_ENVIRONMENT', None) or 'production').strip(),
    }


def _before_send(event, hint):
    request = event.get('request') or {}
    url = (request.get('url') or '').lower()
    if '/health/' in url or url.endswith('/health'):
        return None
    if '/api/v1/health/' in url:
        return None
    exc_info = hint.get('exc_info')
    if exc_info and exc_info[0].__name__ == 'Http404':
        return None
    return event


def init_sentry() -> None:
    global _initialized
    from django.conf import settings

    dsn = (getattr(settings, 'SENTRY_DSN', None) or '').strip()
    if not dsn:
        logger.info('Sentry disabled (SENTRY_DSN not set)')
        return
    if _initialized:
        return

    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    debug = getattr(settings, 'DEBUG', False)
    environment = (getattr(settings, 'SENTRY_ENVIRONMENT', None) or 'production').strip()
    raw_rate = getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', '0.1')
    try:
        traces_rate = float(raw_rate)
    except (TypeError, ValueError):
        traces_rate = 0.1
    if debug and traces_rate > 0.2:
        traces_rate = 0.0

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=False,
            ),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            ),
        ],
        traces_sample_rate=traces_rate,
        send_default_pii=False,
        before_send=_before_send,
        attach_stacktrace=True,
        max_breadcrumbs=50,
    )
    _initialized = True
    logger.info('Sentry initialized (env=%s, traces=%s)', environment, traces_rate)
