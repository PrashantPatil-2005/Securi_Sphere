"""Baseline schema — use alembic stamp head on existing DBs created via migrate.py."""

revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Schema is managed by app.services.migrate on startup for greenfield installs.
    # This revision establishes Alembic history for CI and future autogenerate.
    pass


def downgrade() -> None:
    pass
