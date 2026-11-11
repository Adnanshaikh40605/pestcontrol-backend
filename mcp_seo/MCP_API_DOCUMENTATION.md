# MCP API Documentation

Transport: **Streamable HTTP** (MCP Python SDK v2).

## Mounts

| Site | MCP path | Resource URI prefix |
|------|----------|---------------------|
| PestControl99 | `/mcp/pestcontrol` | `resource://pestcontrol/...` |
| DeepCleaning99 | `/mcp/deepcleaning` | `resource://deepcleaning/...` |

Auth: `Authorization: Bearer <token>` required on MCP mounts.

## Website information tools

| Tool | Description |
|------|-------------|
| `get_website_info` | Name, base URL, public contact, home title/description |
| `get_website_pages` | Paginated sitemap pages with category |
| `get_page_content` | Truncated visible text |
| `get_page_metadata` | Title, description, canonical, robots, H1/H2, OG |
| `get_page_title` | Title only |
| `get_page_description` | Meta description only |
| `get_canonical_url` | Canonical link |
| `get_robots_txt` | Live robots.txt |
| `get_sitemap` | Paginated sitemap URLs |
| `get_internal_links` | Same-origin anchors on a page |

## Technical SEO tools

| Tool | Description |
|------|-------------|
| `check_page_status` | HTTP status |
| `check_broken_links` | Capped internal link status checks |
| `check_missing_metadata` | Missing title/description/canonical sample |
| `check_duplicate_titles` | Duplicate titles in sitemap sample |
| `check_duplicate_descriptions` | Duplicate descriptions in sitemap sample |
| `check_image_alt_text` | Images missing alt |
| `check_canonical_tags` | Canonical presence / match |
| `check_robots_indexability` | Meta robots + robots.txt |
| `check_structured_data` | All JSON-LD on a page |
| `check_heading_structure` | H1/H2 audit |
| `check_mobile_metadata` | Viewport meta |

## Structured data tools

| Tool | Schema type |
|------|-------------|
| `get_organization_schema` | Organization |
| `get_local_business_schema` | LocalBusiness |
| `get_service_schema` | Service |
| `get_product_schema` | Product |
| `get_breadcrumb_schema` | BreadcrumbList |
| `get_faq_schema` | FAQPage |

Each returns matching JSON-LD items plus a light required-field validation.

## Content tools

| Tool | Description |
|------|-------------|
| `get_service_pages` | Service URLs from sitemap |
| `get_blog_posts` | Pest: `/api/public/blogs/`; DeepCleaning: `/guides/` sitemap |
| `get_blog_categories` | Pest categories API; DeepCleaning guides grouping |
| `get_faq_content` | FAQ schema + extracted Q&A |
| `get_location_pages` | City/area landing pages |
| `search_website_content` | Search sitemap/meta/blogs |
| `get_public_pricing` | Allowlisted public rate catalogs |
| `get_public_business_info` | Public NAP + org schemas |

## Resources

| URI | Content |
|-----|---------|
| `resource://{site}/overview` | Website overview |
| `resource://{site}/sitemap` | Sitemap page 1 |
| `resource://{site}/robots` | robots.txt |
| `resource://{site}/services` | Service list |
| `resource://{site}/blog` | Blog/guides |
| `resource://{site}/faq` | FAQ |
| `resource://{site}/business` | Public business info |

`{site}` is `pestcontrol` or `deepcleaning`.

## Example tool result shape

```json
{
  "url": "https://www.pestcontrol99.com/services/cockroach-pest-control/",
  "http_status": 200,
  "title": "Cockroach Pest Control | Pest Control 99",
  "description": "Professional cockroach control in Mumbai and Pune.",
  "canonical_url": "https://www.pestcontrol99.com/services/cockroach-pest-control/",
  "robots": "index,follow",
  "h1": ["Cockroach Pest Control"],
  "h2": ["Residential Treatment", "Commercial Treatment"]
}
```

Missing fields are returned as `null` or empty lists.
