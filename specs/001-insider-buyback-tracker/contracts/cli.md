# CLI Contract: openinsider_tracker

Invoked as `python -m openinsider_tracker <command> [options]` — automatically by
the in-process scheduler inside the single `app` container, or manually via
`docker compose exec app python -m openinsider_tracker <command>`. Text in/out per
Constitution Principle IV: options in, structured result to stdout, errors to
stderr with non-zero exit code.

## `migrate`

Applies any pending Alembic schema migrations to the SQLite database. Idempotent —
safe to run when there is nothing pending. Run once before the first `serve`, and
again after any upgrade that ships a schema change.

```text
python -m openinsider_tracker migrate
```

- Exit 0: database is up to date (whether or not any migration actually ran).
- Exit 1: a migration failed to apply; the database is left at its last successful
  revision (Alembic's own transactional guarantees), and the error is printed to
  stderr per Constitution Principle II (fail loudly, never partially/silently).

## `ingest`

Fetches new data from all configured sources and persists new/updated
`InsiderTransaction` and `BuybackEvent` records.

```text
python -m openinsider_tracker ingest [--source sec_edgar|openinsider|all] [--since DATE]
```

- Exit 0: ingestion completed (individual source failures are logged, not fatal,
  per FR-015's retry/backoff requirement).
- Exit 1: configuration error (e.g., missing required env var).
- stdout: JSON summary — `{"source": ..., "fetched": N, "new": N, "updated": N, "failed": N}` per source.

## `classify`

Evaluates un-classified (or, with `--reclassify`, all) records against the current
`ThresholdConfiguration` and creates/updates `Signal` rows.

```text
python -m openinsider_tracker classify [--reclassify]
```

- stdout: JSON summary — `{"evaluated": N, "notable": N}`.

## `notify`

Sends email notifications for `Signal` rows with `notification_status = pending`.

```text
python -m openinsider_tracker notify
```

- stdout: JSON summary — `{"sent": N, "failed": N}`.
- Never raises for individual send failures (FR-013); non-zero exit only on total
  configuration failure (e.g., unreachable SMTP relay for every attempt).

## `serve`

Starts the FastAPI dashboard/API and the in-process scheduler that periodically
runs `ingest` → `classify` → `notify` (used by the `app` container's entrypoint).

```text
python -m openinsider_tracker serve [--host 0.0.0.0] [--port 8000] [--no-scheduler]
```

`--no-scheduler` disables the background poll loop (useful for tests or when
driving `ingest`/`classify`/`notify` manually against a running dashboard).

## `thresholds`

Reads or updates the singleton `ThresholdConfiguration` (FR-014), independent of the
web API — usable for scripting/automation without the dashboard running.

```text
python -m openinsider_tracker thresholds show
python -m openinsider_tracker thresholds set --min-insider-buy-value 1000000
python -m openinsider_tracker thresholds set --min-notable-role-buy-value 100000
python -m openinsider_tracker thresholds set --notable-filer-roles officer,director
```

`--min-notable-role-buy-value` is the threshold applied when the filer's role is in
`notable_filer_roles`; `--min-insider-buy-value` applies to everyone else. Role
alone never makes a transaction notable (FR-004) — omitted flags keep their
current value.
