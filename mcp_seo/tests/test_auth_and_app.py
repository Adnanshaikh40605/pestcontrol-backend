from starlette.testclient import TestClient

from mcp_seo.rate_limit import RateLimiter
from mcp_seo.server import create_app


def test_health_is_public():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_mcp_requires_bearer_token():
    app = create_app()
    with TestClient(app) as client:
        denied = client.post("/mcp/pestcontrol/", content=b"{}")
        assert denied.status_code == 401

        wrong = client.post(
            "/mcp/pestcontrol/",
            headers={"Authorization": "Bearer wrong"},
            content=b"{}",
        )
        assert wrong.status_code == 401

        # Correct token passes auth middleware. MCP may still return a protocol
        # error for a bare `{}` body; that is still progress past 401/503.
        allowed = client.post(
            "/mcp/pestcontrol/",
            headers={"Authorization": "Bearer test-pest-token"},
            content=b"{}",
        )
        assert allowed.status_code not in (401, 503)


def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit_per_minute=2)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
