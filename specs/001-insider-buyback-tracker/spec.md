# Feature Specification: Insider Trading & Buyback Signal Tracker

**Feature Branch**: `001-insider-buyback-tracker`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Build an insider-trading and buyback signal tracker: ingest SEC EDGAR Form 4 filings and OpenInsider-style aggregated data to detect (1) large or notable individual insider transactions by executives/directors/other tracked filers, and (2) corporate stock buybacks (companies repurchasing their own shares, e.g. a large company like Toyota buying $100M of its own stock) as a bullish signal. Surface both signal types in a dashboard the user can review, and send email notifications when new notable signals are detected, so the user can stay on top of market activity and decide when to buy. Do not include any trading bot or brokerage execution capability in this feature — that is explicitly out of scope and deferred."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review notable signals on a dashboard (Priority: P1)

As the user, I want a single dashboard where recently detected notable insider
transactions and corporate buyback signals are listed, so I can quickly scan what's
happening in the market without checking multiple sources myself.

**Why this priority**: This is the core value of the product — everything else
(notifications, filtering) is secondary to having a trustworthy, up-to-date list of
signals in one place. Without this, there is no product.

**Independent Test**: Can be fully tested by ingesting a batch of known SEC Form 4
filings and OpenInsider-style records (including at least one large insider buy and
one corporate buyback), then confirming both appear correctly on the dashboard with
accurate company, filer/transaction details, and dollar amounts — no notification
system required.

**Acceptance Scenarios**:

1. **Given** a new Form 4 filing discloses a director purchasing $2M of company
   stock, **When** the ingestion pipeline processes it, **Then** the transaction
   appears on the dashboard with the filer's name/role, company, transaction date,
   share count, price, and total value.
2. **Given** a company announces or executes a large buyback (e.g., $100M of its own
   shares), **When** the ingestion pipeline processes the disclosure, **Then** the
   buyback appears on the dashboard as a distinct signal type from insider
   transactions, with the company, disclosed amount, and disclosure date.
3. **Given** the dashboard is showing signals, **When** the user opens it, **Then**
   signals are sorted with the most recent first and each signal links back to its
   original source filing.
4. **Given** a routine, non-notable transaction (e.g., a small scheduled option
   exercise below the notability threshold), **When** it is ingested, **Then** it
   does NOT appear on the dashboard's default view.

---

### User Story 2 - Get emailed when a new notable signal appears (Priority: P2)

As the user, I want to receive an email as soon as a new notable insider transaction
or buyback is detected, so I don't have to keep the dashboard open to stay informed.

**Why this priority**: This turns the tracker from a "pull" tool the user must
remember to check into a "push" tool that surfaces opportunities in time to act on
them — but it depends on the detection/dashboard pipeline from User Story 1 already
existing.

**Independent Test**: Can be fully tested by feeding a known notable signal into the
already-working detection pipeline and confirming a single, correctly formatted
email is sent to the configured address within the target latency, without needing
to touch the dashboard UI at all.

**Acceptance Scenarios**:

1. **Given** the notability detection pipeline flags a new signal, **When** the
   signal is first recorded, **Then** an email is sent to the user's configured
   address containing the company, signal type, key figures, and a link to view it
   on the dashboard.
2. **Given** a signal was already emailed once, **When** the same underlying filing
   is re-processed (e.g., re-fetched by a scheduled poll), **Then** no duplicate
   email is sent for it.
3. **Given** multiple notable signals are detected in the same ingestion run,
   **When** notifications are sent, **Then** the user receives one email per signal
   (or a single batched digest covering all of them — see Assumptions), not a
   flood of indistinguishable messages.

---

### User Story 3 - Tune what counts as "notable" (Priority: P3)

As the user, I want to adjust the thresholds that decide whether a transaction or
buyback is "notable," so the dashboard and emails stay focused on signals I actually
care about instead of routine noise.

**Why this priority**: Valuable for reducing noise once the pipeline is live, but
the system is usable with sensible built-in defaults (see Assumptions) even before
this exists, so it is lower priority than detection and notification themselves.

**Independent Test**: Can be fully tested by changing a threshold value (e.g., the
minimum dollar amount for an insider buy) and confirming that previously-excluded
signals near the old threshold now appear (or previously-included ones disappear),
without needing any other part of the system to change.

**Acceptance Scenarios**:

1. **Given** the user lowers the minimum dollar threshold for insider buys,
   **When** the next ingestion run processes historical or new filings against the
   updated threshold, **Then** additional transactions that now qualify appear on
   the dashboard.
