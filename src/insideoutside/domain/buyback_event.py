from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

DisclosureType = Literal["authorized", "executed"]
Source = Literal["sec_edgar"]


class BuybackEvent(BaseModel):
    """A disclosed corporate stock repurchase action. See data-model.md."""

    id: UUID = Field(default_factory=uuid4)
    company_name: str
    ticker: str | None = None
    cik: str
    disclosure_type: DisclosureType
    amount: Decimal
    disclosure_date: date
    source: Source
    source_ref: str
    source_url: str
    fetched_at: datetime
    superseded_by_id: UUID | None = None
