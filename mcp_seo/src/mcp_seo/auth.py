"""Bearer authentication and rate-limit middleware for MCP mounts."""

from __future__ import annotations

import logging
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from mcp_seo.rate_limit import RateLimiter

logger = logging.getLogger("mcp_seo.auth")


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    parts = header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Require a site-specific bearer token and enforce rate limits."""

    def __init__(
        self,
        app,
        *,
        expected_token: str,
        site_key: str,
        rate_limiter: RateLimiter,
    ) -> None:
        super().__init__(app)
        self.expected_token = expected_token or ""
        self.site_key = site_key
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        token = _extract_bearer(request)
        if not self.expected_token:
            logger.warning("auth_denied site=%s reason=token_not_configured", self.site_key)
            return JSONResponse(
                {"error": "MCP authentication is not configured for this site"},
                status_code=503,
            )
        if not token or not secrets.compare_digest(token, self.expected_token):
            logger.info("auth_denied site=%s path=%s", self.site_key, request.url.path)
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        if not self.rate_limiter.allow(f"{self.site_key}:{token[:8]}"):
            logger.info("rate_limited site=%s path=%s", self.site_key, request.url.path)
            return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

        return await call_next(request)
