import argparse
import json

from insideoutside.config import Config
from insideoutside.ingestion.orchestrator import run_ingest as _run_ingest_orchestrator
from insideoutside.storage.db import Database


def run_ingest(args: argparse.Namespace, config: Config) -> int:
    with Database(config.db_path) as db:
        summary = _run_ingest_orchestrator(db, source=args.source, fixture_path=args.fixture)
    for result in summary["results"]:
        print(json.dumps(result))
    return 0
