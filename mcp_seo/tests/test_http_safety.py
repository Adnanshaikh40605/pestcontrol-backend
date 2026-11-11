import pytest

from mcp_seo.config import get_settings
from mcp_seo.http_client import HttpSafetyError, resolve_api_url, resolve_site_url


def test_resolve_site_url_allows_same_origin():
    site = get_settings().pestcontrol
    assert resolve_site_url(site, "/services/").endswith("/services/")
    assert resolve_site_url(site, "https://www.pestcontrol99.com/contact/").endswith("/contact/")


def test_resolve_site_url_blocks_other_hosts_and_api():
    site = get_settings().pestcontrol
    with pytest.raises(HttpSafetyError):
        resolve_site_url(site, "https://deepcleaning99.com/")
    with pytest.raises(HttpSafetyError):
        resolve_site_url(site, "/api/public/blogs/")
    with pytest.raises(HttpSafetyError):
        resolve_site_url(site, "/../etc/passwd")


def test_resolve_api_url_allowlist():
    settings = get_settings()
    assert resolve_api_url(settings, "/api/public/blogs/").endswith("/api/public/blogs/")
    assert resolve_api_url(settings, "/api/v1/deepcleaning-rates/catalog/").endswith(
        "/api/v1/deepcleaning-rates/catalog/"
    )
    with pytest.raises(HttpSafetyError):
        resolve_api_url(settings, "/api/v1/jobcards/")
    with pytest.raises(HttpSafetyError):
        resolve_api_url(settings, "/api/partner/bookings/")
