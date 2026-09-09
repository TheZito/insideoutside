# Phase 0 Research: Insider Trading & Buyback Signal Tracker

All Technical Context choices below were made during planning (no items were left
as `NEEDS CLARIFICATION` in plan.md); this document records the reasoning so it
isn't re-litigated during implementation.

## 1. Language & core framework

**Decision**: Python 3.12, FastAPI for the web layer, SQLAlchemy 2.x for storage.

**Rationale**: Strong ecosystem for HTTP fetching, HTML/XML parsing, and financial
data handling; FastAPI gives a JSON API and server-rendered dashboard (via Jinja2)
from one small service without a separate frontend build step, matching the
Simplicity principle. Team/user familiarity with Python was assumed as a reasonable
default for a personal data-processing tool.

**Alternatives considered**: Node/TypeScript (rejected — no ecosystem advantage here
and would split tooling between the CLI/worker and web layers); Go (rejected —
faster and simpler to deploy as a single binary, but weaker ecosystem for ad-hoc
HTML scraping and would add friction to the SEC XML/OpenInsider-style parsing work).

## 2. SEC Form 4 (insider transactions) ingestion

**Decision**: Poll SEC EDGAR's per-filer submissions feed
(`data.sec.gov/submissions/CIK##########.json`) for a tracked-filer list plus SEC's
"current events" Form 4 feed (`sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4`)
for cross-company discovery, then fetch and parse each filing's ownership XML for
transaction detail (shares, price, transaction code, footnotes indicating a 10b5-1
plan).

**Rationale**: Both are free, official, and public; the ownership XML embedded in
every Form 4 filing is structured and includes the transaction code needed to
distinguish open-market discretionary buys/sells (codes P/S) from routine,
plan-driven activity (code F, and filings with an explicit Rule 10b5-1 footnote) —
directly supporting FR-006 and edge case handling for routine vs. discretionary
transactions.

**Alternatives considered**: A paid market-data vendor API (rejected — violates the
"no paid subscription required for v1" assumption and adds an external dependency
for something SEC already publishes for free); EDGAR full-text search alone
(rejected as the sole source — good for discovery but not a substitute for the
structured ownership XML needed for exact share/price figures).

## 3. OpenInsider-style aggregated feed

**Decision**: Fetch and parse OpenInsider's public HTML listing pages as a
cross-check/aggregation source, with a documented per-request delay and a caching
layer so the same page isn't re-fetched more often than the polling interval
requires.

**Rationale**: OpenInsider has no official public API; scraping its public pages is
the only way to get its pre-aggregated view, which is valuable as a second signal
confirming SEC-derived data and catching anything the direct EDGAR poll missed.
Constitution's Data Handling & Compliance Standards requires respecting rate limits
and robots.txt — a single polite scheduled poll (not per-user, on-demand traffic)
keeps this well within reasonable use.

**Alternatives considered**: Skipping OpenInsider and relying solely on EDGAR
(rejected — the spec explicitly calls for OpenInsider-style aggregation as a named
source and cross-check, per FR-002 and the de-duplication requirement in FR-007,
which only matters if there are two sources to de-duplicate between).

## 4. Corporate buyback disclosures

**Decision**: Use SEC EDGAR full-text search
(`efts.sec.gov/LATEST/search-index`) scoped to 8-K Item 7.01/8.01 and 10-Q/10-K
filings containing repurchase-program language, combined with the standard
Item 703 "Issuer Purchases of Equity Securities" table format that public companies
must include in periodic filings when they have repurchased stock.

**Rationale**: There is no single clean "buyback events" feed; Item 703 is the
closest thing to a structured, mandated disclosure of actual repurchase activity,
and full-text search over 8-Ks catches buyback *authorizations* (announcements)
sooner, letting the system distinguish "authorized" vs. "executed" per the spec's
edge cases. Both are free, official SEC sources.

**Alternatives considered**: A financial-data vendor with a dedicated buybacks
endpoint (rejected for the same no-paid-subscription reason as insider data); press
release scraping (rejected as a v1 source — too heterogeneous in format to parse
reliably; can be revisited later without changing the domain model, since
`Buyback Event` is source-agnostic).

## 5. Scheduling approach

**Decision**: APScheduler running in a background thread inside the single `app`
process (the same process serving the FastAPI dashboard/API), invoking the same
library functions the CLI's `ingest`/`classify`/`notify` commands call, on an hourly
cron-style interval configurable via an environment variable.

