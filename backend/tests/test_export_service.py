"""Tests for export service — CSV, JSON, PDF export."""

import json

from fastapi.responses import Response

from app.services.export_service import export_csv, export_json, export_pdf


# ---------------------------------------------------------------------------
# export_csv
# ---------------------------------------------------------------------------

def test_export_csv_basic():
    rows = [{"name": "web-01", "status": "online"}, {"name": "db-01", "status": "offline"}]
    resp = export_csv(rows, "hosts.csv")
    assert isinstance(resp, Response)
    assert resp.media_type == "text/csv"
    assert "hosts.csv" in resp.headers["Content-Disposition"]
    body = resp.body.decode()
    assert "name,status" in body
    assert "web-01" in body
    assert "db-01" in body


def test_export_csv_empty():
    resp = export_csv([], "empty.csv")
    body = resp.body.decode()
    assert "No data" in body


def test_export_csv_special_characters():
    rows = [{"name": "host,with,commas", "desc": 'value"with"quotes'}]
    resp = export_csv(rows, "special.csv")
    body = resp.body.decode()
    assert "host,with,commas" in body


def test_export_csv_single_column():
    rows = [{"host": "web-01"}, {"host": "web-02"}]
    resp = export_csv(rows, "hosts.csv")
    body = resp.body.decode()
    assert "host" in body
    assert "web-01" in body
    assert "web-02" in body


# ---------------------------------------------------------------------------
# export_json
# ---------------------------------------------------------------------------

def test_export_json_basic():
    rows = [{"name": "web-01", "cpu": 45}]
    resp = export_json(rows, "data.json")
    assert resp.media_type == "application/json"
    body = json.loads(resp.body.decode())
    assert len(body) == 1
    assert body[0]["name"] == "web-01"


def test_export_json_empty():
    resp = export_json([], "empty.json")
    body = json.loads(resp.body.decode())
    assert body == []


def test_export_json_preserves_types():
    rows = [{"count": 42, "flag": True, "nested": {"key": "val"}}]
    resp = export_json(rows, "types.json")
    body = json.loads(resp.body.decode())
    assert body[0]["count"] == 42
    assert body[0]["flag"] is True
    assert body[0]["nested"]["key"] == "val"


# ---------------------------------------------------------------------------
# export_pdf
# ---------------------------------------------------------------------------

def test_export_pdf_basic():
    rows = [{"host": "web-01", "cpu": 45}]
    resp = export_pdf(rows, "Test Report", "report.pdf")
    assert resp.media_type == "application/pdf"
    assert len(resp.body) > 0


def test_export_pdf_empty():
    resp = export_pdf([], "Empty Report", "empty.pdf")
    assert resp.media_type == "application/pdf"
    assert len(resp.body) > 0


def test_export_pdf_headers():
    rows = [{"col1": "val1", "col2": "val2"}]
    resp = export_pdf(rows, "Title", "test.pdf")
    assert "test.pdf" in resp.headers["Content-Disposition"]
