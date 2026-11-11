# SEO MCP Server (PestControl99 + DeepCleaning99)

Read-only [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes public SEO data for:

- **PestControl99** — `https://www.pestcontrol99.com`
- **DeepCleaning99** — `https://deepcleaning99.com`

It fetches live HTML, sitemaps, robots.txt, and allowlisted public Django APIs. It does **not** access CRM, bookings, payments, or customer PII.

## Quick start

```bash
cd mcp_seo
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# set MCP_PESTCONTROL_TOKEN and MCP_DEEPCLEANING_TOKEN
uvicorn mcp_seo.server:app --host 0.0.0.0 --port 8100
```

Health check: `GET http://127.0.0.1:8100/health`

MCP endpoints:

- `http://127.0.0.1:8100/mcp/pestcontrol`
- `http://127.0.0.1:8100/mcp/deepcleaning`

Both require `Authorization: Bearer <site-token>`.

## Documentation

- [MCP_SETUP.md](MCP_SETUP.md) — local run and deploy
- [MCP_API_DOCUMENTATION.md](MCP_API_DOCUMENTATION.md) — tools and resources
- [MCP_SECURITY.md](MCP_SECURITY.md) — auth, allowlists, and data boundaries
- [MCP_TESTING.md](MCP_TESTING.md) — test plan and commands

## Important

This package is isolated from the Django CRM process. Do not mount it into the existing production gunicorn service without a separate Railway service and tokens.
