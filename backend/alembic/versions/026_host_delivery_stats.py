"""Add hosts.delivery_stats for agent-reported delivery telemetry.

Agents include a sanitized delivery-stats block in their heartbeat (buffered
count, last flush, consecutive failures, dropped totals). The API stores the
latest snapshot on the host row so the host operations UI can show real
backlog/failure state without a separate telemetry store.

Baseline 001 uses Base.metadata.create_all(), so fresh databases already have
the column; the statement is IF NOT EXISTS.
"""

from alembic import op

revision = "026_host_delivery_stats"
down_revision = "025_investigation_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE hosts ADD COLUMN IF NOT EXISTS delivery_stats JSONB"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE hosts DROP COLUMN IF EXISTS delivery_stats")
