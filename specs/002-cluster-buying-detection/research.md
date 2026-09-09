# Phase 0 Research: Cluster Buying Detection

## 1. Grouping algorithm

**Decision**: Per company (by CIK), sort qualifying transactions (discretionary,
buy, not superseded) by `transaction_date`. Walk the sorted list with a greedy
sliding window: start a new group at the first transaction; while the next
transaction's date is within `cluster_window_days` of the *current group's start
date*, add it to the group; otherwise close the current group and start a new one
at that transaction. A group becomes a cluster candidate if it contains 2+
distinct filers (by `filer_id`, falling back to normalized `filer_name`).

**Rationale**: This is a single linear pass per company, easy to reason about and
test, and matches the spec's Assumption that a cluster's window is anchored to its
own contributing transactions' span rather than a fixed calendar window relative
to "today." At this project's data volumes (tens of transactions per company at
most), a more sophisticated interval-clustering algorithm would be unjustified
complexity (Constitution Principle III).

**Alternatives considered**: A true "any two transactions within window_days of
each other are linked, transitively" (union-find) approach — more correct in
theory for irregular gaps, but meaningfully more complex to implement and test
for a difference that, at this scale, is very unlikely to matter (insider buying
clusters are rare events, not high-frequency data). Deferred unless real usage
shows the greedy approach mis-groups something in practice.

## 2. Distinct-filer identity

**Decision**: Add an optional `filer_id` field to `InsiderTransaction`, populated
from the Form 4 XML's `rptOwnerCik` (already parsed and available in
`sec_edgar_form4.py`, just not currently retained). Use `filer_id` for distinct-
filer counting when present, falling back to a normalized (lowercased, trimmed)
`filer_name` when absent (e.g., for OpenInsider-sourced candidates, which don't
expose a filer CIK).

**Rationale**: `rptOwnerCik` is a stable SEC-assigned identifier for the
reporting person, so it's a strictly better identity key than name matching
(handles name variants/typos, avoids conflating two different people who happen
to share a name). It costs nothing extra to fetch since the parser already reads
that XML node for role determination — this just retains a field already in hand.

**Alternatives considered**: Name-only matching (rejected as the primary key —
weaker identity, though kept as the necessary fallback for the source that
doesn't expose a filer CIK at all).

## 3. Where cluster detection runs

**Decision**: Inside the existing `classify` CLI command, as an added pass after
the existing per-record classification loop, in a new
`classification/cluster_buying.py` module.

**Rationale**: `classify` already owns "evaluate ingested records against current
thresholds and update signals" — cluster detection is exactly that, just grouped
across records instead of per-record. No new CLI subcommand, no new scheduler
job; the existing hourly `ingest → classify → notify` cycle picks this up for
free (research.md §5 in 001).

**Alternatives considered**: A separate `cluster` CLI subcommand run on its own
schedule — rejected as unjustified complexity; nothing about cluster detection
needs a different cadence than the classification it's part of.

## 4. Storage shape

**Decision**: A new `cluster_buy_events` table (`ClusterBuyEventORM`) with a JSON
column listing contributing `InsiderTransaction` ids — the same pattern already
used for `ThresholdConfiguration.notable_filer_roles`, rather than a many-to-many
join table.

**Rationale**: At this scale (a handful of contributing transactions per
cluster, at most), a join table buys referential integrity the codebase doesn't
otherwise lean on, at the cost of an extra table and extra queries. The JSON-list
pattern is already established in this codebase for exactly this kind of small,
bounded collection.

**Alternatives considered**: A `cluster_buy_event_id` foreign key directly on
`InsiderTransaction` (one cluster per transaction) — rejected because a
transaction that's part of one cluster could plausibly need re-grouping if
earlier data is amended/superseded; keeping the list on the cluster side (rebuilt
each classify run for the affected company) is simpler to keep correct than
maintaining a back-reference on every transaction.

## 5. Cluster signal recomputation vs. append-only

**Decision**: Each `classify` run recomputes cluster groupings for companies with
new or changed qualifying transactions since the last run. A recomputed group is
matched against existing `ClusterBuyEvent` rows for that company **by
contributing-transaction-id overlap**, not by company alone — a company CAN have
multiple, unrelated `ClusterBuyEvent`s over time (e.g., a cluster in January and
an unrelated one in June share nothing and must stay two separate rows). If a
recomputed group shares at least one `contributing_transaction_id` with an
existing row, that row's membership/aggregate fields are **replaced** in place
(not a new row); a group sharing no transaction with any existing row becomes a
new `ClusterBuyEvent`. This matches FR-005's "update, not duplicate." A `Signal`
already `sent` for a cluster stays `sent` (no re-notification) even as the
`ClusterBuyEvent` it wraps is updated in place, per FR-007/SC-002.

**Interaction with a window-length change (User Story 3)**: changing
`cluster_window_days` and running `classify --reclassify` re-groups from scratch
and can *split* a previously-single cluster into two smaller ones (or merge two
into one, for a widened window). When a split leaves a `sent` cluster's original
transaction set divided across pieces that individually no longer meet
`min_cluster_filer_count`, the original `ClusterBuyEvent` row is matched (by the
overlap rule above) to whichever resulting piece contains a majority of its
original `contributing_transaction_ids`, and updated in place with the smaller
membership; its `Signal.is_notable` flips to `false` if that piece no longer
meets the minimum, but `notification_status` is left as `sent` (it was already
delivered — 001 already treats a signal's `notification_status` as a one-way
history of "was this emailed," not a live reflection of current notability;
see 001 research.md §6 for the analogous precedent with amended filings). The
other piece, if it independently meets the minimum, is created as a new
`ClusterBuyEvent` with its own new `Signal` (which CAN be notified, since it's a
distinct signal, not a duplicate of the original).

**Rationale**: Directly implements FR-005's "update an existing cluster signal ...
rather than creating a duplicate" and User Story 2's "no second email" acceptance
scenario, using the same notification-status state machine 001 already built for
the other two signal types (no new state machine needed). Matching by
transaction-id overlap (rather than by company) is the only rule that stays
correct both for the common case (a cluster simply grows) and the less common
one (a config change reshapes it).

**Alternatives considered**: Treating each `classify` run's grouping as
immutable and superseding the old `ClusterBuyEvent` the way amended filings
supersede old `InsiderTransaction`s (001 research.md §6) — considered, but
rejected as unnecessary indirection here: a cluster isn't "corrected" the way an
amended SEC filing is, it just grows, so in-place update of the aggregate fields
is simpler and matches the natural mental model of "the cluster now includes one
more buyer."
