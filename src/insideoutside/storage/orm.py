import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid_str() -> str:
    return str(uuid.uuid4())


class InsiderTransactionORM(Base):
    __tablename__ = "insider_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    company_name: Mapped[str] = mapped_column(String)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    cik: Mapped[str] = mapped_column(String)
    filer_name: Mapped[str] = mapped_column(String)
    filer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    filer_role: Mapped[str] = mapped_column(String)
    transaction_type: Mapped[str] = mapped_column(String)
    transaction_code: Mapped[str] = mapped_column(String)
    is_discretionary: Mapped[bool] = mapped_column(Boolean)
    share_count: Mapped[str] = mapped_column(Numeric)
    price_per_share: Mapped[str | None] = mapped_column(Numeric, nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date)
    filing_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String)
    source_ref: Mapped[str] = mapped_column(String, unique=True)
    source_url: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("insider_transactions.id"), nullable=True
    )


class BuybackEventORM(Base):
    __tablename__ = "buyback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    company_name: Mapped[str] = mapped_column(String)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    cik: Mapped[str] = mapped_column(String)
    disclosure_type: Mapped[str] = mapped_column(String)
    amount: Mapped[str] = mapped_column(Numeric)
    disclosure_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String)
    source_ref: Mapped[str] = mapped_column(String, unique=True)
    source_url: Mapped[str] = mapped_column(String)
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("buyback_events.id"), nullable=True
    )


class ClusterBuyEventORM(Base):
    __tablename__ = "cluster_buy_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    company_name: Mapped[str] = mapped_column(String)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    cik: Mapped[str] = mapped_column(String)
    window_start: Mapped[date] = mapped_column(Date)
    window_end: Mapped[date] = mapped_column(Date)
    distinct_filer_count: Mapped[int] = mapped_column(Integer)
    total_value: Mapped[str] = mapped_column(Numeric)
    contributing_transaction_ids: Mapped[list] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SignalORM(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    signal_type: Mapped[str] = mapped_column(String)
    insider_transaction_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("insider_transactions.id"), nullable=True
    )
    buyback_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("buyback_events.id"), nullable=True
    )
    cluster_buy_event_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("cluster_buy_events.id"), nullable=True
    )
    is_notable: Mapped[bool] = mapped_column(Boolean)
    is_discretionary: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluated_threshold_snapshot: Mapped[dict] = mapped_column(JSON)
    notification_status: Mapped[str] = mapped_column(String, default="not_applicable")
    notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ThresholdConfigurationORM(Base):
    __tablename__ = "threshold_configuration"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid_str)
    min_insider_buy_value: Mapped[str] = mapped_column(Numeric)
    min_notable_role_buy_value: Mapped[str] = mapped_column(Numeric, server_default="100000")
    notable_filer_roles: Mapped[list] = mapped_column(JSON)
    min_buyback_amount: Mapped[str] = mapped_column(Numeric)
    cluster_window_days: Mapped[int] = mapped_column(Integer, server_default="14")
    min_cluster_filer_count: Mapped[int] = mapped_column(Integer, server_default="2")
