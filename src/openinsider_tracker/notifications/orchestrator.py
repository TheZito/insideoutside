import logging
from collections.abc import Callable

from openinsider_tracker.config import Config
from openinsider_tracker.notifications.composer import compose_signal_email
from openinsider_tracker.notifications.mailer import EmailSendError, send_email
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.repositories.buyback_repo import BuybackEventRepository
from openinsider_tracker.storage.repositories.cluster_buy_repo import ClusterBuyEventRepository
from openinsider_tracker.storage.repositories.insider_transaction_repo import (
    InsiderTransactionRepository,
)
from openinsider_tracker.storage.repositories.signal_repo import SignalRepository

logger = logging.getLogger(__name__)


def run_notify(
    db: Database,
    config: Config,
    *,
    send_email_fn: Callable = send_email,
) -> dict:
    """FR-011/012/013: send one email per pending notable signal; never send a
    duplicate for an already-notified signal; a failed send marks the signal
    failed but never removes it from the dashboard."""
    signal_repo = SignalRepository(db)
    txn_repo = InsiderTransactionRepository(db)
    buyback_repo = BuybackEventRepository(db)
    cluster_repo = ClusterBuyEventRepository(db)

    dashboard_base_url = f"http://{config.host}:{config.port}"
    sent = 0
    failed = 0

    for signal in signal_repo.list_pending_notifications():
        subject, body = compose_signal_email(
            signal,
            txn_repo=txn_repo,
            buyback_repo=buyback_repo,
            cluster_repo=cluster_repo,
            dashboard_base_url=dashboard_base_url,
        )
        try:
            send_email_fn(config, to=config.notify_email_to, subject=subject, body=body)
        except EmailSendError:
            logger.exception("Failed to send notification for signal %s", signal.id)
            signal.transition_notification("failed")
            signal_repo.save(signal)
            failed += 1
            continue

        signal.transition_notification("sent")
        signal_repo.save(signal)
        sent += 1

    return {"sent": sent, "failed": failed}
