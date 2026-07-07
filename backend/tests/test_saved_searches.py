from app.schemas.saved_search import SavedSearchCreate, SavedSearchUpdate


def test_saved_search_create_defaults():
    body = SavedSearchCreate(name="Failed logins", query="event_type:ssh_login_failure")
    assert body.alert_enabled is False
    assert body.interval_minutes == 5


def test_saved_search_update_partial():
    body = SavedSearchUpdate(alert_enabled=True)
    assert body.name is None
    assert body.alert_enabled is True
