import argparse
import json
from decimal import Decimal

from insideoutside.config import Config
from insideoutside.domain.threshold_configuration import ThresholdConfiguration
from insideoutside.storage.db import Database
from insideoutside.storage.repositories.threshold_repo import (
    ThresholdConfigurationRepository,
)


def _fmt_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(value.to_integral_value())
    return str(value)


def _serialize(config: ThresholdConfiguration) -> dict:
    return {
        "min_insider_buy_value": _fmt_decimal(config.min_insider_buy_value),
        "min_notable_role_buy_value": _fmt_decimal(config.min_notable_role_buy_value),
        "notable_filer_roles": config.notable_filer_roles,
        "min_buyback_amount": _fmt_decimal(config.min_buyback_amount),
        "cluster_window_days": config.cluster_window_days,
        "min_cluster_filer_count": config.min_cluster_filer_count,
    }


def run_thresholds(args: argparse.Namespace, config: Config) -> int:
    with Database(config.db_path) as db:
        repo = ThresholdConfigurationRepository(db)

        if args.thresholds_command == "show":
            print(json.dumps(_serialize(repo.get())))
            return 0

        if args.thresholds_command == "set":
            current = repo.get()
            new_config = ThresholdConfiguration(
                min_insider_buy_value=(
                    Decimal(args.min_insider_buy_value)
                    if args.min_insider_buy_value is not None
                    else current.min_insider_buy_value
                ),
                min_notable_role_buy_value=(
                    Decimal(args.min_notable_role_buy_value)
                    if args.min_notable_role_buy_value is not None
                    else current.min_notable_role_buy_value
                ),
                notable_filer_roles=(
                    [r.strip() for r in args.notable_filer_roles.split(",") if r.strip()]
                    if args.notable_filer_roles is not None
                    else current.notable_filer_roles
                ),
                min_buyback_amount=(
                    Decimal(args.min_buyback_amount)
                    if args.min_buyback_amount is not None
                    else current.min_buyback_amount
                ),
                cluster_window_days=(
                    args.cluster_window_days
                    if args.cluster_window_days is not None
                    else current.cluster_window_days
                ),
                min_cluster_filer_count=(
                    args.min_cluster_filer_count
                    if args.min_cluster_filer_count is not None
                    else current.min_cluster_filer_count
                ),
            )
            updated = repo.set(new_config)
            print(json.dumps(_serialize(updated)))
            return 0

        return 2
