"""
alert lifecycle and columns

Revision ID: 20260809_0005
Revises: 20260810_0004
Create Date: 2026-08-09 00:00:00.000000
"""


from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260809_0005"
down_revision = "20260810_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # Determine which lowercase enum labels we need to ensure exist before using them
    target_labels = {"active", "watching", "confirmed", "resolved", "dismissed"}

    # Query existing enum labels for alert_status
    existing_labels = set()
    try:
        rows = bind.execute(
            sa.text(
                "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = :t"
            ),
            {"t": "alert_status"},
        ).fetchall()
        existing_labels = {r[0] for r in rows}
    except Exception:
        # If we cannot query pg_enum (type may not exist), fall back to empty set to attempt adds.
        existing_labels = set()

    # Add only the missing labels, using autocommit so Postgres commits the new enum value immediately
    missing = target_labels - existing_labels
    for label in sorted(missing):
        # Use autocommit_block so ALTER TYPE runs outside the migration transaction
        with op.get_context().autocommit_block():
            op.execute(sa.text(f"ALTER TYPE alert_status ADD VALUE '{label}'"))

    # Re-query to confirm needed destination labels exist before performing updates
    try:
        rows = bind.execute(
            sa.text(
                "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = :t"
            ),
            {"t": "alert_status"},
        ).fetchall()
        existing_labels = {r[0] for r in rows}
    except Exception:
        existing_labels = set()

    # Validate that destination enum values exist
    required_for_updates = {"active", "watching", "resolved", "dismissed"}
    if not required_for_updates.issubset(existing_labels):
        missing_after = required_for_updates - existing_labels
        raise RuntimeError(f"Missing enum labels required for migration UPDATEs: {missing_after}")

    # Map legacy values to new lowercase values where applicable
    op.execute("UPDATE alerts SET status = 'active' WHERE status = 'NEW'")
    op.execute("UPDATE alerts SET status = 'watching' WHERE status = 'ACKNOWLEDGED'")
    op.execute("UPDATE alerts SET status = 'resolved' WHERE status = 'RESOLVED'")
    op.execute("UPDATE alerts SET status = 'dismissed' WHERE status = 'DISMISSED'")

    # Add lifecycle columns
    op.add_column(
        "alerts",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("dismissed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add foreign key constraints for new user references
    op.create_foreign_key(
        op.f("fk_alerts_confirmed_by_users"),
        "alerts",
        "users",
        ["confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_alerts_dismissed_by_users"),
        "alerts",
        "users",
        ["dismissed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_alerts_resolved_by_users"),
        "alerts",
        "users",
        ["resolved_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add indexes for newly added FK columns
    op.create_index(op.f("ix_alerts_confirmed_by"), "alerts", ["confirmed_by"], unique=False)
    op.create_index(op.f("ix_alerts_dismissed_by"), "alerts", ["dismissed_by"], unique=False)
    op.create_index(op.f("ix_alerts_resolved_by"), "alerts", ["resolved_by"], unique=False)


def downgrade() -> None:
    # Remove columns
    op.drop_index(op.f("ix_alerts_resolved_by"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_dismissed_by"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_confirmed_by"), table_name="alerts")

    op.drop_constraint(op.f("fk_alerts_resolved_by_users"), "alerts", type_="foreignkey")
    op.drop_constraint(op.f("fk_alerts_dismissed_by_users"), "alerts", type_="foreignkey")
    op.drop_constraint(op.f("fk_alerts_confirmed_by_users"), "alerts", type_="foreignkey")

    op.drop_column("alerts", "resolved_by")
    op.drop_column("alerts", "dismissed_reason")
    op.drop_column("alerts", "dismissed_by")
    op.drop_column("alerts", "dismissed_at")
    op.drop_column("alerts", "confirmed_by")
    op.drop_column("alerts", "confirmed_at")

    # Note: enum values cannot be cleanly removed in Postgres; leave added values in type.
