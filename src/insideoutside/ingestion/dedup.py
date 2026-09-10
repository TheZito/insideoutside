import logging

from insideoutside.domain.buyback_event import BuybackEvent
from insideoutside.domain.insider_transaction import InsiderTransaction
from insideoutside.storage.repositories.buyback_repo import BuybackEventRepository
from insideoutside.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from insideoutside.storage.repositories.signal_repo import SignalRepository

logger = logging.getLogger(__name__)


def _supersede_prior_signal(prior_signal, signal_repo: SignalRepository) -> None:
    if prior_signal and not prior_signal.is_superseded:
        prior_signal.mark_superseded()
        signal_repo.save(prior_signal)
        logger.info("Signal %s marked superseded (underlying filing amended)", prior_signal.id)


def ingest_insider_transaction(
    candidate: InsiderTransaction,
    *,
    txn_repo: InsiderTransactionRepository,
    signal_repo: SignalRepository,
) -> InsiderTransaction:
    """De-duplicate and persist one candidate InsiderTransaction. See research.md §6.

    - Same (source, source_ref) as an existing record: treated as a re-fetch of the
      same filing, upserted in place (FR-007, FR-012).
    - SEC-sourced candidate matching an existing record's (cik, filer_name,
      transaction_date) under a DIFFERENT source_ref: treated as an amendment —
      the prior record and its Signal (if any) are marked superseded (FR-016).
    - OpenInsider-sourced candidate fuzzy-matching an existing SEC-sourced record:
      the existing record is returned as-is; no duplicate is created (FR-007).
    """
    if candidate.source == "sec_edgar":
        existing_same_ref = txn_repo.get_by_source_ref(candidate.source_ref)
        if existing_same_ref:
            return txn_repo.upsert_by_source_ref(candidate)

        priors = [
            p
            for p in txn_repo.find_by_natural_key(
                cik=candidate.cik,
                filer_name=candidate.filer_name,
                transaction_date=candidate.transaction_date,
            )
            if p.superseded_by_id is None
        ]
        new_row = txn_repo.upsert_by_source_ref(candidate)
        for prior in priors:
            txn_repo.mark_superseded(prior.id, new_row.id)
            _supersede_prior_signal(signal_repo.get_for_insider_transaction(prior.id), signal_repo)
        return new_row

    if candidate.source == "openinsider":
        match = txn_repo.find_by_fuzzy_match(
            ticker=candidate.ticker,
            filer_name=candidate.filer_name,
            transaction_date=candidate.transaction_date,
            share_count=candidate.share_count,
        )
        if match:
            return match
        return txn_repo.upsert_by_source_ref(candidate)

    raise ValueError(f"Unknown source: {candidate.source}")


def ingest_buyback_event(
    candidate: BuybackEvent,
    *,
    event_repo: BuybackEventRepository,
    signal_repo: SignalRepository,
) -> BuybackEvent:
    """De-duplicate and persist one candidate BuybackEvent. See research.md §6."""
    existing_same_ref = event_repo.get_by_source_ref(candidate.source_ref)
    if existing_same_ref:
        return event_repo.upsert_by_source_ref(candidate)

    priors = [
        p
        for p in event_repo.find_by_natural_key(
            cik=candidate.cik,
            disclosure_date=candidate.disclosure_date,
            disclosure_type=candidate.disclosure_type,
        )
        if p.superseded_by_id is None
    ]
    new_row = event_repo.upsert_by_source_ref(candidate)
    for prior in priors:
        event_repo.mark_superseded(prior.id, new_row.id)
        _supersede_prior_signal(signal_repo.get_for_buyback_event(prior.id), signal_repo)
    return new_row
