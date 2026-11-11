"""PestControl99 site helpers."""

from __future__ import annotations

from urllib.parse import urlparse

from mcp_seo.config import SiteConfig

PUBLIC_CONTACT = {
    "brand": "Pest Control 99",
    "legal_name": "Multi Pest Care LLP",
    "website": "https://www.pestcontrol99.com",
    "email": "accounts@pestcontrol99.com",
    "phone": "+91 77100 32627",
    "whatsapp": "917710032627",
}


def is_service_path(path: str) -> bool:
    return path.rstrip("/").startswith("/services") or path == "/services/"


def is_location_path(path: str, site: SiteConfig) -> bool:
    return any(path.startswith(prefix) for prefix in site.location_path_prefixes)


def is_blog_path(path: str) -> bool:
    return path.startswith("/blog/")


def classify_url(url: str, site: SiteConfig) -> str:
    path = urlparse(url).path or "/"
    if is_service_path(path):
        return "service"
    if is_location_path(path, site):
        return "location"
    if is_blog_path(path):
        return "blog"
    if path in {"/", ""}:
        return "home"
    if path.startswith("/contact"):
        return "contact"
    if path.startswith("/about"):
        return "about"
    if path.startswith("/brochure"):
        return "pricing"
    return "page"
