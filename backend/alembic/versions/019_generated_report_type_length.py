"""Increase generated_reports.report_type length."""

from alembic import op
import sqlalchemy as sa


revision = "019_generated_report_type_length"
down_revision = "018_threat_intel_feeds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'generated_reports'
              AND column_name = 'report_type'
              AND character_maximum_length = 20
          ) THEN
            ALTER TABLE generated_reports
              ALTER COLUMN report_type TYPE VARCHAR(64);
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.alter_column(
        "generated_reports",
        "report_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=False,
    )
