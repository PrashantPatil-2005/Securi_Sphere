"""Unit tests for notification rule severity matching."""

from app.services.notification_rules import severity_meets_minimum


def test_merge_settings_for_test_overrides():
    from uuid import uuid4

    from app.models.notification import NotificationSettings
    from app.services.notification_rules import _merge_settings_for_test

    base = NotificationSettings(
        user_id=uuid4(),
        email_enabled=False,
        email_address="saved@example.com",
        slack_enabled=True,
        slack_webhook_url="https://hooks.slack.com/old",
        telegram_enabled=False,
        telegram_chat_id=None,
    )
    merged = _merge_settings_for_test(
        base,
        email_enabled=True,
        email_address="new@example.com",
    )
    assert merged.email_enabled is True
    assert merged.email_address == "new@example.com"
    assert merged.slack_webhook_url == "https://hooks.slack.com/old"


def test_severity_meets_minimum():
    assert severity_meets_minimum("critical", "high")
    assert severity_meets_minimum("high", "high")
    assert not severity_meets_minimum("low", "high")
