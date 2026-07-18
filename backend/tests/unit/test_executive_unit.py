"""Unit tests for executive report helpers."""

from app.services.executive_report import _build_recommendations, export_executive_pdf


def test_build_recommendations_critical():
    recs = _build_recommendations(
        summary={"critical_alerts": 3, "online_hosts": 10, "total_hosts": 10, "average_risk_score": 30},
        open_offenses=0,
        ueba_open=0,
        failed={"total_failures": 0},
    )
    assert any("critical" in r.lower() for r in recs)


def test_build_recommendations_default():
    recs = _build_recommendations(
        summary={"critical_alerts": 0, "online_hosts": 10, "total_hosts": 10, "average_risk_score": 20},
        open_offenses=0,
        ueba_open=0,
        failed={"total_failures": 0},
    )
    assert len(recs) >= 1


def test_export_executive_pdf_bytes():
    data = {
        "title": "Test Executive Report",
        "period_start": "2026-07-01T00:00:00+00:00",
        "period_end": "2026-07-07T00:00:00+00:00",
        "generated_at": "2026-07-07T12:00:00+00:00",
        "executive_summary": {
            "total_hosts": 5,
            "online_hosts": 4,
            "active_alerts": 2,
            "critical_alerts": 0,
            "total_events": 100,
            "period_alerts": 3,
            "average_risk_score": 25,
        },
        "severity_distribution": [{"severity": "high", "count": 1, "percentage": 50}],
        "top_risky_hosts": [{"host_name": "web-01", "risk_score": 80, "active_alerts": 1}],
        "mitre_techniques": [{"technique_id": "T1110", "tactic": "Credential Access", "count": 5}],
        "failed_logins": {"total": 10, "unique_ips": 2, "top_ips": [{"source_ip": "203.0.113.1", "count": 7}]},
        "open_offenses": 1,
        "open_incidents": 0,
        "ueba_open_anomalies": 0,
        "recommendations": ["Continue monitoring."],
    }
    response = export_executive_pdf(data, "test.pdf")
    assert response.media_type == "application/pdf"
    assert response.body[:4] == b"%PDF"
