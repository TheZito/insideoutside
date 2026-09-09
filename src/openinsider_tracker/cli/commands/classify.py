import argparse
import json
import logging

from openinsider_tracker.classification.cluster_buying import classify_cluster, detect_clusters
from openinsider_tracker.classification.rules import classify_buyback, classify_insider_transaction
from openinsider_tracker.config import Config
from openinsider_tracker.domain.cluster_buy_event import ClusterBuyEvent
from openinsider_tracker.domain.signal import Signal
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from openinsider_tracker.storage.repositories.signal_repo import SignalRepository
from openinsider_tracker.storage.repositories.threshold_repo import (
    ThresholdConfigurationRepository,
)

logger = logging.getLogger(__name__)


def _threshold_snapshot(config) -> dict:
    return {
        "min_insider_buy_value": str(config.min_insider_buy_value),
        "min_notable_role_buy_value": str(config.min_notable_role_buy_value),
        "notable_filer_roles": list(config.notable_filer_roles),
        "min_buyback_amount": str(config.min_buyback_amount),
        "cluster_window_days": config.cluster_window_days,
        "min_cluster_filer_count": config.min_cluster_filer_count,
    }


def _upsert_signal(
    signal_repo: SignalRepository,
    existing: Signal | None,
    *,
    signal_type: str,
    link_kwargs: dict,
    is_notable: bool,
    is_discretionary: bool | None,
    snapshot: dict,
    downgrade_on_not_notable: bool = True,
) -> Signal:
    """Create-or-update a Signal for one classified record and save it. Shared
    by all three signal types so the notification_status transition rule lives
    in exactly one place.

    `downgrade_on_not_notable` controls what happens when a previously-notable
    signal is reclassified as not notable: insider-transaction and buyback
    signals reset to not_applicable, but a cluster signal deliberately does NOT
    (an already-sent cluster's history must survive a later window/threshold
    change splitting it below the minimum -- see research.md §5).
    """
    signal = existing or Signal(
        signal_type=signal_type,
        is_notable=is_notable,
        is_discretionary=is_discretionary,
        evaluated_threshold_snapshot=snapshot,
        notification_status="pending" if is_notable else "not_applicable",
        **link_kwargs,
    )
    if existing is not None:
        signal.is_notable = is_notable
        signal.is_discretionary = is_discretionary
        signal.evaluated_threshold_snapshot = snapshot
        if is_notable and signal.notification_status == "not_applicable":
            signal.notification_status = "pending"
        elif not is_notable and downgrade_on_not_notable:
            signal.notification_status = "not_applicable"
    signal_repo.save(signal)
    return signal


def _classify_insider_transactions(
    txn_repo: InsiderTransactionRepository,
    signal_repo: SignalRepository,
    thresholds,
    snapshot: dict,
    reclassify: bool,
) -> tuple[int, int]:
    evaluated = 0
    notable = 0
    for txn in txn_repo.list():
        if txn.superseded_by_id is not None:
            continue
        existing = signal_repo.get_for_insider_transaction(txn.id)
        if existing is not None and not reclassify:
            continue
        result = classify_insider_transaction(txn, thresholds)
        evaluated += 1
        notable += 1 if result.is_notable else 0
        _upsert_signal(
            signal_repo,
            existing,
            signal_type="insider_transaction",
            link_kwargs={"insider_transaction_id": txn.id},
            is_notable=result.is_notable,
            is_discretionary=txn.is_discretionary,
            snapshot=snapshot,
        )
    return evaluated, notable


