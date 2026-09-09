from decimal import Decimal

import pytest
from pydantic import ValidationError

from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration


def test_defaults_match_spec_assumptions():
    config = ThresholdConfiguration()
    assert config.min_insider_buy_value == Decimal("1000000")
    assert config.min_notable_role_buy_value == Decimal("100000")
    assert config.min_buyback_amount == Decimal("50000000")
    assert set(config.notable_filer_roles) == {"officer", "director"}
    assert config.cluster_window_days == 14
    assert config.min_cluster_filer_count == 2


def test_negative_min_insider_buy_value_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(min_insider_buy_value=Decimal("-1"))


def test_negative_min_notable_role_buy_value_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(min_notable_role_buy_value=Decimal("-1"))


def test_negative_min_buyback_amount_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(min_buyback_amount=Decimal("-1"))


def test_threshold_for_role_uses_role_specific_value_for_notable_roles():
    config = ThresholdConfiguration(
        min_insider_buy_value=Decimal("1000000"),
        min_notable_role_buy_value=Decimal("100000"),
        notable_filer_roles=["director"],
    )
    assert config.threshold_for_role("director") == Decimal("100000")
    assert config.threshold_for_role("other") == Decimal("1000000")


def test_empty_notable_filer_roles_is_allowed_for_amount_only_mode():
    config = ThresholdConfiguration(notable_filer_roles=[])
    assert config.notable_filer_roles == []


def test_invalid_filer_role_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(notable_filer_roles=["ceo_of_everything"])


def test_cluster_window_days_below_one_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(cluster_window_days=0)


def test_min_cluster_filer_count_below_two_is_rejected():
    with pytest.raises(ValidationError):
        ThresholdConfiguration(min_cluster_filer_count=1)
