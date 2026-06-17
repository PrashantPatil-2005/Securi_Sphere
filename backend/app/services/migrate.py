"""Apply schema upgrades for advanced features on existing databases."""
import asyncio

from sqlalchemy import text

from app.database import Base, engine

# Safe additive migrations for PostgreSQL (existing dev DBs).
COLUMN_MIGRATIONS = [
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_hash VARCHAR(64)",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_version VARCHAR(20)",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_hash_changed_at TIMESTAMPTZ",
    "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS health_status VARCHAR(20) DEFAULT 'healthy'",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS mitre_technique_id VARCHAR(20)",
    "ALTER TABLE events ADD COLUMN IF NOT EXISTS mitre_tactic VARCHAR(50)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_technique_id VARCHAR(20)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS mitre_tactic VARCHAR(50)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS revoked_by UUID REFERENCES users(id)",
    "ALTER TABLE enrollment_tokens ADD COLUMN IF NOT EXISTS label VARCHAR(100)",
    "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES users(id)",
]

INDEX_MIGRATIONS = [
    "CREATE INDEX IF NOT EXISTS ix_events_timestamp_host ON events (timestamp DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_events_host_severity ON events (host_id, severity)",
    "CREATE INDEX IF NOT EXISTS ix_events_type_timestamp ON events (event_type, timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_created_status ON alerts (created_at DESC, status)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_host_severity ON alerts (host_id, severity)",
    "CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status)",
    "CREATE INDEX IF NOT EXISTS ix_metrics_recorded_host ON metrics (recorded_at DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_timelines_started_host ON attack_timelines (started_at DESC, host_id)",
    "CREATE INDEX IF NOT EXISTS ix_offenses_host_status ON offenses (host_id, status)",
    "CREATE INDEX IF NOT EXISTS ix_offenses_created ON offenses (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_offense_events_offense ON offense_events (offense_id)",
    "CREATE INDEX IF NOT EXISTS ix_host_risk_scores_host_time ON host_risk_scores (host_id, recorded_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_host_risk_scores_risk ON host_risk_scores (risk_score DESC)",
    "CREATE INDEX IF NOT EXISTS ix_saved_searches_user ON saved_searches (user_id)",
    "CREATE INDEX IF NOT EXISTS ix_generated_reports_created ON generated_reports (created_at DESC)",
]


async def migrate_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for stmt in COLUMN_MIGRATIONS:
            await conn.execute(text(stmt))
        for stmt in INDEX_MIGRATIONS:
            await conn.execute(text(stmt))
    print("Schema migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate_schema())
