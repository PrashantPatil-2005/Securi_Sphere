"""Check constraints for domain enums."""

from alembic import op

revision = "003_constraints"
down_revision = "002_indexes"
branch_labels = None
depends_on = None

CONSTRAINTS = [
    ("events", "chk_events_severity", "severity IN ('info','low','medium','high','critical')"),
    ("alerts", "chk_alerts_severity", "severity IN ('info','low','medium','high','critical')"),
    ("alerts", "chk_alerts_status", "status IN ('open','investigating','resolved','closed')"),
    ("offenses", "chk_offenses_status", "status IN ('open','investigating','closed')"),
    ("host_threat_scores", "chk_threat_score_range", "score >= 0 AND score <= 100"),
]


def _add_check(table: str, name: str, check: str) -> str:
    return f"""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = '{name}'
      ) THEN
        ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({check});
      END IF;
    END $$;
    """


def upgrade() -> None:
    for table, name, check in CONSTRAINTS:
        op.execute(_add_check(table, name, check))


def downgrade() -> None:
    for table, name, _ in reversed(CONSTRAINTS):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
