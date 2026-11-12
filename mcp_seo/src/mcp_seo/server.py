"""ASGI entrypoint: dual Streamable HTTP MCP mounts for both websites."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount, Route

from mcp_seo.auth import BearerAuthMiddleware
from mcp_seo.config import get_settings
from mcp_seo.rate_limit import get_rate_limiter
from mcp_seo.tools.register import register_site_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mcp_seo.server")


def _build_mcp(name: str, site_key: str) -> MCPServer:
    server = MCPServer(
        name,
        instructions=(
            f"Read-only SEO tools for {name}. "
            "Only public website HTML and allowlisted public APIs are available. "
            "No CRM, bookings, payments, or private customer data."
        ),
    )
    register_site_tools(server, site_key)
    return server


def create_app() -> Starlette:
    settings = get_settings()
    limiter = get_rate_limiter(settings.rate_limit_per_minute)

    pest_mcp = _build_mcp("PestControl99 SEO", "pestcontrol")
    deep_mcp = _build_mcp("DeepCleaning99 SEO", "deepcleaning")

    # Host allowlist from MCP_ALLOWED_HOSTS (must include the public Railway hostname).
    host_allow = list(settings.allowed_hosts) + [
        "localhost:*",
        "127.0.0.1:*",
        f"{settings.host}:*",
        "*.up.railway.app",
        "*.railway.app",
    ]
    origin_allow = [
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8100",
        "http://127.0.0.1:8100",
    ]
    for host in settings.allowed_hosts:
        bare = host.split(":")[0].strip()
        if not bare or bare in {"0.0.0.0", "localhost", "127.0.0.1"}:
            continue
        origin_allow.append(f"https://{bare}")
        origin_allow.append(f"http://{bare}")
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=host_allow,
        allowed_origins=origin_allow,
    )

    pest_inner = pest_mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )
    deep_inner = deep_mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )

    async def health(_: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "mcp-seo",
                "auth_required": settings.require_auth,
                "endpoints": {
                    "pestcontrol": "/mcp/pestcontrol/",
                    "deepcleaning": "/mcp/deepcleaning/",
                },
            }
        )

    async def home(_: Request) -> HTMLResponse:
        auth_note = (
            "Open access — no login or token needed."
            if not settings.require_auth
            else "Bearer token required (MCP_REQUIRE_AUTH=true)."
        )
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SEO MCP — PestControl99 & DeepCleaning99</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #111; line-height: 1.5; }}
    h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
    .muted {{ color: #555; margin-bottom: 1.5rem; }}
    .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin: 12px 0; }}
    a {{ color: #0b57d0; word-break: break-all; }}
    code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>SEO MCP (Production)</h1>
  <p class="muted">{auth_note} Read-only public website SEO tools only.</p>
  <div class="card">
    <strong>PestControl99</strong><br />
    <a href="/mcp/pestcontrol/">/mcp/pestcontrol/</a>
  </div>
  <div class="card">
    <strong>DeepCleaning99</strong><br />
    <a href="/mcp/deepcleaning/">/mcp/deepcleaning/</a>
  </div>
  <p>Health: <a href="/health"><code>/health</code></a></p>
  <p class="muted">Connect these URLs in Cursor / Claude MCP (Streamable HTTP). Opening the MCP path in a normal browser tab is OK — it is public — but SEO tools are used by the MCP client, not as a website page.</p>
</body>
</html>"""
        return HTMLResponse(html)

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with pest_mcp.session_manager.run():
            async with deep_mcp.session_manager.run():
                logger.info(
                    "MCP SEO server ready pest=%s deep=%s auth_required=%s",
                    "/mcp/pestcontrol",
                    "/mcp/deepcleaning",
                    settings.require_auth,
                )
                yield

    mount_middleware = [
        Middleware(
            BearerAuthMiddleware,
            expected_token=settings.pestcontrol.token,
            site_key="pestcontrol",
            rate_limiter=limiter,
            require_auth=settings.require_auth,
        )
    ]
    deep_middleware = [
        Middleware(
            BearerAuthMiddleware,
            expected_token=settings.deepcleaning.token,
            site_key="deepcleaning",
            rate_limiter=limiter,
            require_auth=settings.require_auth,
        )
    ]

    app = Starlette(
        routes=[
            Route("/", home, methods=["GET"]),
            Route("/health", health, methods=["GET"]),
            Route("/health/", health, methods=["GET"]),
            Mount("/mcp/pestcontrol", app=pest_inner, middleware=mount_middleware),
            Mount("/mcp/deepcleaning", app=deep_inner, middleware=deep_middleware),
        ],
        lifespan=lifespan,
    )
    return app


app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "mcp_seo.server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
