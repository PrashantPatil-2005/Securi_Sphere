"""Alembic 013 — per-user dashboard widget layouts."""

from alembic import op

revision = "013_dashboard_layouts"
down_revision = "012_notification_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS dashboard_layouts (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            widgets JSONB NOT NULL DEFAULT '[]',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_dashboard_layouts_user ON dashboard_layouts (user_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dashboard_layouts")
