from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration


@dataclass(frozen=True)
class ClusterCandidate:
    """A detected group of 2+ distinct filers' discretionary buys at the same
    company within a window. Not yet evaluated against a notability threshold --
    see classify_cluster. See research.md §1."""

    company_name: str
    ticker: str | None
    cik: str
    window_start: date
    window_end: date
    distinct_filer_count: int
    total_value: Decimal
    contributing_transaction_ids: list[UUID]


@dataclass(frozen=True)
class ClassificationResult:
    is_notable: bool


def _filer_identity(txn: InsiderTransaction) -> str:
    """Prefer the stable SEC-assigned filer_id; fall back to normalized name for
    sources (e.g. OpenInsider) that don't expose one. See research.md §2."""
    if txn.filer_id:
        return f"id:{txn.filer_id}"
    return f"name:{txn.filer_name.strip().lower()}"


def _finalize_group(group: list[InsiderTransaction]) -> ClusterCandidate | None:
    """Turn a same-company, same-window group of transactions into a candidate,
    or None if it doesn't have 2+ distinct filers (not a cluster)."""
    if not group:
        return None
    identities = {_filer_identity(t) for t in group}
    if len(identities) < 2:
        return None
    return ClusterCandidate(
        company_name=group[0].company_name,
        ticker=group[0].ticker,
        cik=group[0].cik,
        window_start=min(t.transaction_date for t in group),
        window_end=max(t.transaction_date for t in group),
        distinct_filer_count=len(identities),
        total_value=sum(
            (t.total_value for t in group if t.total_value is not None),
            start=Decimal("0"),
        ),
        contributing_transaction_ids=[t.id for t in group],
    )


def detect_clusters(
    transactions: list[InsiderTransaction], *, window_days: int
) -> list[ClusterCandidate]:
    """Group qualifying transactions (discretionary buys, not superseded) by
    company, then by a greedy same-window grouping anchored to each group's
    start date (research.md §1). Only groups with 2+ distinct filers are
    returned as candidates -- a single filer is never a "cluster" regardless of
    configuration (FR-011 excludes everything else: sells, non-discretionary
    transactions, and superseded records, from grouping entirely)."""
    qualifying = [
        txn
        for txn in transactions
        if txn.transaction_type == "buy"
        and txn.is_discretionary
        and txn.superseded_by_id is None
    ]

    by_company: dict[str, list[InsiderTransaction]] = {}
    for txn in qualifying:
        by_company.setdefault(txn.cik, []).append(txn)

    candidates: list[ClusterCandidate] = []
    for company_txns in by_company.values():
        company_txns.sort(key=lambda t: t.transaction_date)
        group: list[InsiderTransaction] = []

        for txn in company_txns:
            if not group:
                group = [txn]
                continue
            group_start = group[0].transaction_date
            if (txn.transaction_date - group_start).days <= window_days:
                group.append(txn)
            else:
                candidate = _finalize_group(group)
                if candidate:
                    candidates.append(candidate)
                group = [txn]

        candidate = _finalize_group(group)
        if candidate:
            candidates.append(candidate)

    return candidates


def classify_cluster(
    candidate: ClusterCandidate, config: ThresholdConfiguration
) -> ClassificationResult:
    """FR-003: notable iff the distinct-filer count meets the configured minimum."""
    return ClassificationResult(is_notable=candidate.distinct_filer_count >= config.min_cluster_filer_count)
