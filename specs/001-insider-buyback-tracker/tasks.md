# Tasks: Insider Trading & Buyback Signal Tracker

**Input**: Design documents from `/specs/001-insider-buyback-tracker/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included and REQUIRED, not optional — Constitution Principle I (Test-First,
NON-NEGOTIABLE) mandates a failing test before implementation for all data
ingestion, parsing, and business logic in this project.

**Organization**: Tasks are grouped by user story (from spec.md) to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- File paths are relative to the repository root and match plan.md's Project Structure

## Path Conventions

Single Python project, single deployable service (per plan.md):
`src/openinsider_tracker/{domain,ingestion,classification,notifications,storage,scheduler,cli,web}`,
`tests/{unit,integration,contract,fixtures}`, root `Dockerfile` + `docker-compose.yml`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure per plan.md: `src/openinsider_tracker/{domain,ingestion,classification,notifications,storage/repositories,scheduler,cli,web/routes,web/templates}`, `tests/{unit/domain,unit/classification,integration/ingestion,integration/storage,integration/notifications,integration/classification,contract,fixtures}`
- [X] T002 Initialize Python project in `pyproject.toml` with dependencies: fastapi, uvicorn, sqlalchemy, alembic, httpx, apscheduler, pydantic, jinja2, pytest, pytest-asyncio
- [X] T003 [P] Configure ruff lint/format rules in `pyproject.toml`
- [X] T004 [P] Create `.env.example` documenting `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `NOTIFY_EMAIL_TO`, `DB_PATH`, `POLL_INTERVAL_MINUTES`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain models, storage, and scaffolding that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (write FIRST, ensure they FAIL before implementation)

- [X] T005 [P] Unit test: `InsiderTransaction` validation (required fields; `total_value = share_count * price_per_share`; rejects missing `transaction_date`) in `tests/unit/domain/test_insider_transaction.py`
- [X] T006 [P] Unit test: `BuybackEvent` validation (required fields; `disclosure_type` enum) in `tests/unit/domain/test_buyback_event.py`
- [X] T007 [P] Unit test: `Signal` state transitions (`not_applicable` terminal; `pending → sent/failed`; `is_superseded` false→true terminal) in `tests/unit/domain/test_signal.py`
- [X] T008 [P] Unit test: `ThresholdConfiguration` defaults (`min_insider_buy_value=1_000_000`, `min_buyback_amount=50_000_000`) and rejects negative values in `tests/unit/domain/test_threshold_configuration.py`
- [X] T009 [P] Integration test: repositories perform create/get/list/upsert-by-`source_ref` round-trip against a temp-file SQLite database, with the schema brought up by running the `migrate` CLI subcommand as test setup (not `Base.metadata.create_all`), in `tests/integration/storage/test_repositories.py`

### Implementation for Foundational

- [X] T010 [P] Implement `InsiderTransaction` domain model in `src/openinsider_tracker/domain/insider_transaction.py` (makes T005 pass)
- [X] T011 [P] Implement `BuybackEvent` domain model in `src/openinsider_tracker/domain/buyback_event.py` (makes T006 pass)
- [X] T012 [P] Implement `Signal` domain model in `src/openinsider_tracker/domain/signal.py` (makes T007 pass)
- [X] T013 [P] Implement `ThresholdConfiguration` domain model with defaults in `src/openinsider_tracker/domain/threshold_configuration.py` (makes T008 pass)
- [X] T014 Implement SQLAlchemy engine/session/Base setup (SQLite file path from config) in `src/openinsider_tracker/storage/db.py`
- [X] T015 Implement SQLAlchemy ORM models for all four entities in `src/openinsider_tracker/storage/orm.py` (depends on T010-T014)
- [X] T016 Set up the Alembic migration environment and the initial schema migration (exposing a callable `apply_migrations()` for the CLI to wire up next) in `src/openinsider_tracker/storage/migrations/` (depends on T015)
- [X] T017 [P] Implement `InsiderTransactionRepository` in `src/openinsider_tracker/storage/repositories/insider_transaction_repo.py` (depends on T015)
- [X] T018 [P] Implement `BuybackEventRepository` in `src/openinsider_tracker/storage/repositories/buyback_repo.py` (depends on T015)
- [X] T019 [P] Implement `SignalRepository` in `src/openinsider_tracker/storage/repositories/signal_repo.py` (depends on T015)
- [X] T020 [P] Implement `ThresholdConfigurationRepository` (singleton get/set) in `src/openinsider_tracker/storage/repositories/threshold_repo.py` (depends on T015; T017-T020 together make T009 pass)
- [X] T021 [P] Implement shared retry/backoff HTTP client helper in `src/openinsider_tracker/ingestion/http_client.py`
- [X] T022 Implement application config loader (env vars for DB path, SMTP, poll interval, notify-to address) in `src/openinsider_tracker/config.py`
- [X] T023 Implement CLI scaffold wiring `migrate|ingest|classify|notify|serve|thresholds` subcommands in `src/openinsider_tracker/cli/main.py` and `src/openinsider_tracker/__main__.py`: `migrate` is fully implemented here (calling T016's `apply_migrations()`, per contracts/cli.md), the rest are stubs completed in their own story phases (depends on T016, T022; makes T009's setup path work)
- [X] T024 Implement FastAPI app factory plus `GET /healthz` (verifies DB connectivity) in `src/openinsider_tracker/web/app.py` (depends on T014, T022)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Review notable signals on a dashboard (Priority: P1) 🎯 MVP

