"""Alembic 018 — threat intel feeds for reference sets."""

from alembic import op

revision = "018_threat_intel_feeds"
down_revision = "017_false_positive_feedback_loop"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS source_type VARCHAR(16) NOT NULL DEFAULT 'manual'")
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS feed_url TEXT")
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS feed_format VARCHAR(16)")
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS feed_last_sync_at TIMESTAMPTZ")
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS feed_last_sync_status VARCHAR(16)")
    op.execute("ALTER TABLE reference_sets ADD COLUMN IF NOT EXISTS feed_last_sync_error VARCHAR(255)")


def downgrade() -> None:
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS feed_last_sync_error")
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS feed_last_sync_status")
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS feed_last_sync_at")
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS feed_format")
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS feed_url")
    op.execute("ALTER TABLE reference_sets DROP COLUMN IF EXISTS source_type")
