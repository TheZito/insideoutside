from datetime import date, datetime
from decimal import Decimal

import pytest

from insideoutside.domain.insider_transaction import InsiderTransaction
from insideoutside.domain.signal import Signal
from insideoutside.ingestion.dedup import ingest_insider_transaction
from insideoutside.storage.db import Database
from insideoutside.storage.migrations import apply_migrations
from insideoutside.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from insideoutside.storage.repositories.signal_repo import SignalRepository


@pytest.fixture
def repos(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    database = Database(str(db_path))
    yield InsiderTransactionRepository(database), SignalRepository(database)
    database.dispose()


def _txn(**overrides):
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


def test_same_accession_number_ingested_twice_yields_one_record(repos):
    txn_repo, signal_repo = repos
    first = ingest_insider_transaction(_txn(), txn_repo=txn_repo, signal_repo=signal_repo)
    second = ingest_insider_transaction(_txn(), txn_repo=txn_repo, signal_repo=signal_repo)
    assert first.id == second.id
    assert len(txn_repo.list()) == 1


def test_amended_filing_supersedes_prior_and_marks_its_signal_superseded(repos):
    txn_repo, signal_repo = repos
    original = ingest_insider_transaction(_txn(), txn_repo=txn_repo, signal_repo=signal_repo)

    signal = Signal(
        signal_type="insider_transaction",
        insider_transaction_id=original.id,
        is_notable=True,
        is_discretionary=True,
        evaluated_threshold_snapshot={},
        notification_status="pending",
    )
    signal_repo.save(signal)

    amended = ingest_insider_transaction(
        _txn(source_ref="0000912057-26-012399-0", share_count=Decimal("1200")),
        txn_repo=txn_repo,
        signal_repo=signal_repo,
    )

    assert amended.id != original.id
    prior = txn_repo.get(original.id)
    assert prior.superseded_by_id == amended.id

    prior_signal = signal_repo.get_for_insider_transaction(original.id)
    assert prior_signal.is_superseded is True
