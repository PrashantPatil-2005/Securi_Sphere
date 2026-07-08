"""Alembic 020 — product telemetry events."""

from alembic import op

revision = "020_telemetry_events"
down_revision = "019_generated_report_type_length"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry_events (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id),
            event VARCHAR(100) NOT NULL,
            properties JSONB,
            session_id VARCHAR(64),
            page_path VARCHAR(255),
            ip_address VARCHAR(45),
            request_id VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_events_event ON telemetry_events (event)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_events_user_id ON telemetry_events (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_events_created_at ON telemetry_events (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_telemetry_events_session_id ON telemetry_events (session_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telemetry_events")
