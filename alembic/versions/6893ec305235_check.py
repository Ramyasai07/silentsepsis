"""add auth staff ids and seed roles

Revision ID: 6893ec305235
Revises: 20260805_0001
Create Date: 2026-08-07 05:50:18.434056
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "6893ec305235"
down_revision: Union[str, Sequence[str], None] = "20260805_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("staff_id", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_users_staff_id"), "users", ["staff_id"], unique=True)

    op.execute(sa.text("""
            INSERT INTO roles (id, name, description)
            VALUES
                (
                    gen_random_uuid(),
                    'Admin',
                    'Hospital administrator with staff provisioning access.'
                ),
                (
                    gen_random_uuid(),
                    'Physician',
                    'Physician user with clinical access.'
                ),
                (
                    gen_random_uuid(),
                    'Nurse',
                    'Nurse user with clinical access.'
                )
            ON CONFLICT (name) DO NOTHING
            """))

    op.alter_column("users", "staff_id", nullable=False)


def downgrade() -> None:
    roles_table = sa.table("roles", sa.column("name", sa.String))
    op.execute(
        roles_table.delete().where(
            roles_table.c.name.in_(("Admin", "Physician", "Nurse"))
        )
    )
    op.drop_index(op.f("ix_users_staff_id"), table_name="users")
    op.drop_column("users", "staff_id")
