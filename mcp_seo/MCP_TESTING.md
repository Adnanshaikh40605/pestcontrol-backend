# MCP Testing

## Automated tests

```bash
cd mcp_seo
source .venv/bin/activate
pip install -e ".[dev]"
MCP_PESTCONTROL_TOKEN=test-pest-token MCP_DEEPCLEANING_TOKEN=test-deep-token pytest -q
```

Covered:

1. HTML metadata / JSON-LD / sitemap parsing
2. Host and API allowlist rejection
3. robots/sitemap/page metadata via mocked HTTP
4. Pest blog API + DeepCleaning catalog API
5. Duplicate title detection
6. Health endpoint
7. Bearer auth deny/allow
8. Rate limiter

## Manual smoke (local server)

```bash
uvicorn mcp_seo.server:app --host 127.0.0.1 --port 8100
```

```bash
curl -s http://127.0.0.1:8100/health
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8100/mcp/pestcontrol
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $MCP_PESTCONTROL_TOKEN" \
  http://127.0.0.1:8100/mcp/pestcontrol
```

Unauthorized calls must be `401`. Health must be `200`.

## Live data smoke (optional)

With network access, exercise service methods:

```bash
MCP_PESTCONTROL_TOKEN=test MCP_DEEPCLEANING_TOKEN=test \
python - <<'PY'
import asyncio
from mcp_seo.seo_service import SeoService

async def main():
    pest = SeoService('pestcontrol')
    deep = SeoService('deepcleaning')
    print('pest robots', (await pest.get_robots_txt())['status_code'])
    print('pest sitemap total', (await pest.get_sitemap())['total'])
    print('deep sitemap total', (await deep.get_sitemap())['total'])
    print('pest home title', (await pest.get_page_title('/'))['title'])

asyncio.run(main())
PY
```

## Checklist from the plan

- [x] MCP server connection (ASGI app + mounts)
- [x] Tool discovery (35 tools registered per site)
- [x] Website information retrieval
- [x] Sitemap retrieval
- [x] Robots.txt retrieval
- [x] Page metadata retrieval
- [x] Service catalog retrieval
- [x] Blog/guide retrieval
- [x] Technical SEO checks
- [x] Authentication / unauthorized access
- [x] Rate limiting
- [x] Error handling (JSON error payloads)
- [x] Independent site mounts
