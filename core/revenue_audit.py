"""
Write ActivityLog rows for revenue-model payout / settlement events.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


def log_revenue_event(
    *,
    action: str,
    booking_id: Optional[str] = None,
    details: Optional[dict[str, Any] | str] = None,
    user: Optional[User] = None,
) -> None:
    try:
        from core.models import ActivityLog

        if isinstance(details, dict):
            detail_text = json.dumps(details, default=str)
        else:
            detail_text = details or ''
        ActivityLog.objects.create(
            user=user,
            action=action,
            booking_id=str(booking_id) if booking_id is not None else None,
            details=detail_text,
        )
    except Exception as exc:
        logger.exception('Revenue audit log failed (%s): %s', action, exc)
