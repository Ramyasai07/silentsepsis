"""add patient ward management fields

Revision ID: 20260807_0002
Revises: 6893ec305235
Create Date: 2026-08-07 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "20260807_0002"
down_revision: Union[str, Sequence[str], None] = "6893ec305235"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("wards", sa.Column("capacity", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE wards SET capacity = 0 WHERE capacity IS NULL"))
    op.alter_column("wards", "capacity", nullable=False)

    op.add_column(
        "patients", sa.Column("bed_number", sa.String(length=40), nullable=True)
    )
    op.execute(sa.text("""
            UPDATE patients
            SET bed_number = 'UNASSIGNED-' || substr(id::text, 1, 8)
            WHERE bed_number IS NULL
            """))
    op.alter_column("patients", "bed_number", nullable=False)
    op.create_index(
        op.f("ix_patients_ward_id_bed_number"),
        "patients",
        ["ward_id", "bed_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_patients_ward_id_bed_number"), table_name="patients")
    op.drop_column("patients", "bed_number")
    op.drop_column("wards", "capacity")
