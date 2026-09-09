from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from openinsider_tracker.domain.cluster_buy_event import ClusterBuyEvent


def _valid_kwargs(**overrides):
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
    return kwargs


def test_valid_cluster_buy_event_round_trips_fields():
    event = ClusterBuyEvent(**_valid_kwargs())
    assert event.distinct_filer_count == 2
    assert event.total_value == Decimal("110000")


def test_window_end_before_window_start_is_rejected():
    with pytest.raises(ValidationError):
        ClusterBuyEvent(**_valid_kwargs(window_start=date(2026, 8, 10), window_end=date(2026, 8, 1)))


def test_window_start_equal_to_window_end_is_allowed():
    event = ClusterBuyEvent(
        **_valid_kwargs(window_start=date(2026, 8, 1), window_end=date(2026, 8, 1))
    )
    assert event.window_start == event.window_end


def test_negative_distinct_filer_count_is_rejected():
    with pytest.raises(ValidationError):
        ClusterBuyEvent(**_valid_kwargs(distinct_filer_count=-1))


def test_missing_company_name_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["company_name"]
    with pytest.raises(ValidationError):
        ClusterBuyEvent(**kwargs)


def test_missing_contributing_transaction_ids_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["contributing_transaction_ids"]
    with pytest.raises(ValidationError):
        ClusterBuyEvent(**kwargs)
