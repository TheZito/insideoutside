import argparse
import logging

import uvicorn

from insideoutside.config import Config
from insideoutside.scheduler.scheduler import create_scheduler
from insideoutside.storage.db import Database
from insideoutside.web.app import create_app

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
