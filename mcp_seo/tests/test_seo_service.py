import pytest
import respx
from httpx import Response

from mcp_seo.seo_service import SeoService


@pytest.mark.asyncio
@respx.mock
async def test_get_robots_and_sitemap(sample_sitemap):
    respx.get("https://www.pestcontrol99.com/robots.txt").mock(
        return_value=Response(200, text="User-agent: *\nAllow: /\n")
    )
    respx.get("https://www.pestcontrol99.com/sitemap.xml").mock(
        return_value=Response(200, text=sample_sitemap, headers={"content-type": "application/xml"})
    )
    service = SeoService("pestcontrol")
    robots = await service.get_robots_txt()
    assert robots["status_code"] == 200
    assert "Allow: /" in robots["content"]

    sitemap = await service.get_sitemap(page=1, page_size=10)
    assert sitemap["total"] == 6
    assert any(u.endswith("/services/") for u in sitemap["results"])

    pages = await service.list_pages(page=1, page_size=10)
    categories = {row["category"] for row in pages["results"]}
    assert "service" in categories
    assert "location" in categories
    assert "blog" in categories


@pytest.mark.asyncio
@respx.mock
async def test_page_metadata_and_technical_checks(sample_html):
    url = "https://www.pestcontrol99.com/services/cockroach-pest-control/"
    respx.get(url).mock(return_value=Response(200, text=sample_html, headers={"content-type": "text/html"}))
    respx.get("https://www.pestcontrol99.com/robots.txt").mock(
        return_value=Response(200, text="User-agent: *\nAllow: /\nDisallow: /thank-you/\n")
    )
    service = SeoService("pestcontrol")
    meta = await service.get_page_metadata(url)
    assert meta["title"].startswith("Cockroach")
    assert meta["canonical_url"].endswith("/services/cockroach-pest-control/")

    alts = await service.check_image_alt_text(url)
    assert alts["missing_alt_count"] == 1

    headings = await service.check_heading_structure(url)
    assert headings["has_single_h1"] is True

    schema = await service.get_schema_by_type("Service", url)
    assert schema["count"] == 1
    assert schema["validation"][0]["is_valid"] is True

    indexability = await service.check_robots_indexability(url)
    assert indexability["indexable"] is True


@pytest.mark.asyncio
@respx.mock
async def test_pest_blog_and_deepcleaning_catalog():
    respx.get("https://api.vacationbna.site/api/public/blogs/").mock(
        return_value=Response(
            200,
            json={"count": 1, "results": [{"title": "Monsoon Tips", "slug": "monsoon-tips"}]},
        )
    )
    respx.get("https://api.vacationbna.site/api/v1/deepcleaning-rates/catalog/").mock(
        return_value=Response(200, json={"rates": [{"name": "Full Home", "price": 2999}]})
    )
    respx.get("https://deepcleaning99.com/prices/").mock(
        return_value=Response(
            200,
            text="<html><head><title>Prices</title><meta name='description' content='Rates' /></head><body><h1>Prices</h1></body></html>",
        )
    )

    pest = SeoService("pestcontrol")
    blogs = await pest.get_blog_posts(page=1, page_size=10)
    assert blogs["source"] == "api"
    assert blogs["results"][0]["title"] == "Monsoon Tips"

    deep = SeoService("deepcleaning")
    pricing = await deep.get_public_pricing()
    assert pricing["source"] == "api+prices_page"
    assert pricing["catalog"]["rates"][0]["name"] == "Full Home"


@pytest.mark.asyncio
@respx.mock
async def test_duplicate_title_detection(sample_html, sample_sitemap):
    respx.get("https://www.pestcontrol99.com/sitemap.xml").mock(
        return_value=Response(200, text=sample_sitemap)
    )
    # All pages return same title to force duplicates
    respx.get(url__regex=r"https://www\.pestcontrol99\.com/.*").mock(
        return_value=Response(200, text=sample_html)
    )
    service = SeoService("pestcontrol")
    result = await service.check_duplicate_titles(limit=6)
    assert result["scanned"] >= 1
    assert any(item["count"] > 1 for item in result["duplicates"])
