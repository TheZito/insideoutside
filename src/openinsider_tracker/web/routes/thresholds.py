from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ValidationError

from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration
from openinsider_tracker.storage.repositories.threshold_repo import (
    ThresholdConfigurationRepository,
)

router = APIRouter()


class ThresholdUpdateRequest(BaseModel):
    """All fields are optional: an omitted field keeps its current value,
    mirroring the CLI's `thresholds set` behavior rather than forcing every PUT
    to resupply every threshold across all three signal types."""

    min_insider_buy_value: Decimal | None = None
    min_notable_role_buy_value: Decimal | None = None
    notable_filer_roles: list[str] | None = None
    min_buyback_amount: Decimal | None = None
    cluster_window_days: int | None = None
    min_cluster_filer_count: int | None = None


def _to_response(config: ThresholdConfiguration) -> dict:
    return {
        "min_insider_buy_value": float(config.min_insider_buy_value),
        "min_notable_role_buy_value": float(config.min_notable_role_buy_value),
        "notable_filer_roles": config.notable_filer_roles,
        "min_buyback_amount": float(config.min_buyback_amount),
        "cluster_window_days": config.cluster_window_days,
        "min_cluster_filer_count": config.min_cluster_filer_count,
    }


@router.get("/api/thresholds")
def get_thresholds(request: Request) -> dict:
    repo = ThresholdConfigurationRepository(request.app.state.db)
    return _to_response(repo.get())


@router.put("/api/thresholds")
def update_thresholds(request: Request, body: ThresholdUpdateRequest) -> dict:
    repo = ThresholdConfigurationRepository(request.app.state.db)
    current = repo.get()
    try:
        config = ThresholdConfiguration(
            min_insider_buy_value=body.min_insider_buy_value
            if body.min_insider_buy_value is not None
            else current.min_insider_buy_value,
            min_notable_role_buy_value=body.min_notable_role_buy_value
            if body.min_notable_role_buy_value is not None
            else current.min_notable_role_buy_value,
            notable_filer_roles=body.notable_filer_roles
            if body.notable_filer_roles is not None
            else current.notable_filer_roles,
            min_buyback_amount=body.min_buyback_amount
            if body.min_buyback_amount is not None
            else current.min_buyback_amount,
            cluster_window_days=body.cluster_window_days
            if body.cluster_window_days is not None
            else current.cluster_window_days,
            min_cluster_filer_count=body.min_cluster_filer_count
            if body.min_cluster_filer_count is not None
            else current.min_cluster_filer_count,
        )
    except (ValidationError, InvalidOperation) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    updated = repo.set(config)
    return _to_response(updated)
