"""Add revoked_at column to refresh_tokens for session revocation."""

from alembic import op
import sqlalchemy as sa

revision = "024_refresh_token_revoked_at"
down_revision = "023_additional_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "revoked_at")
