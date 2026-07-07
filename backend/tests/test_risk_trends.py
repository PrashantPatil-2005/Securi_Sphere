from datetime import datetime, timezone

from app.utils.query import TimeRange, resolve_time_range


def test_choose_risk_bucket_short_range():
    now = datetime.now(timezone.utc)
    tr = resolve_time_range("24h", None, None)
    from app.services.risk_trends import choose_risk_bucket

    assert choose_risk_bucket(tr) == "hour"


def test_choose_risk_bucket_long_range():
    tr = resolve_time_range("30d", None, None)
    from app.services.risk_trends import choose_risk_bucket

    assert choose_risk_bucket(tr) == "day"
