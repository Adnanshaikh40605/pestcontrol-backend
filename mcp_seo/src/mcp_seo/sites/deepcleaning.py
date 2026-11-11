"""DeepCleaning99 site helpers."""

from __future__ import annotations

from urllib.parse import urlparse

from mcp_seo.config import SiteConfig

PUBLIC_CONTACT = {
    "brand": "Deepcleaning99",
    "legal_name": "Multi Pest Care LLP",
    "website": "https://deepcleaning99.com",
    "phone": "+91 77100 82627",
    "whatsapp": "917710082627",
}

SERVICE_SLUGS = {
    "/full-home-deep-cleaning/",
    "/bathroom-deep-cleaning/",
    "/kitchen-deep-cleaning/",
    "/sofa-cleaning/",
    "/carpet-cleaning/",
    "/mattress-cleaning/",
    "/commercial-deep-cleaning/",
    "/office-deep-cleaning/",
    "/residential-deep-cleaning/",
    "/scheduled-cleaning/",
}


def is_service_path(path: str) -> bool:
    normalized = path if path.endswith("/") else path + "/"
    return normalized in SERVICE_SLUGS


def is_location_path(path: str, site: SiteConfig) -> bool:
    return any(path.startswith(prefix) for prefix in site.location_path_prefixes)


def is_guide_path(path: str) -> bool:
    return path.startswith("/guides/")


def classify_url(url: str, site: SiteConfig) -> str:
    path = urlparse(url).path or "/"
    if is_service_path(path):
        return "service"
    if is_location_path(path, site):
        return "location"
    if is_guide_path(path):
        return "blog"
    if path.rstrip("/") == "/faqs":
        return "faq"
    if path.rstrip("/") in {"/prices", "/cleaning-prices"}:
        return "pricing"
    if path.rstrip("/") in {"/contact-us", "/about-us"}:
        return "contact" if "contact" in path else "about"
    if path in {"/", ""}:
        return "home"
    return "page"
