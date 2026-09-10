from __future__ import annotations

from uuid import UUID

from insideoutside.domain.cluster_buy_event import ClusterBuyEvent
from insideoutside.storage.db import Database
from insideoutside.storage.orm import ClusterBuyEventORM


def _to_domain(row: ClusterBuyEventORM) -> ClusterBuyEvent:
    # ORM column names match the domain model's field names 1:1, so pydantic's
    # from_attributes mode can build it directly -- including coercing the
    # stored list[str] of transaction ids into list[UUID], the same coercion
    # normal keyword construction already relied on.
    return ClusterBuyEvent.model_validate(row, from_attributes=True)


def _apply_domain(row: ClusterBuyEventORM, event: ClusterBuyEvent) -> None:
    row.company_name = event.company_name
    row.ticker = event.ticker
    row.cik = event.cik
    row.window_start = event.window_start
    row.window_end = event.window_end
    row.distinct_filer_count = event.distinct_filer_count
    row.total_value = event.total_value
    row.contributing_transaction_ids = [str(t) for t in event.contributing_transaction_ids]
    row.updated_at = event.updated_at
    row.created_at = event.created_at


class ClusterBuyEventRepository:
    def __init__(self, db: Database):
        self._db = db

    def get(self, id: UUID | str) -> ClusterBuyEvent | None:
        with self._db.session() as session:
            row = session.get(ClusterBuyEventORM, str(id))
            return _to_domain(row) if row else None

    def list_by_company(self, *, cik: str) -> list[ClusterBuyEvent]:
        with self._db.session() as session:
            rows = session.query(ClusterBuyEventORM).filter_by(cik=cik).all()
            return [_to_domain(row) for row in rows]

    def create(self, event: ClusterBuyEvent) -> ClusterBuyEvent:
        with self._db.session() as session:
            row = ClusterBuyEventORM(id=str(event.id))
            _apply_domain(row, event)
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def upsert_by_overlapping_transactions(self, candidate: ClusterBuyEvent) -> ClusterBuyEvent:
        """Match `candidate` against existing rows for its company by shared
        contributing_transaction_ids (NOT by company alone -- a company can have
        multiple, unrelated clusters over time). A match is replaced in place;
        no match creates a new row. See research.md §5."""
        candidate_ids = {str(t) for t in candidate.contributing_transaction_ids}
        with self._db.session() as session:
            rows = session.query(ClusterBuyEventORM).filter_by(cik=candidate.cik).all()
            match = next(
                (row for row in rows if candidate_ids & set(row.contributing_transaction_ids)),
                None,
            )
            if match is None:
                row = ClusterBuyEventORM(id=str(candidate.id))
                _apply_domain(row, candidate)
                session.add(row)
            else:
                row = match
                _apply_domain(row, candidate)
            session.commit()
            session.refresh(row)
            return _to_domain(row)
