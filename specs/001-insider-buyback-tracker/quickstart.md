# Quickstart: Insider Trading & Buyback Signal Tracker

Validates the feature end-to-end using the Docker Compose stack — a single `app`
service, no host-installed Python or database required (Constitution: Containerized
Deployment).

## Prerequisites

- Docker and Docker Compose installed.
- A copy of `.env.example` as `.env` with at minimum: `SMTP_HOST`/`SMTP_PORT`/
  `SMTP_USER`/`SMTP_PASSWORD` and `NOTIFY_EMAIL_TO` (your own address). The SQLite
  file path defaults to a path on the service's named volume and normally doesn't
  need to be set.

## Bring up the stack

```bash
docker compose up -d
docker compose exec app python -m insideoutside migrate   # apply schema
```

## Validate User Story 1 — dashboard shows notable signals

1. Seed a known fixture instead of waiting for a live poll:
   ```bash
   docker compose exec app python -m insideoutside ingest --source sec_edgar --fixture tests/fixtures/sample_form4_large_buy.xml
   docker compose exec app python -m insideoutside ingest --source sec_edgar --fixture tests/fixtures/sample_8k_buyback_100m.xml
   docker compose exec app python -m insideoutside classify
   ```
2. Open `http://localhost:8000` (or `curl http://localhost:8000/api/signals`).
3. **Expected**: both the insider buy and the buyback appear, most recent first,
   each with company, amount, date, and a working link to its source filing
   (spec Acceptance Scenarios 1–3). A routine/small transaction fixture, if seeded,
   does NOT appear in the default (`notable_only=true`) view (Acceptance Scenario 4).

## Validate User Story 2 — email on new notable signal

```bash
docker compose exec app python -m insideoutside notify
```

**Expected**: one email arrives at `NOTIFY_EMAIL_TO` for each newly-notable signal
from the previous step, containing company, signal type, key figures, and a
dashboard link. Re-running `notify` sends no duplicate email for the same signal.

## Validate User Story 3 — adjustable thresholds

```bash
curl -X PUT http://localhost:8000/api/thresholds \
  -H 'Content-Type: application/json' \
  -d '{"min_insider_buy_value": 100000, "notable_filer_roles": ["officer","director"], "min_buyback_amount": 50000000}'
docker compose exec app python -m insideoutside classify --reclassify
```

**Expected**: previously below-threshold insider transactions in the fixture data
now appear as notable signals on the dashboard, with no code change or rebuild.

## Running the test suite

```bash
docker compose exec app pytest
```

**Expected**: unit tests (no I/O), integration tests (against a disposable temp-file
SQLite database), and contract tests (CLI + `/api/*`) all pass.
