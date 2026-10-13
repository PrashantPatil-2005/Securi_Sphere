"""Add incident investigation fields and event process/docker fields.

The SQLAlchemy models gained these columns while the live schema (stamped at
024) still lacked them, so any SELECT against `incidents` / `events` failed with
UndefinedColumnError. Baseline 001 uses Base.metadata.create_all(), so fresh
databases already have these columns; every statement is therefore IF NOT EXISTS.
"""

from alembic import op

revision = "025_investigation_fields"
down_revision = "024_refresh_token_revoked_at"
branch_labels = None
depends_on = None


INCIDENT_COLUMNS = [
    ("confidence", "DOUBLE PRECISION NOT NULL DEFAULT 0.0"),
    ("first_observed", "TIMESTAMP WITH TIME ZONE"),
    ("last_observed", "TIMESTAMP WITH TIME ZONE"),
    ("affected_hosts", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("affected_users", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("affected_services", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("affected_containers", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("mitre_technique_ids", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("mitre_tactics", "JSONB NOT NULL DEFAULT '[]'::jsonb"),
    ("simulated", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("source", "VARCHAR(20)"),
]

EVENT_COLUMNS = [
    ("process_id", "VARCHAR(100)"),
    ("parent_process_id", "VARCHAR(100)"),
    ("docker_service_id", "VARCHAR(100)"),
    ("docker_container_name", "VARCHAR(255)"),
]

EVENT_INDEXES = [
    ("ix_events_process_id", "process_id"),
    ("ix_events_parent_process_id", "parent_process_id"),
    ("ix_events_docker_service_id", "docker_service_id"),
]


def upgrade() -> None:
    for name, ddl in INCIDENT_COLUMNS:
        op.execute(f"ALTER TABLE incidents ADD COLUMN IF NOT EXISTS {name} {ddl}")

    for name, ddl in EVENT_COLUMNS:
        # `events` may be RANGE-partitioned: ALTER on the parent propagates to
        # every partition, and a partition created later inherits the columns.
        op.execute(f"ALTER TABLE events ADD COLUMN IF NOT EXISTS {name} {ddl}")

    for index, column in EVENT_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {index} ON events ({column})")


def downgrade() -> None:
    for index, _column in reversed(EVENT_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {index}")

    for name, _ddl in reversed(EVENT_COLUMNS):
        op.execute(f"ALTER TABLE events DROP COLUMN IF EXISTS {name}")

    for name, _ddl in reversed(INCIDENT_COLUMNS):
        op.execute(f"ALTER TABLE incidents DROP COLUMN IF EXISTS {name}")
