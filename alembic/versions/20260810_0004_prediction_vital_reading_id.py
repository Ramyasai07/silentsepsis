"""add vital_reading_id to predictions

Revision ID: 20260810_0004
Revises: 20260808_0003
Create Date: 2026-08-10 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260810_0004"
down_revision: Union[str, Sequence[str], None] = "20260808_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "predictions",
        sa.Column(
            "vital_reading_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vital_readings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_predictions_vital_reading_id"), "predictions", ["vital_reading_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_predictions_vital_reading_id"), table_name="predictions")
    op.drop_column("predictions", "vital_reading_id")
