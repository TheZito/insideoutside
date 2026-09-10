from datetime import date

from fastapi import APIRouter, HTTPException, Query, Request

from insideoutside.storage.repositories.buyback_repo import BuybackEventRepository
from insideoutside.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository
from insideoutside.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from insideoutside.storage.repositories.signal_repo import SignalRepository

router = APIRouter()


def _resolve_signal(signal, txn_repo, buyback_repo, cluster_repo) -> tuple[dict, object]:
    """Return (summary dict, underlying record) for a signal. Both list and
    detail views need the record resolved exactly once per signal_type."""
    if signal.signal_type == "insider_transaction":
        txn = txn_repo.get(signal.insider_transaction_id)
        summary = {
            "company_name": txn.company_name,
            "ticker": txn.ticker,
            "summary": f"{txn.filer_name} ({txn.filer_role}) {txn.transaction_type} "
            f"{txn.share_count} shares @ {txn.price_per_share}",
            "amount": float(txn.total_value) if txn.total_value is not None else None,
            "event_date": txn.transaction_date.isoformat(),
            "source_url": txn.source_url,
        }
        return summary, txn
    if signal.signal_type == "buyback":
        event = buyback_repo.get(signal.buyback_event_id)
        summary = {
            "company_name": event.company_name,
            "ticker": event.ticker,
            "summary": f"{event.disclosure_type} buyback of {event.amount}",
            "amount": float(event.amount),
            "event_date": event.disclosure_date.isoformat(),
            "source_url": event.source_url,
        }
        return summary, event
    cluster = cluster_repo.get(signal.cluster_buy_event_id)
    summary = {
        "company_name": cluster.company_name,
        "ticker": cluster.ticker,
        "summary": (
            f"{cluster.distinct_filer_count} insiders bought between "
            f"{cluster.window_start.isoformat()} and {cluster.window_end.isoformat()}"
        ),
        "amount": float(cluster.total_value),
        "event_date": cluster.window_end.isoformat(),
        "source_url": None,
    }
    return summary, cluster


def query_signals(
    db,
    *,
    notable_only: bool = True,
    signal_type: str | None = None,
    since: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Plain function shared by the /api/signals endpoint and the server-rendered
    dashboard, so the dashboard always reflects the same query (FR-010)."""
    signal_repo = SignalRepository(db)
    txn_repo = InsiderTransactionRepository(db)
    buyback_repo = BuybackEventRepository(db)
    cluster_repo = ClusterBuyEventRepository(db)

    signals, total = signal_repo.list(
        notable_only=notable_only,
        signal_type=signal_type,
        since=since,
        limit=limit,
        offset=offset,
    )

    items = []
    for signal in signals:
        underlying, _record = _resolve_signal(signal, txn_repo, buyback_repo, cluster_repo)
        items.append(
            {
                "id": str(signal.id),
                "signal_type": signal.signal_type,
                "is_notable": signal.is_notable,
                "is_discretionary": signal.is_discretionary,
                "notification_status": signal.notification_status,
                **underlying,
            }
        )

    return {"items": items, "total": total}


@router.get("/api/signals")
def list_signals(
    request: Request,
    notable_only: bool = True,
    signal_type: str | None = None,
    since: date | None = None,
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
) -> dict:
    return query_signals(
        request.app.state.db,
        notable_only=notable_only,
        signal_type=signal_type,
        since=since,
        limit=limit,
        offset=offset,
    )


@router.get("/api/signals/{signal_id}")
def get_signal(signal_id: str, request: Request) -> dict:
    db = request.app.state.db
    signal_repo = SignalRepository(db)
    txn_repo = InsiderTransactionRepository(db)
    buyback_repo = BuybackEventRepository(db)
    cluster_repo = ClusterBuyEventRepository(db)

    signal = signal_repo.get(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")

    underlying, record = _resolve_signal(signal, txn_repo, buyback_repo, cluster_repo)

    return {
        "id": str(signal.id),
        "signal_type": signal.signal_type,
        "is_notable": signal.is_notable,
        "is_discretionary": signal.is_discretionary,
        "is_superseded": signal.is_superseded,
        "notification_status": signal.notification_status,
        "evaluated_threshold_snapshot": signal.evaluated_threshold_snapshot,
        **underlying,
        "record": record.model_dump(mode="json") if record else None,
    }
