import argparse
import json
import logging
import sys

from insideoutside.config import load_config
from insideoutside.storage.migrations import apply_migrations

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="insideoutside")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("migrate", help="Apply pending database schema migrations")

    ingest_parser = subparsers.add_parser("ingest", help="Fetch new data from sources")
    ingest_parser.add_argument(
        "--source", choices=["sec_edgar", "openinsider", "all"], default="all"
    )
    ingest_parser.add_argument("--fixture", help="Path to a local fixture file, for testing")

    subparsers.add_parser("classify", help="Classify ingested records as notable or not").add_argument(
        "--reclassify", action="store_true", help="Re-evaluate all existing records"
    )

    subparsers.add_parser("notify", help="Send email notifications for pending notable signals")

    serve_parser = subparsers.add_parser("serve", help="Run the dashboard/API and scheduler")
    serve_parser.add_argument("--host", default=None)
    serve_parser.add_argument("--port", type=int, default=None)
    serve_parser.add_argument("--no-scheduler", action="store_true")

    thresholds_parser = subparsers.add_parser("thresholds", help="View or update thresholds")
    thresholds_sub = thresholds_parser.add_subparsers(dest="thresholds_command", required=True)
    thresholds_sub.add_parser("show")
    set_parser = thresholds_sub.add_parser("set")
    set_parser.add_argument("--min-insider-buy-value", type=str, default=None)
    set_parser.add_argument("--min-notable-role-buy-value", type=str, default=None)
    set_parser.add_argument("--min-buyback-amount", type=str, default=None)
    set_parser.add_argument("--cluster-window-days", type=int, default=None)
    set_parser.add_argument("--min-cluster-filer-count", type=int, default=None)
    set_parser.add_argument("--notable-filer-roles", type=str, default=None, help="comma-separated")

    return parser


def _cmd_migrate(args: argparse.Namespace, config) -> int:
    apply_migrations(config.db_path)
    print(json.dumps({"status": "ok"}))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "migrate":
        return _cmd_migrate(args, config)
    if args.command == "ingest":
        from insideoutside.cli.commands.ingest import run_ingest

        return run_ingest(args, config)
    if args.command == "classify":
        from insideoutside.cli.commands.classify import run_classify

        return run_classify(args, config)
    if args.command == "notify":
        from insideoutside.cli.commands.notify import run_notify

        return run_notify(args, config)
    if args.command == "thresholds":
        from insideoutside.cli.commands.thresholds import run_thresholds

        return run_thresholds(args, config)
    if args.command == "serve":
        from insideoutside.cli.commands.serve import run_serve

        return run_serve(args, config)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
