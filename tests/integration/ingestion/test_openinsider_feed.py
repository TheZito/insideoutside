from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openinsider_tracker.ingestion.openinsider_feed import parse_openinsider_page

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_openinsider_page_parses_into_candidate_transactions():
    html = (FIXTURES / "sample_openinsider_page.html").read_text()
    candidates = parse_openinsider_page(
        html,
        source_url="https://openinsider.com/latest-insider-trading",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.ticker == "TM"
    assert candidate.company_name == "Toyota Motor Corp"
    assert candidate.filer_name == "Jane Doe"
    assert candidate.filer_role == "director"
    assert candidate.transaction_type == "buy"
    assert candidate.share_count == Decimal("1000")
    assert candidate.price_per_share == Decimal("150.25")
    assert candidate.transaction_date == date(2026, 8, 1)
    assert candidate.filing_date == date(2026, 8, 3)
    assert candidate.source == "openinsider"
