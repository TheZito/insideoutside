# Implementation Plan: Insider Trading & Buyback Signal Tracker

**Branch**: `001-insider-buyback-tracker` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-insider-buyback-tracker/spec.md`

## Summary

Build a personal, containerized system that polls SEC EDGAR (Form 4 filings and
full-text search for buyback disclosures) and an OpenInsider-style aggregated feed,
classifies transactions/buybacks as "notable" against configurable dollar
thresholds, de-duplicates across sources, stores them with full provenance, renders
them on a dashboard, and emails the user when a new notable signal appears. Core
detection/classification/notification logic lives in an independently testable
Python library with CLI entry points (Constitution Principle IV); the same
application process runs a FastAPI dashboard/API and an in-process scheduler that
periodically invokes that library, persisting to a SQLite file on a mounted volume.
The whole system is a single container, brought up with `docker compose up`
(Constitution: Containerized Deployment).

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: FastAPI + Jinja2 (dashboard/API), SQLAlchemy 2.x (ORM),
httpx (HTTP client for SEC EDGAR / OpenInsider-style fetches), APScheduler (running
in a background thread inside the app process for recurring polls), Pydantic
(validation of parsed filing data), a stdlib-`smtplib`-based mailer (no external
email service dependency for v1)

**Storage**: SQLite (a single file on a Docker-managed named volume, holding insider
transactions, buyback events, signals, threshold configuration, and notification
state; sufficient because exactly one process reads/writes it)

**Testing**: pytest (unit, integration against a disposable temp-file SQLite
database, and contract tests for the CLI and the dashboard's JSON API)

**Target Platform**: Linux containers via Docker / Docker Compose (host-OS agnostic)

**Project Type**: Single Python project — library-first core with CLI entry points,
plus a thin web service consuming the same library (not a separate frontend/backend
split; there is no client-side app framework for v1)

**Performance Goals**: Dashboard renders ≥90 days of signal history in <3s (SC-003);
ingestion poll runs hourly by default (configurable, not real-time streaming)

**Constraints**: Must run entirely via `docker compose up` with no host-installed
runtime/DB (Constitution: Containerized Deployment); must respect upstream rate
limits/robots.txt (Constitution: Data Handling & Compliance Standards); single-user,
no auth system required (spec Assumptions)

**Scale/Scope**: Single user; expected volume on the order of tens to low hundreds
of notable signals per week across all tracked filers/companies; multi-year
historical retention with no anticipated performance concern at this scale

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Test-First (NON-NEGOTIABLE) | tasks.md (next phase) will sequence a failing test before each implementation task for ingestion, classification, notification, and API/CLI behavior | PASS (enforced at task-generation, not architecture) |
| II. Data Accuracy & Source Integrity | data-model.md defines provenance fields (source, source reference, fetched_at) on every ingested record; parse/validation failures raise rather than silently coerce (Pydantic models, no default-on-error) | PASS |
| III. Simplicity & YAGNI | Single Python codebase, a single container — the dashboard, the scheduled ingest/classify/notify loop, and storage (SQLite, in-process) all run together, since there is no independent-scaling, process-isolation, or multi-writer need for a single-user tool. Two earlier drafts of this plan (a separate worker service, then a separate Postgres service) were dropped once neither was backed by a measured, current need — see research.md §5/§8 for the reasoning trail. |
| IV. CLI-First & Library-First Architecture | Ingestion, classification, and notification are implemented in `src/insideoutside/` as a library with CLI subcommands (`ingest`, `classify`, `notify`); both the FastAPI app and its internal scheduler call this library rather than duplicating logic, and the same commands are runnable manually via `docker compose exec app ...` | PASS |
| V. Financial Safety & Human Oversight for Automated Trading | Not applicable — this feature has no trade-execution capability (spec FR-017); no brokerage credentials or order logic exist in this plan | PASS (N/A, explicitly excluded) |
| Containerized Deployment | `docker-compose.yml` defines a single `app` service with a named volume for the SQLite file; no host-installed dependency required to build/run/test | PASS |
| Data Handling & Compliance Standards | Research (Phase 0) documents rate-limit/backoff approach per source; SMTP credentials supplied via env file, not committed | PASS |

No violations requiring justification — Complexity Tracking table is omitted.

**Post-Design Re-check** (after Phase 1 data-model/contracts/quickstart): the
design introduced no new services, dependencies, or deviations beyond what's listed
above — still a single container, still one library-first Python codebase,
provenance and validation rules are explicit in data-model.md (storage-engine
agnostic, so the SQLite choice required no data-model changes), and no
trading/brokerage surface was added. Gate remains PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-insider-buyback-tracker/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli.md
│   └── api.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/
└── insideoutside/
    ├── domain/            # Entities: InsiderTransaction, BuybackEvent, Signal, ThresholdConfig
    ├── ingestion/         # SEC EDGAR Form 4 client, EDGAR full-text (buyback) client,
    │                      # OpenInsider-style client, shared retry/backoff + de-dup logic
    ├── classification/    # Notability rules engine (thresholds, discretionary vs. routine)
    ├── notifications/     # Email composition + sending, sent-state tracking
    ├── storage/           # SQLAlchemy models + repositories over SQLite; lightweight
    │                      # schema migrations (Alembic), applied via an explicit
    │                      # `migrate` CLI subcommand (see contracts/cli.md), not
    │                      # automatically at startup
    ├── scheduler/         # APScheduler setup: runs ingest/classify/notify on an interval
    │                      # inside the app process's background thread
    ├── cli/               # `python -m insideoutside` subcommands: ingest, classify,
    │                      # notify, serve (starts the FastAPI app + scheduler)
    └── web/               # FastAPI app: JSON API + Jinja2 dashboard templates (reads only)

tests/
├── unit/                  # domain + classification logic, no I/O
├── integration/           # ingestion clients (against recorded fixtures), storage, notify
└── contract/              # CLI command contracts, web JSON API contracts

Dockerfile                  # single image: runs `serve`, which starts the API,
                             # dashboard, and the in-process scheduler together
docker-compose.yml           # a single `app` service, with a named volume for the
                             # SQLite file
.env.example                 # documents required env vars (SMTP creds, thresholds,
                              # DB file path override)
```

**Structure Decision**: Single Python project, single deployable service (no
frontend/backend split, no separate worker or database service — the dashboard is
server-rendered by the same process that runs the scheduler and exposes the JSON
API). Core logic is isolated under `domain/`, `ingestion/`, `classification/`, and
`notifications/` so it is independently unit-testable without touching SQLite or the
network, per Constitution Principle IV; `storage/`, `scheduler/`, and `web/` are the
only layers that touch the database, the background loop, or HTTP serving, and
`cli/` is the single entry point both the automated schedule and any manual operator
use to invoke the library.

## Complexity Tracking

*No constitution violations — table intentionally omitted.*
