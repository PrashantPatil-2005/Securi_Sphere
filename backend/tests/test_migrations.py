from app.services.detection import SUPPORTED_RULE_TYPES


def test_supported_rule_types_exported():
    assert "agent_offline" in SUPPORTED_RULE_TYPES


def test_index_migrations_defined():
    from app.services.migrate import INDEX_MIGRATIONS
    assert len(INDEX_MIGRATIONS) >= 10
    assert any("events" in idx for idx in INDEX_MIGRATIONS)
