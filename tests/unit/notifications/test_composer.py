from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from openinsider_tracker.domain.cluster_buy_event import ClusterBuyEvent
from openinsider_tracker.domain.signal import Signal
from openinsider_tracker.notifications.composer import compose_signal_email
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.migrations import apply_migrations
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)


@pytest.fixture
def repos(tmp_path):
    db_path = tmp_path / "test.db"
    apply_migrations(str(db_path))
    db = Database(str(db_path))
    yield (
        InsiderTransactionRepository(db),
        BuybackEventRepository(db),
        ClusterBuyEventRepository(db),
    )
    db.dispose()


def test_cluster_buy_email_mentions_filer_count_and_combined_value(repos):
    txn_repo, buyback_repo, cluster_repo = repos
    cluster = cluster_repo.create(
        ClusterBuyEvent(
            company_name="Toyota Motor Corp",
            ticker="TM",
            cik="0001094517",
            window_start=date(2026, 8, 1),
            window_end=date(2026, 8, 4),
            distinct_filer_count=2,
            total_value=Decimal("110000"),
            contributing_transaction_ids=[uuid4(), uuid4()],
        )
    )
    signal = Signal(
        signal_type="cluster_buy",
        cluster_buy_event_id=cluster.id,
        is_notable=True,
        is_discretionary=None,
        evaluated_threshold_snapshot={},
        notification_status="pending",
    )

    subject, body = compose_signal_email(
        signal,
        txn_repo=txn_repo,
        buyback_repo=buyback_repo,
        cluster_repo=cluster_repo,
        dashboard_base_url="http://localhost:8000",
    )

    assert "Toyota Motor Corp" in subject
    assert "2" in subject or "2" in body
    assert "110,000" in body or "$110,000" in body
    assert "2026-08-01" in body
    assert "2026-08-04" in body