2. **Given** the user changes a threshold, **When** the change is saved, **Then** it
   takes effect for future detection without requiring a code change or redeploy.

---

### User Story 4 - Sort and search dashboard signals (Priority: P4)

As the user, I want to sort the dashboard by date, type, company, or amount, and
filter it with a free-text search, so I can quickly find a specific company's
signal or spot the largest transaction without scrolling through everything.

**Why this priority**: A pure usability improvement on top of the dashboard from
User Story 1 — valuable once there's enough signal history to make scanning
tedious, but the dashboard is fully usable without it, so it's the lowest
priority of the four stories.

**Independent Test**: Can be fully tested by loading a dashboard with multiple
signals, clicking each sortable column header and confirming rows reorder
correctly (ascending then descending), and typing into the search box and
confirming only matching rows remain visible — no ingestion or classification
changes required.

**Acceptance Scenarios**:

1. **Given** the dashboard is showing multiple signals, **When** the user clicks
   the "Amount" column header, **Then** rows reorder by amount ascending, and
   clicking it again reorders them descending.
2. **Given** the dashboard is showing multiple signals, **When** the user clicks
   the "Date" or "Company" column header, **Then** rows reorder accordingly.
3. **Given** the dashboard is showing multiple signals, **When** the user types
   text into the search box, **Then** only rows whose company, ticker, or details
   match that text remain visible, and the shown-count updates to match.

---

### User Story 5 - Control how many signals are shown at once (Priority: P5)

As the user, I want to choose how many signal rows are visible at a time — a fixed
count (10, 25, or 50) or an "infinite scroll" mode that reveals more automatically
as I scroll — so the dashboard stays manageable whether I have a handful of signals
or hundreds.

**Why this priority**: A display-density preference on top of the dashboard from
User Story 1 and the sort/search from User Story 4 — useful as signal history
grows, but the dashboard is fully usable with a single long list without it, so
it's the lowest priority story.

**Independent Test**: Can be fully tested by loading a dashboard with more rows
than the smallest page-size option, selecting each page-size option and confirming
only that many rows are visible at once (with a way to reach the rest), switching
to infinite scroll and confirming additional rows appear as the user scrolls near
the bottom, and reloading the page to confirm the last-selected option is still
applied — no ingestion, classification, or API changes required.

**Acceptance Scenarios**:

1. **Given** the dashboard has more signals than the smallest page-size option,
   **When** the user selects "10 rows," **Then** only 10 rows are visible at once
   and the user has a way to reach additional rows.
2. **Given** the user selects "25 rows" or "50 rows," **When** the selection is
   applied, **Then** the visible row count matches the selection.
3. **Given** the user selects "infinite scroll," **When** the user scrolls near the
   bottom of the visible rows, **Then** additional rows are automatically revealed
   without a page reload or an explicit "load more" click.
4. **Given** a sort order or search filter is active, **When** the user changes the
   page-size/infinite-scroll selection, **Then** the active sort and search results
   remain applied to the newly-visible rows rather than resetting.
5. **Given** the user selected a display option on a previous visit, **When** the
   user reloads or reopens the dashboard, **Then** the same option is still
   selected without the user having to reselect it.

---

### Edge Cases

- What happens when a Form 4 filing is later amended or corrected by the filer?
  The dashboard MUST reflect the corrected figures and MUST NOT show two
  conflicting entries for the same underlying event.
- How does the system handle an insider transaction that is a routine, scheduled
  sale (e.g., a pre-arranged 10b5-1 plan sale) rather than a discretionary buy?
  These MUST be distinguishable from discretionary buys so they don't get treated
  as a bullish signal.
- How does the system handle the same underlying event appearing in both the SEC
  EDGAR feed and the OpenInsider-style aggregated feed? It MUST be shown once, not
  duplicated.
- What happens when an upstream data source (SEC EDGAR or the aggregated feed) is
  temporarily unavailable or rate-limits the tracker? Ingestion MUST retry with
  backoff and MUST NOT silently skip a filing.
- What happens when a buyback is authorized (announced) but not yet executed, versus
  actually executed? These are different degrees of signal strength and MUST be
  distinguishable to the user.
- What happens when email delivery fails (bounced address, provider outage)? The
  signal MUST still be visible on the dashboard even if its notification failed.
- What happens when "infinite scroll" reaches the last available signal? The
  dashboard MUST indicate no further rows remain rather than showing a perpetual
  loading state.
- What happens when the total number of signals is smaller than the selected page
  size (e.g., "50 rows" selected but only 6 signals exist)? All available rows MUST
  be shown with no empty placeholder rows or pagination controls implying more
  exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ingest insider transaction data from SEC EDGAR Form 4
  filings on a recurring, automated schedule.
