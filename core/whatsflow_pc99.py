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
STAFF_LEAD_TEMPLATE_DEFAULT = "pc99_staff_inquiry_notice"
BOOKING_CONFIRMATION_TEMPLATE_DEFAULT = "pc99_booking_confirmation"
BOOKING_CONFIRMATION_TERMS_DEFAULT = "Standard service terms apply."
LANGUAGE = "en_US"

# Meta rejected pc99_website_lead_alert (INVALID_FORMAT): 7 vars and no examples.
# This copy matches approved pc99_inquiry_received (4 vars + sample values).
STAFF_LEAD_TEMPLATE_BODY = (
    "Dear Team,\n\n"
    "A customer inquiry was received on PestControl99.com.\n\n"
    "Inquiry Details:\n"
    "- Customer Name: {{1}}\n"
    "- Mobile Number: {{2}}\n"
    "- Service Type: {{3}}\n"
    "- Selected Area: {{4}}\n\n"
    "Please contact the customer with pricing and booking details.\n\n"
    "www.pestcontrol99.com\n"
    "Call: 8080748282\n\n"
    "Regards,\n"
    "PestControl99.com"
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


def _sso_access_token(*, timeout: float = 15) -> str | None:
    key = _api_key()
    if not key:
        return None
    try:
        res = requests.post(
            f"{_api_base()}/api/auth/sso-login/",
            json={"api_key": key},
            headers={"Content-Type": "application/json"},
            timeout=timeout,
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
    timeout: float = 20,
    sso_timeout: float | None = None,
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

    token = _sso_access_token(timeout=sso_timeout if sso_timeout is not None else min(15.0, timeout))
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
            timeout=timeout,
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
    Never sends to the customer mobile — recipient is always the staff number.
    Idempotency key: website-lead-staff:{inquiry_id}

    Approved template pc99_staff_inquiry_notice has 4 body vars:
      {{1}} Customer Name
      {{2}} Mobile Number
      {{3}} Service Type (+ property when available)
      {{4}} Selected Area (+ message when available)
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

    service_line = _str(service, "Pest Control")
    prop = _str(property_type, "")
    if prop and prop != "—":
        service_line = f"{service_line} ({prop})"

    area_line = _str(city)
    note = _str(message, "")
    if note and note != "—":
        area_line = f"{area_line} | {note}" if area_line != "—" else note

    params = [
        _str(name, "Customer"),
        _str(mobile),
        service_line,
        area_line,
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
    request_timeout: float = 8,
) -> bool:
    """
    Deliver customer-app OTP via WhatsFlow AUTH template (soft-fail).

    Configure Meta/WhatsFlow template name with settings.CUSTOMER_OTP_WHATSAPP_TEMPLATE
    (e.g. login_otp). AUTH templates accept a single body param — the OTP code.

    request_timeout caps SSO+send so OTP APIs never hang on Meta/WhatsFlow.
    """
    template = (getattr(settings, "CUSTOMER_OTP_WHATSAPP_TEMPLATE", "") or "").strip()
    if not template:
        logger.warning("Customer OTP WhatsApp skipped (CUSTOMER_OTP_WHATSAPP_TEMPLATE unset).")
        return False
    # AUTH / login_otp templates only have {{1}} = OTP. Do not send purpose as {{2}}.
    # Split budget roughly half for SSO, half for template send.
    budget = max(2.0, float(request_timeout))
    sso_budget = max(1.5, min(5.0, budget * 0.4))
    send_budget = max(1.5, budget - sso_budget)
    result = send_template_by_phone(
        phone=mobile,
        template_name=template,
        body_params=[str(otp)],
        customer_name=customer_name or "Customer",
        external_id=f"customer-otp:{normalize_whatsapp_phone(mobile)}:{purpose}",
        timeout=send_budget,
        sso_timeout=sso_budget,
    )
    return bool(result.get("ok"))


def _booking_amount(job) -> "Decimal":
    from decimal import Decimal

    from core.payment_utils import parse_jobcard_price

    price = parse_jobcard_price(getattr(job, "price", None))
    total = Decimal(str(getattr(job, "total_amount", None) or 0))
    return max(price, total)


def _format_service_date(job) -> str:
    """e.g. 05 Aug 2026 (IST calendar day)."""
    from zoneinfo import ZoneInfo

    from django.utils import timezone as dj_tz

    dt = getattr(job, "schedule_datetime", None)
    if not dt:
        return "—"
    if dj_tz.is_naive(dt):
        dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
    local = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    # %-d is not portable on Windows; strip leading zero manually.
    day = str(local.day)
    return f"{day.zfill(2)} {local.strftime('%b')} {local.year}"


def _format_service_time(job) -> str:
    """Prefer time_slot text; else schedule clock in 12h form (e.g. 10:00 AM)."""
    from zoneinfo import ZoneInfo

    from django.utils import timezone as dj_tz

    slot = (getattr(job, "time_slot", None) or "").strip()
    if slot:
        return _str(slot)

    dt = getattr(job, "schedule_datetime", None)
    if not dt:
        return "—"
    if dj_tz.is_naive(dt):
        dt = dj_tz.make_aware(dt, dj_tz.get_current_timezone())
    local = dt.astimezone(ZoneInfo("Asia/Kolkata"))
    return local.strftime("%I:%M %p").lstrip("0")


def _format_amount_inr(job) -> str:
    """Plain INR number for template body that already says 'INR {{7}}'."""
    amount = _booking_amount(job)
    if amount <= 0:
        return "0"
    if amount == amount.to_integral_value():
        return str(int(amount))
    return f"{amount:.2f}".rstrip("0").rstrip(".")


def _selected_area(job) -> str:
    loc = getattr(job, "master_location", None)
    if loc is not None and getattr(loc, "name", None):
        return _str(loc.name)
    for attr in ("city", "bhk_size", "client_address"):
        val = (getattr(job, attr, None) or "").strip()
        if val:
            return _str(val)
    return "—"


def build_booking_confirmation_params(job) -> list[str]:
    """
    Body params for approved Meta template pc99_booking_confirmation:

      {{1}} Customer name
      {{2}} Booking ID
      {{3}} Service Type
      {{4}} Selected Area
      {{5}} Service Date
      {{6}} Service Time
      {{7}} Amount (INR number)
      {{8}} Terms & Conditions
    """
    client = getattr(job, "client", None)
    name = getattr(client, "full_name", None) if client is not None else None
    terms = (
        getattr(settings, "BOOKING_CONFIRMATION_WHATSAPP_TERMS", "") or ""
    ).strip() or BOOKING_CONFIRMATION_TERMS_DEFAULT
    return [
        _str(name, "Customer"),
        _str(getattr(job, "code", None) or getattr(job, "pk", None), "—"),
        _str(getattr(job, "service_type", None), "Pest Control"),
        _selected_area(job),
        _format_service_date(job),
        _format_service_time(job),
        _format_amount_inr(job),
        _str(terms, BOOKING_CONFIRMATION_TERMS_DEFAULT),
    ]


def booking_confirmation_eligible(
    job,
    *,
    previous_amount=None,
    allow_estimated: bool = False,
) -> bool:
    """
    True when this JobCard should receive pc99_booking_confirmation.

    Skips drafts (no price), estimated pending quotes, follow-ups, complaints,
    auto-generated visits, and cancelled jobs.
    When previous_amount is provided (CRM edit), only fire on 0 → >0 transition.
    """
    from decimal import Decimal

    if job is None or not getattr(job, "pk", None):
        return False

    from core.models import JobCard

    if getattr(job, "status", None) == JobCard.JobStatus.CANCELLED:
        return False
    if getattr(job, "is_complaint_call", False):
        return False
    if getattr(job, "is_followup_visit", False):
        return False
    if getattr(job, "parent_job_id", None):
        return False
    if getattr(job, "is_auto_generated", False):
        return False

    source = getattr(job, "creation_source", None) or ""
    if source in {
        JobCard.CreationSource.AMC_AUTO,
        JobCard.CreationSource.REMINDER_AUTO,
        JobCard.CreationSource.COMPLAINT_AUTO,
    }:
        return False

    amount = _booking_amount(job)
    if amount <= 0:
        return False

    if previous_amount is not None:
        try:
            prev = Decimal(str(previous_amount))
        except Exception:
            prev = Decimal("0")
        if prev > 0:
            return False
    elif not allow_estimated and getattr(job, "is_price_estimated", False):
        return False

    client = getattr(job, "client", None)
    mobile = getattr(client, "mobile", None) if client is not None else None
    if not mobile or not str(mobile).strip():
        return False
    return True


def notify_booking_confirmation(job) -> dict[str, Any]:
    """
    Send pc99_booking_confirmation to the customer (soft-fail).

    Returns WhatsFlow-style dict: {ok, message_id, error, skipped?}.
    Never raises.
    """
    try:
        enabled = getattr(settings, "BOOKING_CONFIRMATION_WHATSAPP_ENABLED", True)
        if not enabled:
            return {"ok": False, "message_id": "", "error": "disabled", "skipped": True}

        if not booking_confirmation_eligible(job, allow_estimated=True):
            return {"ok": False, "message_id": "", "error": "not_eligible", "skipped": True}

        template = (
            getattr(settings, "BOOKING_CONFIRMATION_WHATSAPP_TEMPLATE", "")
            or BOOKING_CONFIRMATION_TEMPLATE_DEFAULT
        ).strip()

        client = job.client
        params = build_booking_confirmation_params(job)
        result = send_template_by_phone(
            phone=client.mobile,
            template_name=template,
            body_params=params,
            customer_name=getattr(client, "full_name", None) or "Customer",
            external_id=f"booking-confirmation:{job.pk}",
        )
        result["skipped"] = False
        if not result.get("ok"):
            logger.warning(
                "Booking confirmation WhatsApp failed for job #%s: %s",
                job.pk,
                result.get("error"),
            )
        return result
    except Exception as exc:
        logger.error(
            "Booking confirmation WhatsApp error for job #%s: %s",
            getattr(job, "pk", None),
            exc,
            exc_info=True,
        )
        return {"ok": False, "message_id": "", "error": str(exc)[:400], "skipped": False}


def schedule_booking_confirmation_whatsapp(
    job,
    *,
    previous_amount=None,
) -> None:
    """
    Soft-fail send after the surrounding DB transaction commits.

    Covers website / customer-app / CRM create via JobCardService.create_jobcard,
    CRM price confirm on edit, and quotation convert.
    """
    from django.db import transaction

    if job is None or not getattr(job, "pk", None):
        return

    job_id = job.pk
    prev = previous_amount

    def _run():
        try:
            from core.models import JobCard

            latest = (
                JobCard.objects.select_related("client", "master_location")
                .filter(pk=job_id)
                .first()
            )
            if not latest:
                return
            if not booking_confirmation_eligible(latest, previous_amount=prev):
                return
            notify_booking_confirmation(latest)
        except Exception:
            logger.exception(
                "schedule_booking_confirmation_whatsapp failed for job #%s",
                job_id,
            )

    if transaction.get_connection().in_atomic_block:
        transaction.on_commit(_run)
    else:
        _run()
