# Implementation Plan: Cluster Buying Detection

**Branch**: `002-cluster-buying-detection` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-cluster-buying-detection/spec.md`

## Summary

Extend the existing `insideoutside` codebase (specs/001-insider-buyback-tracker)
with a third signal type: a **cluster buy**, detected when two or more distinct
insiders at the same company each make a discretionary open-market buy within a
rolling window (default 14 days). Detection runs as an added step inside the
existing `classify` command, against `InsiderTransaction` rows 001 already
ingests — no new ingestion, no new service, no new dependency. Cluster signals
flow through the same `Signal`/dashboard/notification machinery already built for
the other two signal types.

## Technical Context

This feature adds to, and does not change, 001's Technical Context (Python 3.12,
FastAPI + Jinja2, SQLAlchemy + SQLite, single Docker Compose `app` service — see
specs/001-insider-buyback-tracker/plan.md for the full baseline). Nothing here
introduces a new dependency, a new container, or a new external data source.

**New surface area**: one new domain entity (`ClusterBuyEvent`), one new
classification module (grouping + threshold logic), one new repository, one
Alembic migration, and additive changes to the existing `Signal` model,
`ThresholdConfiguration`, the `/api/signals` and `/api/thresholds` routes, the
dashboard template, the email composer, and the `classify`/`thresholds` CLI
subcommands — all extending existing code paths rather than adding new ones.

**Identity for "distinct insider"**: uses `filer_name` (already captured) as the
identity key for v1, plus a new optional `filer_id` field (the SEC `rptOwnerCik`,
already present in the Form 4 XML 001 already parses but currently discarded) to
make that identity more reliable going forward. Falls back to name-matching when
`filer_id` is unavailable (e.g., OpenInsider-sourced candidates).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Test-First (NON-NEGOTIABLE) | tasks.md will sequence a failing test before each implementation task, same as 001 | PASS |
| II. Data Accuracy & Source Integrity | Every `ClusterBuyEvent` carries its contributing transaction ids, each of which already carries its own provenance (source, source_ref, fetched_at) from 001; no new external data source, so no new provenance surface to get wrong | PASS |
| III. Simplicity & YAGNI | Reuses the existing single-service architecture and SQLite; clustering uses a simple greedy same-company date-window grouping (documented in research.md) rather than a general interval-clustering algorithm, since the data volumes here are small | PASS |
| IV. CLI-First & Library-First Architecture | Detection + classification logic lives in `classification/cluster_buying.py`, invoked from the existing `classify` CLI subcommand — no new subcommand, no logic embedded directly in the web layer | PASS |
| V. Financial Safety & Human Oversight for Automated Trading | Not applicable — no trade-execution capability added; this only affects what counts as a notable *signal* | PASS (N/A) |
| Containerized Deployment | No new service; still one `app` container, one `docker-compose.yml` | PASS |
| Data Handling & Compliance Standards | No new external source, no new secret | PASS |

No violations — Complexity Tracking table omitted.

**Post-Design Re-check** (after Phase 1 data-model/contracts/quickstart): design
introduced one new table (`cluster_buy_events`) and additive columns on three
existing tables, all via a single migration — still no new service, no new
dependency. `ClusterBuyEvent`'s JSON-list storage of contributing transaction ids
(research.md §4) keeps referential bookkeeping simple rather than adding a join
table. Gate remains PASS.

## Project Structure

### Documentation (this feature)

```text
specs/002-cluster-buying-detection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (deltas against 001's contracts)
│   ├── cli-delta.md
│   └── api-delta.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root — additions/changes to the existing 001 tree)

```text
src/insideoutside/
├── domain/
│   ├── insider_transaction.py    # + optional filer_id field
│   ├── signal.py                 # + "cluster_buy" signal_type, cluster_buy_event_id
│   ├── threshold_configuration.py# + cluster_window_days, min_cluster_filer_count
│   └── cluster_buy_event.py      # NEW
├── classification/
│   ├── rules.py                  # unchanged (FR-012: existing classification untouched)
│   └── cluster_buying.py         # NEW: grouping (detection) + threshold check
├── ingestion/
│   └── sec_edgar_form4.py        # + parse rptOwnerCik into filer_id (additive)
├── storage/
│   ├── orm.py                    # + ClusterBuyEventORM, Signal.cluster_buy_event_id,
│   │                              #   InsiderTransactionORM.filer_id, new threshold columns
│   ├── migrations/versions/
│   │   └── 0003_cluster_buying.py  # NEW single migration for all of the above
│   └── repositories/
│       └── cluster_buy_repo.py   # NEW
├── cli/commands/
│   ├── classify.py               # + invoke cluster detection/classification pass
│   └── thresholds.py             # + --cluster-window-days, --min-cluster-filer-count
├── notifications/
│   └── composer.py               # + cluster_buy branch
└── web/
    ├── routes/signals.py         # + cluster_buy branch in the summary dispatcher
    ├── routes/thresholds.py      # + new fields in request/response
    └── templates/dashboard.html  # + cluster_buy badge styling

tests/
├── unit/classification/test_cluster_buying.py       # NEW
├── unit/domain/test_cluster_buy_event.py             # NEW
├── integration/classification/test_cluster_detection.py  # NEW
├── integration/storage/test_cluster_buy_repo.py      # NEW (or folded into existing repo test)
└── contract/test_cli_classify.py, test_api_signals.py, test_api_thresholds.py  # extended
```

**Structure Decision**: No new deployable unit, no new top-level package — this
is additive work inside the existing single Python project and single Docker
service from 001, consistent with Constitution Principle III (no new
infrastructure without a measured need) and FR-012 (existing behavior for the
other two signal types must not change).

## Complexity Tracking

*No constitution violations — table intentionally omitted.*
