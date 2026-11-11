from mcp_seo.html_seo import (
    filter_structured_data,
    parse_page,
    parse_sitemap_urls,
    validate_schema,
)


def test_parse_page_metadata(sample_html):
    page = parse_page(sample_html, "https://www.pestcontrol99.com/services/cockroach-pest-control/")
    assert page["title"] == "Cockroach Pest Control | Pest Control 99"
    assert "cockroach" in (page["description"] or "").lower()
    assert page["canonical_url"].endswith("/services/cockroach-pest-control/")
    assert page["h1"] == ["Cockroach Pest Control"]
    assert len(page["h2"]) == 2
    assert page["viewport"]
    assert any(link["url"].endswith("/services/") for link in page["internal_links"])
    assert not any("example.com" in link["url"] for link in page["internal_links"])
    missing = [img for img in page["images"] if img["missing_alt"]]
    assert len(missing) == 1


def test_structured_data_and_validation(sample_html):
    page = parse_page(sample_html, "https://www.pestcontrol99.com/services/cockroach-pest-control/")
    services = filter_structured_data(page["structured_data"], "Service")
    orgs = filter_structured_data(page["structured_data"], "Organization")
    assert len(services) == 1
    assert len(orgs) == 1
    valid = validate_schema(services[0], "Service")
    assert valid["is_valid"] is True


def test_parse_sitemap(sample_sitemap):
    urls = parse_sitemap_urls(sample_sitemap)
    assert len(urls) == 6
    assert urls[0].endswith("/")
