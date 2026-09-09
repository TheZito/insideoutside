import argparse
import logging

import uvicorn

from openinsider_tracker.config import Config
from openinsider_tracker.scheduler.scheduler import create_scheduler
from openinsider_tracker.storage.db import Database
from openinsider_tracker.web.app import create_app

logger = logging.getLogger(__name__)


def run_serve(args: argparse.Namespace, config: Config) -> int:
    """Per contracts/cli.md: `migrate` MUST be run explicitly before the first
    `serve` (see quickstart.md) -- serve does not auto-migrate."""
    with Database(config.db_path) as db:
        app = create_app(db)

        scheduler = None
        if not args.no_scheduler:
            scheduler = create_scheduler(config)
            scheduler.start()
            logger.info(
                "Scheduler started: polling every %d minutes", config.poll_interval_minutes
            )

        try:
            uvicorn.run(app, host=args.host or config.host, port=args.port or config.port)
        finally:
            if scheduler is not None:
                scheduler.shutdown(wait=False)

    return 0