- **FR-002**: System MUST ingest an OpenInsider-style aggregated feed of insider
  transactions on a recurring, automated schedule, as a second, cross-checking
  source of the same underlying filings.
- **FR-003**: System MUST ingest corporate stock buyback disclosures (buyback
  program announcements and/or executed repurchases) on a recurring, automated
  schedule.
- **FR-004**: System MUST classify each ingested insider transaction as "notable"
  or "routine" based on BOTH the filer's role and the transaction's dollar value —
  a notable role (officer/director by default) alone is never sufficient; the
  applicable dollar threshold (lower for a notable role, higher otherwise) MUST
  also be met. System MUST default to a documented set of thresholds (see
  Assumptions) when no user configuration exists yet.
- **FR-005**: System MUST classify each ingested buyback disclosure as "notable" or
  not, based on a configurable minimum dollar amount.
- **FR-006**: System MUST distinguish discretionary insider buys/sells from routine,
  pre-scheduled transactions (e.g., 10b5-1 plan activity), and MUST exclude routine
  transactions from "notable" classification by default.
- **FR-007**: System MUST de-duplicate signals that represent the same underlying
  filing or disclosure across data sources, so each real-world event appears exactly
  once.
- **FR-008**: System MUST retain, for every stored signal, its data provenance
  (originating source, source URL or filing identifier, and fetch timestamp).
- **FR-009**: System MUST present a dashboard listing notable signals, showing at
  minimum: company/ticker, signal type (insider transaction vs. buyback), key
  figures (dollar value, shares, price), relevant date, and a link to the source
  filing.
- **FR-010**: Dashboard MUST default to showing notable signals sorted by most
  recent first, and MUST allow the user to view the underlying routine transactions
  that were excluded, on request.
- **FR-011**: System MUST send an email notification to a user-configured address
  when a new notable signal is first recorded.
- **FR-012**: System MUST NOT send more than one notification for the same
  underlying signal, even if the source data is re-fetched or re-processed.
- **FR-013**: System MUST continue to record and display a signal on the dashboard
  even if its email notification fails to send.
- **FR-014**: System MUST allow the user to adjust notability thresholds (dollar
  amounts for insider transactions and for buybacks) without requiring a code
  change.
- **FR-015**: System MUST handle upstream data source unavailability by retrying
  with backoff, and MUST NOT silently drop a filing it failed to fetch or parse.
- **FR-016**: When the underlying filing behind a recorded signal is later amended
  or corrected by the filer, the system MUST ensure only the current signal for
  that underlying event is ever shown to the user — the prior signal MUST NOT
  remain visible as a separate, conflicting entry alongside the corrected one.
- **FR-017**: System MUST NOT provide any capability to place, execute, or transmit
  trades to a brokerage — this feature is limited to detection, display, and
  notification only.
- **FR-018**: Dashboard MUST allow the user to sort the displayed signals by date,
  signal type, company, and amount, in either ascending or descending order.
- **FR-019**: Dashboard MUST allow the user to filter displayed signals with a
  free-text search matching against company name, ticker, and signal details.
- **FR-020**: Dashboard MUST allow the user to choose how many signal rows are
  visible at once: a fixed count of 10, 25, or 50, or an "infinite scroll" mode.
- **FR-021**: When "infinite scroll" is selected, dashboard MUST automatically
  reveal additional rows as the user scrolls near the bottom of the currently
  visible rows, without requiring an explicit "load more" action or page reload.
- **FR-022**: Dashboard MUST persist the user's selected page-size/infinite-scroll
  preference across page reloads.
- **FR-023**: When a fixed page size is selected, dashboard MUST provide a way to
  reach rows beyond the current page without losing the active sort order or
  search filter.

### Key Entities

- **Insider Transaction**: A single disclosed trade by a company insider (officer,
  director, or other tracked filer). Attributes include filer name, filer role,
  company/ticker, transaction type (buy/sell), whether it is discretionary or
  routine/scheduled, share count, price per share, total dollar value, transaction
  date, filing date, source, and source reference (filing identifier/URL).
- **Buyback Event**: A disclosed corporate stock repurchase action. Attributes
  include company/ticker, disclosure type (authorization/announcement vs. executed
  repurchase), disclosed or executed dollar amount, disclosure date, source, and
  source reference.
- **Signal**: The notable-or-not classification wrapping either an Insider
  Transaction or a Buyback Event once it has been evaluated against current
  thresholds. Attributes include signal type, notability status, the threshold
  values it was evaluated against, and notification status (sent/failed/not
  applicable).
