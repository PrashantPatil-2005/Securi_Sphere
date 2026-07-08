"""Analytics materialized views — migration 016."""

from alembic import op

revision = "016_analytics_materialized_views"
down_revision = "015_immutable_audit"
branch_labels = None
depends_on = None

_VIEWS = [
    (
        "mv_events_daily",
        """
        CREATE MATERIALIZED VIEW mv_events_daily AS
        SELECT
          (date_trunc('day', e.timestamp AT TIME ZONE 'UTC'))::date AS bucket_day,
          e.host_id,
          e.event_type,
          e.severity,
          COUNT(*)::bigint AS event_count
        FROM events e
        WHERE e.source IS NULL OR e.source != 'simulation'
        GROUP BY 1, 2, 3, 4
        """,
        "CREATE UNIQUE INDEX uq_mv_events_daily ON mv_events_daily (bucket_day, host_id, event_type, severity)",
    ),
    (
        "mv_alerts_daily",
        """
        CREATE MATERIALIZED VIEW mv_alerts_daily AS
        SELECT
          (date_trunc('day', a.created_at AT TIME ZONE 'UTC'))::date AS bucket_day,
          a.severity,
          COUNT(*)::bigint AS alert_count
        FROM alerts a
        GROUP BY 1, 2
        """,
        "CREATE UNIQUE INDEX uq_mv_alerts_daily ON mv_alerts_daily (bucket_day, severity)",
    ),
    (
        "mv_failed_logins_daily",
        """
        CREATE MATERIALIZED VIEW mv_failed_logins_daily AS
        SELECT
          (date_trunc('day', e.timestamp AT TIME ZONE 'UTC'))::date AS bucket_day,
          e.host_id,
          COALESCE(e.username, '') AS username,
          COUNT(*)::bigint AS fail_count
        FROM events e
        WHERE e.event_type = 'ssh_login_failure'
          AND (e.source IS NULL OR e.source != 'simulation')
        GROUP BY 1, 2, 3
        """,
        "CREATE UNIQUE INDEX uq_mv_failed_logins_daily ON mv_failed_logins_daily (bucket_day, host_id, username)",
    ),
]


def upgrade() -> None:
    for name, create_sql, index_sql in _VIEWS:
        op.execute(f"{create_sql} WITH NO DATA")
        op.execute(index_sql)
        op.execute(f"REFRESH MATERIALIZED VIEW {name}")


def downgrade() -> None:
    for name, _, _ in reversed(_VIEWS):
        op.execute(f"DROP MATERIALIZED VIEW IF EXISTS {name}")
