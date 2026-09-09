from datetime import date, datetime
from decimal import Decimal

import pytest

from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.ingestion.dedup import ingest_insider_transaction
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.migrations import apply_migrations
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from openinsider_tracker.storage.repositories.signal_repo import SignalRepository


@pytest.fixture
def repos(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    database = Database(str(db_path))
    yield InsiderTransactionRepository(database), SignalRepository(database)
    database.dispose()


def _sec_txn(**overrides):
    kwargs = dict(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        filer_name="Jane Doe",
        filer_role="director",
        transaction_type="buy",
        transaction_code="P",
        is_discretionary=True,
        share_count=Decimal("1000"),
        price_per_share=Decimal("150.25"),
        transaction_date=date(2026, 8, 1),
        filing_date=date(2026, 8, 3),
        source="sec_edgar",
        source_ref="0000912057-26-012345-0",
        source_url="https://www.sec.gov/example",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    kwargs.update(overrides)
    return InsiderTransaction(**kwargs)


def _openinsider_candidate(**overrides):
    kwargs = dict(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="",
        filer_name="Jane Doe",
        filer_role="director",
        transaction_type="buy",
        transaction_code="P",
        is_discretionary=True,
        share_count=Decimal("1000"),
        price_per_share=Decimal("150.25"),
        transaction_date=date(2026, 8, 1),
        filing_date=date(2026, 8, 3),
        source="openinsider",
        source_ref="openinsider:TM:2026-08-01:JaneDoe",
        source_url="https://openinsider.com/example",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    kwargs.update(overrides)
    return InsiderTransaction(**kwargs)


def test_openinsider_record_matching_existing_sec_record_does_not_duplicate(repos):
    txn_repo, signal_repo = repos
    sec_record = ingest_insider_transaction(_sec_txn(), txn_repo=txn_repo, signal_repo=signal_repo)

    result = ingest_insider_transaction(
        _openinsider_candidate(), txn_repo=txn_repo, signal_repo=signal_repo
    )

    assert result.id == sec_record.id
    assert len(txn_repo.list()) == 1


def test_openinsider_record_with_no_sec_match_is_kept(repos):
    txn_repo, signal_repo = repos
    result = ingest_insider_transaction(
        _openinsider_candidate(ticker="ZZZ", company_name="Zzz Corp"),
        txn_repo=txn_repo,
        signal_repo=signal_repo,
    )
    assert result.source == "openinsider"
    assert len(txn_repo.list()) == 1
