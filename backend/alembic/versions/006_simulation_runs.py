"""Alembic 006 — simulation run history table."""

from alembic import op

revision = "006_simulation_runs"
down_revision = "005_agent_cert"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id UUID PRIMARY KEY,
            host_id UUID NOT NULL REFERENCES hosts(id),
            user_id UUID NOT NULL REFERENCES users(id),
            scenario_id VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            event_count INTEGER NOT NULL DEFAULT 0,
            alert_count INTEGER NOT NULL DEFAULT 0,
            offense_count INTEGER NOT NULL DEFAULT 0,
            timeline_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulation_runs_host_id ON simulation_runs (host_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulation_runs_user_id ON simulation_runs (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulation_runs_scenario_id ON simulation_runs (scenario_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_simulation_runs_created_at ON simulation_runs (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS simulation_runs")
