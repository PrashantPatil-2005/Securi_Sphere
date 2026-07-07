"""Integration tests for host metrics API."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host


@pytest.mark.asyncio
async def test_list_metrics_empty(analyst_client: AsyncClient):
    host_id, _ = await enroll_test_host(analyst_client, "metrics-api-host")
    res = await analyst_client.get("/api/v1/metrics", params={"host_id": host_id})
    assert res.status_code == 200
    assert res.json() == []
