from datetime import date, datetime
from decimal import Decimal

from openinsider_tracker.classification.cluster_buying import classify_cluster, detect_clusters
from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration


def _txn(**overrides):
    kwargs = dict(
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        filer_name="Alice Chen",
        filer_id="0001111111",
        filer_role="director",
        transaction_type="buy",
        transaction_code="P",
        is_discretionary=True,
        share_count=Decimal("100"),
        price_per_share=Decimal("300"),
        transaction_date=date(2026, 8, 1),
        filing_date=date(2026, 8, 3),
        source="sec_edgar",
        source_ref="ref-a",
        source_url="https://example.test",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )
    kwargs.update(overrides)
    return InsiderTransaction(**kwargs)


def test_two_distinct_filers_at_same_company_within_window_form_one_cluster():
    txn_a = _txn(source_ref="a")
    txn_b = _txn(
        source_ref="b",
        filer_name="Bob Diaz",
        filer_id="0002222222",
        filer_role="officer",
        transaction_date=date(2026, 8, 4),
    )
    candidates = detect_clusters([txn_a, txn_b], window_days=14)
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.distinct_filer_count == 2
    assert candidate.window_start == date(2026, 8, 1)
    assert candidate.window_end == date(2026, 8, 4)
    assert candidate.total_value == Decimal("60000")  # 100@300 + 100@300
    assert {txn_a.id, txn_b.id} == set(candidate.contributing_transaction_ids)


def test_different_companies_are_never_grouped_together():
    txn_a = _txn(source_ref="a", cik="0001094517")
    txn_b = _txn(source_ref="b", cik="0009999999", filer_name="Bob Diaz", filer_id="0002222222")
    candidates = detect_clusters([txn_a, txn_b], window_days=14)
    assert candidates == []


def test_same_filer_buying_twice_counts_once_not_twice():
    txn_a = _txn(source_ref="a", transaction_date=date(2026, 8, 1))
    txn_b = _txn(source_ref="b", transaction_date=date(2026, 8, 5))  # same filer as txn_a
    txn_c = _txn(
        source_ref="c",
        filer_name="Bob Diaz",
        filer_id="0002222222",
        transaction_date=date(2026, 8, 6),
    )
    candidates = detect_clusters([txn_a, txn_b, txn_c], window_days=14)
    assert len(candidates) == 1
    assert candidates[0].distinct_filer_count == 2


def test_sells_and_non_discretionary_transactions_are_excluded():
    txn_a = _txn(source_ref="a")
    txn_b_sell = _txn(
        source_ref="b", filer_name="Bob Diaz", filer_id="0002222222", transaction_type="sell"
    )
    txn_c_routine = _txn(
        source_ref="c", filer_name="Carol Nguyen", filer_id="0003333333", is_discretionary=False
    )
    candidates = detect_clusters([txn_a, txn_b_sell, txn_c_routine], window_days=14)
    assert candidates == []


def test_transactions_outside_window_do_not_group():
    txn_a = _txn(source_ref="a", transaction_date=date(2026, 8, 1))
    txn_b = _txn(
        source_ref="b",
        filer_name="Bob Diaz",
        filer_id="0002222222",
        transaction_date=date(2026, 9, 1),
    )
    candidates = detect_clusters([txn_a, txn_b], window_days=14)
    assert candidates == []


def test_superseded_transactions_are_excluded():
    txn_a = _txn(source_ref="a")
    txn_b = _txn(
        source_ref="b",
        filer_name="Bob Diaz",
        filer_id="0002222222",
        superseded_by_id="99999999-9999-9999-9999-999999999999",
    )
    candidates = detect_clusters([txn_a, txn_b], window_days=14)
    assert candidates == []


def test_classify_cluster_notable_iff_meets_min_filer_count():
    txn_a = _txn(source_ref="a")
    txn_b = _txn(source_ref="b", filer_name="Bob Diaz", filer_id="0002222222")
    candidate = detect_clusters([txn_a, txn_b], window_days=14)[0]

    lenient = ThresholdConfiguration(min_cluster_filer_count=2)
    assert classify_cluster(candidate, lenient).is_notable is True

    strict = ThresholdConfiguration(min_cluster_filer_count=3)
    assert classify_cluster(candidate, strict).is_notable is False
