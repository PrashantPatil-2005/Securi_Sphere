"""Alembic 014 — TOTP MFA on users."""

from alembic import op

revision = "014_user_mfa"
down_revision = "013_dashboard_layouts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret VARCHAR(64)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_pending_secret VARCHAR(64)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_backup_codes JSONB NOT NULL DEFAULT '[]'")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS mfa_backup_codes")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS mfa_pending_secret")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS mfa_secret")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS mfa_enabled")
