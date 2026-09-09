# Feature Specification: Cluster Buying Detection

**Feature Branch**: `002-cluster-buying-detection`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Detect insider 'cluster buying': when multiple different insiders (officers, directors, or other tracked filers) at the same company each make discretionary open-market buys within a short rolling time window, treat that as its own notable signal, distinct from and in addition to the existing single-transaction notability check -- since multiple insiders buying around the same time is a stronger conviction signal than any one of those buys evaluated in isolation, even if some of the individual buys wouldn't have cleared the existing per-transaction dollar thresholds on their own. This extends the existing insider-buyback-tracker feature (specs/001-insider-buyback-tracker) with a new signal type; it does not change buyback detection or email/dashboard mechanics, which should be reused as-is for this new signal type."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See cluster buying as its own signal on the dashboard (Priority: P1)

As the user, I want the dashboard to call out when multiple different insiders at the
same company have bought stock within a short window of each other, so I can spot a
stronger conviction signal that a single insider's purchase wouldn't show on its own.

**Why this priority**: This is the entire value of the feature — everything else
(notification, tuning) is secondary to the detection and its visibility.

**Independent Test**: Ingest Form 4 fixtures for two different filers at the same
company buying within the detection window (including at least one buy too small to
be notable on its own per the existing per-transaction rule), classify, and confirm a
distinct cluster signal appears on the dashboard showing the company, the number of
distinct filers, the date range, and the combined dollar value.

**Acceptance Scenarios**:

1. **Given** two different insiders at the same company each make a discretionary
   open-market buy within the configured window, **When** the system classifies
   ingested data, **Then** a cluster signal is created showing both filers'
   contribution, the window's date range, and the combined value.
2. **Given** one of those two buys is below the existing single-transaction dollar
   threshold, **When** classification runs, **Then** that transaction still counts
   toward the cluster even though it isn't independently notable.
3. **Given** the same filer buys twice within the window, **When** classification
   runs, **Then** that filer counts once toward the distinct-filer count, not twice.
4. **Given** only one insider at a company has bought recently, **When**
   classification runs, **Then** no cluster signal is created for that company.
5. **Given** a corporate buyback and two insiders' individual buys happen at the same
   company around the same time, **When** classification runs, **Then** the buyback
   is NOT counted toward the cluster (cluster buying is about multiple people, not a
   single corporate action).

---

### User Story 2 - Get emailed when a new cluster signal appears (Priority: P2)

As the user, I want an email when a cluster buying signal first becomes notable, the
same way I already get emailed for other notable signals, so cluster buying doesn't
require me to check the dashboard to notice it.

**Why this priority**: Depends on User Story 1's detection existing; reuses the
already-built notification mechanism rather than adding a new one.

**Independent Test**: Feed a qualifying cluster into the already-working detection
pipeline and confirm exactly one email is sent, using the existing notification
system's format and delivery guarantees.

**Acceptance Scenarios**:

1. **Given** a cluster signal newly crosses the notable threshold, **When** the
   notification step runs, **Then** an email is sent identifying the company, the
   number of distinct filers involved, and the combined value.
2. **Given** a cluster signal has already been notified, **When** an additional
   qualifying transaction later joins the same cluster within its window, **Then**
   no second email is sent for that cluster (the existing signal is updated, not
   re-notified).

---

### User Story 3 - Tune cluster detection sensitivity (Priority: P3)

As the user, I want to adjust how many distinct insiders are required, and how wide
the time window is, so I can control how sensitive cluster detection is to noise.

**Why this priority**: Valuable for reducing noise once the feature is live, but the
feature is usable with sensible defaults even before this exists.

**Independent Test**: Change the minimum distinct-filer count or window length and
confirm that previously-qualifying or previously-excluded clusters change status
accordingly on the next classification run.

**Acceptance Scenarios**:

1. **Given** the user raises the minimum distinct-filer count, **When**
   classification next runs, **Then** clusters that no longer meet the new minimum
   stop being notable going forward.
2. **Given** the user changes the window length, **When** classification next runs,
   **Then** grouping of transactions into clusters reflects the new window.

---

### Edge Cases

- What happens when the same filer buys multiple times within the window? Counted
  once toward the distinct-filer count (per Acceptance Scenario 3); the additional
  purchase still adds to the cluster's combined dollar value.
- What happens when a corporate buyback occurs alongside insider buying at the same
  company? The buyback is never counted toward a cluster — cluster buying is
  specifically about multiple distinct people, not a single corporate action (per
  Acceptance Scenario 5).
- What happens when a routine, non-discretionary transaction (e.g., a 10b5-1 plan
  buy) occurs within the window? It MUST NOT count toward the cluster, for the same
  reason it isn't independently notable — it doesn't reflect spontaneous conviction.
