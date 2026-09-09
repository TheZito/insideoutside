from __future__ import annotations

from uuid import UUID

from openinsider_tracker.domain.buyback_event import BuybackEvent
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.orm import BuybackEventORM


def _to_domain(row: BuybackEventORM) -> BuybackEvent:
    # ORM column names match the domain model's field names 1:1, so pydantic's
    # from_attributes mode can build it directly.
    return BuybackEvent.model_validate(row, from_attributes=True)


def _apply_domain(row: BuybackEventORM, event: BuybackEvent) -> None:
    row.company_name = event.company_name
    row.ticker = event.ticker
    row.cik = event.cik
    row.disclosure_type = event.disclosure_type
    row.amount = event.amount
    row.disclosure_date = event.disclosure_date
    row.source = event.source
    row.source_ref = event.source_ref
    row.source_url = event.source_url
    row.fetched_at = event.fetched_at
    row.superseded_by_id = str(event.superseded_by_id) if event.superseded_by_id else None


class BuybackEventRepository:
    def __init__(self, db: Database):
        self._db = db

    def get(self, id: UUID | str) -> BuybackEvent | None:
        with self._db.session() as session:
            row = session.get(BuybackEventORM, str(id))
            return _to_domain(row) if row else None

    def get_by_source_ref(self, source_ref: str) -> BuybackEvent | None:
        with self._db.session() as session:
            row = session.query(BuybackEventORM).filter_by(source_ref=source_ref).one_or_none()
            return _to_domain(row) if row else None

    def list(self) -> list[BuybackEvent]:
        with self._db.session() as session:
            rows = session.query(BuybackEventORM).order_by(BuybackEventORM.disclosure_date.desc())
            return [_to_domain(row) for row in rows]

    def upsert_by_source_ref(self, event: BuybackEvent) -> BuybackEvent:
        with self._db.session() as session:
            existing = (
                session.query(BuybackEventORM).filter_by(source_ref=event.source_ref).one_or_none()
            )
            if existing:
                _apply_domain(existing, event)
                row = existing
            else:
                row = BuybackEventORM(id=str(event.id))
                _apply_domain(row, event)
                session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def find_by_natural_key(
        self, *, cik: str, disclosure_date, disclosure_type: str
    ) -> list[BuybackEvent]:
        with self._db.session() as session:
            rows = (
                session.query(BuybackEventORM)
                .filter_by(cik=cik, disclosure_date=disclosure_date, disclosure_type=disclosure_type)
                .all()
            )
            return [_to_domain(row) for row in rows]

    def mark_superseded(self, id: UUID | str, superseded_by_id: UUID | str) -> None:
        with self._db.session() as session:
            row = session.get(BuybackEventORM, str(id))
            if row is None:
                return
            row.superseded_by_id = str(superseded_by_id)
            session.commit()
