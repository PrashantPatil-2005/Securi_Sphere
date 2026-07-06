"""Convert events to monthly RANGE partitions (PostgreSQL)."""

from alembic import op

revision = "004_event_partitions"
down_revision = "003_constraints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.config import settings

    if not settings.event_partitioning_enabled:
        return

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'public.events'::regclass) THEN
            RETURN;
          END IF;

          ALTER TABLE events RENAME TO events_legacy;

          CREATE TABLE events (
            id UUID NOT NULL,
            host_id UUID NOT NULL REFERENCES hosts(id),
            event_type VARCHAR(100) NOT NULL,
            mitre_technique_id VARCHAR(20),
            mitre_tactic VARCHAR(50),
            severity VARCHAR(20) NOT NULL,
            category VARCHAR(50),
            description TEXT,
            source VARCHAR(50),
            source_ip INET,
            username VARCHAR(255),
            raw_log TEXT,
            raw_event TEXT,
            normalized_event JSONB,
            metadata JSONB,
            timestamp TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (id, timestamp)
          ) PARTITION BY RANGE (timestamp);

          CREATE TABLE events_default PARTITION OF events DEFAULT;
          INSERT INTO events SELECT * FROM events_legacy;
          DROP TABLE events_legacy;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_partitioned_table WHERE partrelid = 'public.events'::regclass) THEN
            RETURN;
          END IF;
          CREATE TABLE events_flat AS SELECT * FROM events;
          DROP TABLE events CASCADE;
          ALTER TABLE events_flat ADD PRIMARY KEY (id);
          ALTER TABLE events_flat RENAME TO events;
        END $$;
        """
    )
