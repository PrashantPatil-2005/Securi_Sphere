"""Alembic 010 — SOAR playbooks and run audit."""

from alembic import op

revision = "010_playbooks"
down_revision = "009_reference_sets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS playbooks (
            id UUID PRIMARY KEY,
            name VARCHAR(128) NOT NULL UNIQUE,
            description TEXT,
            trigger_event VARCHAR(64) NOT NULL,
            min_severity VARCHAR(16),
            webhook_url VARCHAR(1024) NOT NULL,
            webhook_secret VARCHAR(255),
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS playbook_runs (
            id UUID PRIMARY KEY,
            playbook_id UUID NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
            trigger_event VARCHAR(64) NOT NULL,
            status VARCHAR(32) NOT NULL,
            http_status INTEGER,
            error_message TEXT,
            payload JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_playbook_runs_playbook_id ON playbook_runs (playbook_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_playbook_runs_created_at ON playbook_runs (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS playbook_runs")
    op.execute("DROP TABLE IF EXISTS playbooks")
