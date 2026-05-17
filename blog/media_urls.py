"""Build browser-loadable public URLs for uploaded blog media."""

from urllib.parse import urlparse, urlunparse

from django.conf import settings


def build_public_media_url(request, url_or_path: str) -> str:
    """
    Return an absolute URL that the CRM/browser can load in <img src>.
    Fixes localhost / wrong Host headers behind Railway proxies.
    """
    if not url_or_path:
        return url_or_path

    if url_or_path.startswith(("http://", "https://")):
        url = url_or_path
    elif request:
        url = request.build_absolute_uri(url_or_path)
    else:
        url = url_or_path

    public_base = getattr(settings, "PUBLIC_API_BASE_URL", "").strip().rstrip("/")
    if not public_base:
        return url

    if "://" not in public_base:
        public_base = f"https://{public_base}"

    parsed = urlparse(url)
    base_parsed = urlparse(public_base)

    rewrite_hosts = {"localhost", "127.0.0.1", "0.0.0.0"}
    if parsed.hostname in rewrite_hosts:
        return urlunparse(
            (
                base_parsed.scheme or "https",
                base_parsed.netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

    return url
