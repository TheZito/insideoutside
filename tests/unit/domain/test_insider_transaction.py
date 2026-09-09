from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from openinsider_tracker.domain.insider_transaction import InsiderTransaction


def _valid_kwargs(**overrides):
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
    return kwargs


def test_total_value_is_derived_from_share_count_and_price():
    txn = InsiderTransaction(**_valid_kwargs())
    assert txn.total_value == Decimal("150250.00")


def test_total_value_is_none_when_price_is_none():
    txn = InsiderTransaction(**_valid_kwargs(price_per_share=None))
    assert txn.total_value is None


def test_missing_transaction_date_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["transaction_date"]
    with pytest.raises(ValidationError):
        InsiderTransaction(**kwargs)


def test_missing_source_ref_is_rejected():
    kwargs = _valid_kwargs()
    del kwargs["source_ref"]
    with pytest.raises(ValidationError):
        InsiderTransaction(**kwargs)


def test_invalid_transaction_type_is_rejected():
    with pytest.raises(ValidationError):
        InsiderTransaction(**_valid_kwargs(transaction_type="hold"))


def test_invalid_filer_role_is_rejected():
    with pytest.raises(ValidationError):
        InsiderTransaction(**_valid_kwargs(filer_role="ceo_of_everything"))


def test_filer_id_is_optional_and_defaults_to_none():
    txn = InsiderTransaction(**_valid_kwargs())
    assert txn.filer_id is None


def test_filer_id_can_be_set_explicitly():
    txn = InsiderTransaction(**_valid_kwargs(filer_id="0001111111"))
    assert txn.filer_id == "0001111111"
