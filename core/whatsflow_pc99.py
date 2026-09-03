"""
Soft-fail WhatsFlow (Meta Cloud API) helpers for Pest Control 99 templates.

Used for website inquiry auto-replies and staff lead alerts where the CRM
frontend is not in the loop. Never raises to callers — inquiry creation must
not break if Meta/WhatsFlow is unavailable.
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
STAFF_LEAD_TEMPLATE_DEFAULT = "pc99_website_lead_alert"
LANGUAGE = "en_US"

STAFF_LEAD_TEMPLATE_BODY = (
    "New website inquiry received.\n\n"
    "Lead ID: {{1}}\n"
    "Customer: {{2}}\n"
    "Phone: {{3}}\n"
    "City: {{4}}\n"
    "Service: {{5}}\n"
    "Property: {{6}}\n"
    "Message: {{7}}\n\n"
    "Open CRM Website Leads to follow up."
)


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
    # WhatsApp templates reject very long variable values / newlines poorly.
    text = re.sub(r"\s+", " ", text)
    if len(text) > 240:
        text = text[:237] + "..."
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
) -> dict[str, Any]:
    """
    Send a WhatsFlow template message.

    Returns:
        {"ok": bool, "message_id": str, "error": str}
    """
    if not _is_configured():
        return {"ok": False, "message_id": "", "error": "whatsflow_not_configured"}

    digits = normalize_whatsapp_phone(phone)
    if len(digits) < 12:
        return {"ok": False, "message_id": "", "error": "invalid_phone"}

    token = _sso_access_token()
    if not token:
        return {"ok": False, "message_id": "", "error": "whatsflow_sso_failed"}

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
        payload = res.json() if res.content else {}
        if res.ok:
            data = payload.get("data") if isinstance(payload, dict) else None
            record = data if isinstance(data, dict) else payload if isinstance(payload, dict) else {}
            message_id = str(
                (record or {}).get("message_id")
                or (record or {}).get("wamid")
                or (record or {}).get("id")
                or ""
            )
            return {"ok": True, "message_id": message_id, "error": ""}
        err = ""
        if isinstance(payload, dict):
            err = str(
                payload.get("error")
                or (payload.get("error") or {})
                or payload.get("detail")
                or payload.get("message")
                or res.text[:300]
            )
            if isinstance(payload.get("error"), dict):
                err = str(payload["error"].get("detail") or payload["error"])[:400]
        else:
            err = res.text[:300]
        logger.warning(
            "WhatsFlow template %s failed status=%s body=%s",
            template_name,
            res.status_code,
            res.text[:400],
        )
        return {"ok": False, "message_id": "", "error": err or f"http_{res.status_code}"}
    except requests.RequestException as exc:
        logger.error("WhatsFlow template error: %s", exc, exc_info=True)
        return {"ok": False, "message_id": "", "error": str(exc)[:400]}


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
    result = send_template_by_phone(
        phone=mobile,
        template_name=INQUIRY_TEMPLATE,
        body_params=params,
        customer_name=name,
        external_id=external,
    )
    return bool(result.get("ok"))


def notify_staff_website_lead(
    *,
    inquiry_id: int | str,
    name: str,
    mobile: str,
    city: str | None = None,
    service: str | None = None,
    property_type: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """
    Notify configured staff WhatsApp about a new website lead.

    Soft-fail. Uses WEBSITE_LEAD_STAFF_WHATSAPP + WEBSITE_LEAD_STAFF_WHATSAPP_TEMPLATE.
    Idempotency key: website-lead-staff:{inquiry_id}
    """
    enabled = getattr(settings, "WEBSITE_LEAD_STAFF_WHATSAPP_ENABLED", True)
    if not enabled:
        return {"ok": False, "message_id": "", "error": "disabled", "skipped": True}

    staff_phone = (getattr(settings, "WEBSITE_LEAD_STAFF_WHATSAPP", "") or "").strip()
    if not staff_phone:
        return {"ok": False, "message_id": "", "error": "staff_phone_unset", "skipped": True}

    template = (
        getattr(settings, "WEBSITE_LEAD_STAFF_WHATSAPP_TEMPLATE", "") or STAFF_LEAD_TEMPLATE_DEFAULT
    ).strip()
    params = [
        _str(inquiry_id),
        _str(name, "Customer"),
        _str(mobile),
        _str(city),
        _str(service, "Pest Control"),
        _str(property_type, "Residential"),
        _str(message, "—"),
    ]
    result = send_template_by_phone(
        phone=staff_phone,
        template_name=template,
        body_params=params,
        customer_name="Staff",
        external_id=f"website-lead-staff:{inquiry_id}",
    )
    result["skipped"] = False
    return result


def ensure_staff_lead_template_draft(*, force: bool = False) -> dict[str, Any]:
    """
    Create (or return existing) WhatsFlow draft for the staff lead alert template.

    Does not submit to Meta automatically — operator must Submit in WhatsFlow CRM
    or WhatsApp Manager, then wait for APPROVED before production sends succeed.
    """
    if not _is_configured():
        return {"ok": False, "error": "whatsflow_not_configured"}

    token = _sso_access_token()
    if not token:
        return {"ok": False, "error": "whatsflow_sso_failed"}

    template_name = (
        getattr(settings, "WEBSITE_LEAD_STAFF_WHATSAPP_TEMPLATE", "") or STAFF_LEAD_TEMPLATE_DEFAULT
    ).strip()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        listed = requests.get(
            f"{_api_base()}/api/v1/campaigns/templates/?search={template_name}",
            headers=headers,
            timeout=20,
        )
        if listed.ok:
            rows = (listed.json() or {}).get("results") or []
            for row in rows:
                if (row.get("name") or "") == template_name and not force:
                    return {
                        "ok": True,
                        "created": False,
                        "id": row.get("id"),
                        "name": template_name,
                        "status": row.get("status"),
                        "meta_status": row.get("meta_status"),
                        "category": row.get("category"),
                    }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)[:300]}

    payload = {
        "name": template_name,
        "language": LANGUAGE,
        "category": "utility",
        "body": STAFF_LEAD_TEMPLATE_BODY,
        "allow_category_change": True,
    }
    try:
        created = requests.post(
            f"{_api_base()}/api/v1/campaigns/templates/",
            headers=headers,
            json=payload,
            timeout=30,
        )
        body = created.json() if created.content else {}
        if created.ok or created.status_code == 201:
            return {
                "ok": True,
                "created": True,
                "id": body.get("id"),
                "name": template_name,
                "status": body.get("status"),
                "meta_status": body.get("meta_status"),
                "category": body.get("category"),
                "body": body.get("body") or STAFF_LEAD_TEMPLATE_BODY,
            }
        return {
            "ok": False,
            "error": str(body.get("error") or body.get("detail") or created.text[:300]),
        }
    except requests.RequestException as exc:
        return {"ok": False, "error": str(exc)[:300]}


def notify_customer_otp(
    *,
    mobile: str,
    otp: str,
    purpose: str = "login",
    customer_name: str | None = None,
) -> bool:
    """
    Deliver customer-app OTP via WhatsFlow AUTH template (soft-fail).

    Configure Meta/WhatsFlow template name with settings.CUSTOMER_OTP_WHATSAPP_TEMPLATE
    (e.g. login_otp). AUTH templates accept a single body param — the OTP code.
    """
    template = (getattr(settings, "CUSTOMER_OTP_WHATSAPP_TEMPLATE", "") or "").strip()
    if not template:
        logger.warning("Customer OTP WhatsApp skipped (CUSTOMER_OTP_WHATSAPP_TEMPLATE unset).")
        return False
    # AUTH / login_otp templates only have {{1}} = OTP. Do not send purpose as {{2}}.
    result = send_template_by_phone(
        phone=mobile,
        template_name=template,
        body_params=[str(otp)],
        customer_name=customer_name or "Customer",
        external_id=f"customer-otp:{normalize_whatsapp_phone(mobile)}:{purpose}",
    )
    return bool(result.get("ok"))
