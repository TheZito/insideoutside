from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

FilerRole = Literal["officer", "director", "ten_percent_owner", "other"]

# Defaults per spec.md Assumptions.
DEFAULT_MIN_INSIDER_BUY_VALUE = Decimal("1000000")
DEFAULT_MIN_NOTABLE_ROLE_BUY_VALUE = Decimal("100000")
DEFAULT_MIN_BUYBACK_AMOUNT = Decimal("50000000")
DEFAULT_NOTABLE_FILER_ROLES: list[FilerRole] = ["officer", "director"]
DEFAULT_CLUSTER_WINDOW_DAYS = 14
DEFAULT_MIN_CLUSTER_FILER_COUNT = 2


class ThresholdConfiguration(BaseModel):
    """Singleton notability threshold configuration. See data-model.md.

    Two dollar thresholds apply to insider buys, chosen by filer role: a filer
    whose role is in `notable_filer_roles` (officer/director by default) must
    clear `min_notable_role_buy_value`; everyone else must clear the higher
    `min_insider_buy_value`. Role alone is never sufficient -- the amount always
    matters too (see spec.md Assumptions).
    """

    id: UUID = Field(default_factory=uuid4)
    min_insider_buy_value: Decimal = DEFAULT_MIN_INSIDER_BUY_VALUE
    min_notable_role_buy_value: Decimal = DEFAULT_MIN_NOTABLE_ROLE_BUY_VALUE
    notable_filer_roles: list[FilerRole] = Field(
        default_factory=lambda: list(DEFAULT_NOTABLE_FILER_ROLES)
    )
    min_buyback_amount: Decimal = DEFAULT_MIN_BUYBACK_AMOUNT
    cluster_window_days: int = DEFAULT_CLUSTER_WINDOW_DAYS
    min_cluster_filer_count: int = DEFAULT_MIN_CLUSTER_FILER_COUNT

    @field_validator("min_insider_buy_value", "min_notable_role_buy_value", "min_buyback_amount")
    @classmethod
    def _must_be_non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("threshold amounts must be non-negative")
        return value

    @field_validator("cluster_window_days")
    @classmethod
    def _window_must_be_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("cluster_window_days must be at least 1")
        return value

    @field_validator("min_cluster_filer_count")
    @classmethod
    def _min_filer_count_must_be_at_least_two(cls, value: int) -> int:
        if value < 2:
            raise ValueError(
                "min_cluster_filer_count must be at least 2 (a cluster of one filer isn't a cluster)"
            )
        return value

    def threshold_for_role(self, role: FilerRole) -> Decimal:
        if role in self.notable_filer_roles:
            return self.min_notable_role_buy_value
        return self.min_insider_buy_value
