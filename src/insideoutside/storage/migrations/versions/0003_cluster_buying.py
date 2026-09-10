"""cluster buying detection

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "insider_transactions",
        sa.Column("filer_id", sa.String, nullable=True),
    )

    op.create_table(
        "cluster_buy_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String, nullable=False),
        sa.Column("ticker", sa.String, nullable=True),
        sa.Column("cik", sa.String, nullable=False),
        sa.Column("window_start", sa.Date, nullable=False),
        sa.Column("window_end", sa.Date, nullable=False),
        sa.Column("distinct_filer_count", sa.Integer, nullable=False),
        sa.Column("total_value", sa.Numeric, nullable=False),
        sa.Column("contributing_transaction_ids", sa.JSON, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    # SQLite can't ALTER a table to add a column with a new FK constraint
    # directly; batch mode does it via copy-and-move instead.
    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(
            sa.Column(
                "cluster_buy_event_id",
                sa.String(36),
                sa.ForeignKey("cluster_buy_events.id", name="fk_signals_cluster_buy_event_id"),
                nullable=True,
            )
        )

    op.add_column(
        "threshold_configuration",
        sa.Column("cluster_window_days", sa.Integer, nullable=False, server_default="14"),
    )
    op.add_column(
        "threshold_configuration",
        sa.Column("min_cluster_filer_count", sa.Integer, nullable=False, server_default="2"),
    )


def downgrade() -> None:
    op.drop_column("threshold_configuration", "min_cluster_filer_count")
    op.drop_column("threshold_configuration", "cluster_window_days")
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_column("cluster_buy_event_id")
    op.drop_table("cluster_buy_events")
    op.drop_column("insider_transactions", "filer_id")
