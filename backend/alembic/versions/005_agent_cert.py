"""Alembic 005 — agent mTLS fingerprint column."""

from alembic import op

revision = "005_agent_cert"
down_revision = "004_event_partitions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS agent_cert_fingerprint VARCHAR(64)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE hosts DROP COLUMN IF EXISTS agent_cert_fingerprint")
