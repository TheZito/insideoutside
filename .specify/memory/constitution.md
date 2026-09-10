<!--
Sync Impact Report
- Version change: 1.1.0 → 1.2.0
- Modified principles: none
- Added sections:
  - Containerized Deployment (new cross-cutting standard: the system MUST run as
    Docker containers, orchestrated via a single docker-compose.yml)
- Removed sections: none
- Deferred items: none
- Templates checked for alignment: plan-template.md, spec-template.md, tasks-template.md,
  checklist-template.md (no agent-specific placeholders requiring edits found; these read
  the constitution at runtime and are not modified by this command). Note for
  /speckit-plan on the in-progress 001-insider-buyback-tracker feature: its Technical
  Context MUST reflect this containerization requirement.
-->

# insideoutside Constitution

## Core Principles

### I. Test-First (NON-NEGOTIABLE)
Tests MUST be written before implementation for all data ingestion, parsing, and
business logic. The Red-Green-Refactor cycle is strictly enforced: write a failing
test, get it approved as reflecting the intended behavior, then implement until it
passes. No feature or bugfix MUST be merged without a test that reproduces the
behavior it establishes or fixes.
**Rationale**: This project surfaces financial data people may act on. Manual QA
cannot enumerate every filing format or edge case; regression tests are the only
durable guarantee that behavior stays correct as the codebase evolves.

### II. Data Accuracy & Source Integrity
All ingested data — SEC EDGAR/Form 4 filings, OpenInsider-style aggregated feeds,
and corporate buyback disclosures — MUST be validated against its source schema
before persistence. This includes both signal types the tracker exists to surface:
large or notable individual insider transactions (executives, directors, other
tracked filers) and companies repurchasing their own stock. Every derived or stored
record MUST retain provenance (source URL/filing identifier, fetch timestamp).
Parsing or validation failures MUST fail loudly (raise, log, and surface) and MUST
NOT be silently dropped, coerced, or defaulted. Any discrepancy between source data
and stored data MUST be treated and tracked as a bug, not an accepted edge case.
**Rationale**: The user acts on this data — first as a dashboard/alert signal, later
as direct input to an automated trading bot. Silent data corruption or quiet gaps are
strictly worse than a visible outage, because they erode trust without anyone
noticing until money is on the line.

### III. Simplicity & YAGNI
Every feature starts with the simplest design that satisfies its current, stated
requirement. New abstraction layers, configuration options, generalized frameworks,
or infrastructure (extra services, caches, queues) MUST NOT be introduced for
hypothetical future needs. Any added complexity MUST be justified by a measured,
present need, documented in the change that introduces it.
**Rationale**: Keeps a focused tracker maintainable by a small team, avoids premature
architecture, and keeps the codebase legible for the data-integrity work that matters
more than infrastructure sophistication.

### IV. CLI-First & Library-First Architecture
Core logic (scraping, parsing, filtering, alerting, scoring) MUST be implemented as
standalone, independently testable modules or libraries before any UI or API wraps
them. Each library MUST expose its functionality via a CLI entry point using a
text in/out protocol (stdin/args → stdout, errors → stderr), so it can be scripted,
composed, and run from cron/automation without a UI.
**Rationale**: Decouples business logic from presentation, keeps logic testable in
isolation (supporting Principle I), and makes the tracker automatable for scheduled
data pulls and alerts.

### V. Financial Safety & Human Oversight for Automated Trading
This project's end goal includes a bot that connects to a brokerage account and
executes trades against a limited pool of funds, informed by the insider/buyback
signals this system detects. Any code that can place a live trade MUST be built and
proven in a simulated/paper-trading mode first, using historical or delayed data,
before it is allowed to touch a real brokerage connection. Live trading MUST be
gated behind an explicit, human-set configuration flag that defaults to off and MUST
NOT be enabled by any automated process. The bot MUST operate within an explicit,
human-configured funds cap and per-trade/position size limit, and MUST support an
immediate human-triggered kill switch that halts all new order placement. Every
signal that leads to a trade decision, and the decision itself, MUST be logged in a
form a human can audit after the fact.
**Rationale**: Once this system can move real money, a bug is no longer a bad
dashboard row — it is a financial loss. These constraints exist so automation is
additive to the user's judgment, not a replacement for it, and so failures are
capped and reviewable rather than open-ended.

## Data Handling & Compliance Standards

Filing and market data is public, but upstream sources impose usage constraints
that MUST be respected: scrapers MUST implement rate limiting and backoff, and MUST
honor documented rate limits and robots.txt of any scraped source (e.g., SEC EDGAR,
openinsider.com). Storage MUST NOT include personal data beyond what is already
present in the public filing itself. Secrets (API keys, notification credentials,
tokens) MUST NOT be committed to the repository and MUST be supplied via environment
variables or a secrets manager. Brokerage API keys and credentials are the
highest-sensitivity secret this project handles: they MUST NOT appear in logs, error
messages, or committed files, and access to them MUST be limited to the trading bot
component described in Principle V.

## Containerized Deployment

The entire system — every service required to build, run, and test it end to end
(ingestion workers/schedulers, the dashboard/web service, its database, and any
supporting services such as a mail sender) — MUST run as Docker containers and MUST
be brought up as a whole via a single `docker compose up` against a
`docker-compose.yml` at the repository root. Any new service added to the system
MUST be added to this compose definition; there MUST NOT be a service that only runs
"on the host" outside of Docker. Local development and CI MUST NOT require
installing language runtimes, databases, or other dependencies directly on the host
to build, run, or test the system — Docker is the supported, canonical way to do so.
Runtime secrets/credentials (mailer credentials, future brokerage credentials, etc.)
MUST be supplied to containers via environment variables or an env file excluded
from version control, never baked into an image, per the existing secrets-handling
requirement above.
**Rationale**: A single `docker compose up` keeps the system reproducible and
portable regardless of the host machine, and avoids "works on my machine" drift
between the ingestion pipeline, dashboard, and (eventually) the trading bot as more
services are added.

## Development Workflow

All changes MUST go through review before merging to the main branch. Continuous
integration MUST run the full automated test suite, and it MUST pass before a change
is merged. Any change touching data-parsing or scoring logic MUST include or update
tests that cover the changed behavior, per Principle I.

## Governance

This constitution supersedes all other project practices, conventions, and
informal agreements. Amendments require: (1) a documented rationale for the change,
(2) a version bump following semantic versioning (MAJOR for backward-incompatible
principle removals/redefinitions, MINOR for new principles or materially expanded
guidance, PATCH for clarifications and wording fixes), and (3) propagation of the
change to any dependent templates or agent guidance files that reference these
principles. All pull requests and reviews MUST verify compliance with these
principles; any deviation or added complexity MUST be explicitly justified in the
change description. Use repository-level agent guidance files (e.g., CLAUDE.md) for
day-to-day development conventions that supplement, but never contradict, this
constitution.

**Version**: 1.2.0 | **Ratified**: 2026-09-07 | **Last Amended**: 2026-09-07
