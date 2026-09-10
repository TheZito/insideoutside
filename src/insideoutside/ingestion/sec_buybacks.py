import re
from datetime import date, datetime
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from insideoutside.domain.buyback_event import BuybackEvent
from insideoutside.ingestion.http_client import fetch_with_retry

FULL_TEXT_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index?q=%22repurchase%22&forms=8-K"

_AUTHORIZATION_PATTERN = re.compile(
    r"authoriz\w*[^.]{0,120}?repurchase[^.]{0,120}?\$?([\d,]+(?:\.\d+)?)\s*(million|billion)?",
    re.IGNORECASE,
)
_TOTAL_VALUE_PATTERN = re.compile(r"total value:?\s*\$?([\d,]+(?:\.\d+)?)", re.IGNORECASE)


def _parse_amount(digits: str, scale: str | None) -> Decimal:
    amount = Decimal(digits.replace(",", ""))
    if scale and scale.lower() == "million":
        amount *= Decimal("1000000")
    elif scale and scale.lower() == "billion":
        amount *= Decimal("1000000000")
    return amount


def parse_buyback_disclosure_html(
    html: str,
    *,
    company_name: str,
    ticker: str | None,
    cik: str,
    accession_number: str,
    disclosure_date: date,
    source_url: str,
    fetched_at: datetime,
) -> BuybackEvent:
    """Parse an SEC buyback disclosure (8-K authorization language, or an
    Item 703 "Issuer Purchases of Equity Securities" table showing an executed
    repurchase) into a BuybackEvent. See research.md §4."""
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    total_value_match = _TOTAL_VALUE_PATTERN.search(text)
    if total_value_match:
        amount = _parse_amount(total_value_match.group(1), None)
        disclosure_type = "executed"
    else:
        authorization_match = _AUTHORIZATION_PATTERN.search(text)
        if not authorization_match:
            raise ValueError("Could not find a buyback authorization or executed amount in disclosure")
        amount = _parse_amount(authorization_match.group(1), authorization_match.group(2))
        disclosure_type = "authorized"

    return BuybackEvent(
        company_name=company_name,
        ticker=ticker,
        cik=cik,
        disclosure_type=disclosure_type,
        amount=amount,
        disclosure_date=disclosure_date,
        source="sec_edgar",
        source_ref=f"{accession_number}-item703",
        source_url=source_url,
        fetched_at=fetched_at,
    )


def fetch_recent_buyback_filing_urls(client: httpx.Client) -> list[dict]:
    """Query SEC EDGAR full-text search for recent 8-K filings mentioning a
    repurchase (research.md §4). Returns a list of {"accession_number", "cik",
    "company_name", "url"} dicts. Live-network path: the exact JSON shape should
    be confirmed against a real request post-deploy; failures here surface as a
    FetchError rather than being silently skipped (Constitution Principle II).
    """
    response = fetch_with_retry(FULL_TEXT_SEARCH_URL, client=client)
    payload = response.json()
    results = []
    for hit in payload.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        accession_number = hit.get("_id", "").split(":")[0]
        cik = (source.get("ciks") or [""])[0]
        results.append(
            {
                "accession_number": accession_number,
                "cik": cik,
                "company_name": (source.get("display_names") or ["Unknown"])[0],
                "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_number.replace('-', '')}",
            }
        )
    return results
