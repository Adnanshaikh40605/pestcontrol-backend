"""Public URLs for uploaded files (job selfies, etc.)."""

from urllib.parse import quote, urlparse, urlunparse

from django.conf import settings
from django.core.files.storage import default_storage


def _public_api_base() -> str:
    base = getattr(settings, 'PUBLIC_API_BASE_URL', 'https://api.vacationbna.site').strip().rstrip('/')
    if '://' not in base:
        base = f'https://{base}'
    return base


def _rewrite_localhost(request, url: str) -> str:
    from blog.media_urls import build_public_media_url

    return build_public_media_url(request, url)


def media_proxy_url(file_name: str) -> str:
    """CRM-safe URL that streams the file through the API (works when /media/ 404s on Railway)."""
    return f"{_public_api_base()}/api/v1/media-file/?path={quote(file_name, safe='')}"


def is_safe_media_path(path: str) -> bool:
    if not path or '..' in path or path.startswith('/'):
        return False
    allowed_prefixes = ('job_selfies/', 'blog/')
    return any(path.startswith(prefix) for prefix in allowed_prefixes)


def build_file_field_url(request, file_field) -> str | None:
    """
    Return a browser-loadable URL for ImageField/FileField.
    Prefer direct S3/CDN URLs; fall back to API media proxy for local/Railway storage.
    """
    if not file_field or not file_field.name:
        return None

    try:
        url = default_storage.url(file_field.name)
    except Exception:
        return None

    if url.startswith(('http://', 'https://')):
        parsed = urlparse(url)
        api_host = urlparse(_public_api_base()).hostname

        if parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0'):
            return _rewrite_localhost(request, url)

        # Direct object storage / CDN (not API /media/ mount)
        if parsed.hostname != api_host:
            return url

        # Absolute URL on API host — often /media/... which 404s on Railway; use proxy
        return media_proxy_url(file_field.name)

    # Relative path
    if request:
        absolute = request.build_absolute_uri(url)
        if urlparse(absolute).hostname == urlparse(_public_api_base()).hostname:
            return media_proxy_url(file_field.name)
        return _rewrite_localhost(request, absolute)

    return media_proxy_url(file_field.name)
