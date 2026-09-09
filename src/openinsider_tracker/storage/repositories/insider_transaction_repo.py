from __future__ import annotations

from uuid import UUID

from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.orm import InsiderTransactionORM


def _to_domain(row: InsiderTransactionORM) -> InsiderTransaction:
    # ORM column names match the domain model's field names 1:1, so pydantic's
    # from_attributes mode can build it directly (and coerces str->UUID,
    # str->Decimal, etc. the same way normal keyword construction would).
    return InsiderTransaction.model_validate(row, from_attributes=True)


def _apply_domain(row: InsiderTransactionORM, txn: InsiderTransaction) -> None:
    row.company_name = txn.company_name
    row.ticker = txn.ticker
    row.cik = txn.cik
    row.filer_name = txn.filer_name
    row.filer_role = txn.filer_role
    row.transaction_type = txn.transaction_type
    row.transaction_code = txn.transaction_code
    row.is_discretionary = txn.is_discretionary
    row.share_count = txn.share_count
    row.price_per_share = txn.price_per_share
    row.transaction_date = txn.transaction_date
    row.filing_date = txn.filing_date
    row.source = txn.source
    row.source_ref = txn.source_ref
    row.source_url = txn.source_url
    row.fetched_at = txn.fetched_at
    row.superseded_by_id = str(txn.superseded_by_id) if txn.superseded_by_id else None


class InsiderTransactionRepository:
    def __init__(self, db: Database):
        self._db = db

    def get(self, id: UUID | str) -> InsiderTransaction | None:
        with self._db.session() as session:
            row = session.get(InsiderTransactionORM, str(id))
            return _to_domain(row) if row else None

    def get_by_source_ref(self, source_ref: str) -> InsiderTransaction | None:
        with self._db.session() as session:
            row = (
                session.query(InsiderTransactionORM)
                .filter_by(source_ref=source_ref)
                .one_or_none()
            )
            return _to_domain(row) if row else None

    def list(self) -> list[InsiderTransaction]:
        with self._db.session() as session:
            rows = session.query(InsiderTransactionORM).order_by(
                InsiderTransactionORM.transaction_date.desc()
            )
            return [_to_domain(row) for row in rows]

    def upsert_by_source_ref(self, txn: InsiderTransaction) -> InsiderTransaction:
        with self._db.session() as session:
            existing = (
                session.query(InsiderTransactionORM)
                .filter_by(source_ref=txn.source_ref)
                .one_or_none()
            )
            if existing:
                _apply_domain(existing, txn)
                row = existing
            else:
                row = InsiderTransactionORM(id=str(txn.id))
                _apply_domain(row, txn)
                session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def find_by_natural_key(
        self, *, cik: str, filer_name: str, transaction_date
    ) -> list[InsiderTransaction]:
        """Candidates for amendment detection: same filer/company/date, any source_ref."""
        with self._db.session() as session:
            rows = (
                session.query(InsiderTransactionORM)
                .filter_by(cik=cik, filer_name=filer_name, transaction_date=transaction_date)
                .all()
            )
            return [_to_domain(row) for row in rows]

    def find_by_fuzzy_match(
        self, *, ticker: str | None, filer_name: str, transaction_date, share_count
    ) -> InsiderTransaction | None:
        """Cross-source match for an OpenInsider-style candidate against an
        existing SEC-sourced record (research.md §6)."""
        with self._db.session() as session:
            row = (
                session.query(InsiderTransactionORM)
                .filter_by(
                    ticker=ticker,
                    filer_name=filer_name,
                    transaction_date=transaction_date,
                    share_count=share_count,
                    source="sec_edgar",
                )
                .first()
            )
            return _to_domain(row) if row else None

    def mark_superseded(self, id: UUID | str, superseded_by_id: UUID | str) -> None:
        with self._db.session() as session:
            row = session.get(InsiderTransactionORM, str(id))
            if row is None:
                return
            row.superseded_by_id = str(superseded_by_id)
            session.commit()
