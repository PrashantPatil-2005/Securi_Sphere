"""Check constraints for domain enums."""

from alembic import op

revision = "003_constraints"
down_revision = "002_indexes"
branch_labels = None
depends_on = None

CONSTRAINTS = [
    "ALTER TABLE events ADD CONSTRAINT IF NOT EXISTS chk_events_severity CHECK (severity IN ('info','low','medium','high','critical'))",
    "ALTER TABLE alerts ADD CONSTRAINT IF NOT EXISTS chk_alerts_severity CHECK (severity IN ('info','low','medium','high','critical'))",
    "ALTER TABLE alerts ADD CONSTRAINT IF NOT EXISTS chk_alerts_status CHECK (status IN ('open','investigating','resolved','closed'))",
    "ALTER TABLE offenses ADD CONSTRAINT IF NOT EXISTS chk_offenses_status CHECK (status IN ('open','investigating','closed'))",
    "ALTER TABLE host_threat_scores ADD CONSTRAINT IF NOT EXISTS chk_threat_score_range CHECK (score >= 0 AND score <= 100)",
]


def upgrade() -> None:
    for stmt in CONSTRAINTS:
        op.execute(stmt)


def downgrade() -> None:
    for stmt in reversed(CONSTRAINTS):
        name = stmt.split("IF NOT EXISTS ")[1].split(" CHECK")[0].strip()
        table = stmt.split("TABLE ")[1].split(" ADD")[0].strip()
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
