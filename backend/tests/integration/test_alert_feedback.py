"""Integration tests for alert false-positive feedback loop."""

import pytest
from httpx import AsyncClient

from tests.integration.helpers import enroll_test_host, event_payload, ingest_events


@pytest.mark.asyncio
async def test_mark_false_positive_closes_alert_and_updates_rule_counts(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "feedback-loop-host")
    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("ssh_login_failure", severity="medium") for _ in range(6)],
    )

    listed = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    if not items:
        pytest.skip("No open alerts generated for feedback flow in this environment")
    alert = items[0]

    res = await analyst_client.patch(
        f"/api/v1/alerts/{alert['id']}/feedback",
        json={"label": "false_positive", "note": "Lab noise"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["feedback_label"] == "false_positive"
    assert body["feedback_note"] == "Lab noise"
    assert body["status"] == "closed"

    insights = await analyst_client.get("/api/v1/alert-rules/feedback-insights")
    assert insights.status_code == 200, insights.text
    insight_items = insights.json()["items"]
    matched = next((i for i in insight_items if i["rule_id"] == alert["rule_id"]), None)
    assert matched is not None
    assert matched["false_positive_count"] >= 1


@pytest.mark.asyncio
async def test_mark_true_positive_updates_feedback(analyst_client: AsyncClient):
    host_id, api_key = await enroll_test_host(analyst_client, "feedback-loop-host-tp")
    await ingest_events(
        analyst_client,
        api_key,
        [event_payload("ssh_login_failure", severity="medium") for _ in range(6)],
    )

    listed = await analyst_client.get("/api/v1/alerts", params={"host_id": host_id, "status": "open"})
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    if not items:
        pytest.skip("No open alerts generated for feedback flow in this environment")
    alert = items[0]

    res = await analyst_client.patch(
        f"/api/v1/alerts/{alert['id']}/feedback",
        json={"label": "true_positive"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["feedback_label"] == "true_positive"
