"""Register read-only SEO tools and resources on an MCPServer instance."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import MCPServer

from mcp_seo.http_client import HttpSafetyError
from mcp_seo.seo_service import SeoService


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _error(exc: Exception) -> str:
    return _json({"error": str(exc), "type": exc.__class__.__name__})


def register_site_tools(mcp: MCPServer, site_key: str) -> None:
    service = SeoService(site_key)

    @mcp.tool()
    async def get_website_info() -> str:
        """Return public website name, base URL, contact, and home metadata."""
        try:
            return _json(await service.get_website_info())
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_website_pages(page: int = 1, page_size: int = 50) -> str:
        """List public pages from the live sitemap with category labels."""
        try:
            return _json(await service.list_pages(page=page, page_size=page_size))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_page_content(path_or_url: str = "/", max_chars: int = 8000) -> str:
        """Extract visible public text content from a page (truncated)."""
        try:
            return _json(await service.get_page_content(path_or_url, max_chars=max_chars))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_page_metadata(path_or_url: str = "/") -> str:
        """Return title, description, canonical, robots, headings, and related SEO fields."""
        try:
            return _json(await service.get_page_metadata(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_page_title(path_or_url: str = "/") -> str:
        """Return the HTML title for a public page."""
        try:
            return _json(await service.get_page_title(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_page_description(path_or_url: str = "/") -> str:
        """Return the meta description for a public page."""
        try:
            return _json(await service.get_page_description(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_canonical_url(path_or_url: str = "/") -> str:
        """Return the canonical URL declared on a public page."""
        try:
            return _json(await service.get_canonical_url(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_robots_txt() -> str:
        """Fetch the live robots.txt file."""
        try:
            return _json(await service.get_robots_txt())
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_sitemap(page: int = 1, page_size: int = 50) -> str:
        """Fetch and paginate URLs from the live sitemap.xml."""
        try:
            return _json(await service.get_sitemap(page=page, page_size=page_size))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_internal_links(path_or_url: str = "/", page: int = 1, page_size: int = 50) -> str:
        """List internal links found on a public page."""
        try:
            return _json(await service.get_internal_links(path_or_url, page=page, page_size=page_size))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_page_status(path_or_url: str = "/") -> str:
        """Check HTTP status for a public page."""
        try:
            return _json(await service.check_page_status(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_broken_links(path_or_url: str = "/") -> str:
        """Check a capped set of internal links from a page for non-success statuses."""
        try:
            return _json(await service.check_broken_links(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_missing_metadata(limit: int = 30) -> str:
        """Scan sitemap pages for missing title, description, or canonical tags."""
        try:
            return _json(await service.check_missing_metadata(limit=limit))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_duplicate_titles(limit: int = 40) -> str:
        """Find duplicate page titles across a sitemap sample."""
        try:
            return _json(await service.check_duplicate_titles(limit=limit))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_duplicate_descriptions(limit: int = 40) -> str:
        """Find duplicate meta descriptions across a sitemap sample."""
        try:
            return _json(await service.check_duplicate_descriptions(limit=limit))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_image_alt_text(path_or_url: str = "/") -> str:
        """Report images missing alt text on a public page."""
        try:
            return _json(await service.check_image_alt_text(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_canonical_tags(path_or_url: str = "/") -> str:
        """Validate canonical tag presence and whether it matches the requested URL."""
        try:
            return _json(await service.check_canonical_tags(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_robots_indexability(path_or_url: str = "/") -> str:
        """Check meta robots and robots.txt rules for indexability."""
        try:
            return _json(await service.check_robots_indexability(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_structured_data(path_or_url: str = "/") -> str:
        """Return JSON-LD structured data found on a public page."""
        try:
            return _json(await service.check_structured_data(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_heading_structure(path_or_url: str = "/") -> str:
        """Inspect H1/H2 heading structure on a public page."""
        try:
            return _json(await service.check_heading_structure(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def check_mobile_metadata(path_or_url: str = "/") -> str:
        """Check viewport / mobile-related metadata on a public page."""
        try:
            return _json(await service.check_mobile_metadata(path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_organization_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate Organization JSON-LD from a page."""
        try:
            return _json(await service.get_schema_by_type("Organization", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_local_business_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate LocalBusiness JSON-LD from a page."""
        try:
            return _json(await service.get_schema_by_type("LocalBusiness", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_service_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate Service JSON-LD from a page."""
        try:
            return _json(await service.get_schema_by_type("Service", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_product_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate Product JSON-LD from a page, if present."""
        try:
            return _json(await service.get_schema_by_type("Product", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_breadcrumb_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate BreadcrumbList JSON-LD from a page."""
        try:
            return _json(await service.get_schema_by_type("BreadcrumbList", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_faq_schema(path_or_url: str = "/") -> str:
        """Retrieve and validate FAQPage JSON-LD from a page."""
        try:
            return _json(await service.get_schema_by_type("FAQPage", path_or_url))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_service_pages(page: int = 1, page_size: int = 50) -> str:
        """List public service pages discovered from the sitemap."""
        try:
            return _json(await service.get_service_pages(page=page, page_size=page_size))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_blog_posts(page: int = 1, page_size: int = 20, query: str = "") -> str:
        """List public blog or guide content (API for PestControl99, sitemap for DeepCleaning99)."""
        try:
            return _json(await service.get_blog_posts(page=page, page_size=page_size, query=query))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_blog_categories() -> str:
        """List public blog categories or guide groupings."""
        try:
            return _json(await service.get_blog_categories())
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_faq_content(path_or_url: str = "") -> str:
        """Retrieve FAQ schema and extracted Q&A from a public FAQ or home page."""
        try:
            target = path_or_url or None
            return _json(await service.get_faq_content(target))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_location_pages(page: int = 1, page_size: int = 50) -> str:
        """List public location / city landing pages from the sitemap."""
        try:
            return _json(await service.get_location_pages(page=page, page_size=page_size))
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def search_website_content(query: str, page: int = 1, page_size: int = 20) -> str:
        """Search public sitemap paths, page metadata, and blog APIs for a query."""
        try:
            return _json(await service.search_website_content(query, page=page, page_size=page_size))
        except HttpSafetyError as exc:
            return _error(exc)
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_public_pricing() -> str:
        """Return public pricing catalog data from allowlisted APIs plus pricing page metadata."""
        try:
            return _json(await service.get_public_pricing())
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    @mcp.tool()
    async def get_public_business_info() -> str:
        """Return public business contact information and organization schemas."""
        try:
            return _json(await service.get_public_business_info())
        except Exception as exc:  # noqa: BLE001
            return _error(exc)

    # Resources
    @mcp.resource(f"resource://{site_key}/overview")
    async def resource_overview() -> str:
        """Website overview resource."""
        return _json(await service.get_website_info())

    @mcp.resource(f"resource://{site_key}/sitemap")
    async def resource_sitemap() -> str:
        """Live sitemap resource."""
        return _json(await service.get_sitemap(page=1, page_size=50))

    @mcp.resource(f"resource://{site_key}/robots")
    async def resource_robots() -> str:
        """Live robots.txt resource."""
        return _json(await service.get_robots_txt())

    @mcp.resource(f"resource://{site_key}/services")
    async def resource_services() -> str:
        """Service catalog resource from sitemap."""
        return _json(await service.get_service_pages(page=1, page_size=50))

    @mcp.resource(f"resource://{site_key}/blog")
    async def resource_blog() -> str:
        """Blog / guides resource."""
        return _json(await service.get_blog_posts(page=1, page_size=20))

    @mcp.resource(f"resource://{site_key}/faq")
    async def resource_faq() -> str:
        """FAQ resource."""
        return _json(await service.get_faq_content())

    @mcp.resource(f"resource://{site_key}/business")
    async def resource_business() -> str:
        """Public business information resource."""
        return _json(await service.get_public_business_info())