**Goal**: Ingest SEC Form 4 filings, SEC buyback disclosures, and an OpenInsider-style
feed; classify notability; de-duplicate; and surface notable signals on a dashboard
with links back to source filings.

**Independent Test**: Ingest fixtures for a large insider buy, a buyback, and a
routine/small transaction; classify; confirm `GET /api/signals` (and the dashboard)
shows only the two notable signals, most recent first, each linking to its source —
no notification system required.

### Tests for User Story 1 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T025 [P] [US1] Add fixture files `sample_form4_large_buy.xml`, `sample_form4_routine_10b5-1.xml`, `sample_8k_buyback_100m.xml`, `sample_openinsider_page.html` in `tests/fixtures/`
- [X] T026 [P] [US1] Integration test: SEC Form 4 XML fixture (large discretionary buy) parses into correct `InsiderTransaction` fields in `tests/integration/ingestion/test_sec_edgar_form4.py`
- [X] T027 [P] [US1] Integration test: SEC 8-K/Item 703 buyback fixture parses into correct `BuybackEvent` fields, distinguishing authorized vs. executed, in `tests/integration/ingestion/test_sec_buybacks.py`
- [X] T028 [P] [US1] Integration test: OpenInsider-style HTML fixture parses into `InsiderTransaction` candidate records in `tests/integration/ingestion/test_openinsider_feed.py`
- [X] T029 [P] [US1] Integration test: the same SEC accession number ingested twice yields one record; an amended filing supersedes the prior one via `superseded_by_id`, and the prior signal (if any) is marked `is_superseded=true` in `tests/integration/ingestion/test_dedup.py`
- [X] T030 [P] [US1] Integration test: a SEC-sourced record and its OpenInsider-style counterpart for the same event fuzzy-match to a single `InsiderTransaction` in `tests/integration/ingestion/test_cross_source_dedup.py`
- [X] T031 [P] [US1] Integration test: a transient source failure is retried with backoff and never silently dropped (mocked flaky HTTP) in `tests/integration/ingestion/test_retry_backoff.py`
- [X] T032 [P] [US1] Unit test: notability rules — a discretionary buy at/above threshold, or by a notable filer role, is notable; 10b5-1/routine-tagged transactions are excluded by default, in `tests/unit/classification/test_notability_rules.py`
- [X] T033 [P] [US1] Contract test: CLI `ingest --source sec_edgar --fixture ...` produces the documented JSON summary and persists records, in `tests/contract/test_cli_ingest.py`
- [X] T034 [P] [US1] Contract test: CLI `classify` marks notable vs. routine per default thresholds and produces the documented JSON summary, in `tests/contract/test_cli_classify.py`
- [X] T035 [P] [US1] Contract test: `GET /api/signals` returns notable-only, most-recent-first results, includes `is_discretionary` on each item, supports `signal_type`/`since`/`limit`/`offset`, and never returns an `is_superseded=true` signal, per contracts/api.md, in `tests/contract/test_api_signals.py`
- [X] T036 [P] [US1] Contract test: `GET /api/signals/{id}` returns full detail including provenance fields and `is_superseded`, 404 when not found, in `tests/contract/test_api_signal_detail.py`

### Implementation for User Story 1

