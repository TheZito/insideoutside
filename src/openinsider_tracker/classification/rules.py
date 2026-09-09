from dataclasses import dataclass

from openinsider_tracker.domain.buyback_event import BuybackEvent
from openinsider_tracker.domain.insider_transaction import InsiderTransaction
from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration


@dataclass(frozen=True)
class ClassificationResult:
    is_notable: bool


def classify_insider_transaction(
    txn: InsiderTransaction, config: ThresholdConfiguration
) -> ClassificationResult:
    """FR-004, FR-006: notable if it's a discretionary buy whose dollar value clears
    the threshold for its filer's role. A notable role (officer/director by
    default) gets a lower bar (`min_notable_role_buy_value`); everyone else must
    clear the higher `min_insider_buy_value`. Role alone is never sufficient --
    amount always matters too. Routine/non-discretionary transactions and sells
    are never notable (edge case, spec Assumptions)."""
    if txn.transaction_type != "buy":
        return ClassificationResult(is_notable=False)
    if not txn.is_discretionary:
        return ClassificationResult(is_notable=False)
    if txn.total_value is None:
        return ClassificationResult(is_notable=False)

    threshold = config.threshold_for_role(txn.filer_role)
    return ClassificationResult(is_notable=txn.total_value >= threshold)


def classify_buyback(
    event: BuybackEvent, config: ThresholdConfiguration
) -> ClassificationResult:
    """FR-005: notable if the disclosed/executed amount is at/above the threshold."""
    return ClassificationResult(is_notable=event.amount >= config.min_buyback_amount)
