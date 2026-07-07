"""Alembic 015 — immutable audit log hash chain and mutation guards."""

from alembic import op
import sqlalchemy as sa

revision = "015_immutable_audit"
down_revision = "014_user_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS chain_seq BIGINT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS prev_hash VARCHAR(64)")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entry_hash VARCHAR(64)")

    op.execute(
        """
        WITH ordered AS (
          SELECT id, row_number() OVER (ORDER BY timestamp ASC, id ASC) AS seq
          FROM audit_logs
        )
        UPDATE audit_logs AS a
        SET chain_seq = o.seq
        FROM ordered AS o
        WHERE a.id = o.id AND a.chain_seq IS NULL
        """
    )

    op.execute("CREATE SEQUENCE IF NOT EXISTS audit_logs_chain_seq_seq")
    op.execute(
        """
        SELECT setval(
          'audit_logs_chain_seq_seq',
          GREATEST(COALESCE((SELECT MAX(chain_seq) FROM audit_logs), 0), 1),
          (SELECT COUNT(*) > 0 FROM audit_logs)
        )
        """
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT chain_seq, id, user_id, action, resource_type, resource_id,
                   ip_address::text AS ip_address, details, timestamp
            FROM audit_logs
            WHERE entry_hash IS NULL
            ORDER BY chain_seq ASC
            """
        )
    ).fetchall()

    if rows:
        from uuid import UUID

        from app.services.audit_chain import GENESIS_HASH, compute_entry_hash

        prev_hash = GENESIS_HASH
        for row in rows:
            entry_hash = compute_entry_hash(
                chain_seq=row.chain_seq,
                entry_id=UUID(str(row.id)),
                user_id=UUID(str(row.user_id)) if row.user_id else None,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=UUID(str(row.resource_id)) if row.resource_id else None,
                ip_address=row.ip_address,
                details=row.details,
                timestamp_iso=row.timestamp.isoformat(),
                prev_hash=prev_hash,
            )
            bind.execute(
                sa.text(
                    "UPDATE audit_logs SET prev_hash = :prev_hash, entry_hash = :entry_hash WHERE chain_seq = :chain_seq"
                ),
                {"prev_hash": prev_hash, "entry_hash": entry_hash, "chain_seq": row.chain_seq},
            )
            prev_hash = entry_hash

    op.execute("ALTER TABLE audit_logs ALTER COLUMN chain_seq SET DEFAULT nextval('audit_logs_chain_seq_seq')")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN chain_seq SET NOT NULL")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN prev_hash SET NOT NULL")
    op.execute("ALTER TABLE audit_logs ALTER COLUMN entry_hash SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_audit_logs_chain_seq ON audit_logs (chain_seq)")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
        RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'UPDATE' THEN
            RAISE EXCEPTION 'audit_logs are immutable: updates are not allowed';
          ELSIF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'audit_logs are immutable: deletes are not allowed';
          END IF;
          RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs")
    op.execute(
        """
        CREATE TRIGGER audit_logs_immutable
        BEFORE UPDATE OR DELETE ON audit_logs
        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable ON audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_log_mutation()")
    op.execute("DROP INDEX IF EXISTS ix_audit_logs_chain_seq")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS entry_hash")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS prev_hash")
    op.execute("ALTER TABLE audit_logs DROP COLUMN IF EXISTS chain_seq")
    op.execute("DROP SEQUENCE IF EXISTS audit_logs_chain_seq_seq")
