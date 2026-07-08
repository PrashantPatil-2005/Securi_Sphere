"""Alembic 017 — false-positive feedback loop fields."""

from alembic import op

revision = "017_false_positive_feedback_loop"
down_revision = "016_analytics_materialized_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS feedback_label VARCHAR(32)")
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS feedback_note TEXT")
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMPTZ")
    op.execute("ALTER TABLE alerts ADD COLUMN IF NOT EXISTS feedback_by UUID REFERENCES users(id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alerts_feedback_label ON alerts (feedback_label)")

    op.execute("ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS false_positive_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS true_positive_count INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE alert_rules ADD COLUMN IF NOT EXISTS feedback_last_updated_at TIMESTAMPTZ")


def downgrade() -> None:
    op.execute("ALTER TABLE alert_rules DROP COLUMN IF EXISTS feedback_last_updated_at")
    op.execute("ALTER TABLE alert_rules DROP COLUMN IF EXISTS true_positive_count")
    op.execute("ALTER TABLE alert_rules DROP COLUMN IF EXISTS false_positive_count")

    op.execute("DROP INDEX IF EXISTS ix_alerts_feedback_label")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS feedback_by")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS feedback_at")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS feedback_note")
    op.execute("ALTER TABLE alerts DROP COLUMN IF EXISTS feedback_label")
