"""Integration tests for compliance reports API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compliance_templates(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/reports/compliance/templates")
    assert res.status_code == 200
    body = res.json()
    assert len(body) >= 2
    ids = {t["id"] for t in body}
    assert "soc2" in ids
    assert "iso27001" in ids


@pytest.mark.asyncio
async def test_compliance_report_json(analyst_client: AsyncClient):
    res = await analyst_client.get(
        "/api/v1/reports/compliance",
        params={"framework": "soc2", "report_type": "monthly", "format": "json"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["framework_id"] == "soc2"
    assert "controls" in body
    assert "summary" in body
    assert body["summary"]["compliance_score"] >= 0


@pytest.mark.asyncio
async def test_compliance_report_pdf(analyst_client: AsyncClient):
    res = await analyst_client.get(
        "/api/v1/reports/compliance",
        params={"framework": "iso27001", "report_type": "weekly", "format": "pdf"},
    )
    assert res.status_code == 200, res.text
    assert res.content[:4] == b"%PDF"
