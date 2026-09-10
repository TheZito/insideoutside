from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

SignalType = Literal["insider_transaction", "buyback", "cluster_buy"]
NotificationStatus = Literal["not_applicable", "pending", "sent", "failed"]

_VALID_NOTIFICATION_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"sent", "failed"},
    "sent": set(),
    "failed": set(),
    "not_applicable": set(),
}


class Signal(BaseModel):
    """Wraps an InsiderTransaction or BuybackEvent once classified. See data-model.md."""

    id: UUID = Field(default_factory=uuid4)
    signal_type: SignalType
    insider_transaction_id: UUID | None = None
    buyback_event_id: UUID | None = None
    cluster_buy_event_id: UUID | None = None
    is_notable: bool
    is_discretionary: bool | None = None
    is_superseded: bool = False
    evaluated_threshold_snapshot: dict[str, Any]
    notification_status: NotificationStatus
    notified_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _check_signal_type_linkage(self) -> "Signal":
        if self.signal_type == "insider_transaction" and self.insider_transaction_id is None:
            raise ValueError("insider_transaction_id is required when signal_type=insider_transaction")
        if self.signal_type == "buyback" and self.buyback_event_id is None:
            raise ValueError("buyback_event_id is required when signal_type=buyback")
        if self.signal_type == "cluster_buy" and self.cluster_buy_event_id is None:
            raise ValueError("cluster_buy_event_id is required when signal_type=cluster_buy")
        return self

    def transition_notification(self, new_status: NotificationStatus) -> None:
        allowed = _VALID_NOTIFICATION_TRANSITIONS.get(self.notification_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition notification_status from "
                f"{self.notification_status!r} to {new_status!r}"
            )
        self.notification_status = new_status
        if new_status == "sent":
            self.notified_at = datetime.now(UTC)

    def mark_superseded(self) -> None:
        if self.is_superseded:
            raise ValueError("Signal is already superseded")
        self.is_superseded = True
