import pytest
from pydantic import ValidationError

from insideoutside.domain.signal import Signal


def _valid_kwargs(**overrides):
    kwargs = dict(
        signal_type="insider_transaction",
        insider_transaction_id="11111111-1111-1111-1111-111111111111",
        buyback_event_id=None,
        is_notable=True,
        is_discretionary=True,
        is_superseded=False,
        evaluated_threshold_snapshot={"min_insider_buy_value": 1000000},
        notification_status="pending",
    )
    kwargs.update(overrides)
    return kwargs


def test_not_applicable_is_terminal_and_disallows_pending():
    signal = Signal(**_valid_kwargs(is_notable=False, notification_status="not_applicable"))
    with pytest.raises(ValueError):
        signal.transition_notification("pending")


def test_pending_can_transition_to_sent():
    signal = Signal(**_valid_kwargs())
    signal.transition_notification("sent")
    assert signal.notification_status == "sent"


def test_pending_can_transition_to_failed():
    signal = Signal(**_valid_kwargs())
    signal.transition_notification("failed")
    assert signal.notification_status == "failed"


def test_is_superseded_transitions_false_to_true_and_is_terminal():
    signal = Signal(**_valid_kwargs())
    signal.mark_superseded()
    assert signal.is_superseded is True
    with pytest.raises(ValueError):
        signal.mark_superseded()


def test_buyback_signal_has_null_is_discretionary():
    signal = Signal(
        **_valid_kwargs(
            signal_type="buyback",
            insider_transaction_id=None,
            buyback_event_id="22222222-2222-2222-2222-222222222222",
            is_discretionary=None,
        )
    )
    assert signal.is_discretionary is None


def test_invalid_notification_status_is_rejected():
    with pytest.raises(ValidationError):
        Signal(**_valid_kwargs(notification_status="bounced"))


def test_cluster_buy_signal_requires_cluster_buy_event_id():
    with pytest.raises(ValidationError):
        Signal(
            **_valid_kwargs(
                signal_type="cluster_buy",
                insider_transaction_id=None,
                buyback_event_id=None,
                cluster_buy_event_id=None,
                is_discretionary=None,
            )
        )


def test_cluster_buy_signal_with_event_id_is_valid_and_has_null_is_discretionary():
    signal = Signal(
        **_valid_kwargs(
            signal_type="cluster_buy",
            insider_transaction_id=None,
            buyback_event_id=None,
            cluster_buy_event_id="33333333-3333-3333-3333-333333333333",
            is_discretionary=None,
        )
    )
    assert signal.cluster_buy_event_id is not None
    assert signal.is_discretionary is None
