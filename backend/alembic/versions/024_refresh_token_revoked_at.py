"""Add revoked_at column to refresh_tokens for session revocation."""

from alembic import op
import sqlalchemy as sa

revision = "024_refresh_token_revoked_at"
down_revision = "023_additional_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Baseline migration 001 runs Base.metadata.create_all(), which already
    # creates revoked_at from the current model. Use IF NOT EXISTS so fresh
    # databases (and databases migrated before the column was added to the
    # model) both reach head without a DuplicateColumn error.
    op.execute(
        "ALTER TABLE refresh_tokens "
        "ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMP WITH TIME ZONE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE refresh_tokens DROP COLUMN IF EXISTS revoked_at")
