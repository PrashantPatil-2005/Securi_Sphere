"""Alembic 009 — reference sets and building blocks."""

from alembic import op

revision = "009_reference_sets"
down_revision = "008_user_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS reference_sets (
            id UUID PRIMARY KEY,
            name VARCHAR(128) NOT NULL UNIQUE,
            description TEXT,
            set_type VARCHAR(32) NOT NULL DEFAULT 'ip',
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS reference_set_entries (
            id UUID PRIMARY KEY,
            set_id UUID NOT NULL REFERENCES reference_sets(id) ON DELETE CASCADE,
            value VARCHAR(512) NOT NULL,
            note VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (set_id, value)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_reference_set_entries_value ON reference_set_entries (value)")
    op.execute("""
        CREATE TABLE IF NOT EXISTS building_blocks (
            id UUID PRIMARY KEY,
            name VARCHAR(128) NOT NULL UNIQUE,
            description TEXT,
            category VARCHAR(64) NOT NULL DEFAULT 'custom',
            siem_query TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS building_blocks")
    op.execute("DROP TABLE IF EXISTS reference_set_entries")
    op.execute("DROP TABLE IF EXISTS reference_sets")
