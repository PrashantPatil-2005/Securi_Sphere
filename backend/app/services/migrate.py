"""Apply schema upgrades for existing databases."""
import asyncio
import logging

from sqlalchemy import text

import app.models  # noqa: F401 — register all models with Base.metadata
from app.database import Base, engine

logger = logging.getLogger(__name__)

COLUMN_MIGRATIONS = [
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_hash VARCHAR(64)",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_version VARCHAR(20)",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_hash_changed_at TIMESTAMPTZ",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS health_status VARCHAR(20) DEFAULT 'healthy'",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS api_key_created_at TIMESTAMPTZ",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS api_key_revoked_at TIMESTAMPTZ",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS mitre_technique_id VARCHAR(20)",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS mitre_tactic VARCHAR(50)",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS source_ip INET",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS username VARCHAR(255)",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS raw_event TEXT",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS normalized_event JSONB",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_technique_id VARCHAR(20)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_tactic VARCHAR(50)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS revoked_by UUID REFERENCES users(id)",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS label VARCHAR(100)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES users(id)",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(255)",
    "ALTER TABLE offenses ADD COLUMN IF NOT EXISTS alert_count INTEGER DEFAULT 0",
    "ALTER TABLE offenses ADD COLUMN IF NOT EXISTS related_hosts JSONB DEFAULT '[]'",
    "ALTER TABLE offenses ADD COLUMN IF NOT EXISTS related_users JSONB DEFAULT '[]'",
    "ALTER TABLE offenses ADD COLUMN IF NOT EXISTS timeline JSONB DEFAULT '[]'",
    "ALTER TABLE offenses ADD COLUMN IF NOT EXISTS incident_id UUID REFERENCES incidents(id)",
    "ALTER TABLE attack_timelines ADD COLUMN IF NOT EXISTS fingerprint VARCHAR(64)",
    "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS slack_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE notification_settings ADD COLUMN IF NOT EXISTS slack_webhook_url VARCHAR(512)",
    "ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS alert_enabled BOOLEAN DEFAULT FALSE",
    "ALTER TABLE saved_searches ADD COLUMN IF NOT EXISTS interval_minutes INTEGER DEFAULT 5",
    """CREATE TABLE IF NOT EXISTS maintenance_windows (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        host_id UUID NOT NULL REFERENCES hosts(id),
        reason TEXT,
        starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        ends_at TIMESTAMPTZ NOT NULL,
        created_by UUID REFERENCES users(id)
    )""",
    "CREATE INDEX IF NOT EXISTS ix_maintenance_host_ends ON maintenance_windows (host_id, ends_at)",
]

INDEX_MIGRATIONS = [
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
]

CONSTRAINT_MIGRATIONS = [
    "ALTER TABLE events ADD CONSTRAINT IF NOT EXISTS chk_events_severity CHECK (severity IN ('info','low','medium','high','critical'))",
    "ALTER TABLE alerts ADD CONSTRAINT IF NOT EXISTS chk_alerts_severity CHECK (severity IN ('info','low','medium','high','critical'))",
    "ALTER TABLE alerts ADD CONSTRAINT IF NOT EXISTS chk_alerts_status CHECK (status IN ('open','investigating','resolved','closed'))",
    "ALTER TABLE offenses ADD CONSTRAINT IF NOT EXISTS chk_offenses_status CHECK (status IN ('open','investigating','closed'))",
    "ALTER TABLE host_threat_scores ADD CONSTRAINT IF NOT EXISTS chk_threat_score_range CHECK (score >= 0 AND score <= 100)",
]


async def migrate_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    for stmt in COLUMN_MIGRATIONS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Column migration skipped: %s — %s", stmt[:60], exc)

    for stmt in INDEX_MIGRATIONS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Index migration skipped: %s — %s", stmt[:60], exc)

    for stmt in CONSTRAINT_MIGRATIONS:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception as exc:
            logger.warning("Constraint migration skipped: %s — %s", stmt[:60], exc)

    logger.info("Schema migration complete (%d indexes defined)", len(INDEX_MIGRATIONS))


if __name__ == "__main__":
    asyncio.run(migrate_schema())
