from datetime import date, datetime
from decimal import Decimal

from openinsider_tracker.classification.rules import classify_buyback, classify_insider_transaction
from openinsider_tracker.domain.buyback_event import BuybackEvent
from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration


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
        price_per_share=Decimal("2000"),
        transaction_date=date(2026, 8, 1),
        filing_date=date(2026, 8, 3),
        source="sec_edgar",
        source_ref="ref-1",
        source_url="https://example.test",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    kwargs.update(overrides)
    return InsiderTransaction(**kwargs)


def test_discretionary_buy_at_or_above_threshold_is_notable():
    config = ThresholdConfiguration(min_insider_buy_value=Decimal("1000000"))
    txn = _txn(share_count=Decimal("1000"), price_per_share=Decimal("2000"))  # $2,000,000
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is True


def test_discretionary_buy_below_threshold_and_non_notable_role_is_not_notable():
    config = ThresholdConfiguration(
        min_insider_buy_value=Decimal("1000000"), notable_filer_roles=["ten_percent_owner"]
    )
    txn = _txn(
        share_count=Decimal("10"), price_per_share=Decimal("5"), filer_role="other"
    )  # $50, role not notable
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is False


def test_notable_role_below_its_own_lower_threshold_is_not_notable():
    """Role alone is never sufficient -- a $1 buy by a director is still excluded
    even though director is a notable role, because it doesn't clear
    min_notable_role_buy_value."""
    config = ThresholdConfiguration(
        min_insider_buy_value=Decimal("1000000"),
        min_notable_role_buy_value=Decimal("100000"),
        notable_filer_roles=["director"],
    )
    txn = _txn(share_count=Decimal("1"), price_per_share=Decimal("1"), filer_role="director")
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is False


def test_notable_role_at_or_above_its_own_lower_threshold_is_notable():
    """A director buy that clears the lower role-specific threshold is notable
    even though it's well below the general min_insider_buy_value."""
    config = ThresholdConfiguration(
        min_insider_buy_value=Decimal("1000000"),
        min_notable_role_buy_value=Decimal("100000"),
        notable_filer_roles=["director"],
    )
    txn = _txn(share_count=Decimal("1000"), price_per_share=Decimal("150"), filer_role="director")
    result = classify_insider_transaction(txn, config)  # $150,000
    assert result.is_notable is True


def test_non_notable_role_must_clear_the_higher_general_threshold():
    config = ThresholdConfiguration(
        min_insider_buy_value=Decimal("1000000"),
        min_notable_role_buy_value=Decimal("100000"),
        notable_filer_roles=["director"],
    )
    txn = _txn(
        share_count=Decimal("1000"), price_per_share=Decimal("150"), filer_role="other"
    )  # $150,000 -- clears the role threshold but "other" isn't a notable role
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is False


def test_routine_10b5_1_transaction_is_excluded_even_above_threshold():
    config = ThresholdConfiguration(min_insider_buy_value=Decimal("1000000"))
    txn = _txn(
        is_discretionary=False,
        share_count=Decimal("1000"),
        price_per_share=Decimal("2000"),
    )
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is False


def test_sell_transactions_are_never_notable():
    config = ThresholdConfiguration(min_insider_buy_value=Decimal("1"))
    txn = _txn(transaction_type="sell", is_discretionary=True)
    result = classify_insider_transaction(txn, config)
    assert result.is_notable is False


def test_buyback_at_or_above_threshold_is_notable():
    config = ThresholdConfiguration(min_buyback_amount=Decimal("50000000"))
    event = BuybackEvent(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        disclosure_type="executed",
        amount=Decimal("100000000"),
        disclosure_date=date(2026, 8, 1),
        source="sec_edgar",
        source_ref="ref-2",
        source_url="https://example.test",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    result = classify_buyback(event, config)
    assert result.is_notable is True


def test_buyback_below_threshold_is_not_notable():
    config = ThresholdConfiguration(min_buyback_amount=Decimal("50000000"))
    event = BuybackEvent(
        company_name="Small Co",
        ticker="SM",
        cik="0009999999",
        disclosure_type="executed",
        amount=Decimal("1000000"),
        disclosure_date=date(2026, 8, 1),
        source="sec_edgar",
        source_ref="ref-3",
        source_url="https://example.test",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    result = classify_buyback(event, config)
    assert result.is_notable is False
