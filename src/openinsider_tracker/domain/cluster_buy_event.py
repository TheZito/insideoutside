from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class ClusterBuyEvent(BaseModel):
    """A detected group of discretionary buys by different insiders at the same
    company within a window. See data-model.md."""

    id: UUID = Field(default_factory=uuid4)
    company_name: str
    ticker: str | None = None
    cik: str
    window_start: date
    window_end: date
    distinct_filer_count: int
    total_value: Decimal
    contributing_transaction_ids: list[UUID]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("distinct_filer_count")
    @classmethod
    def _must_be_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("distinct_filer_count must be non-negative")
        return value

    @model_validator(mode="after")
    def _window_end_not_before_start(self) -> "ClusterBuyEvent":
        if self.window_end < self.window_start:
            raise ValueError("window_end must not be before window_start")
        return self