def _classify_buybacks(
    buyback_repo: BuybackEventRepository,
    signal_repo: SignalRepository,
    thresholds,
    snapshot: dict,
    reclassify: bool,
) -> tuple[int, int]:
    evaluated = 0
    notable = 0
    for event in buyback_repo.list():
        if event.superseded_by_id is not None:
            continue
        existing = signal_repo.get_for_buyback_event(event.id)
        if existing is not None and not reclassify:
            continue
        result = classify_buyback(event, thresholds)
        evaluated += 1
        notable += 1 if result.is_notable else 0
        _upsert_signal(
            signal_repo,
            existing,
            signal_type="buyback",
            link_kwargs={"buyback_event_id": event.id},
            is_notable=result.is_notable,
            is_discretionary=None,
            snapshot=snapshot,
        )
    return evaluated, notable


def _classify_clusters(
    txn_repo: InsiderTransactionRepository,
    cluster_repo: ClusterBuyEventRepository,
    signal_repo: SignalRepository,
    thresholds,
    snapshot: dict,
) -> tuple[int, int]:
    """Recompute cluster groupings from scratch every run (research.md §5) --
    at this project's data volumes this is cheap, and it means `--reclassify`
    needs no special-casing: every `classify` run already re-groups everything,
    so a threshold/window change takes effect on the very next run.
    """
    transactions = [t for t in txn_repo.list() if t.superseded_by_id is None]
    candidates = detect_clusters(transactions, window_days=thresholds.cluster_window_days)

    clusters_detected = len(candidates)
    clusters_notable = 0

    for candidate in candidates:
        result = classify_cluster(candidate, thresholds)
        clusters_notable += 1 if result.is_notable else 0

        cluster_event = ClusterBuyEvent(
            company_name=candidate.company_name,
            ticker=candidate.ticker,
            cik=candidate.cik,
            window_start=candidate.window_start,
            window_end=candidate.window_end,
            distinct_filer_count=candidate.distinct_filer_count,
            total_value=candidate.total_value,
            contributing_transaction_ids=candidate.contributing_transaction_ids,
        )
        saved_event = cluster_repo.upsert_by_overlapping_transactions(cluster_event)

        existing_signal = signal_repo.get_for_cluster_buy_event(saved_event.id)
        was_notable = existing_signal.is_notable if existing_signal is not None else None

        _upsert_signal(
            signal_repo,
            existing_signal,
            signal_type="cluster_buy",
            link_kwargs={"cluster_buy_event_id": saved_event.id},
            is_notable=result.is_notable,
            is_discretionary=None,
            snapshot=snapshot,
            downgrade_on_not_notable=False,
        )

        if existing_signal is None:
            event_desc = "created"
        elif was_notable != result.is_notable:
            event_desc = f"updated (notability changed {was_notable} -> {result.is_notable})"
        else:
            event_desc = "updated"
        logger.info(
            "Cluster %s for %s: %d filers, notable=%s",
            event_desc,
            candidate.company_name,
            candidate.distinct_filer_count,
            result.is_notable,
        )

    return clusters_detected, clusters_notable


def run_classify(args: argparse.Namespace, config: Config) -> int:
    with Database(config.db_path) as db:
        txn_repo = InsiderTransactionRepository(db)
        buyback_repo = BuybackEventRepository(db)
        signal_repo = SignalRepository(db)
        cluster_repo = ClusterBuyEventRepository(db)
        threshold_repo = ThresholdConfigurationRepository(db)
        thresholds = threshold_repo.get()
        snapshot = _threshold_snapshot(thresholds)

        txn_evaluated, txn_notable = _classify_insider_transactions(
            txn_repo, signal_repo, thresholds, snapshot, args.reclassify
        )
        buyback_evaluated, buyback_notable = _classify_buybacks(
            buyback_repo, signal_repo, thresholds, snapshot, args.reclassify
        )
        clusters_detected, clusters_notable = _classify_clusters(
            txn_repo, cluster_repo, signal_repo, thresholds, snapshot
        )

        print(
            json.dumps(
                {
                    "evaluated": txn_evaluated + buyback_evaluated,
                    "notable": txn_notable + buyback_notable,
                    "clusters_detected": clusters_detected,
                    "clusters_notable": clusters_notable,
                }
            )
        )
        return 0
