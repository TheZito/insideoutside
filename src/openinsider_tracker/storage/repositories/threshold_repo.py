from __future__ import annotations

from openinsider_tracker.domain.threshold_configuration import ThresholdConfiguration
from openinsider_tracker.storage.db import Database
from openinsider_tracker.storage.orm import ThresholdConfigurationORM

_SINGLETON_ID = "00000000-0000-0000-0000-000000000001"


def _to_domain(row: ThresholdConfigurationORM) -> ThresholdConfiguration:
    # ORM column names match the domain model's field names 1:1, so pydantic's
    # from_attributes mode can build it directly.
    return ThresholdConfiguration.model_validate(row, from_attributes=True)


class ThresholdConfigurationRepository:
    """Manages the single ThresholdConfiguration row (v1 is single-user)."""

    def __init__(self, db: Database):
        self._db = db

    def get(self) -> ThresholdConfiguration:
        with self._db.session() as session:
            row = session.get(ThresholdConfigurationORM, _SINGLETON_ID)
            if row is None:
                config = ThresholdConfiguration(id=_SINGLETON_ID)
                row = ThresholdConfigurationORM(
                    id=_SINGLETON_ID,
                    min_insider_buy_value=config.min_insider_buy_value,
                    min_notable_role_buy_value=config.min_notable_role_buy_value,
                    notable_filer_roles=config.notable_filer_roles,
                    min_buyback_amount=config.min_buyback_amount,
                    cluster_window_days=config.cluster_window_days,
                    min_cluster_filer_count=config.min_cluster_filer_count,
                )
                session.add(row)
                session.commit()
                session.refresh(row)
            return _to_domain(row)

    def set(self, config: ThresholdConfiguration) -> ThresholdConfiguration:
        with self._db.session() as session:
            row = session.get(ThresholdConfigurationORM, _SINGLETON_ID)
            if row is None:
                row = ThresholdConfigurationORM(id=_SINGLETON_ID)
                session.add(row)
            row.min_insider_buy_value = config.min_insider_buy_value
            row.min_notable_role_buy_value = config.min_notable_role_buy_value
            row.notable_filer_roles = config.notable_filer_roles
            row.min_buyback_amount = config.min_buyback_amount
            row.cluster_window_days = config.cluster_window_days
            row.min_cluster_filer_count = config.min_cluster_filer_count
            session.commit()
            session.refresh(row)
            return _to_domain(row)
