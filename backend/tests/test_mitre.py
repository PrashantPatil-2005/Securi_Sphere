"""Tests for MITRE ATT&CK service functions."""

from types import SimpleNamespace

from app.services.mitre import (
    EVENT_MITRE_MAP,
    MITRE_SEED,
    enrich_event,
    event_types_for_technique,
    get_matrix_summary,
)


# ---------------------------------------------------------------------------
# EVENT_MITRE_MAP
# ---------------------------------------------------------------------------

def test_event_mitre_map_has_known_types():
    expected = {
        "ssh_login_failure",
        "ssh_login_success",
        "root_login",
        "sudo_usage",
        "service_failure",
        "service_start",
        "service_stop",
    }
    assert set(EVENT_MITRE_MAP.keys()) == expected


def test_each_mapping_has_required_fields():
    for event_type, mapping in EVENT_MITRE_MAP.items():
        assert "technique_id" in mapping, f"{event_type} missing technique_id"
        assert "tactic" in mapping, f"{event_type} missing tactic"
        assert "name" in mapping, f"{event_type} missing name"
        assert mapping["technique_id"].startswith("T"), f"{event_type} bad technique_id format"


# ---------------------------------------------------------------------------
# MITRE_SEED
# ---------------------------------------------------------------------------

def test_mitre_seed_non_empty():
    assert len(MITRE_SEED) >= 20


def test_mitre_seed_unique_technique_ids():
    ids = [m["technique_id"] for m in MITRE_SEED]
    assert len(ids) == len(set(ids))


def test_mitre_seed_entries_have_required_fields():
    for m in MITRE_SEED:
        assert "technique_id" in m
        assert "tactic" in m
        assert "name" in m


# ---------------------------------------------------------------------------
# enrich_event
# ---------------------------------------------------------------------------

def test_enrich_event_known_type():
    event = SimpleNamespace(
        event_type="ssh_login_failure",
        mitre_technique_id=None,
        mitre_tactic=None,
        metadata_=None,
    )
    enrich_event(event)
    assert event.mitre_technique_id == "T1110.001"
    assert event.mitre_tactic == "Credential Access"
    assert event.metadata_["mitre"]["technique_id"] == "T1110.001"


def test_enrich_event_unknown_type():
    event = SimpleNamespace(
        event_type="unknown_event",
        mitre_technique_id=None,
        mitre_tactic=None,
        metadata_=None,
    )
    enrich_event(event)
    assert event.mitre_technique_id is None
    assert event.mitre_tactic is None


def test_enrich_event_preserves_existing_metadata():
    event = SimpleNamespace(
        event_type="sudo_usage",
        mitre_technique_id=None,
        mitre_tactic=None,
        metadata_={"existing_key": "value"},
    )
    enrich_event(event)
    assert event.metadata_["existing_key"] == "value"
    assert "mitre" in event.metadata_


# ---------------------------------------------------------------------------
# event_types_for_technique
# ---------------------------------------------------------------------------

def test_event_types_for_technique_brute_force():
    types = event_types_for_technique("T1110.001")
    assert "ssh_login_failure" in types


def test_event_types_for_technique_service_stop():
    types = event_types_for_technique("T1489")
    assert "service_failure" in types
    assert "service_stop" in types


def test_event_types_for_technique_no_match():
    types = event_types_for_technique("T9999")
    assert types == []


# ---------------------------------------------------------------------------
# get_matrix_summary
# ---------------------------------------------------------------------------

def test_get_matrix_summary_empty():
    assert get_matrix_summary([]) == {}


def test_get_matrix_summary_groups_by_technique():
    events = [
        SimpleNamespace(event_type="ssh_login_failure", mitre_technique_id=None),
        SimpleNamespace(event_type="ssh_login_failure", mitre_technique_id="T1110.001"),
        SimpleNamespace(event_type="ssh_login_success", mitre_technique_id=None),
    ]
    summary = get_matrix_summary(events)
    assert "T1110.001" in summary
    assert summary["T1110.001"]["count"] == 2
    assert summary["T1110.001"]["tactic"] == "Credential Access"


def test_get_matrix_summary_uses_event_type_fallback():
    events = [
        SimpleNamespace(event_type="sudo_usage", mitre_technique_id=None),
    ]
    summary = get_matrix_summary(events)
    assert "T1548.003" in summary
    assert summary["T1548.003"]["count"] == 1


def test_get_matrix_summary_skips_unknown():
    events = [
        SimpleNamespace(event_type="completely_unknown", mitre_technique_id=None),
    ]
    summary = get_matrix_summary(events)
    assert summary == {}
