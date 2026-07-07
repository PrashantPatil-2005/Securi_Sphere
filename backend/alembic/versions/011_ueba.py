"""Alembic 011 — UEBA anomaly detections."""

from alembic import op

revision = "011_ueba"
down_revision = "010_playbooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS ueba_anomalies (
            id UUID PRIMARY KEY,
            entity_type VARCHAR(32) NOT NULL,
            entity_key VARCHAR(255) NOT NULL,
            entity_label VARCHAR(255) NOT NULL,
            metric VARCHAR(64) NOT NULL,
            observed_value INTEGER NOT NULL,
            baseline_mean DOUBLE PRECISION NOT NULL,
            baseline_stddev DOUBLE PRECISION NOT NULL,
            z_score DOUBLE PRECISION NOT NULL,
            severity VARCHAR(20) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            description TEXT NOT NULL,
            context JSONB DEFAULT '{}',
            alert_id UUID,
            detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_ueba_anomalies_entity ON ueba_anomalies (entity_type, entity_key)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ueba_anomalies_status_detected ON ueba_anomalies (status, detected_at DESC)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_ueba_open_entity_metric
        ON ueba_anomalies (entity_type, entity_key, metric)
        WHERE status = 'open'
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ueba_anomalies")
