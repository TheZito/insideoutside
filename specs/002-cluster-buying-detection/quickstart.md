# Quickstart: Cluster Buying Detection

Validates this feature against the same running stack as 001
(`docker compose up -d` — see specs/001-insider-buyback-tracker/quickstart.md for
first-time setup). No new services, no new env vars required.

## Prerequisites

- 001's stack already up and migrated (`docker compose up -d`, then
  `docker compose exec app python -m insideoutside migrate` to pick up
  this feature's schema changes too).

## Validate User Story 1 — cluster signal appears on the dashboard

1. Seed two Form 4 fixtures for two different filers at the same company, within
   the default 14-day window, at least one below the existing single-transaction
   threshold:
   ```bash
   docker compose exec app python -m insideoutside ingest --source sec_edgar --fixture tests/fixtures/sample_form4_cluster_filer_a.xml
   docker compose exec app python -m insideoutside ingest --source sec_edgar --fixture tests/fixtures/sample_form4_cluster_filer_b.xml
   docker compose exec app python -m insideoutside classify
   ```
2. `curl http://localhost:8000/api/signals?signal_type=cluster_buy`
3. **Expected**: one `cluster_buy` signal, `distinct_filer_count: 2`, combined
   `amount` equal to the sum of both transactions' values, `window_start`/
   `window_end` matching the two transaction dates.

## Validate User Story 2 — email on new cluster signal

```bash
docker compose exec app python -m insideoutside notify
```

**Expected**: one email identifying the company, distinct filer count, and
combined value. Re-running `ingest`+`classify` with a third qualifying filer at
the same company, then `notify` again, updates the existing cluster (filer count
now 3) but sends no second email for it (FR-007/SC-002).

## Validate User Story 3 — tune sensitivity

```bash
docker compose exec app python -m insideoutside thresholds set --min-cluster-filer-count 3
docker compose exec app python -m insideoutside classify --reclassify
```

**Expected**: with only 2 distinct filers in the fixture data, the cluster from
Story 1 is no longer notable after raising the minimum to 3.

## Regression check (SC-003)

```bash
docker compose exec app pytest tests/ -k "not cluster"
```

**Expected**: all of 001's existing tests still pass unmodified — this feature
must not change single-transaction or buyback behavior.
