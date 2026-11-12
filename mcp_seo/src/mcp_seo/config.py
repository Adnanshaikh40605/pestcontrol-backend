"""Environment-driven configuration for the SEO MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class SiteConfig:
    key: str
    name: str
    site_base: str
    token_env: str
    api_base: str
    service_path_prefixes: tuple[str, ...] = ()
    location_path_prefixes: tuple[str, ...] = ()
    blog_path_prefixes: tuple[str, ...] = ()
    faq_paths: tuple[str, ...] = ()
    contact_paths: tuple[str, ...] = ()

    @property
    def token(self) -> str:
        return _env(self.token_env)

    def absolute(self, path: str = "/") -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.site_base.rstrip('/')}{path}"


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8100
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1")
    # Open by default so SEO staff can use MCP URLs without tokens.
    require_auth: bool = False
    public_api_base: str = "https://api.vacationbna.site"
    request_timeout_seconds: float = 10.0
    max_body_bytes: int = 2_000_000
    rate_limit_per_minute: int = 60
    page_cache_ttl: int = 300
    sitemap_cache_ttl: int = 900
    robots_cache_ttl: int = 3600
    broken_link_limit: int = 25
    max_page_size: int = 50
    pestcontrol: SiteConfig = field(default_factory=lambda: SiteConfig(
        key="pestcontrol",
        name="PestControl99",
        site_base="https://www.pestcontrol99.com",
        token_env="MCP_PESTCONTROL_TOKEN",
        api_base="https://api.vacationbna.site",
        service_path_prefixes=("/services/",),
        location_path_prefixes=("/pest-control-", "/pest-control-in-", "/monsoon-pest-control-"),
        blog_path_prefixes=("/blog/",),
        faq_paths=(),
        contact_paths=("/contact/", "/about/", "/brochure/"),
    ))
    deepcleaning: SiteConfig = field(default_factory=lambda: SiteConfig(
        key="deepcleaning",
        name="DeepCleaning99",
        site_base="https://deepcleaning99.com",
        token_env="MCP_DEEPCLEANING_TOKEN",
        api_base="https://api.vacationbna.site",
        service_path_prefixes=(
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
        ),
        location_path_prefixes=("/deep-cleaning-",),
        blog_path_prefixes=("/guides/",),
        faq_paths=("/faqs/",),
        contact_paths=("/contact-us/", "/about-us/", "/prices/"),
    ))

    def site(self, key: str) -> SiteConfig:
        if key == "pestcontrol":
            return self.pestcontrol
        if key == "deepcleaning":
            return self.deepcleaning
        raise KeyError(f"Unknown site key: {key}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    api = _env("PUBLIC_API_BASE", "https://api.vacationbna.site").rstrip("/")
    hosts = tuple(
        h.strip()
        for h in _env("MCP_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
        if h.strip()
    )
    pest = SiteConfig(
        key="pestcontrol",
        name="PestControl99",
        site_base=_env("PESTCONTROL_SITE_BASE", "https://www.pestcontrol99.com").rstrip("/"),
        token_env="MCP_PESTCONTROL_TOKEN",
        api_base=api,
        service_path_prefixes=("/services/",),
        location_path_prefixes=("/pest-control-", "/pest-control-in-", "/monsoon-pest-control-"),
        blog_path_prefixes=("/blog/",),
        faq_paths=(),
        contact_paths=("/contact/", "/about/", "/brochure/"),
    )
    deep = SiteConfig(
        key="deepcleaning",
        name="DeepCleaning99",
        site_base=_env("DEEPCLEANING_SITE_BASE", "https://deepcleaning99.com").rstrip("/"),
        token_env="MCP_DEEPCLEANING_TOKEN",
        api_base=api,
        service_path_prefixes=(
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
        ),
        location_path_prefixes=("/deep-cleaning-",),
        blog_path_prefixes=("/guides/",),
        faq_paths=("/faqs/",),
        contact_paths=("/contact-us/", "/about-us/", "/prices/"),
    )
    require_auth = _env("MCP_REQUIRE_AUTH", "false").lower() in ("1", "true", "yes", "on")
    return Settings(
        host=_env("MCP_HOST", "0.0.0.0"),
        port=_env_int("MCP_PORT", 8100),
        allowed_hosts=hosts or ("localhost", "127.0.0.1"),
        require_auth=require_auth,
        public_api_base=api,
        request_timeout_seconds=float(_env("MCP_REQUEST_TIMEOUT_SECONDS", "10") or 10),
        max_body_bytes=_env_int("MCP_MAX_BODY_BYTES", 2_000_000),
        rate_limit_per_minute=_env_int("MCP_RATE_LIMIT_PER_MINUTE", 60),
        page_cache_ttl=_env_int("MCP_PAGE_CACHE_TTL_SECONDS", 300),
        sitemap_cache_ttl=_env_int("MCP_SITEMAP_CACHE_TTL_SECONDS", 900),
        robots_cache_ttl=_env_int("MCP_ROBOTS_CACHE_TTL_SECONDS", 3600),
        broken_link_limit=_env_int("MCP_BROKEN_LINK_LIMIT", 25),
        pestcontrol=pest,
        deepcleaning=deep,
    )
