"""
Utility helpers for sending notifications via Telegram.
"""
from __future__ import annotations

import logging
from typing import Iterable

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    """
    Return True when Telegram credentials are configured.

    Ensures we have both a bot token and a chat id before attempting to send
    anything to Telegram. This allows environments without credentials to
    simply skip the notification logic.
    """
    enabled = getattr(settings, "TELEGRAM_NOTIFICATIONS_ENABLED", False)
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", "")
    return bool(enabled and token and chat_id)


def send_telegram_message(text: str) -> bool:
    """
    Send a plain-text message to the configured Telegram chat.

    Returns:
        bool: True when Telegram acknowledges the request, False otherwise.
    """
    if not _is_configured():
        logger.debug("Telegram notification skipped (credentials missing).")
        return False

    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.ok:
            return True

        logger.warning(
            "Telegram notification failed with status %s: %s",
            response.status_code,
            response.text,
        )
    except requests.RequestException as exc:
        logger.error("Telegram notification error: %s", exc, exc_info=True)

    return False


def notify_new_inquiry(*, name: str, mobile: str, city: str, service: str, message: str, email: str | None = None) -> bool:
    """
    Format and dispatch a Telegram notification for a newly created inquiry.

    Args:
        name: Customer name.
        mobile: Customer contact number.
        city: City provided in the inquiry.
        service: Service interest detail.
        message: Inquiry message body.
        email: Optional email address supplied by the customer.
    """
    timestamp = timezone.now().astimezone().strftime("%Y-%m-%d %H:%M")

    details: Iterable[str] = (
        f"New inquiry received ({timestamp})",
        "",
        f"Name   : {name or 'N/A'}",
        f"Mobile : {mobile or 'N/A'}",
        f"City   : {city or 'N/A'}",
        f"Service: {service or 'N/A'}",
        *( [f"Email  : {email}"] if email else [] ),
        "",
        "Message:",
        message or "N/A",
    )

    text = "\n".join(details)
    return send_telegram_message(text)


