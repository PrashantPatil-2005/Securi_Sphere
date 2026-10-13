"""Tests for the port_scan detection rule (Scenario E network reconnaissance)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.services.detection import get_checker

pytestmark = pytest.mark.integration


async def _admin_user_id():
    from sqlalchemy import select

    from app.database import async_session
    from app.models.user import User

    async with async_session() as db:
        user = (
            await db.execute(select(User).where(User.email == "admin@test.local"))
        ).scalar_one()
        return user.id


async def _get_or_create_port_scan_rule():
    """Fetch the seeded port_scan rule, creating it if this DB was seeded pre-merge."""
    from sqlalchemy import select

    from app.database import async_session
    from app.models.alert_rule import AlertRule

    async with async_session() as db:
        rule = (
            await db.execute(
                select(AlertRule).where(AlertRule.rule_type == "port_scan")
            )
        ).scalar_one_or_none()
        if rule:
            return rule.id, rule.threshold, rule.window_minutes
        rule = AlertRule(
            name="Port Scan / Network Recon",
            rule_type="port_scan",
            threshold=10,
            window_minutes=5,
            severity="high",
            enabled=True,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return rule.id, rule.threshold, rule.window_minutes


def _make_flow_event(host_id, src_ip, dst_ip, dst_port, minutes_ago=0):
    from app.models.event import Event

    now = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return Event(
        id=uuid4(),
        host_id=host_id,
        event_type="network_flow",
        severity="info",
        source_ip=src_ip,
        source="flow-collector",
        description=f"TCP {src_ip} → {dst_ip}:{dst_port}",
        metadata_={
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "dst_port": dst_port,
            "protocol": "tcp",
        },
        timestamp=now,
    )


class TestPortScanCheckerRegistration:
    def test_registered(self):
        checker = get_checker("port_scan")
        assert checker is not None
        assert checker.rule_type == "port_scan"

    def test_description(self):
        checker = get_checker("port_scan")
        assert "reconnaissance" in checker.description.lower()


class TestPortScanDetection:
    @pytest.mark.asyncio
    async def test_fires_when_distinct_ports_exceed_threshold(self, prepare_database):
        from app.database import async_session
        from app.models.alert_rule import AlertRule
        from app.models.host import Host
        from app.services.detection import PortScanChecker
        from sqlalchemy import select

        host_id = uuid4()
        created_by = await _admin_user_id()
        rule_id, threshold, window_minutes = await _get_or_create_port_scan_rule()
        async with async_session() as db:
            host = Host(
                id=host_id,
                name=f"scan-host-{host_id.hex[:8]}",
                status="online",
                created_by=created_by,
            )
            db.add(host)
            rule = (
                await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
            ).scalar_one()
            for port in (21, 22, 23, 25, 80, 110, 143, 443, 3306, 8080):
                db.add(
                    _make_flow_event(
                        host_id, "198.51.100.7", "10.0.0.10", port, minutes_ago=1
                    )
                )
            await db.flush()

            checker = PortScanChecker()
            result = await checker.check(db, host, rule, datetime.now(timezone.utc))
            assert result is not None
            assert "198.51.100.7" in result["title"]
            assert result["mitre_technique_id"] == "T1046"
            assert result["mitre_tactic"] == "discovery"
            # Alert description must carry source, ports, window, and event refs
            desc = result["description"]
            assert "198.51.100.7" in desc
            assert "22" in desc and "3306" in desc
            assert str(window_minutes) in desc
            assert "Event refs:" in desc
            await db.rollback()

    @pytest.mark.asyncio
    async def test_does_not_fire_below_threshold(self, prepare_database):
        from app.database import async_session
        from app.models.alert_rule import AlertRule
        from app.models.host import Host
        from app.services.detection import PortScanChecker
        from sqlalchemy import select

        host_id = uuid4()
        created_by = await _admin_user_id()
        rule_id, _threshold, _window = await _get_or_create_port_scan_rule()
        async with async_session() as db:
            host = Host(
                id=host_id,
                name=f"scan-low-{host_id.hex[:8]}",
                status="online",
                created_by=created_by,
            )
            db.add(host)
            rule = (
                await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
            ).scalar_one()
            # Only 3 distinct ports — below default threshold of 10
            for port in (22, 80, 443):
                db.add(
                    _make_flow_event(
                        host_id, "198.51.100.7", "10.0.0.10", port, minutes_ago=1
                    )
                )
            await db.flush()

            checker = PortScanChecker()
            result = await checker.check(db, host, rule, datetime.now(timezone.utc))
            assert result is None
            await db.rollback()

    @pytest.mark.asyncio
    async def test_groups_by_source_ip(self, prepare_database):
        """Two sources with few ports each must not combine into one alert."""
        from app.database import async_session
        from app.models.alert_rule import AlertRule
        from app.models.host import Host
        from app.services.detection import PortScanChecker
        from sqlalchemy import select

        host_id = uuid4()
        created_by = await _admin_user_id()
        rule_id, _threshold, _window = await _get_or_create_port_scan_rule()
        async with async_session() as db:
            host = Host(
                id=host_id,
                name=f"scan-src-{host_id.hex[:8]}",
                status="online",
                created_by=created_by,
            )
            db.add(host)
            rule = (
                await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
            ).scalar_one()
            # Source A: 5 ports. Source B: 5 ports. Neither alone reaches 10.
            for port in (21, 22, 23, 25, 80):
                db.add(_make_flow_event(host_id, "10.1.1.1", "10.0.0.10", port))
            for port in (443, 3306, 8080, 110, 143):
                db.add(_make_flow_event(host_id, "10.1.1.2", "10.0.0.10", port))
            await db.flush()

            checker = PortScanChecker()
            result = await checker.check(db, host, rule, datetime.now(timezone.utc))
            assert result is None
            await db.rollback()


class TestFlowsEndpointIntegration:
    @pytest.mark.asyncio
    async def test_agent_flows_ingested_and_flow_status_reports_active(self, admin_client, prepare_database):
        """POST /agent/flows ingests network_flow events; GET /hosts/{id}/flow-status reflects them."""
        from datetime import datetime as dt

        from tests.integration.helpers import enroll_test_host

        host_id, api_key = await enroll_test_host(admin_client, "flow-host-e2e")
        now = dt.now(timezone.utc).isoformat()
        flows = [
            {
                "src_ip": "198.51.100.9",
                "dst_ip": "10.0.0.10",
                "src_port": 40000 + i,
                "dst_port": port,
                "protocol": "tcp",
                "direction": "outbound",
                "severity": "info",
                "source": "agent-flow-collector",
                "timestamp": now,
            }
            for i, port in enumerate((21, 22, 23, 25, 80, 110, 143, 443, 3306, 8080))
        ]
        res = await admin_client.post(
            "/api/v1/agent/flows",
            headers={"X-API-Key": api_key},
            json={"flows": flows},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["ingested"] == 10

        # Flow-status endpoint (admin) must show the collector as active.
        status_res = await admin_client.get(f"/api/v1/hosts/{host_id}/flow-status")
        assert status_res.status_code == 200, status_res.text
        status = status_res.json()
        assert status["collector_active"] is True
        assert status["flow_count_24h"] == 10
        assert status["distinct_dst_ports_24h"] == 10
        assert status["last_flow_at"] is not None
