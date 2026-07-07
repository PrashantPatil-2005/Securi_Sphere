"""Centralized HTTP timeout helpers."""

from __future__ import annotations

from app.config import settings


def resolve_request_timeout(path: str) -> float | None:
    """Return timeout seconds for an incoming request path, or None to skip."""
    if path.startswith("/health"):
        return None
    if path.startswith("/api/v1/agent"):
        return settings.request_timeout_agent_seconds
    if "/export" in path:
        return settings.request_timeout_export_seconds
    return settings.request_timeout_seconds


def outbound_timeout(*, short: bool = False) -> float:
    if short:
        return settings.outbound_http_timeout_short_seconds
    return settings.outbound_http_timeout_seconds
