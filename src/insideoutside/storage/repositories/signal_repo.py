from __future__ import annotations

from datetime import date
from uuid import UUID

from insideoutside.domain.signal import Signal
from insideoutside.storage.db import Database
from insideoutside.storage.orm import (
    BuybackEventORM,
    ClusterBuyEventORM,
    InsiderTransactionORM,
    SignalORM,
)


def _to_domain(row: SignalORM) -> Signal:
    # ORM column names match the domain model's field names 1:1, so pydantic's
    # from_attributes mode can build it directly (the signal_type linkage
    # validator still runs -- a stored row always satisfies it).
    return Signal.model_validate(row, from_attributes=True)


def _apply_domain(row: SignalORM, signal: Signal) -> None:
    row.signal_type = signal.signal_type
    row.insider_transaction_id = (
        str(signal.insider_transaction_id) if signal.insider_transaction_id else None
    )
    row.buyback_event_id = str(signal.buyback_event_id) if signal.buyback_event_id else None
    row.cluster_buy_event_id = (
        str(signal.cluster_buy_event_id) if signal.cluster_buy_event_id else None
    )
    row.is_notable = signal.is_notable
    row.is_discretionary = signal.is_discretionary
    row.is_superseded = signal.is_superseded
    row.evaluated_threshold_snapshot = signal.evaluated_threshold_snapshot
    row.notification_status = signal.notification_status
    row.notified_at = signal.notified_at
    row.created_at = signal.created_at


class SignalRepository:
    def __init__(self, db: Database):
        self._db = db

    def get(self, id: UUID | str) -> Signal | None:
        with self._db.session() as session:
            row = session.get(SignalORM, str(id))
            return _to_domain(row) if row else None

    def get_for_insider_transaction(self, insider_transaction_id: UUID | str) -> Signal | None:
        with self._db.session() as session:
            row = (
                session.query(SignalORM)
                .filter_by(insider_transaction_id=str(insider_transaction_id))
                .one_or_none()
            )
            return _to_domain(row) if row else None

    def get_for_buyback_event(self, buyback_event_id: UUID | str) -> Signal | None:
        with self._db.session() as session:
            row = (
                session.query(SignalORM)
                .filter_by(buyback_event_id=str(buyback_event_id))
                .one_or_none()
            )
            return _to_domain(row) if row else None

    def get_for_cluster_buy_event(self, cluster_buy_event_id: UUID | str) -> Signal | None:
        with self._db.session() as session:
            row = (
                session.query(SignalORM)
                .filter_by(cluster_buy_event_id=str(cluster_buy_event_id))
                .one_or_none()
            )
            return _to_domain(row) if row else None

    def save(self, signal: Signal) -> Signal:
        with self._db.session() as session:
            row = session.get(SignalORM, str(signal.id))
            if row is None:
                row = SignalORM(id=str(signal.id))
                session.add(row)
            _apply_domain(row, signal)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def list(
        self,
        *,
        notable_only: bool = True,
        signal_type: str | None = None,
        since: date | None = None,
        limit: int = 100,
        offset: int = 0,
        include_superseded: bool = False,
    ) -> tuple[list[Signal], int]:
        with self._db.session() as session:
            query = session.query(SignalORM)
            if not include_superseded:
                query = query.filter(SignalORM.is_superseded.is_(False))
            if notable_only:
                query = query.filter(SignalORM.is_notable.is_(True))
            if signal_type:
                query = query.filter(SignalORM.signal_type == signal_type)
            if since:
                query = query.outerjoin(
                    InsiderTransactionORM,
                    SignalORM.insider_transaction_id == InsiderTransactionORM.id,
                ).outerjoin(
                    BuybackEventORM, SignalORM.buyback_event_id == BuybackEventORM.id
                ).outerjoin(
                    ClusterBuyEventORM, SignalORM.cluster_buy_event_id == ClusterBuyEventORM.id
                ).filter(
                    (InsiderTransactionORM.transaction_date >= since)
                    | (BuybackEventORM.disclosure_date >= since)
                    | (ClusterBuyEventORM.window_end >= since)
                )
            total = query.count()
            rows = (
                query.order_by(SignalORM.created_at.desc()).offset(offset).limit(limit).all()
            )
            return [_to_domain(row) for row in rows], total

    def list_pending_notifications(self) -> list[Signal]:
        with self._db.session() as session:
            rows = session.query(SignalORM).filter_by(notification_status="pending").all()
            return [_to_domain(row) for row in rows]