- [X] T037 [US1] Implement the SEC EDGAR Form 4 client (submissions feed + ownership XML parsing) in `src/openinsider_tracker/ingestion/sec_edgar_form4.py` (depends on T010, T021; makes T026 pass)
- [X] T038 [US1] Implement the SEC EDGAR buyback client (full-text search + Item 703 parsing) in `src/openinsider_tracker/ingestion/sec_buybacks.py` (depends on T011, T021; makes T027 pass)
- [X] T039 [US1] Implement the OpenInsider-style feed client (rate-limited fetch + HTML parsing) in `src/openinsider_tracker/ingestion/openinsider_feed.py` (depends on T010, T021; makes T028 pass)
- [X] T040 [US1] Implement de-duplication and supersession logic (natural keys per research.md §6): on detecting an amendment, set `superseded_by_id` on the prior `InsiderTransaction`/`BuybackEvent` row AND mark any `Signal` wrapping it as `is_superseded=true`, in `src/openinsider_tracker/ingestion/dedup.py` (depends on T017, T018, T019; makes T029, T030 pass)
- [X] T041 [US1] Wire the retry/backoff helper (T021) into all three ingestion clients so fetch failures retry instead of dropping silently (makes T031 pass)
- [X] T042 [US1] Implement `ingest` orchestration — fetch all sources, de-duplicate, persist via repositories with provenance — in `src/openinsider_tracker/ingestion/orchestrator.py` (depends on T037-T041)
- [X] T043 [US1] Wire the `ingest` CLI subcommand to the orchestrator with JSON summary output in `src/openinsider_tracker/cli/main.py` (depends on T042, T023; makes T033 pass)
- [X] T044 [US1] Implement the notability classification engine covering BOTH signal types — insider transactions (dollar threshold, filer-role check, discretionary-vs-routine, setting `Signal.is_discretionary`) and buyback events (`min_buyback_amount` threshold, per FR-005) — in `src/openinsider_tracker/classification/rules.py` (depends on T013, T019, T020; makes T032 pass)
- [X] T045 [US1] Wire the `classify` CLI subcommand in `src/openinsider_tracker/cli/main.py` (depends on T044, T023; makes T034 pass)
- [X] T046 [US1] Implement `GET /api/signals` (filter/sort/paginate, always excluding `is_superseded=true`, including `is_discretionary` per contracts/api.md) in `src/openinsider_tracker/web/routes/signals.py` (depends on T019, T024; makes T035 pass)
- [X] T047 [US1] Implement `GET /api/signals/{id}` in `src/openinsider_tracker/web/routes/signals.py` (depends on T046; makes T036 pass)
- [X] T048 [US1] Register the signals routes on the FastAPI app in `src/openinsider_tracker/web/app.py` (depends on T046, T047, T024)
- [X] T049 [US1] Implement the server-rendered dashboard page (Jinja2), using the same signal query as `/api/signals`, with source links and a visible discretionary/routine indicator per `is_discretionary` (SC-006), in `src/openinsider_tracker/web/routes/dashboard.py` and `src/openinsider_tracker/web/templates/dashboard.html` (depends on T046)

**Checkpoint**: User Story 1 is fully functional and independently testable — matches quickstart.md's User Story 1 section.

---

## Phase 4: User Story 2 - Get emailed when a new notable signal appears (Priority: P2)

**Goal**: Send an email to the user as soon as a new notable signal is recorded, with
no duplicates and no dependency on the dashboard being open.

**Independent Test**: Feed a known notable signal into the already-working
classification pipeline and confirm exactly one correctly formatted email is sent,
without touching the dashboard UI.

### Tests for User Story 2 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T050 [P] [US2] Contract test: CLI `notify` sends one email per pending notable signal, marks it sent, and sends no duplicate on re-run, in `tests/contract/test_cli_notify.py`
- [X] T051 [P] [US2] Integration test: a simulated SMTP failure marks the signal's `notification_status=failed` while it remains visible via `GET /api/signals`, in `tests/integration/notifications/test_notify_failure.py`
- [X] T052 [P] [US2] Integration test: multiple notable signals in one run each produce a correctly formatted, correctly addressed email, in `tests/integration/notifications/test_notify_batch.py`

### Implementation for User Story 2

