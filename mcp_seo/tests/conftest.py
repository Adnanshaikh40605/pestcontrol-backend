from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("MCP_PESTCONTROL_TOKEN", "test-pest-token")
os.environ.setdefault("MCP_DEEPCLEANING_TOKEN", "test-deep-token")
# Auth tests expect locked mode; production defaults to open access.
os.environ.setdefault("MCP_REQUIRE_AUTH", "true")
os.environ.setdefault("PESTCONTROL_SITE_BASE", "https://www.pestcontrol99.com")
os.environ.setdefault("DEEPCLEANING_SITE_BASE", "https://deepcleaning99.com")
os.environ.setdefault("PUBLIC_API_BASE", "https://api.vacationbna.site")

from mcp_seo.cache import CACHE  # noqa: E402
from mcp_seo.config import get_settings  # noqa: E402


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def clear_cache_and_settings():
    CACHE.clear()
    get_settings.cache_clear()
    yield
    CACHE.clear()
    get_settings.cache_clear()


@pytest.fixture
def sample_html() -> str:
    return (FIXTURES / "sample_page.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_sitemap() -> str:
    return (FIXTURES / "sitemap.xml").read_text(encoding="utf-8")