**Rationale**: Keeps scheduling logic inside the one app process (no separate worker
container, no external scheduler service) while still going through the same
library entry points the CLI uses, so the scheduled path and a manual/debug
invocation (`docker compose exec app python -m openinsider_tracker ingest`) run
identical code — supporting Constitution Principle IV without a second container.
An earlier draft of this plan put the scheduler in a dedicated `worker` container;
that was reversed after review because nothing in this feature needs independent
scaling or process isolation between "serving requests" and "running the poll," and
a background thread is materially simpler than a second container for the same
outcome (Principle III).

**Alternatives considered**: A separate `worker` container running the scheduler
(rejected — see above); host-level cron calling `docker compose exec` (rejected —
reintroduces a host dependency, which Containerized Deployment disallows); a message
queue with separate scheduler/consumer services (rejected — unjustified complexity
at this scale).

**Risk noted**: a long-running ingest job in the background thread could, if not
implemented carefully, contend with the web server's event loop. Mitigation: the
scheduler thread does its own blocking I/O (HTTP fetches, SQLite writes) off the
FastAPI async event loop, so dashboard requests are not blocked by an in-progress
poll; this is a task-level implementation detail, not an architecture change.

## 6. De-duplication strategy

**Decision**: De-duplicate on a normalized natural key per signal type —
`(CIK, accession number, transaction line index)` for insider transactions sourced
from SEC, matched against OpenInsider-style records by `(ticker, filer name,
transaction date, share count)` fuzzy match; `(CIK, accession number, item type)`
for buyback disclosures.

**Rationale**: SEC accession numbers are globally unique and stable, giving an exact
key for SEC-sourced records and for detecting amended/corrected filings (same
accession number superseding an earlier one, satisfying the "amended filing" edge
case). The fuzzy match against OpenInsider-style records is necessarily approximate
since that source doesn't expose the accession number directly.

**Alternatives considered**: Hashing raw record content (rejected — an amended
filing intentionally changes content, which would defeat de-duplication rather than
supersede the record).

## 7. Email notifications

**Decision**: stdlib `smtplib` sending via a user-configured SMTP relay (e.g., the
user's own provider or a transactional SMTP service), address and credentials
supplied via environment variables.

**Rationale**: Avoids taking on a dedicated email-service SDK/dependency for a
single-recipient use case; SMTP is a well-understood, swappable integration point if
the user later prefers a specific provider.

**Alternatives considered**: A transactional email API/SDK (e.g., a provider-specific
client library) — not rejected outright, but deferred: nothing in the spec requires
provider-specific features (templates, analytics), so plain SMTP satisfies FR-011
through FR-013 with the least new dependency surface, per Simplicity.

## 8. Storage engine

**Decision**: SQLite, as a single file on a Docker-managed named volume, accessed
through SQLAlchemy.

**Rationale**: Once scheduling moved in-process (§5), there is exactly one process
reading and writing the database, which removes the only reason to run a separate
database server: concurrent multi-process access. SQLite fully supports a single
writer process with the read/query patterns this dashboard needs (SC-003's <3s load
over ~90 days of a low-hundreds-per-week signal volume is trivial for SQLite). This
also directly serves the user's stated goal of a single Compose service to spin up.

**Alternatives considered**: PostgreSQL (an earlier draft's decision — rejected on
reconsideration: it added a second container and a credentials surface to manage
for a benefit — a full client/server DBMS — that only matters with concurrent
writers or a need to query the data from outside the app, neither of which applies
here). If the system later grows a second consumer (e.g., a separate trading-bot
service reading these signals), this decision should be revisited then, not now
(Principle III: complexity justified by a *current* need).

## 9. Containerization layout

**Decision**: One Compose service, `app`, built from a single root `Dockerfile`,
running the FastAPI dashboard/API with the in-process scheduler (§5) and its SQLite
file (§8) on a named volume; a `.env` file (excluded from version control) supplies
SMTP credentials and default thresholds.

**Rationale**: With scheduling in-process and storage as an embedded file rather
than a server, nothing left in this feature needs a second container — matching
both the Constitution's Containerized Deployment standard and the user's explicit
preference for the simplest possible thing to spin up (`docker compose up`, one
service).

**Alternatives considered**: A separate `db` service (rejected, §8); a separate
`worker` service (rejected, §5). Both were this plan's original design and were
reversed after review concluded neither was backed by a measured, current need —
only by generic "separate concerns" best practice that doesn't hold up at this
project's actual scale (single user, single writer, no independent-scaling
requirement).
