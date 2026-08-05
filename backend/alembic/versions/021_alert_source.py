"""Alembic 021 — add source column to alerts for simulation filtering."""

from alembic import op

revision = "021_alert_source"
down_revision = "020_telemetry_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('ALTER TABLE alerts ADD COLUMN IF NOT EXISTS source VARCHAR(50)')
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_source ON alerts (source)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alerts_source")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS source")
