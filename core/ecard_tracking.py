"""
Helpers for E-Card visit tracking: device, traffic source, city-from-IP.
Keep lookups fast — never block the e-card page for long.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional
from urllib.error import URLError, HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

DEVICE_MOBILE = 'Mobile'
DEVICE_DESKTOP = 'Desktop'
DEVICE_TABLET = 'Tablet'

SOURCE_GOOGLE = 'Google Search'
SOURCE_FACEBOOK = 'Facebook'
SOURCE_INSTAGRAM = 'Instagram'
SOURCE_WHATSAPP = 'WhatsApp'
SOURCE_YOUTUBE = 'YouTube'
SOURCE_LINKEDIN = 'LinkedIn'
SOURCE_EMAIL = 'Email'
SOURCE_DIRECT = 'Direct Link'
SOURCE_REFERRAL = 'Another Website (Referral)'


def get_client_ip(request) -> Optional[str]:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR') or request.META.get('HTTP_X_REAL_IP')
    if forwarded:
        return forwarded.split(',')[0].strip() or None
    return request.META.get('REMOTE_ADDR') or None


def detect_device_type(user_agent: str) -> str:
    ua = (user_agent or '').lower()
    if not ua:
        return DEVICE_DESKTOP
    if re.search(r'ipad|tablet|kindle|silk|playbook', ua):
        return DEVICE_TABLET
    # Android tablets often omit "mobile"
    if 'android' in ua and 'mobile' not in ua:
        return DEVICE_TABLET
    if re.search(r'mobi|iphone|ipod|android.*mobile|windows phone|blackberry', ua):
        return DEVICE_MOBILE
    return DEVICE_DESKTOP


def _utm_from_landing(landing_url: str) -> str:
    if not landing_url:
        return ''
    try:
        qs = parse_qs(urlparse(landing_url).query)
        for key in ('utm_source', 'utm_medium', 'source', 'fbclid', 'gclid'):
            vals = qs.get(key) or []
            if vals:
                return str(vals[0])
    except Exception:
        return ''
    return ''


def detect_traffic_source(
    referrer: str = '',
    utm_source: str = '',
    landing_url: str = '',
) -> str:
    utm = (utm_source or _utm_from_landing(landing_url) or '').lower().strip()
    ref = (referrer or '').lower().strip()
    landing = (landing_url or '').lower()

    blob = f'{utm} {ref} {landing}'

    if any(k in blob for k in ('whatsapp', 'wa.me', 'wa_click', 'wame')):
        return SOURCE_WHATSAPP
    if any(k in blob for k in ('instagram', 'ig.', 'ig_')) or 'l.instagram.com' in ref:
        return SOURCE_INSTAGRAM
    if any(k in blob for k in ('facebook', 'fb.', 'fbclid', 'meta.com')) or 'l.facebook.com' in ref:
        return SOURCE_FACEBOOK
    if any(k in blob for k in ('youtube', 'youtu.be', 'yt.')):
        return SOURCE_YOUTUBE
    if any(k in blob for k in ('linkedin', 'lnkd.')):
        return SOURCE_LINKEDIN
    if any(k in blob for k in ('email', 'newsletter', 'mailchimp', 'outlook', 'gmail')) or utm in {
        'email',
        'e-mail',
        'mail',
    }:
        return SOURCE_EMAIL
    if any(k in blob for k in ('google.', 'google.com', 'googleads', 'gclid', 'bing.com', 'yahoo.com')):
        # Organic / paid search via Google (and common search engines mapped to Google Search label)
        if 'google' in blob or 'gclid' in blob:
            return SOURCE_GOOGLE
        # Non-Google search engines → still treat as search-like referral website
        return SOURCE_REFERRAL
    if utm in {'google', 'google_search', 'organic', 'cpc', 'seo'}:
        return SOURCE_GOOGLE

    if not ref or 'pestcontrol99.com' in ref:
        return SOURCE_DIRECT

    return SOURCE_REFERRAL


def city_from_request_headers(request) -> str:
    for header in (
        'HTTP_CF_IPCITY',
        'HTTP_X_VERCEL_IP_CITY',
        'HTTP_X_APPENGINE_CITY',
    ):
        value = (request.META.get(header) or '').strip()
        if value:
            # Cloudflare may URL-encode spaces as %20
            try:
                from urllib.parse import unquote

                value = unquote(value)
            except Exception:
                pass
            return value[:100]
    return ''


def lookup_city_by_ip(ip: Optional[str], timeout: float = 1.2) -> str:
    """Best-effort city lookup. Fails open to Unknown — never raise."""
    if not ip or ip in {'127.0.0.1', '::1', 'localhost'}:
        return 'Unknown'
    # Skip private ranges
    if ip.startswith(('10.', '192.168.', '172.')):
        return 'Unknown'
    try:
        req = Request(
            f'http://ip-api.com/json/{ip}?fields=status,city',
            headers={'User-Agent': 'PestControl99-ECard/1.0'},
        )
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))
        if data.get('status') == 'success' and data.get('city'):
            return str(data['city'])[:100]
    except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.debug('E-Card geo lookup failed for %s: %s', ip, exc)
    except Exception as exc:  # noqa: BLE001 — never break tracking
        logger.debug('E-Card geo lookup unexpected error: %s', exc)
    return 'Unknown'


def resolve_city(request, client_city: str = '') -> str:
    if client_city and client_city.strip() and client_city.strip().lower() != 'unknown':
        return client_city.strip()[:100]
    header_city = city_from_request_headers(request)
    if header_city:
        return header_city
    return lookup_city_by_ip(get_client_ip(request))
