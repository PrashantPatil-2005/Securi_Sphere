"""Baseline schema from SQLAlchemy models."""

from alembic import op

revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import app.models  # noqa: F401 — register models
    from app.database import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    import app.models  # noqa: F401
    from app.database import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind)
