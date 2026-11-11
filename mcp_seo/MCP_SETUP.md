# MCP Setup

## Prerequisites

- Python 3.11+
- Network access to:
  - `https://www.pestcontrol99.com`
  - `https://deepcleaning99.com`
  - `https://api.vacationbna.site` (public blog/catalog endpoints only)

## Local setup

```bash
cd mcp_seo
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Edit `.env`:

```env
MCP_PESTCONTROL_TOKEN=your-long-random-pest-token
MCP_DEEPCLEANING_TOKEN=your-long-random-deep-token
PESTCONTROL_SITE_BASE=https://www.pestcontrol99.com
DEEPCLEANING_SITE_BASE=https://deepcleaning99.com
PUBLIC_API_BASE=https://api.vacationbna.site
MCP_ALLOWED_HOSTS=localhost,127.0.0.1,127.0.0.1:8100,localhost:8100
MCP_PORT=8100
```

Start:

```bash
uvicorn mcp_seo.server:app --host 0.0.0.0 --port 8100
```

Or:

```bash
python -m mcp_seo.server
```

## Endpoints

| Path | Purpose |
|------|---------|
| `GET /health` | Liveness (no auth) |
| `/mcp/pestcontrol` | Streamable HTTP MCP for PestControl99 |
| `/mcp/deepcleaning` | Streamable HTTP MCP for DeepCleaning99 |

## Connect an MCP client (Cursor example)

Add a remote MCP server entry (names and UI vary by client):

```json
{
  "mcpServers": {
    "pestcontrol99-seo": {
      "url": "http://127.0.0.1:8100/mcp/pestcontrol",
      "headers": {
        "Authorization": "Bearer your-long-random-pest-token"
      }
    },
    "deepcleaning99-seo": {
      "url": "http://127.0.0.1:8100/mcp/deepcleaning",
      "headers": {
        "Authorization": "Bearer your-long-random-deep-token"
      }
    }
  }
}
```

Use Streamable HTTP transport. Do not commit real tokens.

## Deploy on Railway (separate service)

1. Create a **new** Railway service from this monorepo.
2. Root directory / start command:

```bash
cd mcp_seo && pip install -e . && uvicorn mcp_seo.server:app --host 0.0.0.0 --port $PORT
```

3. Set environment variables from `.env.example` (tokens required).
4. Add your Railway hostname to `MCP_ALLOWED_HOSTS` (DNS rebinding protection).
5. Do **not** replace the existing Django `Procfile` or website Vercel projects.

## Isolation guarantees

- No Django migrations
- No CRM schema changes
- No website URL changes
- Parent `requirements.txt` unchanged; MCP deps live only under `mcp_seo/`
