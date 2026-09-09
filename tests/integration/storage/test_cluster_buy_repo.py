from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openinsider_tracker.domain.cluster_buy_event import ClusterBuyEvent
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.migrations import apply_migrations
from openinsider_tracker.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository


@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    database = Database(str(db_path))
    yield database
    database.dispose()


def _event(**overrides):
    kwargs = dict(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        window_start=date(2026, 8, 1),
        window_end=date(2026, 8, 4),
        distinct_filer_count=2,
        total_value=Decimal("110000"),
        contributing_transaction_ids=[uuid4(), uuid4()],
    )
    kwargs.update(overrides)
    return ClusterBuyEvent(**kwargs)


def test_create_get_list_roundtrip(db):
    repo = ClusterBuyEventRepository(db)
    created = repo.create(_event())
    fetched = repo.get(created.id)
    assert fetched.company_name == "Toyota Motor Corp"
    assert fetched.distinct_filer_count == 2
    assert repo.list_by_company(cik="0001094517") == [fetched]


def test_upsert_replaces_row_sharing_a_contributing_transaction(db):
    repo = ClusterBuyEventRepository(db)
    txn_a, txn_b, txn_c = uuid4(), uuid4(), uuid4()

    original = repo.create(
        _event(contributing_transaction_ids=[txn_a, txn_b], distinct_filer_count=2)
    )

    grown = _event(
        contributing_transaction_ids=[txn_a, txn_b, txn_c],
        distinct_filer_count=3,
        total_value=Decimal("200000"),
        window_end=date(2026, 8, 11),
    )
    result = repo.upsert_by_overlapping_transactions(grown)

    assert result.id == original.id
    assert result.distinct_filer_count == 3
    assert repo.list_by_company(cik="0001094517") == [result]


def test_upsert_creates_new_row_when_no_transaction_overlaps(db):
    repo = ClusterBuyEventRepository(db)
    repo.create(_event(contributing_transaction_ids=[uuid4(), uuid4()]))

    unrelated = _event(
        contributing_transaction_ids=[uuid4(), uuid4()],
        window_start=date(2026, 11, 1),
        window_end=date(2026, 11, 4),
    )
    result = repo.upsert_by_overlapping_transactions(unrelated)

    all_rows = repo.list_by_company(cik="0001094517")
    assert len(all_rows) == 2
    assert result.id in {row.id for row in all_rows}