- **Notability Threshold Configuration**: The current set of user-adjustable rules
  used to classify signals as notable (e.g., minimum dollar value for insider buys,
  minimum dollar value for buybacks, included/excluded filer roles).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A newly published, notable SEC-disclosed insider transaction or
  buyback appears on the dashboard within 24 hours of becoming publicly available.
- **SC-002**: At least 95% of notable signals result in a delivered email
  notification within 1 hour of the signal first appearing on the dashboard.
- **SC-003**: The dashboard loads and displays at least the last 90 days of notable
  signals in under 3 seconds under normal use.
- **SC-004**: Zero duplicate dashboard entries are produced for the same real-world
  filing or disclosure when it appears in more than one ingested data source.
- **SC-005**: After adjusting a notability threshold, the change is reflected in
  what qualifies as "notable" for all signals processed from that point forward,
  with no code change required.
- **SC-006**: The user can distinguish, without opening the source filing, whether a
  listed insider transaction was discretionary or a routine/scheduled transaction.
- **SC-007**: A user can locate the largest signal by amount, or all signals for a
  specific company, using only on-page sorting and search — no page reload or
  separate query required.
- **SC-008**: A user can switch between page-size options or infinite scroll and
  see the change take effect immediately, with no full page reload.
- **SC-009**: A user's page-size/infinite-scroll preference from a previous visit
  is still applied the next time they open the dashboard, without reselecting it.

## Assumptions

- This is a single-user, personal tool (the requester's own use); multi-user
  accounts, roles, and authentication/authorization are out of scope for this
  feature.
- Default notability thresholds (adjustable via User Story 3) are: insider
  transactions — a discretionary buy is notable if its dollar value meets the
  threshold that applies to the filer's role: $100,000 or more for a Section 16
  officer/director (the "notable role" threshold), or $1,000,000 or more for any
  other filer. **Role alone never makes a transaction notable** — a $500 buy by a
  director is not notable, and a $150,000 buy by a non-officer/director filer is
  not notable either; both the role-appropriate threshold and the dollar amount
  must be satisfied together. (This replaces an earlier draft of this assumption
  that used "value OR role," which — as flagged during `/speckit-analyze` — made
  any officer/director buy notable regardless of size; the user confirmed AND
  semantics with a $100,000 role-specific floor.) Buybacks remain a single
  threshold: disclosed or executed amount of $50,000,000 or more. These defaults
  are a starting point, not a fixed business rule.
- SEC EDGAR (Form 4 / full-text search) and an OpenInsider-style feed are both
  reachable as public data sources without requiring a paid data subscription for
  v1.
- Email is the only notification channel required for v1; other channels (SMS,
  push, Slack, etc.) are out of scope unless requested later.
- The default notification pattern is one email per notable signal as it's
  detected; a batched/digest mode may be considered later but is not required for
  v1's acceptance.
- "Recurring, automated schedule" for ingestion means a periodic poll (e.g., on the
  order of hourly), not real-time streaming; exact frequency is an implementation
  decision made during planning, not a product requirement.
- No trading, order placement, or brokerage integration of any kind is included in
  this feature, per explicit user instruction and per the project constitution's
  Principle V (Financial Safety & Human Oversight for Automated Trading), which
  gates that capability behind a separate, future feature.
- Sorting and search (User Story 4) operate entirely on signals already sent to
  the page; there is no separate paginated "load more as you scroll/search" query.
  This is sufficient at the scale described above and keeps the feature dependency-
  free (no new JS framework). Interactive sort/search behavior is verified by
  manual browser testing rather than an automated test, consistent with
  Constitution Principle I's scope (data ingestion, parsing, and business logic) —
  automated coverage here is limited to asserting the dashboard renders the
  sortable headers and per-row data attributes the client-side behavior depends on.
- Page-size/infinite-scroll (User Story 5) extends the same client-side-only
  approach as User Story 4: the server continues to render all currently-notable
  signals into the page in one response (raising the dashboard's effective row
  cap as needed so this stays true at the user's actual data volume), and
  "10/25/50 rows" or "infinite scroll" purely controls how many of those
  already-rendered rows are revealed at once — no new `/api/signals` query
  parameters, pagination endpoint, or JS framework are introduced. This keeps
  page-size interacting correctly with sort/search "for free," since both
  features operate on the same already-loaded row set. The selected preference
  persists via the browser's local storage (not a server-side user setting,
  consistent with this being a single-user, no-accounts tool per the assumption
  below). Like User Story 4, this is verified by manual browser testing rather
  than an automated test.
