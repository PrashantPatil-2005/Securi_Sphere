"""Tests for middleware components."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# RequestContextMiddleware
# ---------------------------------------------------------------------------

from app.middleware.request_context import RequestContextMiddleware


def _ctx_app():
    app = Starlette()

    async def homepage(request):
        return PlainTextResponse("ok")

    app.add_route("/", homepage)
    app.add_middleware(RequestContextMiddleware)
    return app


def test_request_context_generates_ids():
    client = TestClient(_ctx_app())
    resp = client.get("/")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert "X-Correlation-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


def test_request_context_preserves_client_ids():
    app = _ctx_app()
    client = TestClient(app)
    resp = client.get("/", headers={"X-Request-ID": "my-req-1", "X-Correlation-ID": "my-corr-1"})
    assert resp.headers["X-Request-ID"] == "my-req-1"
    assert resp.headers["X-Correlation-ID"] == "my-corr-1"


def test_request_context_correlation_defaults_to_request_id():
    app = _ctx_app()
    client = TestClient(app)
    resp = client.get("/", headers={"X-Request-ID": "only-this"})
    assert resp.headers["X-Correlation-ID"] == "only-this"


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware
# ---------------------------------------------------------------------------

from app.middleware.security_headers import SecurityHeadersMiddleware


def _sec_app(env="production", csp_enabled=True):
    app = Starlette()

    async def homepage(request):
        return PlainTextResponse("ok")

    app.add_route("/", homepage)
    app.add_middleware(SecurityHeadersMiddleware)
    return app


def test_security_headers_present():
    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.csp_enabled = False
        mock_settings.environment = "production"
        mock_settings.csp_report_uri = None
        client = TestClient(_sec_app())
        resp = client.get("/")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert resp.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
        assert resp.headers["X-XSS-Protection"] == "0"


def test_hsts_in_production():
    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.csp_enabled = False
        mock_settings.environment = "production"
        mock_settings.csp_report_uri = None
        client = TestClient(_sec_app())
        resp = client.get("/")
        assert "Strict-Transport-Security" in resp.headers
        assert "max-age=31536000" in resp.headers["Strict-Transport-Security"]


def test_no_hsts_in_development():
    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.csp_enabled = False
        mock_settings.environment = "development"
        mock_settings.csp_report_uri = None
        client = TestClient(_sec_app())
        resp = client.get("/")
        assert "Strict-Transport-Security" not in resp.headers


def test_csp_added_when_enabled_in_production():
    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.csp_enabled = True
        mock_settings.environment = "production"
        mock_settings.csp_report_uri = None
        client = TestClient(_sec_app())
        resp = client.get("/")
        assert "Content-Security-Policy" in resp.headers
        assert "X-CSP-Nonce" in resp.headers


def test_csp_skipped_in_development():
    with patch("app.middleware.security_headers.settings") as mock_settings:
        mock_settings.csp_enabled = True
        mock_settings.environment = "development"
        mock_settings.csp_report_uri = None
        client = TestClient(_sec_app())
        resp = client.get("/")
        assert "Content-Security-Policy" not in resp.headers


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

from app.middleware.rate_limit import RateLimitMiddleware, _client_ip


def _rate_app():
    app = Starlette()

    async def homepage(request):
        return PlainTextResponse("ok")

    app.add_route("/api/v1/auth/login", homepage)
    app.add_route("/api/v1/events", homepage)
    app.add_middleware(RateLimitMiddleware)
    return app


def test_rate_limit_bypasses_in_testing():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.testing = True
        mock_s.redis_url = None
        mock_s.trusted_proxy = False
        app = Starlette()

        async def homepage(request):
            return PlainTextResponse("ok")

        app.add_route("/api/v1/auth/login", homepage)
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app)
        for _ in range(25):
            resp = client.get("/api/v1/auth/login")
        assert resp.status_code == 200


def test_rate_limit_skips_unknown_paths():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.testing = False
        mock_s.redis_url = None
        mock_s.trusted_proxy = False
        mock_s.environment = "production"
        app = Starlette()

        async def homepage(request):
            return PlainTextResponse("ok")

        app.add_route("/api/v1/unknown", homepage)
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app)
        for _ in range(250):
            resp = client.get("/api/v1/unknown")
        assert resp.status_code == 200


def test_rate_limit_triggers_on_auth_path():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.testing = False
        mock_s.redis_url = None
        mock_s.trusted_proxy = False
        mock_s.environment = "production"
        app = Starlette()

        async def homepage(request):
            return PlainTextResponse("ok")

        app.add_route("/api/v1/auth/login", homepage)
        app.add_middleware(RateLimitMiddleware)
        client = TestClient(app)
        for _ in range(21):
            resp = client.get("/api/v1/auth/login")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers


def test_client_ip_from_x_forwarded_for():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.trusted_proxy = True
        req = MagicMock()
        req.headers = {"X-Forwarded-For": "10.0.0.1, 10.0.0.2"}
        req.client.host = "127.0.0.1"
        assert _client_ip(req) == "10.0.0.1"


def test_client_ip_direct():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.trusted_proxy = False
        req = MagicMock()
        req.headers = {}
        req.client.host = "192.168.1.1"
        assert _client_ip(req) == "192.168.1.1"


def test_client_ip_unknown_when_no_client():
    with patch("app.middleware.rate_limit.settings") as mock_s:
        mock_s.trusted_proxy = False
        req = MagicMock()
        req.headers = {}
        req.client = None
        assert _client_ip(req) == "unknown"


# ---------------------------------------------------------------------------
# RequestTimeoutMiddleware
# ---------------------------------------------------------------------------

from app.middleware.request_timeout import RequestTimeoutMiddleware


def _timeout_app(timeout_enabled=True):
    app = Starlette()

    async def fast(request):
        return PlainTextResponse("ok")

    async def slow(request):
        import asyncio
        await asyncio.sleep(10)
        return PlainTextResponse("slow")

    app.add_route("/fast", fast)
    app.add_route("/slow", slow)

    with patch("app.middleware.request_timeout.settings") as mock_s:
        mock_s.request_timeout_enabled = timeout_enabled
        app.add_middleware(RequestTimeoutMiddleware)
        return app


def test_fast_request_succeeds():
    client = TestClient(_timeout_app())
    resp = client.get("/fast")
    assert resp.status_code == 200


def test_timeout_disabled_passthrough():
    client = TestClient(_timeout_app(timeout_enabled=False))
    resp = client.get("/fast")
    assert resp.status_code == 200
