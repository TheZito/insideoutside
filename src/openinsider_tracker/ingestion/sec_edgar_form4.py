import re
from datetime import date, datetime
from decimal import Decimal
from xml.etree import ElementTree as ET

import httpx

from openinsider_tracker.domain.insider_transaction import (
    FilerRole,
    InsiderTransaction,
    TransactionType,
)
from openinsider_tracker.ingestion.http_client import fetch_with_retry

CURRENT_FORM4_FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&output=atom&count=100"
)
_ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _text(el: ET.Element | None) -> str | None:
    if el is None:
        return None
    value = el.findtext("value")
    if value is not None:
        return value.strip()
    return (el.text or "").strip() or None


def _filer_role(relationship: ET.Element | None) -> FilerRole:
    if relationship is None:
        return "other"

    def _flag(tag: str) -> bool:
        text = relationship.findtext(tag)
        return text is not None and text.strip() in ("1", "true", "True")

    if _flag("isOfficer"):
        return "officer"
    if _flag("isDirector"):
        return "director"
    if _flag("isTenPercentOwner"):
        return "ten_percent_owner"
    return "other"


def _transaction_type(acquired_disposed_code: str | None) -> TransactionType:
    return "sell" if acquired_disposed_code == "D" else "buy"


def _is_discretionary(transaction_code: str, footnote_text: str) -> bool:
    """research.md §2: open-market codes (P/S) are discretionary unless the filing
    itself indicates a Rule 10b5-1 plan; code F (tax withholding) is never
    discretionary."""
    if transaction_code == "F":
        return False
    if "10b5-1" in footnote_text or "10b5 1" in footnote_text:
        return False
    return transaction_code in ("P", "S")


def parse_form4_xml(
    xml_bytes: bytes,
    *,
    accession_number: str,
    source_url: str,
    fetched_at: datetime,
    filing_date: date | None = None,
) -> list[InsiderTransaction]:
    """Parse a Form 4 ownership XML document into one InsiderTransaction per
    non-derivative transaction line (data-model.md natural key: accession number +
    line index, per research.md §6)."""
    root = ET.fromstring(xml_bytes)

    issuer = root.find("issuer")
    company_name = issuer.findtext("issuerName", "").strip()
    ticker = (issuer.findtext("issuerTradingSymbol") or "").strip() or None
    cik = (issuer.findtext("issuerCik") or "").strip()

    owner = root.find("reportingOwner")
    owner_id = owner.find("reportingOwnerId")
    filer_name = owner_id.findtext("rptOwnerName", "").strip()
    filer_id = (owner_id.findtext("rptOwnerCik") or "").strip() or None
    filer_role = _filer_role(owner.find("reportingOwnerRelationship"))

    period_of_report = root.findtext("periodOfReport")
    resolved_filing_date = filing_date or date.fromisoformat(period_of_report.strip())

    footnotes_by_id: dict[str, str] = {}
    footnotes_el = root.find("footnotes")
    if footnotes_el is not None:
        for footnote in footnotes_el.findall("footnote"):
            footnote_id = footnote.get("id", "")
            footnotes_by_id[footnote_id] = (footnote.text or "").strip()

    transactions: list[InsiderTransaction] = []
    table = root.find("nonDerivativeTable")
    if table is None:
        return transactions

    for index, txn_el in enumerate(table.findall("nonDerivativeTransaction")):
        transaction_date = date.fromisoformat(
            _text(txn_el.find("transactionDate")) or period_of_report.strip()
        )
        coding = txn_el.find("transactionCoding")
        transaction_code = (coding.findtext("transactionCode") or "").strip()

        amounts = txn_el.find("transactionAmounts")
        share_count = Decimal(_text(amounts.find("transactionShares")) or "0")
        price_text = _text(amounts.find("transactionPricePerShare"))
        price_per_share = Decimal(price_text) if price_text else None
        acquired_disposed = _text(amounts.find("transactionAcquiredDisposedCode"))

        footnote_ids = [
            fn.get("id", "") for fn in txn_el.findall("transactionFootnoteIndex")
        ]
        footnote_text = " ".join(footnotes_by_id.get(fid, "") for fid in footnote_ids)

        transactions.append(
            InsiderTransaction(
                company_name=company_name,
                ticker=ticker,
                cik=cik,
                filer_name=filer_name,
                filer_id=filer_id,
                filer_role=filer_role,
                transaction_type=_transaction_type(acquired_disposed),
                transaction_code=transaction_code,
                is_discretionary=_is_discretionary(transaction_code, footnote_text),
                share_count=share_count,
                price_per_share=price_per_share,
                transaction_date=transaction_date,
                filing_date=resolved_filing_date,
                source="sec_edgar",
                source_ref=f"{accession_number}-{index}",
                source_url=source_url,
                fetched_at=fetched_at,
            )
        )

    return transactions


def fetch_recent_filing_index_urls(client: httpx.Client) -> list[str]:
    """Fetch SEC EDGAR's "current events" Form 4 feed and return filing index page
    URLs discovered in it (research.md §2). Live-network path: the SEC's Atom feed
    format is standard, but the exact index-page layout can only be fully verified
    against a live request — treat this as best-effort and monitor logs after
    deploying against the real endpoint.
    """
    response = fetch_with_retry(CURRENT_FORM4_FEED_URL, client=client)
    root = ET.fromstring(response.content)
    urls = []
    for entry in root.findall("atom:entry", _ATOM_NS):
        link = entry.find("atom:link", _ATOM_NS)
        if link is not None and link.get("href"):
            urls.append(link.get("href"))
    return urls


def fetch_form4_xml_from_index(client: httpx.Client, index_url: str) -> tuple[bytes, str]:
    """Follow a filing index page to its primary ownership XML document.

    Returns (xml_bytes, accession_number). Raises FetchError if the index page or
    document can't be fetched, or ValueError if no XML document is found on the
    index page — both are surfaced to the caller rather than silently skipped
    (Constitution Principle II).
    """
    index_response = fetch_with_retry(index_url, client=client)
    accession_number = index_url.rstrip("/").split("/")[-1].replace("-index.htm", "")

    xml_hrefs = re.findall(r'href="([^"]+\.xml)"', index_response.text, flags=re.IGNORECASE)
    xml_href = xml_hrefs[0] if xml_hrefs else None
    if xml_href is None:
        raise ValueError(f"No XML document found on filing index page: {index_url}")

    document_url = xml_href if xml_href.startswith("http") else httpx.URL(index_url).join(xml_href)
    xml_response = fetch_with_retry(str(document_url), client=client)
    return xml_response.content, accession_number
