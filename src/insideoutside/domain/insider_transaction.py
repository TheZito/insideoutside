from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

FilerRole = Literal["officer", "director", "ten_percent_owner", "other"]
TransactionType = Literal["buy", "sell"]
Source = Literal["sec_edgar", "openinsider"]


class InsiderTransaction(BaseModel):
    """A single disclosed trade by a company insider. See data-model.md."""

    model_config = ConfigDict(frozen=False)

    id: UUID = Field(default_factory=uuid4)
    company_name: str
    ticker: str | None = None
    cik: str
    filer_name: str
    filer_id: str | None = None
    filer_role: FilerRole
    transaction_type: TransactionType
    transaction_code: str
    is_discretionary: bool
    share_count: Decimal
    price_per_share: Decimal | None = None
    transaction_date: date
    filing_date: date
    source: Source
    source_ref: str
    source_url: str
    fetched_at: datetime
    superseded_by_id: UUID | None = None

    @property
    def total_value(self) -> Decimal | None:
        if self.price_per_share is None:
            return None
        return self.share_count * self.price_per_share
