import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

from openinsider_tracker.ingestion.dedup import ingest_buyback_event, ingest_insider_transaction
from openinsider_tracker.ingestion.http_client import FetchError, fetch_with_retry
from openinsider_tracker.ingestion.openinsider_feed import fetch_latest_page, parse_openinsider_page
from openinsider_tracker.ingestion.sec_buybacks import (
    fetch_recent_buyback_filing_urls,
    parse_buyback_disclosure_html,
)
from openinsider_tracker.ingestion.sec_edgar_form4 import (
    fetch_form4_xml_from_index,
    fetch_recent_filing_index_urls,
    parse_form4_xml,
)
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from openinsider_tracker.storage.repositories.signal_repo import SignalRepository

logger = logging.getLogger(__name__)

_COMPANY_NAME_PATTERN = re.compile(r"([A-Z][\w&.,]*(?:\s+[A-Z][\w&.,]*)*)\s+today")


def _guess_company_name(text: str) -> str:
    match = _COMPANY_NAME_PATTERN.search(text)
    return match.group(1) if match else "Unknown Company"


def _ingest_fixture(
    *,
    source: str,
    fixture_path: str,
    txn_repo: InsiderTransactionRepository,
    buyback_repo: BuybackEventRepository,
    signal_repo: SignalRepository,
) -> dict:
    """Ingest a single local fixture file, for manual testing / quickstart.md.

    Real (non-fixture) ingestion is per-source below and hits the network.
    """
    path = Path(fixture_path).resolve()
    content = path.read_bytes()
    fetched_at = datetime.now(UTC)
    accession_number = path.stem
    new = updated = failed = 0

    try:
        if source == "sec_edgar" and b"<ownershipDocument" in content:
            existing_refs = {t.source_ref for t in txn_repo.list()}
            transactions = parse_form4_xml(
                content,
                accession_number=accession_number,
                source_url=f"file://{path}",
                fetched_at=fetched_at,
            )
            for txn in transactions:
                ingest_insider_transaction(txn, txn_repo=txn_repo, signal_repo=signal_repo)
                if txn.source_ref in existing_refs:
                    updated += 1
                else:
                    new += 1
        elif source == "sec_edgar":
            text = content.decode()
            event = parse_buyback_disclosure_html(
                text,
                company_name=_guess_company_name(text),
                ticker=None,
                cik="UNKNOWN",
                accession_number=accession_number,
                disclosure_date=fetched_at.date(),
                source_url=f"file://{path}",
                fetched_at=fetched_at,
            )
            existing = buyback_repo.get_by_source_ref(event.source_ref)
            ingest_buyback_event(event, event_repo=buyback_repo, signal_repo=signal_repo)
            new += 0 if existing else 1
            updated += 1 if existing else 0
        elif source == "openinsider":
            candidates = parse_openinsider_page(
                content.decode(), source_url=f"file://{path}", fetched_at=fetched_at
            )
            existing_refs = {t.source_ref for t in txn_repo.list()}
            for candidate in candidates:
                result = ingest_insider_transaction(
                    candidate, txn_repo=txn_repo, signal_repo=signal_repo
                )
                if result.source_ref in existing_refs:
                    updated += 1
                else:
                    new += 1
        else:
            raise ValueError(f"Unsupported source for fixture ingestion: {source}")
    except Exception:
        logger.exception("Failed to ingest fixture %s", fixture_path)
        failed += 1

    return {"source": source, "fetched": 1, "new": new, "updated": updated, "failed": failed}