- [X] T053 [US2] Implement the email composer (subject/body with company, signal type, key figures, dashboard link) in `src/openinsider_tracker/notifications/composer.py` (depends on T010, T011, T012)
- [X] T054 [US2] Implement the SMTP sender using config (T022), catching and reporting per-message failures without raising, in `src/openinsider_tracker/notifications/mailer.py`
- [X] T055 [US2] Implement `notify` orchestration — select pending signals, send via composer+mailer, update `notification_status`/`notified_at` — in `src/openinsider_tracker/notifications/orchestrator.py` (depends on T053, T054, T019; makes T050-T052 pass)
- [X] T056 [US2] Wire the `notify` CLI subcommand in `src/openinsider_tracker/cli/main.py` (depends on T055, T023)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Tune what counts as "notable" (Priority: P3)

**Goal**: Let the user adjust notability thresholds and have them apply to future
classification without a code change or rebuild.

**Independent Test**: Change a threshold value and confirm previously-excluded (or
previously-included) signals cross the notability line accordingly.

### Tests for User Story 3 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T057 [P] [US3] Contract test: `GET`/`PUT /api/thresholds` round-trip, and reject invalid values (e.g., negative amounts) with 422, per contracts/api.md, in `tests/contract/test_api_thresholds.py`
- [X] T058 [P] [US3] Contract test: CLI `thresholds show` and `thresholds set` per contracts/cli.md, in `tests/contract/test_cli_thresholds.py`
- [X] T059 [P] [US3] Integration test: after `PUT /api/thresholds` followed by `classify --reclassify`, previously below-threshold fixture transactions become notable, in `tests/integration/classification/test_reclassify.py`

### Implementation for User Story 3

- [X] T060 [US3] Implement `GET /api/thresholds` and `PUT /api/thresholds` in `src/openinsider_tracker/web/routes/thresholds.py` (depends on T020, T024; makes T057 pass)
- [X] T061 [US3] Register the thresholds routes on the FastAPI app in `src/openinsider_tracker/web/app.py` (depends on T060)
- [X] T062 [US3] Wire `thresholds show`/`thresholds set` CLI subcommands in `src/openinsider_tracker/cli/main.py` (depends on T020, T023; makes T058 pass)
- [X] T063 [US3] Add `--reclassify` support to the classification engine/CLI to re-evaluate all existing records against current thresholds, in `src/openinsider_tracker/classification/rules.py` and `src/openinsider_tracker/cli/main.py` (depends on T044, T045; makes T059 pass)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Ties the stories together into the single deployable service and
validates the whole thing end-to-end.

- [X] T064 [P] Implement the in-process APScheduler wiring hourly (configurable) `ingest → classify → notify` calls, run on a background thread off the FastAPI event loop per research.md §5, in `src/openinsider_tracker/scheduler/scheduler.py`
- [X] T065 Wire the `serve` CLI subcommand: start the FastAPI app and the scheduler (unless `--no-scheduler`), in `src/openinsider_tracker/cli/main.py` (depends on T024, T064)
- [X] T066 [P] Write the root `Dockerfile` building the app image and running `serve` as the entrypoint
- [X] T067 [P] Write the root `docker-compose.yml` defining the single `app` service with a named volume for the SQLite file, per plan.md
- [X] T068 [P] Add structured logging across ingestion/classification/notifications so parse/validation failures are always surfaced, never silently swallowed (Constitution Principle II)
- [X] T069 Run quickstart.md validation end-to-end against the built `docker compose up` stack and fix any discrepancies found

---

## Phase 7: User Story 4 - Sort and search dashboard signals (Priority: P4)

**Goal**: Let the user sort the dashboard by date, type, company, or amount, and
filter it with free-text search, entirely client-side against data already on
the page.

**Independent Test**: Load a dashboard with multiple signals, click each sortable
column header and confirm correct ascending/descending reordering, then type into
the search box and confirm only matching rows remain visible.

### Tests for User Story 4 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T070 [P] [US4] Contract test: dashboard HTML includes sortable column headers (`data-key` for date/type/company/amount) and each row carries `data-date`/`data-company`/`data-amount`/`data-search` attributes, and a `#search-box` input exists, in `tests/contract/test_dashboard_sort_search.py`

### Implementation for User Story 4

