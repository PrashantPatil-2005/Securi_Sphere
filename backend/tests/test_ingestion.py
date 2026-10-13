from app.services.detection import SUPPORTED_RULE_TYPES
from app.services.ingest_dedup import event_fingerprint


def test_event_fingerprint_stable():
    from datetime import datetime, timezone
    from uuid import uuid4

    host_id = uuid4()
    fp1 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Failed password")
    fp2 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Failed password")
    fp3 = event_fingerprint(host_id, "ssh_login_failure", raw_log="Different log")
    assert fp1 == fp2
    assert fp1 != fp3


def test_rule_type_validation_set():
    assert len(SUPPORTED_RULE_TYPES) == 15
