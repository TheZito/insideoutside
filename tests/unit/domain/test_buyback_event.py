from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from openinsider_tracker.domain.buyback_event import BuybackEvent


def _valid_kwargs(**overrides):
    kwargs = dict(
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
    kwargs.update(overrides)
    return kwargs


def test_valid_buyback_event_round_trips_fields():
    event = BuybackEvent(**_valid_kwargs())
    assert event.amount == Decimal("100000000")
    assert event.disclosure_type == "executed"


def test_invalid_disclosure_type_is_rejected():
    with pytest.raises(ValidationError):
        BuybackEvent(**_valid_kwargs(disclosure_type="rumored"))


def test_missing_amount_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["amount"]
    with pytest.raises(ValidationError):
        BuybackEvent(**kwargs)


def test_missing_disclosure_date_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["disclosure_date"]
    with pytest.raises(ValidationError):
        BuybackEvent(**kwargs)
