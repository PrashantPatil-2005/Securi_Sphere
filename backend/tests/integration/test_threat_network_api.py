"""Integration tests for threat scores and network topology APIs."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host


@pytest.mark.asyncio
async def test_threat_scores_ranked(analyst_client: AsyncClient):
    await enroll_test_host(analyst_client, "threat-score-host")
    res = await analyst_client.get("/api/v1/threat-scores")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


@pytest.mark.asyncio
async def test_network_topology(analyst_client: AsyncClient):
    await enroll_test_host(analyst_client, "network-topo-host")
    res = await analyst_client.get("/api/v1/network/topology")
    assert res.status_code == 200
    body = res.json()
    assert "nodes" in body and "edges" in body
    assert any(n["id"] == "server" for n in body["nodes"])
