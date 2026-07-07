"""Alembic 008 — user invites for admin provisioning."""

from alembic import op

revision = "008_user_invites"
down_revision = "007_oidc_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_invites (
            id UUID PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            full_name VARCHAR(255),
            role_id UUID NOT NULL REFERENCES roles(id),
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            invited_by_id UUID NOT NULL REFERENCES users(id),
            expires_at TIMESTAMPTZ NOT NULL,
            accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_invites_email ON user_invites (email)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_invites")
