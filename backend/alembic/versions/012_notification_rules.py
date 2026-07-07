"""Alembic 012 — per-user notification rules."""

from alembic import op

revision = "012_notification_rules"
down_revision = "011_ueba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS notification_rules (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(128) NOT NULL,
            trigger_event VARCHAR(32) NOT NULL,
            min_severity VARCHAR(16) NOT NULL DEFAULT 'high',
            channels JSONB NOT NULL DEFAULT '{"email": true, "slack": false, "telegram": false}',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_rules_user ON notification_rules (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_rules_trigger ON notification_rules (trigger_event, enabled)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_rules")
