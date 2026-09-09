from openinsider_tracker.domain.signal import Signal
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)


def compose_signal_email(
    signal: Signal,
    *,
    txn_repo: InsiderTransactionRepository,
    buyback_repo: BuybackEventRepository,
    cluster_repo: ClusterBuyEventRepository,
    dashboard_base_url: str,
) -> tuple[str, str]:
    """Build (subject, body) for a notable signal's notification email (FR-011)."""
    dashboard_link = f"{dashboard_base_url}/api/signals/{signal.id}"

    if signal.signal_type == "insider_transaction":
        record = txn_repo.get(signal.insider_transaction_id)
        value = f"${record.total_value:,.0f}" if record.total_value is not None else "unknown value"
        subject = f"[OpenInsider Tracker] {record.company_name}: insider buy {value}"
        body = (
            f"{record.filer_name} ({record.filer_role}) bought {record.share_count} shares "
            f"of {record.company_name} ({record.ticker or 'n/a'}) at {record.price_per_share} "
            f"on {record.transaction_date}.\n"
            f"Total value: {value}\n"
            f"Source: {record.source_url}\n"
            f"Dashboard: {dashboard_link}\n"
        )
    elif signal.signal_type == "buyback":
        record = buyback_repo.get(signal.buyback_event_id)
        subject = (
            f"[OpenInsider Tracker] {record.company_name}: "
            f"{record.disclosure_type} buyback ${record.amount:,.0f}"
        )
        body = (
            f"{record.company_name} ({record.ticker or 'n/a'}) disclosed a "
            f"{record.disclosure_type} buyback of ${record.amount:,.0f} on {record.disclosure_date}.\n"
            f"Source: {record.source_url}\n"
            f"Dashboard: {dashboard_link}\n"
        )
    else:
        record = cluster_repo.get(signal.cluster_buy_event_id)
        subject = (
            f"[OpenInsider Tracker] {record.company_name}: cluster buying "
            f"({record.distinct_filer_count} insiders, ${record.total_value:,.0f})"
        )
        body = (
            f"{record.distinct_filer_count} different insiders at {record.company_name} "
            f"({record.ticker or 'n/a'}) bought stock between {record.window_start} and "
            f"{record.window_end}, totaling ${record.total_value:,.0f}.\n"
            f"Dashboard: {dashboard_link}\n"
        )

    return subject, body