def run_ingest(
    db: Database,
    *,
    source: str = "all",
    fixture_path: str | None = None,
) -> dict:
    """FR-001/002/003: fetch from configured sources, de-duplicate, and persist
    with provenance. Failures per-source are caught and reported, never silently
    dropped (FR-015, Constitution Principle II)."""
    txn_repo = InsiderTransactionRepository(db)
    buyback_repo = BuybackEventRepository(db)
    signal_repo = SignalRepository(db)

    if fixture_path:
        result = _ingest_fixture(
            source=source,
            fixture_path=fixture_path,
            txn_repo=txn_repo,
            buyback_repo=buyback_repo,
            signal_repo=signal_repo,
        )
        return {"results": [result]}

    # Real network ingestion. Each source's fetch is wrapped in fetch_with_retry
    # (backoff on transient failures) and any exhausted-retry FetchError is caught
    # per-source here so one bad source doesn't block the others (FR-015);
    # individual filing parse failures are likewise caught per-filing so a single
    # malformed filing doesn't abort the whole run (Constitution Principle II: the
    # failure is logged, never silently swallowed).
    results = []
    sources_to_run = ["sec_edgar", "openinsider"] if source == "all" else [source]
    with httpx.Client(timeout=30.0) as client:
        for src in sources_to_run:
            if src == "sec_edgar":
                results.append(_run_sec_edgar(client, txn_repo, buyback_repo, signal_repo))
            elif src == "openinsider":
                results.append(_run_openinsider(client, txn_repo, signal_repo))

    return {"results": results}


def _run_sec_edgar(client, txn_repo, buyback_repo, signal_repo) -> dict:
    fetched = new = updated = failed = 0
    try:
        for index_url in fetch_recent_filing_index_urls(client):
            fetched += 1
            try:
                xml_bytes, accession_number = fetch_form4_xml_from_index(client, index_url)
                transactions = parse_form4_xml(
                    xml_bytes,
                    accession_number=accession_number,
                    source_url=index_url,
                    fetched_at=datetime.now(UTC),
                )
                for txn in transactions:
                    is_new = txn_repo.get_by_source_ref(txn.source_ref) is None
                    ingest_insider_transaction(txn, txn_repo=txn_repo, signal_repo=signal_repo)
                    new += 1 if is_new else 0
                    updated += 0 if is_new else 1
            except (FetchError, ValueError, SyntaxError):
                logger.exception("Failed to ingest Form 4 filing at %s", index_url)
                failed += 1

        for candidate in fetch_recent_buyback_filing_urls(client):
            fetched += 1
            try:
                doc_text = fetch_with_retry(candidate["url"], client=client).text
                event = parse_buyback_disclosure_html(
                    doc_text,
                    company_name=candidate["company_name"],
                    ticker=None,
                    cik=candidate["cik"],
                    accession_number=candidate["accession_number"],
                    disclosure_date=datetime.now(UTC).date(),
                    source_url=candidate["url"],
                    fetched_at=datetime.now(UTC),
                )
                is_new = buyback_repo.get_by_source_ref(event.source_ref) is None
                ingest_buyback_event(event, event_repo=buyback_repo, signal_repo=signal_repo)
                new += 1 if is_new else 0
                updated += 0 if is_new else 1
            except (FetchError, ValueError):
                logger.exception("Failed to ingest buyback filing %s", candidate.get("url"))
                failed += 1
    except FetchError:
        logger.exception("SEC EDGAR discovery feed unavailable")
        failed += 1

    return {"source": "sec_edgar", "fetched": fetched, "new": new, "updated": updated, "failed": failed}


def _run_openinsider(client, txn_repo, signal_repo) -> dict:
    try:
        html = fetch_latest_page(client)
    except FetchError:
        logger.exception("OpenInsider feed unavailable")
        return {"source": "openinsider", "fetched": 0, "new": 0, "updated": 0, "failed": 1}

    candidates = parse_openinsider_page(
        html, source_url="https://openinsider.com/latest-insider-trading", fetched_at=datetime.now(UTC)
    )
    new = updated = 0
    for candidate in candidates:
        is_new = txn_repo.get_by_source_ref(candidate.source_ref) is None
        ingest_insider_transaction(candidate, txn_repo=txn_repo, signal_repo=signal_repo)
        new += 1 if is_new else 0
        updated += 0 if is_new else 1

    return {
        "source": "openinsider",
        "fetched": len(candidates),
        "new": new,
        "updated": updated,
        "failed": 0,
    }
