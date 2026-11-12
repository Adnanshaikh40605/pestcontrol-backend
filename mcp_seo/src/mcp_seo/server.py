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
from starlette.responses import JSONResponse
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
                "endpoints": {
                    "pestcontrol": "/mcp/pestcontrol",
                    "deepcleaning": "/mcp/deepcleaning",
                },
            }
        )

    @asynccontextmanager
    async def lifespan(_: Starlette) -> AsyncIterator[None]:
        async with pest_mcp.session_manager.run():
            async with deep_mcp.session_manager.run():
                logger.info(
                    "MCP SEO server ready pest=%s deep=%s",
                    "/mcp/pestcontrol",
                    "/mcp/deepcleaning",
                )
                yield

    app = Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/health/", health, methods=["GET"]),
            Mount(
                "/mcp/pestcontrol",
                app=pest_inner,
                middleware=[
                    Middleware(
                        BearerAuthMiddleware,
                        expected_token=settings.pestcontrol.token,
                        site_key="pestcontrol",
                        rate_limiter=limiter,
                    )
                ],
            ),
            Mount(
                "/mcp/deepcleaning",
                app=deep_inner,
                middleware=[
                    Middleware(
                        BearerAuthMiddleware,
                        expected_token=settings.deepcleaning.token,
                        site_key="deepcleaning",
                        rate_limiter=limiter,
                    )
                ],
            ),
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
