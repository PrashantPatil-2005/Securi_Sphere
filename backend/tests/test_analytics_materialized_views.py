"""Analytics materialized view helpers."""

from app.services.analytics.materialized_views import MV_NAMES, _bucket_sql, materialized_views_enabled


def test_materialized_views_enabled_default(monkeypatch):
    monkeypatch.setattr(
        "app.services.analytics.materialized_views.settings.analytics_materialized_views_enabled",
        True,
    )
    assert materialized_views_enabled() is True


def test_bucket_sql_daily():
    assert _bucket_sql("daily") == "bucket_day"


def test_bucket_sql_weekly():
    assert "date_trunc('week'" in _bucket_sql("weekly")


def test_bucket_sql_monthly():
    assert "date_trunc('month'" in _bucket_sql("monthly")


def test_mv_names_defined():
    assert "mv_events_daily" in MV_NAMES
    assert "mv_alerts_daily" in MV_NAMES
    assert "mv_failed_logins_daily" in MV_NAMES
