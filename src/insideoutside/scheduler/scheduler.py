import logging

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler

from insideoutside.config import Config
from insideoutside.ingestion.orchestrator import run_ingest
from insideoutside.notifications.orchestrator import run_notify
from insideoutside.storage.db import Database

logger = logging.getLogger(__name__)


def _run_poll_cycle(config: Config) -> None:
    """One ingest -> classify -> notify cycle. Runs in APScheduler's own worker
    thread, off the FastAPI event loop (research.md §5), so a slow/blocking
    network fetch never stalls dashboard requests. Each phase's own error
    handling (FR-015, FR-013) means a failure here is already logged by the
    phase that raised it; this wrapper just guards against wiring bugs."""
    try:
        with Database(config.db_path) as db:
            ingest_summary = run_ingest(db, source="all")
            logger.info("Scheduled ingest complete: %s", ingest_summary)

            from argparse import Namespace

            from insideoutside.cli.commands.classify import run_classify

            run_classify(Namespace(reclassify=False), config)

            notify_summary = run_notify(db, config)
            logger.info("Scheduled notify complete: %s", notify_summary)
    except Exception:
        logger.exception("Scheduled poll cycle failed")


def create_scheduler(config: Config) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(executors={"default": ThreadPoolExecutor(max_workers=1)})
    scheduler.add_job(
        _run_poll_cycle,
        "interval",
        minutes=config.poll_interval_minutes,
        args=[config],
        id="poll_cycle",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
