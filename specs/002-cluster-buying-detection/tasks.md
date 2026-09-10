# Tasks: Cluster Buying Detection

**Input**: Design documents from `/specs/002-cluster-buying-detection/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Included and REQUIRED, not optional — Constitution Principle I (Test-First,
NON-NEGOTIABLE), same as specs/001-insider-buyback-tracker.

**Organization**: Tasks are grouped by user story (from spec.md). This feature is
purely additive to the existing 001 codebase — no new project, no new service.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 (from spec.md)
- All file paths are relative to the repository root, inside the existing
  `src/insideoutside/` and `tests/` trees from 001.

---

## Phase 1: Setup

- [X] T001 [P] Add fixture files `sample_form4_cluster_filer_a.xml`, `sample_form4_cluster_filer_b.xml`, `sample_form4_cluster_filer_c.xml` in `tests/fixtures/` — three different filers (director, officer, officer) at the same company, each a discretionary buy below the existing single-transaction notability threshold, dated within a 14-day span (filer_c dated after a/b for the "cluster grows" scenarios)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema and domain extensions every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational (write FIRST, ensure they FAIL before implementation)

- [X] T002 [P] Unit test: `InsiderTransaction.filer_id` is optional and defaults to `None`, in `tests/unit/domain/test_insider_transaction.py` (extend)
- [X] T003 [P] Unit test: `ClusterBuyEvent` validation (required fields; `window_start <= window_end`; `distinct_filer_count >= 0`) in `tests/unit/domain/test_cluster_buy_event.py`
- [X] T004 [P] Unit test: `Signal` accepts `signal_type="cluster_buy"` with `cluster_buy_event_id` set, and rejects `cluster_buy` without it (mirroring existing insider_transaction/buyback linkage validation), in `tests/unit/domain/test_signal.py` (extend)
- [X] T005 [P] Unit test: `ThresholdConfiguration` defaults `cluster_window_days=14`, `min_cluster_filer_count=2`; rejects `cluster_window_days < 1` and `min_cluster_filer_count < 2`, in `tests/unit/domain/test_threshold_configuration.py` (extend)
- [X] T006 [P] Integration test: `ClusterBuyEventRepository` create/get/list round-trip, and `upsert_by_overlapping_transactions` replaces an existing row in place when the new group shares a `contributing_transaction_id` with it, but creates a separate new row for a same-company group sharing NO transaction with any existing row (research.md §5), against a temp-file SQLite database (schema via `migrate`), in `tests/integration/storage/test_cluster_buy_repo.py`
- [X] T007 [P] Integration test: the SEC Form 4 parser populates `filer_id` from the XML's `rptOwnerCik`, in `tests/integration/ingestion/test_sec_edgar_form4.py` (extend)

### Implementation for Foundational

- [X] T008 [P] Add optional `filer_id` field to `InsiderTransaction` in `src/insideoutside/domain/insider_transaction.py` (makes T002 pass)
- [X] T009 [P] Implement `ClusterBuyEvent` domain model in `src/insideoutside/domain/cluster_buy_event.py` (makes T003 pass)
- [X] T010 Extend `Signal` domain model — add `cluster_buy` to `SignalType`, add `cluster_buy_event_id`, extend `_check_signal_type_linkage` — in `src/insideoutside/domain/signal.py` (makes T004 pass)
- [X] T011 [P] Extend `ThresholdConfiguration` — add `cluster_window_days` (default 14) and `min_cluster_filer_count` (default 2) with validators — in `src/insideoutside/domain/threshold_configuration.py` (makes T005 pass)
- [X] T012 Update `parse_form4_xml` to read `rptOwnerCik` into `filer_id`, in `src/insideoutside/ingestion/sec_edgar_form4.py` (depends on T008; makes T007 pass)
- [X] T013 Extend `src/insideoutside/storage/orm.py`: `InsiderTransactionORM.filer_id`, new `ClusterBuyEventORM` table, `SignalORM.cluster_buy_event_id`, `ThresholdConfigurationORM.cluster_window_days`/`min_cluster_filer_count` (depends on T008-T011)
- [X] T014 Write Alembic migration `0003_cluster_buying.py` covering all of T013's schema changes, with `server_default`s so existing rows backfill correctly, in `src/insideoutside/storage/migrations/versions/` (depends on T013; makes T006 pass together with T015)
- [X] T015 [P] Implement `ClusterBuyEventRepository` — `create`/`get`/`list_by_company`, and `upsert_by_overlapping_transactions(candidate)` which matches an existing row by shared `contributing_transaction_ids` (NOT by company alone — a company can have multiple unrelated clusters over time, per research.md §5) and replaces it in place, or creates a new row if nothing matches — in `src/insideoutside/storage/repositories/cluster_buy_repo.py` (depends on T014; makes T006 pass)
- [X] T016 Update `SignalRepository`: add `get_for_cluster_buy_event`, thread `cluster_buy_event_id` through `_to_domain`/`_apply_domain`, in `src/insideoutside/storage/repositories/signal_repo.py` (depends on T010, T014)
- [X] T017 Update `ThresholdConfigurationRepository` to persist/read the two new fields, in `src/insideoutside/storage/repositories/threshold_repo.py` (depends on T011, T014)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - See cluster buying as its own signal on the dashboard (Priority: P1)

**Goal**: Detect 2+ distinct insiders at the same company buying within the
configured window, and surface it as its own signal on the dashboard.

**Independent Test**: Ingest two same-company Form 4 fixtures for different
filers (each below the single-transaction threshold) within the window,
classify, and confirm a notable `cluster_buy` signal appears via `/api/signals`
and the dashboard with the correct filer count, window, and combined value.

### Tests for User Story 1 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T018 [P] [US1] Unit test: the grouping algorithm groups 2+ distinct filers at the same company within the window into one cluster candidate; excludes a different company's transaction; counts a repeat buy by the same filer once, not twice; excludes non-discretionary and sell transactions, in `tests/unit/classification/test_cluster_buying.py`
- [X] T019 [P] [US1] Unit test: `classify_cluster` marks a candidate notable iff `distinct_filer_count >= min_cluster_filer_count`, in `tests/unit/classification/test_cluster_buying.py`
- [X] T020 [P] [US1] Integration test: ingesting the two fixtures from T001 (each below the single-transaction threshold) and classifying creates one notable `cluster_buy` signal with correct `distinct_filer_count`/`total_value`/window dates; running `classify` again on unchanged data produces the SAME `ClusterBuyEvent` row (no duplicate) and the SAME `Signal` (verifying FR-005's update-not-duplicate guarantee at the storage level, not just the notification level), in `tests/integration/classification/test_cluster_detection.py`
- [X] T021 [P] [US1] Integration test: a corporate buyback and a routine/non-discretionary transaction at the same company and window are never counted toward a cluster, in `tests/integration/classification/test_cluster_detection.py`
- [X] T022 [P] [US1] Contract test: `classify`'s JSON summary includes `clusters_detected`/`clusters_notable`, in `tests/contract/test_cli_classify.py` (extend)
- [X] T023 [P] [US1] Contract test: `GET /api/signals?signal_type=cluster_buy` returns the cluster shape (summary text, combined amount, `event_date` = window end, `source_url: null`) per contracts/api-delta.md, in `tests/contract/test_api_signals.py` (extend)

### Implementation for User Story 1

- [X] T024 [US1] Implement the grouping algorithm (`detect_clusters`) and `classify_cluster` in `src/insideoutside/classification/cluster_buying.py` (depends on T008, T011; makes T018, T019 pass)
- [X] T025 [US1] Wire cluster detection into the `classify` CLI command — after existing per-record classification, group qualifying transactions per company, upsert `ClusterBuyEvent`s via T015's `upsert_by_overlapping_transactions`, create/update `Signal` rows via T016 — in `src/insideoutside/cli/commands/classify.py` (depends on T015, T016, T024; makes T020, T021, T022 pass)
- [X] T026 [US1] Add the `cluster_buy` branch to the signal-summary dispatcher (company/ticker/summary/amount/event_date/`source_url: null`) in `src/insideoutside/web/routes/signals.py` (depends on T015; makes T023 pass)
- [X] T027 [US1] Add cluster-buy badge styling to the dashboard template, in `src/insideoutside/web/templates/dashboard.html` (depends on T026)

**Checkpoint**: User Story 1 fully functional and independently testable.

---

## Phase 4: User Story 2 - Get emailed when a new cluster signal appears (Priority: P2)

**Goal**: Reuse the existing notification mechanism for cluster signals, with the
same no-duplicate-email guarantee as the other two signal types.

**Independent Test**: Feed a qualifying cluster into the notify step and confirm
exactly one email; grow the cluster with a third filer and confirm no second
email is sent.

### Tests for User Story 2 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T028 [P] [US2] Unit test: `compose_signal_email` produces a cluster-appropriate subject/body (company, distinct filer count, combined value, window dates) for a `cluster_buy` signal, in `tests/unit/notifications/test_composer.py`
- [X] T029 [P] [US2] Integration test: a cluster signal already `sent` does NOT get a second email when a third qualifying filer joins the same cluster within its window on a later `ingest`+`classify`+`notify` cycle, in `tests/integration/notifications/test_cluster_no_duplicate.py`

### Implementation for User Story 2

- [X] T030 [US2] Add the `cluster_buy` branch to `compose_signal_email` in `src/insideoutside/notifications/composer.py` (depends on T015; makes T028 pass)
- [X] T031 [US2] Ensure cluster recomputation (T025) never resets an already-`sent`/`failed` Signal's `notification_status` back to `pending` when its `ClusterBuyEvent` is updated, in `src/insideoutside/cli/commands/classify.py` (depends on T025; makes T029 pass)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Tune cluster detection sensitivity (Priority: P3)

**Goal**: Let the user adjust the window length and minimum distinct-filer count.

**Independent Test**: Change `min_cluster_filer_count` and confirm a previously-
notable cluster's status changes accordingly on the next classification run.

### Tests for User Story 3 (write FIRST, ensure they FAIL before implementation) ⚠️

- [X] T032 [P] [US3] Contract test: `GET`/`PUT /api/thresholds` round-trip `cluster_window_days`/`min_cluster_filer_count`, reject `< 1` / `< 2` respectively with 422, in `tests/contract/test_api_thresholds.py` (extend)
- [X] T033 [P] [US3] Contract test: CLI `thresholds set --cluster-window-days` / `--min-cluster-filer-count`, in `tests/contract/test_cli_thresholds.py` (extend)
- [X] T034 [P] [US3] Integration test: raising `min_cluster_filer_count` above an existing cluster's `distinct_filer_count` and running `classify --reclassify` makes it no longer notable; lowering it back restores notability, in `tests/integration/classification/test_cluster_detection.py` (extend)
- [X] T034a [P] [US3] Integration test: narrowing `cluster_window_days` and running `classify --reclassify` on an already-`sent` 3-filer cluster splits it into two smaller groups per research.md §5 — the original `ClusterBuyEvent`/`Signal` is updated in place to the majority-overlap piece (its `notification_status` stays `sent` even if that piece now falls below the minimum and `is_notable` flips to `false`), and the other piece, if independently notable, becomes a new, separately-notifiable `Signal`, in `tests/integration/classification/test_cluster_detection.py` (extend)

### Implementation for User Story 3

- [X] T035 [US3] Add `cluster_window_days`/`min_cluster_filer_count` to the thresholds request/response models in `src/insideoutside/web/routes/thresholds.py` (depends on T017; makes T032 pass)
- [X] T036 [US3] Add `--cluster-window-days`/`--min-cluster-filer-count` flags to `thresholds set` in `src/insideoutside/cli/commands/thresholds.py` and `src/insideoutside/cli/main.py` (depends on T017; makes T033 pass)
- [X] T037 [US3] Ensure `classify --reclassify` re-runs cluster detection from scratch across all companies with qualifying transactions, not just per-record classification, using T015's overlap-matching upsert so a split/merge resolves against existing rows correctly (research.md §5), in `src/insideoutside/cli/commands/classify.py` (depends on T025; makes T034, T034a pass)

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T038 [P] Run 001's full existing test suite unmodified and confirm zero regressions (SC-003) — no changes to buyback detection, single-transaction classification, or their dashboard/email behavior
- [X] T039 Rebuild the Docker image, run `migrate` against the existing volume (verifying the new columns/table backfill correctly on real pre-existing data, not just a fresh database), and validate quickstart.md's three user-story scenarios live against the running container
- [X] T040 [P] Add structured logging distinguishing a newly-created cluster vs. an updated one vs. one newly crossing notability, in `src/insideoutside/cli/commands/classify.py` (Constitution Principle II)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational only
- **User Story 2 (Phase 4)**: Depends on Foundational and reuses US1's cluster detection (T025) as the thing it notifies about, but is independently testable via its own Independent Test
- **User Story 3 (Phase 5)**: Depends on Foundational; exercises US1's detection (T024/T025) via reclassification
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each Phase

- Tests MUST be written and FAIL before their corresponding implementation task (Constitution Principle I)
- Domain model changes (T008-T011) before ORM (T013) before migration (T014) before repositories (T015-T017) before classification logic (T024) before CLI/API wiring (T025-T027, T030, T035-T037)

### Parallel Opportunities

- Foundational tests: T002-T007 in parallel; foundational domain changes: T008, T009, T011 in parallel (T010 touches a shared file, sequence it separately)
- US1 tests: T018-T023 in parallel
- US2 tests: T028-T029 in parallel
- US3 tests: T032-T034a in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (blocks everything)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE** against quickstart.md's User Story 1 section, and run the SC-003 regression check (T038) before going further

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. User Story 1 → validate independently → cluster signals visible
3. User Story 2 → validate independently → adds cluster email notifications
4. User Story 3 → validate independently → adds sensitivity tuning
5. Polish → regression check, live Docker validation, logging

---

## Notes

- This feature touches no trading/brokerage code — out of scope per 001's FR-017 and Constitution Principle V, unaffected here.
- FR-012/SC-003 are the load-bearing constraints of this whole feature: buyback and single-transaction behavior MUST NOT change. T038 is not optional busywork — it's the actual acceptance check for that requirement.
- [P] tasks touch different files with no unmet dependencies.
- Commit after each task or logical group.
