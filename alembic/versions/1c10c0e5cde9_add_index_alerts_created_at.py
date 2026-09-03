"""add_index_alerts_created_at

Revision ID: 1c10c0e5cde9
Revises: 20260809_0005
Create Date: 2026-08-16 06:30:21.743784
"""

from typing import Sequence, Union

from alembic import op

revision: str = "1c10c0e5cde9"
down_revision: Union[str, Sequence[str], None] = "20260809_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_created_at", table_name="alerts")
