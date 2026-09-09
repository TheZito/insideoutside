import argparse
import json

from openinsider_tracker.config import Config
from openinsider_tracker.notifications.orchestrator import run_notify as _run_notify_orchestrator
from openinsider_tracker.storage.db import Database


def run_notify(args: argparse.Namespace, config: Config) -> int:
    with Database(config.db_path) as db:
        summary = _run_notify_orchestrator(db, config)
    print(json.dumps(summary))
    return 0
