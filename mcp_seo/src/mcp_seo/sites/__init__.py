"""Site profiles for PestControl99 and DeepCleaning99."""

from mcp_seo.config import SiteConfig, get_settings


def get_site(site_key: str) -> SiteConfig:
    return get_settings().site(site_key)
