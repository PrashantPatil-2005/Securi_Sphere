from app.services.mitre import EVENT_MITRE_MAP, event_types_for_technique, event_technique_clause


def test_event_types_for_technique():
    types = event_types_for_technique("T1110.001")
    assert "ssh_login_failure" in types


def test_event_types_unknown_technique():
    assert event_types_for_technique("T9999") == []


def test_event_technique_clause_includes_mapped_types():
    clause = event_technique_clause("T1078")
    compiled = str(clause.compile(compile_kwargs={"literal_binds": True}))
    assert "mitre_technique_id" in compiled
    assert "ssh_login_success" in compiled or "event_type" in compiled


def test_matrix_map_covers_seed_techniques():
    technique_ids = {m["technique_id"] for m in EVENT_MITRE_MAP.values()}
    assert "T1110.001" in technique_ids
    assert "T1078" in technique_ids
