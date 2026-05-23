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
    allowed_prefixes = (
        'job_selfies/',
        'technician_selfies/',
        'featured_images/',
        'quill_uploads/',
        'profiles/',
        'quotations/',
        'blog/',
        'partner_profiles/',
    )
    return any(path.startswith(prefix) for prefix in allowed_prefixes)


def full_storage_path(file_field) -> str | None:
    """
    Full object key for S3/local lookup (includes storage location prefix).

    Custom storage ImageField uses SelfieS3Storage(location='technician_selfies'); the DB often
    stores only ``2026/05/uuid.webp`` — the proxy must use
    ``technician_selfies/2026/05/uuid.webp``.
    """
    if not file_field or not file_field.name:
        return None
    name = file_field.name.replace('\\', '/').lstrip('/')
    known_roots = (
        'job_selfies/',
        'technician_selfies/',
        'featured_images/',
        'quill_uploads/',
        'profiles/',
        'quotations/',
        'blog/',
        'partner_profiles/',
    )
    if any(name.startswith(prefix) for prefix in known_roots):
        return name
    location = (getattr(file_field.storage, 'location', None) or '').strip('/')
    if location:
        return f'{location}/{name}'
    return name


def build_file_field_url(request, file_field) -> str | None:
    """
    Return a browser-loadable URL for ImageField/FileField.
    Job selfies use the API media proxy (private S3 — direct bucket URLs return Access Denied).
    Blog/media on public S3/CDN may use direct URLs when readable in the browser.
    """
    full_path = full_storage_path(file_field)
    if not full_path:
        return None

    if full_path.startswith(('job_selfies/', 'technician_selfies/')):
        return media_proxy_url(full_path)

    try:
        url = file_field.storage.url(file_field.name)
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
        return media_proxy_url(full_path)

    # Relative path
    if request:
        absolute = request.build_absolute_uri(url)
        if urlparse(absolute).hostname == urlparse(_public_api_base()).hostname:
            return media_proxy_url(full_path)
        return _rewrite_localhost(request, absolute)

    return media_proxy_url(full_path)
