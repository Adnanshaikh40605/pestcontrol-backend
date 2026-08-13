"""
Soft-fail WhatsFlow (Meta Cloud API) helpers for Pest Control 99 templates.

Used for website inquiry auto-replies where the CRM frontend is not in the loop.
Never raises to callers — booking/inquiry creation must not break.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Sequence

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = "https://api.driveronhire.ai"
INQUIRY_TEMPLATE = "pc99_inquiry_received"
LANGUAGE = "en_US"


def _api_base() -> str:
    base = (getattr(settings, "WHATSFLOW_API_URL", "") or DEFAULT_API_BASE).strip()
    return re.sub(r"/api/?$", "", base).rstrip("/")


def _api_key() -> str:
    return (getattr(settings, "WHATSFLOW_API_KEY", "") or "").strip()


def _is_configured() -> bool:
    return bool(_api_key())


def normalize_whatsapp_phone(raw: str | None) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = f"91{digits}"
    return digits


def _str(value: Any, fallback: str = "—") -> str:
    text = str(value or "").strip()
    return text or fallback


def _sso_access_token() -> str | None:
    key = _api_key()
    if not key:
        return None
    try:
        res = requests.post(
            f"{_api_base()}/api/auth/sso-login/",
            json={"api_key": key},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if not res.ok:
            logger.warning(
                "WhatsFlow SSO failed status=%s body=%s",
                res.status_code,
                res.text[:300],
            )
            return None
        payload = res.json() if res.content else {}
        data = payload.get("data") if isinstance(payload, dict) else None
        record = data if isinstance(data, dict) else payload
        token = str((record or {}).get("access_token") or "").strip()
        return token or None
    except requests.RequestException as exc:
        logger.error("WhatsFlow SSO error: %s", exc, exc_info=True)
        return None


def send_template_by_phone(
    *,
    phone: str,
    template_name: str,
    body_params: Sequence[str],
    customer_name: str | None = None,
    external_id: str | None = None,
) -> bool:
    if not _is_configured():
        logger.debug("WhatsFlow skipped (WHATSFLOW_API_KEY missing).")
        return False

    digits = normalize_whatsapp_phone(phone)
    if len(digits) < 12:
        logger.warning("WhatsFlow skipped invalid phone for template %s", template_name)
        return False

    token = _sso_access_token()
    if not token:
        return False

    body: dict[str, Any] = {
        "phone": digits,
        "template_name": template_name,
        "language": LANGUAGE,
        "body_params": list(body_params),
    }
    if customer_name:
        body["customer_name"] = customer_name
    if external_id:
        body["external_id"] = external_id

    try:
        res = requests.post(
            f"{_api_base()}/api/inbox/messages/template/",
            json=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=20,
        )
        if res.ok:
            return True
        logger.warning(
            "WhatsFlow template %s failed status=%s body=%s",
            template_name,
            res.status_code,
            res.text[:400],
        )
    except requests.RequestException as exc:
        logger.error("WhatsFlow template error: %s", exc, exc_info=True)
    return False


def notify_inquiry_received(
    *,
    name: str,
    mobile: str,
    service: str | None = None,
    area: str | None = None,
    property_type: str | None = None,
    inquiry_id: int | str | None = None,
) -> bool:
    """Send pc99_inquiry_received to the customer (website lead). Soft-fail."""
    params = [
        _str(name, "Customer"),
        _str(service, "Pest Control"),
        _str(area),
        _str(property_type, "Residential"),
    ]
    external = f"website-inquiry:{inquiry_id}" if inquiry_id is not None else None
    return send_template_by_phone(
        phone=mobile,
        template_name=INQUIRY_TEMPLATE,
        body_params=params,
        customer_name=name,
        external_id=external,
    )


def notify_customer_otp(
    *,
    mobile: str,
    otp: str,
    purpose: str = "login",
    customer_name: str | None = None,
) -> bool:
    """
    Deliver customer-app OTP via WhatsFlow template (soft-fail).

    Configure Meta/WhatsFlow template name with settings.CUSTOMER_OTP_WHATSAPP_TEMPLATE.
    Template body must accept OTP as the first body parameter.
    """
    template = (getattr(settings, "CUSTOMER_OTP_WHATSAPP_TEMPLATE", "") or "").strip()
    if not template:
        logger.warning("Customer OTP WhatsApp skipped (CUSTOMER_OTP_WHATSAPP_TEMPLATE unset).")
        return False
    return send_template_by_phone(
        phone=mobile,
        template_name=template,
        body_params=[str(otp), purpose],
        customer_name=customer_name or "Customer",
        external_id=f"customer-otp:{normalize_whatsapp_phone(mobile)}",
    )
