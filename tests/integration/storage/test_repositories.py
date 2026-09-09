from datetime import date
from decimal import Decimal

import pytest

from openinsider_tracker.domain.buyback_event import BuybackEvent
from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.migrations import apply_migrations
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from openinsider_tracker.storage.repositories.threshold_repo import (
    ThresholdConfigurationRepository,
)


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    database = Database(str(db_path))
    yield database
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
        source_ref="0000912057-26-012345",
        source_url="https://www.sec.gov/Archives/edgar/data/example",
        fetched_at="2026-08-03T12:00:00Z",
    )
    kwargs.update(overrides)
    return InsiderTransaction(**kwargs)


def test_insider_transaction_create_get_list_roundtrip(db):
    repo = InsiderTransactionRepository(db)
    created = repo.upsert_by_source_ref(_txn())
    fetched = repo.get(created.id)
    assert fetched.company_name == "Toyota Motor Corp"
    assert fetched.source_ref == "0000912057-26-012345"
    assert repo.list() == [fetched]


def test_insider_transaction_upsert_by_source_ref_is_idempotent(db):
    repo = InsiderTransactionRepository(db)
    first = repo.upsert_by_source_ref(_txn())
    second = repo.upsert_by_source_ref(_txn(filer_name="Jane Doe (amended)"))
    assert first.id == second.id
    assert repo.get(first.id).filer_name == "Jane Doe (amended)"
    assert len(repo.list()) == 1


def test_buyback_event_create_get_list_roundtrip(db):
    repo = BuybackEventRepository(db)
    event = BuybackEvent(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        disclosure_type="executed",
        amount=Decimal("100000000"),
        disclosure_date=date(2026, 8, 1),
        source="sec_edgar",
        source_ref="0000912057-26-012345-item703",
        source_url="https://www.sec.gov/Archives/edgar/data/example",
        fetched_at="2026-08-03T12:00:00Z",
    )
    created = repo.upsert_by_source_ref(event)
    fetched = repo.get(created.id)
    assert fetched.amount == Decimal("100000000")
    assert repo.list() == [fetched]


def test_threshold_configuration_singleton_get_and_set(db):
    repo = ThresholdConfigurationRepository(db)
    default = repo.get()
    assert default.min_insider_buy_value == Decimal("1000000")

    repo.set(ThresholdConfiguration(min_insider_buy_value=Decimal("500000")))
    updated = repo.get()
    assert updated.min_insider_buy_value == Decimal("500000")
