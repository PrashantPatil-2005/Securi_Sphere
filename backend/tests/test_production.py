import pytest

from app.config import settings


def test_production_defaults_documented():
    assert hasattr(settings, "allow_registration")
    assert hasattr(settings, "enable_simulation")
    assert hasattr(settings, "environment")


def test_security_headers_module():
    from app.middleware.security_headers import SecurityHeadersMiddleware
    assert SecurityHeadersMiddleware is not None


def test_system_router_registered():
    from app.routers import system
    assert system.router.prefix == "/system"
