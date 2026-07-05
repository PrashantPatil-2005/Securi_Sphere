"""Performance indexes (additive, idempotent)."""

from alembic import op

revision = "002_indexes"
down_revision = "001_baseline"
branch_labels = None
depends_on = None

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_events_timestamp_host ON events (timestamp DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_events_host_severity ON events (host_id, severity)",
    "CREATE INDEX IF NOT EXISTS ix_events_type_timestamp ON events (event_type, timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS ix_events_category ON events (category)",
    "CREATE INDEX IF NOT EXISTS ix_events_username ON events (username)",
    "CREATE INDEX IF NOT EXISTS ix_events_source_ip ON events (source_ip)",
    "CREATE INDEX IF NOT EXISTS ix_events_normalized_gin ON events USING gin (normalized_event jsonb_path_ops)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_created_status ON alerts (created_at DESC, status)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_host_severity ON alerts (host_id, severity)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_recorded_host ON metrics (recorded_at DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_timelines_started_host ON attack_timelines (started_at DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_timelines_fingerprint ON attack_timelines (fingerprint)",
    "CREATE INDEX IF NOT EXISTS ix_offenses_host_status ON offenses (host_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_offenses_created ON offenses (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_offense_events_offense ON offense_events (offense_id)",
    "CREATE INDEX IF NOT EXISTS ix_host_risk_scores_host_time ON host_risk_scores (host_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_host_risk_scores_risk ON host_risk_scores (risk_score DESC)",
    "CREATE INDEX IF NOT EXISTS ix_saved_searches_user ON saved_searches (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_generated_reports_created ON generated_reports (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_user_sessions_user ON user_sessions (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_agent_nonces_host ON agent_request_nonces (host_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_analytics_daily_date_metric ON analytics_daily_stats (stat_date, metric_name)",
    "CREATE INDEX IF NOT EXISTS ix_in_app_notifications_created ON in_app_notifications (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_maintenance_host_ends ON maintenance_windows (host_id, ends_at)",
]


def upgrade() -> None:
    for stmt in INDEXES:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in reversed(INDEXES):
        name = stmt.split("IF NOT EXISTS ")[1].split(" ON ")[0].strip()
        op.execute(f"DROP INDEX IF EXISTS {name}")
