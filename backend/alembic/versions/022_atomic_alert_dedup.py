"""Atomic alert deduplication and offense number sequence."""

from alembic import op

revision = "022_atomic_alert_dedup"
down_revision = "021_alert_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_alerts_dedup_open
        ON alerts (host_id, rule_id)
        WHERE status = 'open' AND rule_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_alerts_dedup_open_title
        ON alerts (host_id, title)
        WHERE status = 'open' AND rule_id IS NULL
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename = 'offense_number_seq') THEN
                CREATE SEQUENCE offense_number_seq START 1000 INCREMENT 1;
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alerts_dedup_open")
    op.execute("DROP INDEX IF EXISTS ix_alerts_dedup_open_title")
    op.execute("DROP SEQUENCE IF EXISTS offense_number_seq")
