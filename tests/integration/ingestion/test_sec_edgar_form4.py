from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from insideoutside.ingestion.sec_edgar_form4 import parse_form4_xml

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def test_large_discretionary_buy_parses_correctly():
    xml_bytes = (FIXTURES / "sample_form4_large_buy.xml").read_bytes()
    transactions = parse_form4_xml(
        xml_bytes,
        accession_number="0000912057-26-012345",
        source_url="https://www.sec.gov/Archives/edgar/data/example/0000912057-26-012345-index.htm",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert len(transactions) == 1
    txn = transactions[0]
    assert txn.company_name == "Toyota Motor Corp"
    assert txn.ticker == "TM"
    assert txn.cik == "0001094517"
    assert txn.filer_name == "Jane Doe"
    assert txn.filer_role == "director"
    assert txn.transaction_type == "buy"
    assert txn.transaction_code == "P"
    assert txn.is_discretionary is True
    assert txn.share_count == Decimal("1000")
    assert txn.price_per_share == Decimal("150.25")
    assert txn.total_value == Decimal("150250.00")
    assert txn.transaction_date == date(2026, 8, 1)
    assert txn.source == "sec_edgar"
    assert txn.source_ref == "0000912057-26-012345-0"
    assert txn.filer_id == "0001234567"


def test_routine_10b5_1_sale_is_not_discretionary():
    xml_bytes = (FIXTURES / "sample_form4_routine_10b5-1.xml").read_bytes()
    transactions = parse_form4_xml(
        xml_bytes,
        accession_number="0000912057-26-099999",
        source_url="https://www.sec.gov/Archives/edgar/data/example/0000912057-26-099999-index.htm",
        fetched_at=datetime(2026, 8, 3, 12, 0, 0),
    )

    assert len(transactions) == 1
    txn = transactions[0]
    assert txn.filer_role == "officer"
    assert txn.transaction_type == "sell"
    assert txn.transaction_code == "S"
    assert txn.is_discretionary is False
