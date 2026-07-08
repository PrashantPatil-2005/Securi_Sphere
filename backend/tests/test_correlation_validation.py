"""Correlation rule validation unit tests."""

from app.services.correlation.validation import RuleDraft, validate_rule_draft


def test_validate_sequence_rule_ok():
    draft = RuleDraft(
        rule_type="sequence",
        event_sequence=["ssh_login_failure", "ssh_login_success"],
        min_occurrences={"ssh_login_failure": 3},
    )
    assert validate_rule_draft(draft) == []


def test_validate_co_occurrence_requires_two_types():
    draft = RuleDraft(rule_type="co_occurrence", event_sequence=["ssh_login_failure"])
    errors = validate_rule_draft(draft)
    assert any("at least 2" in e for e in errors)


def test_validate_invalid_rule_type():
    draft = RuleDraft(rule_type="invalid", event_sequence=["ssh_login_failure"])
    errors = validate_rule_draft(draft)
    assert any("rule_type" in e for e in errors)
