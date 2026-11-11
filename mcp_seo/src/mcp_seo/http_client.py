"""Safe HTTP client with host allowlists, size limits, and caching."""

from __future__ import annotations

import ipaddress
import logging
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from mcp_seo.cache import CACHE
from mcp_seo.config import SiteConfig, Settings, get_settings

logger = logging.getLogger("mcp_seo.http")

# Only these API path prefixes may be fetched from the public API host.
ALLOWED_API_PREFIXES = (
    "/api/public/blogs/",
    "/api/public/categories/",
    "/api/public/tags/",
    "/api/public/related-blogs/",
    "/api/customer/catalog/",
    "/api/customer/cities/",
    "/api/customer/locations/",
    "/api/v1/deepcleaning-rates/catalog/",
    "/api/deepcleaning-rates/catalog/",
)


class HttpSafetyError(ValueError):
    pass


def _host_allowed(hostname: str, settings: Settings, site: SiteConfig) -> bool:
    host = (hostname or "").lower().rstrip(".")
    if not host:
        return False
    allowed = {
        urlparse(site.site_base).hostname or "",
        urlparse(settings.public_api_base).hostname or "",
        "www.pestcontrol99.com",
        "pestcontrol99.com",
        "deepcleaning99.com",
        "www.deepcleaning99.com",
        "api.vacationbna.site",
    }
    allowed = {h.lower() for h in allowed if h}
    return host in allowed


def _is_private_host(hostname: str) -> bool:
    try:
        ip = ipaddress.ip_address(hostname)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        return hostname.lower() in {"localhost", "metadata.google.internal"}


def resolve_site_url(site: SiteConfig, path_or_url: str) -> str:
    raw = (path_or_url or "/").strip()
    if not raw:
        raw = "/"
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        site_host = (urlparse(site.site_base).hostname or "").lower()
        if (parsed.hostname or "").lower() != site_host:
            raise HttpSafetyError("URL host is outside the allowed site origin")
        path = parsed.path or "/"
    else:
        path = raw if raw.startswith("/") else f"/{raw}"

    if ".." in path.split("/"):
        raise HttpSafetyError("Path traversal is not allowed")
    if path.startswith("/api/"):
        raise HttpSafetyError("Direct /api/ paths on the website are not allowed")
    return site.absolute(path)


def resolve_api_url(settings: Settings, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    if not any(path.startswith(prefix) for prefix in ALLOWED_API_PREFIXES):
        raise HttpSafetyError("API path is not on the public SEO allowlist")
    return f"{settings.public_api_base.rstrip('/')}{path}"


async def fetch_text(
    url: str,
    *,
    site: SiteConfig,
    settings: Settings | None = None,
    cache_ttl: int | None = None,
    cache_key: str | None = None,
    method: str = "GET",
) -> dict[str, Any]:
    settings = settings or get_settings()
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if _is_private_host(host):
        raise HttpSafetyError("Private or loopback hosts are blocked")
    if not _host_allowed(host, settings, site):
        raise HttpSafetyError(f"Host not allowed: {host}")

    api_host = (urlparse(settings.public_api_base).hostname or "").lower()
    if host.lower() == api_host:
        if not any(parsed.path.startswith(prefix) for prefix in ALLOWED_API_PREFIXES):
            raise HttpSafetyError("API path is not on the public SEO allowlist")

    key = cache_key or f"{method}:{url}"
    if cache_ttl and method.upper() == "GET":
        cached = CACHE.get(key)
        if cached is not None:
            return cached

    headers = {
        "User-Agent": "PestControl99-SEO-MCP/1.0 (+https://www.pestcontrol99.com)",
        "Accept": "*/*",
    }
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        max_redirects=5,
        headers=headers,
    ) as client:
        response = await client.request(method.upper(), url)
        content = response.content
        if len(content) > settings.max_body_bytes:
            raise HttpSafetyError("Response body exceeds size limit")
        text = content.decode(response.encoding or "utf-8", errors="replace")
        result = {
            "url": str(response.url),
            "requested_url": url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "last_modified": response.headers.get("last-modified"),
            "text": text,
        }
        if cache_ttl and method.upper() == "GET" and 200 <= response.status_code < 400:
            CACHE.set(key, result, cache_ttl)
        logger.info(
            "fetch site=%s status=%s url=%s bytes=%s",
            site.key,
            response.status_code,
            parsed.path,
            len(content),
        )
        return result


async def fetch_json(
    url: str,
    *,
    site: SiteConfig,
    settings: Settings | None = None,
    cache_ttl: int = 300,
) -> dict[str, Any]:
    result = await fetch_text(url, site=site, settings=settings, cache_ttl=cache_ttl)
    import json

    try:
        data = json.loads(result["text"])
    except Exception as exc:  # noqa: BLE001
        raise HttpSafetyError(f"Invalid JSON from API: {exc}") from exc
    return {
        "url": result["url"],
        "status_code": result["status_code"],
        "data": data,
    }


def join_site(site: SiteConfig, path: str) -> str:
    return urljoin(site.site_base.rstrip("/") + "/", path.lstrip("/"))
