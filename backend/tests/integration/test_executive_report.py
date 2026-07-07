"""Integration tests for executive report API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_executive_report_json(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/reports/executive", params={"report_type": "weekly", "format": "json"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert "executive_summary" in body
    assert "recommendations" in body
    assert body["report_type"] == "weekly"


@pytest.mark.asyncio
async def test_executive_report_pdf(analyst_client: AsyncClient):
    res = await analyst_client.get("/api/v1/reports/executive", params={"report_type": "daily", "format": "pdf"})
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content[:4] == b"%PDF"
