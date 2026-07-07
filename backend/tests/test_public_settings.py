"""Tests for unauthenticated public settings endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_public_settings_includes_ai_and_search():
    res = client.get("/api/v1/settings/public")
    assert res.status_code == 200
    body = res.json()
    assert "ai_assistant_enabled" in body
    assert "ai_provider" in body
    assert "demo_mode" in body
    assert isinstance(body["demo_mode"], bool)
    assert body["search_backend"] in ("postgres", "opensearch")
