"""False-positive feedback helpers for alert rules."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.alert import Alert
from app.models.alert_rule import AlertRule

VALID_FEEDBACK_LABELS = frozenset({"false_positive", "true_positive"})


def apply_feedback_to_rule(rule: AlertRule | None, previous_label: str | None, new_label: str | None) -> None:
    if not rule:
        return

    if previous_label == "false_positive":
        rule.false_positive_count = max(0, (rule.false_positive_count or 0) - 1)
    elif previous_label == "true_positive":
        rule.true_positive_count = max(0, (rule.true_positive_count or 0) - 1)

    if new_label == "false_positive":
        rule.false_positive_count = (rule.false_positive_count or 0) + 1
    elif new_label == "true_positive":
        rule.true_positive_count = (rule.true_positive_count or 0) + 1

    rule.feedback_last_updated_at = datetime.now(timezone.utc)


def rule_feedback_insight(rule: AlertRule) -> dict:
    fp = rule.false_positive_count or 0
    tp = rule.true_positive_count or 0
    total = fp + tp
    fp_rate = round(fp / total, 3) if total else 0.0

    recommendation = "healthy"
    if total >= 5 and fp_rate >= 0.6:
        recommendation = "consider_threshold_increase"
    if total >= 8 and fp_rate >= 0.75:
        recommendation = "consider_disabling_or_refining"

    return {
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "rule_type": rule.rule_type,
        "enabled": rule.enabled,
        "false_positive_count": fp,
        "true_positive_count": tp,
        "feedback_total": total,
        "false_positive_rate": fp_rate,
        "recommendation": recommendation,
        "feedback_last_updated_at": rule.feedback_last_updated_at.isoformat() if rule.feedback_last_updated_at else None,
    }


def apply_feedback_to_alert(alert: Alert, *, label: str | None, note: str | None, user_id) -> None:
    alert.feedback_label = label
    alert.feedback_note = (note or "").strip()[:500] or None
    alert.feedback_by = user_id if label else None
    alert.feedback_at = datetime.now(timezone.utc) if label else None
