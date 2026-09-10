import argparse
import json

from insideoutside.config import Config
from insideoutside.notifications.orchestrator import run_notify as _run_notify_orchestrator
from insideoutside.storage.db import Database


def run_notify(args: argparse.Namespace, config: Config) -> int:
    with Database(config.db_path) as db:
        summary = _run_notify_orchestrator(db, config)
    print(json.dumps(summary))
    return 0