- [X] T071 [US4] Add per-row sort/search data attributes and sortable `<th>` headers to the dashboard template, in `src/openinsider_tracker/web/templates/dashboard.html` (makes T070 pass)
- [X] T072 [US4] Implement client-side sort-on-click-header and filter-on-search-input behavior (vanilla JS, no new dependency) in `src/openinsider_tracker/web/templates/dashboard.html`; verified by manual browser testing per spec.md Assumptions (interactive DOM behavior is presentation, not data/business logic, so it sits outside Constitution Principle I's automated-test mandate — T070 covers the regression-prone part: that the template keeps emitting the attributes this script depends on)

**Checkpoint**: All four user stories are independently functional.

---

## Phase 8: Refinement — role AND amount required for notability (FR-004)

**Purpose**: Close out the ambiguity flagged in `/speckit-analyze` finding A1 —
the original "value OR role" rule made any officer/director buy notable
regardless of size. Changed to AND: a notable role gets a lower dollar floor
(`min_notable_role_buy_value`, default $100,000), everyone else uses the
existing higher floor (`min_insider_buy_value`, default $1,000,000); role alone
is never sufficient.

### Tests (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] Unit test: a notable-role buy below `min_notable_role_buy_value` is NOT notable, in `tests/unit/classification/test_notability_rules.py::test_notable_role_below_its_own_lower_threshold_is_not_notable`
- [X] Unit test: a notable-role buy at/above `min_notable_role_buy_value` IS notable even though far below `min_insider_buy_value`, in `tests/unit/classification/test_notability_rules.py::test_notable_role_at_or_above_its_own_lower_threshold_is_notable`
- [X] Unit test: a non-notable-role buy must still clear the higher `min_insider_buy_value`, in `tests/unit/classification/test_notability_rules.py::test_non_notable_role_must_clear_the_higher_general_threshold`
- [X] Unit test: `ThresholdConfiguration.threshold_for_role` returns the role-specific vs. general value correctly, and rejects a negative `min_notable_role_buy_value`, in `tests/unit/domain/test_threshold_configuration.py`
- [X] Contract test: `GET`/`PUT /api/thresholds` include `min_notable_role_buy_value`, round-trip it, and reject a negative value with 422, in `tests/contract/test_api_thresholds.py`
- [X] Contract test: CLI `thresholds set --min-notable-role-buy-value` updates and persists, in `tests/contract/test_cli_thresholds.py`

### Implementation

- [X] Add `min_notable_role_buy_value` (default 100,000) and `threshold_for_role()` to `src/openinsider_tracker/domain/threshold_configuration.py`
- [X] Change `classify_insider_transaction` to AND semantics via `threshold_for_role`, in `src/openinsider_tracker/classification/rules.py`
- [X] Add the column (`ThresholdConfigurationORM`) in `src/openinsider_tracker/storage/orm.py`, a new Alembic migration `0002_add_min_notable_role_buy_value.py` (server_default so existing rows backfill to 100,000 — verified against a real pre-existing Docker volume, not just a fresh database), and thread the field through `ThresholdConfigurationRepository`, the `/api/thresholds` request/response models, and the `thresholds` CLI subcommand (new `--min-notable-role-buy-value` flag)

**Verification**: confirmed live against the running Docker container — raising
`min_notable_role_buy_value` above an existing director signal's amount and
reclassifying correctly dropped it from "notable"; lowering it back restored it.

---

## Phase 9: User Story 5 - Control how many signals are shown at once (Priority: P5)

**Goal**: Let the user choose a fixed page size (10/25/50) or infinite scroll for
the dashboard's signal list, entirely client-side against rows already on the
page (per spec.md Assumptions), interacting correctly with the existing US4
sort/search state.

**Independent Test**: Load a dashboard with more rows than the smallest page-size
option, select each page-size option and confirm only that many rows are visible,
switch to infinite scroll and confirm more rows appear on scroll, and reload to
confirm the last-selected option persists.

### Tests for User Story 5 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T073 [P] [US5] Contract test: dashboard HTML includes a page-size control
  exposing the 10/25/50/infinite-scroll options (e.g. a `#page-size-select` with
  those values) and every signal row remains present in the DOM (so client-side
  paging has rows to work with), in `tests/contract/test_dashboard_page_size.py`

### Implementation for User Story 5

- [X] T074 [US5] Raise the row limit passed to `query_signals` in
  `src/openinsider_tracker/web/routes/dashboard.py` from the default 100 to a
  documented higher constant (e.g. 500) so page-size/infinite-scroll has enough
  already-rendered rows at the project's actual data volume (per spec.md
  Assumptions — no new query parameters, just a larger single fetch)
