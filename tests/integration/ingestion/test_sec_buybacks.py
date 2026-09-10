from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from insideoutside.ingestion.sec_buybacks import parse_buyback_disclosure_html

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"

_AUTHORIZATION_HTML = """
<html><body>
<p>Toyota Motor Corp announced today that its Board of Directors has authorized a
new share repurchase program of up to $250,000,000 of its common stock.</p>
</body></html>
"""


def test_executed_buyback_table_parses_as_executed_with_correct_amount():
    html = (FIXTURES / "sample_8k_buyback_100m.xml").read_text()
    event = parse_buyback_disclosure_html(
        html,
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        accession_number="0000912057-26-055555",
        disclosure_date=date(2026, 8, 1),
        source_url="https://www.sec.gov/Archives/edgar/data/example/0000912057-26-055555-index.htm",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert event.disclosure_type == "executed"
    assert event.amount == Decimal("100000000")
    assert event.company_name == "Toyota Motor Corp"


def test_authorization_announcement_parses_as_authorized_with_correct_amount():
    event = parse_buyback_disclosure_html(
        _AUTHORIZATION_HTML,
        company_name="Toyota Motor Corp",
        ticker="TM",
        cik="0001094517",
        accession_number="0000912057-26-066666",
        disclosure_date=date(2026, 8, 1),
        source_url="https://www.sec.gov/Archives/edgar/data/example/0000912057-26-066666-index.htm",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert event.disclosure_type == "authorized"
    assert event.amount == Decimal("250000000")
