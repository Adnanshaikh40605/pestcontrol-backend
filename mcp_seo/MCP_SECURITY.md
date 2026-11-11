# MCP Security

## Threat model

This server is a read-only SEO assistant for **public** marketing pages. It must never become a side door into CRM, bookings, payments, or customer records.

## Authentication

- Each MCP mount requires its own bearer token:
  - `MCP_PESTCONTROL_TOKEN` for `/mcp/pestcontrol`
  - `MCP_DEEPCLEANING_TOKEN` for `/mcp/deepcleaning`
- Tokens are compared with `secrets.compare_digest`.
- Missing configuration returns HTTP 503 (not an open endpoint).
- Wrong/missing token returns HTTP 401.
- `/health` is public and returns no secrets.

## Rate limiting

- Per-token sliding window (default 60 requests/minute).
- Exceeded limit returns HTTP 429.

## Data allowlist

Allowed outbound fetches:

1. Configured site origins only (PestControl99 or DeepCleaning99 for the active mount).
2. Public API host paths only:
   - `/api/public/blogs/`
   - `/api/public/categories/`
   - `/api/public/tags/`
   - `/api/public/related-blogs/`
   - `/api/customer/catalog/`
   - `/api/customer/cities/`
   - `/api/customer/locations/`
   - `/api/v1/deepcleaning-rates/catalog/` (and `/api/deepcleaning-rates/catalog/`)

Blocked:

- Private/loopback IPs and metadata hosts
- Path traversal (`..`)
- Website `/api/` paths
- CRM/job/partner/staff endpoints
- Any write/POST tools (none are registered)

## Input validation

- `path_or_url` must resolve to the same site origin.
- Pagination is clamped (max page size 50).
- Broken-link checks are capped (`MCP_BROKEN_LINK_LIMIT`).
- Response bodies are size-limited.

## Secrets handling

- No database credentials are loaded.
- No CRM JWT/Firebase/S3 secrets are required.
- Logs record site key, path, and status — never bearer tokens or full HTML form payloads.

## DNS rebinding protection

Streamable HTTP transport security is enabled. Production hosts must be listed in `MCP_ALLOWED_HOSTS`.

## Residual risks / limitations

- SPA sites may return shell HTML for some routes; the MCP reports what the HTTP response actually contains.
- Large site audits sample sitemap pages; they are not a full crawl of every URL by default.
- Public pricing APIs return only published catalog data; they do not invent missing rates.