- [X] T075 [US5] Add the page-size/infinite-scroll control markup (10/25/50/
  Infinite options) to the dashboard toolbar in
  `src/openinsider_tracker/web/templates/dashboard.html` (makes T073 pass)
- [X] T076 [US5] Implement client-side page-size logic: show only the first N rows
  of the current sorted/filtered row set (from US4's `applyFilter`/sort output),
  re-applying whenever sort or search changes (FR-023), in
  `src/openinsider_tracker/web/templates/dashboard.html` (depends on T071, T072,
  T075)
- [X] T077 [US5] Implement infinite-scroll mode: a scroll listener that reveals
  the next batch of currently-hidden rows as the user nears the bottom of the
  visible list, showing a "no more signals" indicator once exhausted (edge case
  in spec.md), in `src/openinsider_tracker/web/templates/dashboard.html` (depends
  on T076)
- [X] T078 [US5] Persist the selected page-size/infinite-scroll option in
  `localStorage` and restore it on page load (FR-022), in
  `src/openinsider_tracker/web/templates/dashboard.html` (depends on T075)

**Checkpoint**: All five user stories are independently functional.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational; reads `Signal` rows that US1's classification produces, but is independently testable by feeding a signal directly into `notify` (per its Independent Test)
- **User Story 3 (Phase 5)**: Depends on Foundational; exercises the classification engine built in US1 (T044) via reclassification — independently testable via its own Independent Test
- **Polish (Phase 6)**: Depends on all three user stories being complete (the scheduler wires together `ingest`/`classify`/`notify` from US1/US2, and quickstart validation exercises all three)
- **User Story 4 (Phase 7)**: Depends on User Story 1's dashboard existing (it enhances that template); independent of US2/US3/Polish otherwise
- **User Story 5 (Phase 9)**: Depends on User Story 1's dashboard and User Story 4's sort/search JS existing (page-size re-slices US4's sorted/filtered output); independent of US2/US3/Polish otherwise

### Within Each Phase

- Tests MUST be written and FAIL before their corresponding implementation task (Constitution Principle I)
- Domain models before storage; storage before repositories; repositories before orchestration; orchestration before CLI/API wiring

### Parallel Opportunities

- Setup: T003, T004 in parallel
- Foundational tests: T005-T009 in parallel; Foundational domain models: T010-T013 in parallel; repositories: T017-T020 in parallel
- US1 tests: T025-T036 in parallel (fixtures T025 first, since other tests read those files)
- US1 ingestion clients: T037-T039 in parallel (different files)
- US2 tests: T050-T052 in parallel
- US3 tests: T057-T059 in parallel
- Polish: T064, T066, T067, T068 in parallel
- US5: T073 can run alongside T074 (different files)

---

## Parallel Example: User Story 1

```bash
# Fixtures first, then tests together:
Task: "Add fixture files in tests/fixtures/"
Task: "Integration test: SEC Form 4 XML fixture parses correctly in tests/integration/ingestion/test_sec_edgar_form4.py"
Task: "Integration test: SEC buyback fixture parses correctly in tests/integration/ingestion/test_sec_buybacks.py"
Task: "Integration test: OpenInsider-style fixture parses correctly in tests/integration/ingestion/test_openinsider_feed.py"

# Then the three ingestion clients together (different files, all depend only on Foundational):
Task: "Implement SEC EDGAR Form 4 client in src/openinsider_tracker/ingestion/sec_edgar_form4.py"
Task: "Implement SEC EDGAR buyback client in src/openinsider_tracker/ingestion/sec_buybacks.py"
Task: "Implement OpenInsider-style feed client in src/openinsider_tracker/ingestion/openinsider_feed.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE** against quickstart.md's User Story 1 section
5. This is a usable MVP: a dashboard of notable insider/buyback signals, no email yet

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate independently → MVP
3. User Story 2 → validate independently → adds email notifications
4. User Story 3 → validate independently → adds threshold tuning
5. Polish → wires the scheduler, finalizes `docker-compose.yml`/`Dockerfile`, runs full quickstart validation

---

## Notes

- No trading, brokerage, or order-execution task appears anywhere in this list — out of scope per spec FR-017 and Constitution Principle V.
- [P] tasks touch different files with no unmet dependencies.
- Commit after each task or logical group.
- Every implementation task above has a named test task it makes pass — verify that test fails first, per Constitution Principle I.
