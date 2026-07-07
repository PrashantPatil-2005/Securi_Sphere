"""Alembic 007 — OIDC identity fields on users."""

from alembic import op

revision = "007_oidc_users"
down_revision = "006_simulation_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_sub VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS oidc_issuer VARCHAR(512)")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_users_oidc_identity
        ON users (oidc_issuer, oidc_sub)
        WHERE oidc_sub IS NOT NULL
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_oidc_identity")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oidc_issuer")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS oidc_sub")
    op.execute("ALTER TABLE users ALTER COLUMN hashed_password SET NOT NULL")
