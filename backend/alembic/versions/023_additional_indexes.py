"""Additional composite indexes for high-volume query patterns."""

from alembic import op

revision = "023_additional_indexes"
down_revision = "022_atomic_alert_dedup"
branch_labels = None
depends_on = None

INDEXES = [
    # Host listing by status (dashboard, host list)
    "CREATE INDEX IF NOT EXISTS ix_hosts_status_created ON hosts (status, created_at DESC)",
    # MITRE technique filtering on alerts
    "CREATE INDEX IF NOT EXISTS ix_alerts_mitre_technique ON alerts (mitre_technique_id) WHERE mitre_technique_id IS NOT NULL",
    # Audit log queries by user + time
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_timestamp ON audit_logs (user_id, timestamp DESC)",
    # Audit log queries by action + time
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_action_timestamp ON audit_logs (action, timestamp DESC)",
    # Maintenance window batch check (host + time range)
    "CREATE INDEX IF NOT EXISTS ix_maintenance_host_times ON maintenance_windows (host_id, starts_at, ends_at)",
    # Incident listing by status + created
    "CREATE INDEX IF NOT EXISTS ix_incidents_status_created ON incidents (status, created_at DESC)",
    # Offense listing by status + updated
    "CREATE INDEX IF NOT EXISTS ix_offenses_status_updated ON offenses (status, updated_at DESC)",
    # Correlation result dedup: prevent duplicate results per rule+host within a time window
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_correlation_results_dedup ON correlation_results (rule_id, host_id, detected_at)",
]


def upgrade() -> None:
    for stmt in INDEXES:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in reversed(INDEXES):
        name = stmt.split("IF NOT EXISTS ")[1].split(" ON ")[0].strip()
        op.execute(f"DROP INDEX IF EXISTS {name}")
