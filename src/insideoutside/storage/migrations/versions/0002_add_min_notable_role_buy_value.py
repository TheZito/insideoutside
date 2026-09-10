"""add min_notable_role_buy_value

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "threshold_configuration",
        sa.Column(
            "min_notable_role_buy_value",
            sa.Numeric,
            nullable=False,
            server_default="100000",
        ),
    )


def downgrade() -> None:
    op.drop_column("threshold_configuration", "min_notable_role_buy_value")