- What happens when insiders at two different companies buy on the same day? They
  MUST NOT be grouped together — clustering is scoped to a single company.
- What happens when a cluster's contributing transactions are later amended or
  superseded (per 001's supersession handling)? The cluster MUST reflect the current,
  non-superseded transactions only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect when two or more distinct insiders (filers) at the
  same company each make a discretionary open-market buy within a rolling time
  window.
- **FR-002**: System MUST evaluate a detected cluster as its own signal, independent
  of whether its underlying individual transactions were already notable on their
  own.
- **FR-003**: A cluster MUST become notable when the number of distinct contributing
  filers meets or exceeds a configurable minimum (default: 2).
- **FR-004**: System MUST record, for each cluster signal, the contributing filers
  and their transactions, the window's date range, the company, and the combined
  dollar value.
- **FR-005**: System MUST update an existing cluster signal as additional qualifying
  transactions arrive within its window, rather than creating a duplicate cluster
  signal for the same company and window.
- **FR-006**: Dashboard MUST display cluster signals distinctly from single-insider-
  transaction and buyback signals, showing the company, distinct filer count, window
  date range, and combined value.
- **FR-007**: System MUST send an email notification when a cluster signal first
  becomes notable, reusing the existing notification mechanism and its
  duplicate-prevention guarantee (no repeat email as the same cluster is later
  updated).
- **FR-008**: System MUST allow the user to adjust the cluster window length and the
  minimum distinct-filer count without requiring a code change.
- **FR-009**: A transaction MUST be able to contribute to a cluster regardless of
  whether it individually cleared the existing per-transaction notability thresholds.
- **FR-010**: System MUST count a filer only once toward a cluster's distinct-filer
  count no matter how many qualifying purchases that filer makes within the window.
- **FR-011**: System MUST exclude corporate buybacks, sells, and non-discretionary
  transactions (e.g., 10b5-1 plan activity) from cluster grouping entirely.
- **FR-012**: System MUST NOT alter existing buyback detection, existing
  single-transaction notability classification, or the existing dashboard/email
  mechanics for those two signal types.

### Key Entities

- **Cluster Buy Event**: Represents a detected group of discretionary buys by
  different insiders at the same company within a window. Attributes: company/
  ticker/CIK, window start date and end date (the earliest and latest contributing
  transaction dates), distinct filer count, combined dollar value, and the set of
  contributing insider transactions.
- **Signal** (existing entity, extended): gains a third signal type, "cluster buy,"
  alongside the existing "insider transaction" and "buyback" types, following the
  same notability/notification lifecycle already defined for those.
- **Cluster Detection Configuration** (existing Notability Threshold Configuration,
  extended): gains the window length and minimum distinct-filer count, adjustable
  the same way existing thresholds are (see 001's User Story 3).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When two or more distinct insiders at the same company buy within the
  configured window, a cluster signal appears on the dashboard within one
  classification cycle, showing the correct company, filer count, and combined value.
- **SC-002**: The user receives exactly one email per cluster as it first becomes
  notable — no duplicate emails as the same cluster is later updated with additional
  contributing transactions.
- **SC-003**: Existing single-transaction and buyback detection, classification, and
  notification behavior is unchanged by this feature — 001's existing acceptance
  criteria and test suite continue to pass unmodified.
- **SC-004**: The cluster window length and minimum distinct-filer count can be
  changed without a code change or redeploy, and take effect on the next
  classification run.

## Assumptions

- Default cluster detection settings: a 14-day window and a minimum of 2 distinct
  filers. Like all other notability thresholds in this project, these are a starting
  point, adjustable via the same mechanism as existing thresholds (001 User Story 3),
  not a fixed business rule.
- A cluster's window is anchored to its contributing transactions' own dates (the
  span between the earliest and latest qualifying transaction), not a fixed calendar
  window relative to "today." A formed cluster signal is therefore a stable
  historical record and does not disappear or lose notability purely because time
  has passed.
- Clustering is scoped to a single company (by CIK); insiders at different companies
  are never grouped together regardless of timing.
- Only discretionary open-market buys count toward a cluster — the same
  discretionary-only rule already used for single-transaction notability (per
  001's spec). Sells, routine/10b5-1 transactions, and corporate buybacks are
  excluded from cluster grouping entirely (FR-011).
- Once a cluster first becomes notable and is emailed, later-arriving contributing
  transactions within the same window update the existing cluster signal's recorded
  fields (filer count, combined value) but do not trigger a second email, mirroring
  the no-duplicate-notification guarantee already defined for other signal types in
  001.
- This feature reuses 001's existing ingestion, dashboard, and notification
  mechanics as-is; it introduces no new data source and no new ingestion pipeline —
  cluster detection runs against InsiderTransaction records 001 already ingests.
