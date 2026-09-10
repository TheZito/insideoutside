"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "insider_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String, nullable=False),
        sa.Column("ticker", sa.String, nullable=True),
        sa.Column("cik", sa.String, nullable=False),
        sa.Column("filer_name", sa.String, nullable=False),
        sa.Column("filer_role", sa.String, nullable=False),
        sa.Column("transaction_type", sa.String, nullable=False),
        sa.Column("transaction_code", sa.String, nullable=False),
        sa.Column("is_discretionary", sa.Boolean, nullable=False),
        sa.Column("share_count", sa.Numeric, nullable=False),
        sa.Column("price_per_share", sa.Numeric, nullable=True),
        sa.Column("transaction_date", sa.Date, nullable=False),
        sa.Column("filing_date", sa.Date, nullable=False),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("source_ref", sa.String, nullable=False, unique=True),
        sa.Column("source_url", sa.String, nullable=False),
        sa.Column("fetched_at", sa.DateTime, nullable=False),
        sa.Column(
            "superseded_by_id",
            sa.String(36),
            sa.ForeignKey("insider_transactions.id"),
            nullable=True,
        ),
    )

    op.create_table(
        "buyback_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_name", sa.String, nullable=False),
        sa.Column("ticker", sa.String, nullable=True),
        sa.Column("cik", sa.String, nullable=False),
        sa.Column("disclosure_type", sa.String, nullable=False),
        sa.Column("amount", sa.Numeric, nullable=False),
        sa.Column("disclosure_date", sa.Date, nullable=False),
        sa.Column("source", sa.String, nullable=False),
        sa.Column("source_ref", sa.String, nullable=False, unique=True),
        sa.Column("source_url", sa.String, nullable=False),
        sa.Column("fetched_at", sa.DateTime, nullable=False),
        sa.Column(
            "superseded_by_id", sa.String(36), sa.ForeignKey("buyback_events.id"), nullable=True
        ),
    )

    op.create_table(
        "signals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("signal_type", sa.String, nullable=False),
        sa.Column(
            "insider_transaction_id",
            sa.String(36),
            sa.ForeignKey("insider_transactions.id"),
            nullable=True,
        ),
        sa.Column(
            "buyback_event_id", sa.String(36), sa.ForeignKey("buyback_events.id"), nullable=True
        ),
        sa.Column("is_notable", sa.Boolean, nullable=False),
        sa.Column("is_discretionary", sa.Boolean, nullable=True),
        sa.Column("is_superseded", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("evaluated_threshold_snapshot", sa.JSON, nullable=False),
        sa.Column(
            "notification_status",
            sa.String,
            nullable=False,
            server_default="not_applicable",
        ),
        sa.Column("notified_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "threshold_configuration",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("min_insider_buy_value", sa.Numeric, nullable=False),
        sa.Column("notable_filer_roles", sa.JSON, nullable=False),
        sa.Column("min_buyback_amount", sa.Numeric, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("threshold_configuration")
    op.drop_table("signals")
    op.drop_table("buyback_events")
    op.drop_table("insider_transactions")
