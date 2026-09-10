from datetime import date, datetime
from decimal import Decimal

import httpx
from bs4 import BeautifulSoup

from insideoutside.domain.insider_transaction import (
    FilerRole,
    InsiderTransaction,
)
from insideoutside.ingestion.http_client import fetch_with_retry

LATEST_TRADES_URL = "https://openinsider.com/latest-insider-trading"

_ROLE_MAP: dict[str, FilerRole] = {
    "director": "director",
    "officer": "officer",
    "10% owner": "ten_percent_owner",
    "ten percent owner": "ten_percent_owner",
}


def _clean_number(text: str) -> str:
    return text.replace(",", "").replace("+", "").replace("$", "").strip()


def _filer_role(title: str) -> FilerRole:
    lowered = title.lower()
    for key, role in _ROLE_MAP.items():
        if key in lowered:
            return role
    return "other"


def parse_openinsider_page(
    html: str,
    *,
    source_url: str,
    fetched_at: datetime,
) -> list[InsiderTransaction]:
    """Parse an OpenInsider-style listing page into candidate InsiderTransactions.

    These are candidates for cross-source de-duplication (research.md §3) — the
    caller is responsible for matching them against SEC-sourced records before
    persisting, since OpenInsider itself is not the authoritative source.
    """
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if table is None:
        return []

    rows = table.find_all("tr")[1:]  # skip header
    candidates: list[InsiderTransaction] = []

    for row_index, row in enumerate(rows):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if len(cells) < 10:
            continue
        (
            filing_date_text,
            trade_date_text,
            ticker,
            company_name,
            filer_name,
            title,
            trade_type,
            price_text,
            qty_text,
            _value_text,
        ) = cells[:10]

        transaction_type = "buy" if trade_type.strip().upper().startswith("P") else "sell"

        candidates.append(
            InsiderTransaction(
                company_name=company_name,
                ticker=ticker or None,
                cik="",
                filer_name=filer_name,
                filer_role=_filer_role(title),
                transaction_type=transaction_type,
                transaction_code=trade_type.split("-")[0].strip(),
                is_discretionary=True,
                share_count=Decimal(_clean_number(qty_text)),
                price_per_share=Decimal(_clean_number(price_text)),
                transaction_date=date.fromisoformat(trade_date_text),
                filing_date=date.fromisoformat(filing_date_text),
                source="openinsider",
                source_ref=f"openinsider:{ticker}:{trade_date_text}:{filer_name}:{row_index}",
                source_url=source_url,
                fetched_at=fetched_at,
            )
        )

    return candidates


def fetch_latest_page(client: httpx.Client) -> str:
    """Fetch the OpenInsider "latest insider trading" page (research.md §3). A
    single polite scheduled request per poll interval, per Constitution Data
    Handling & Compliance Standards.
    """
    response = fetch_with_retry(LATEST_TRADES_URL, client=client)
    return response.text
