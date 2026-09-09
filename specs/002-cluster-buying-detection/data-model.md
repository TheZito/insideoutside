# Phase 1 Data Model: Cluster Buying Detection

Additive to specs/001-insider-buyback-tracker/data-model.md. Only new/changed
fields are shown below; everything else from 001 is unchanged.

## InsiderTransaction (extended)

| Field | Type | Notes |
|---|---|---|
| filer_id | string, nullable | NEW. SEC `rptOwnerCik` when available (SEC-sourced); null for OpenInsider-sourced candidates without one. Used as the preferred distinct-filer identity for clustering (research.md §2). |

## ClusterBuyEvent (new)

Represents a detected group of discretionary buys by different insiders at the
same company within a window.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| company_name | string | |
| ticker | string, nullable | |
| cik | string | clustering is scoped to one company (spec Assumptions) |
| window_start | date | earliest contributing transaction's `transaction_date` |
| window_end | date | latest contributing transaction's `transaction_date` |
| distinct_filer_count | integer | count of distinct filers, by `filer_id` falling back to normalized `filer_name` (research.md §2) |
| total_value | decimal | sum of contributing transactions' `total_value` |
| contributing_transaction_ids | JSON array of UUID | the `InsiderTransaction` ids that make up this cluster (research.md §4) |
| updated_at | timestamp | last time this cluster's membership/aggregates were recomputed |
| created_at | timestamp | |

**Validation rules**:
- `distinct_filer_count` MUST equal the number of distinct filer identities among
  `contributing_transaction_ids`' underlying transactions — this is a
  computed/derived field, recorded (not independently settable) so the dashboard
  doesn't need to re-derive it on every read.
- `window_end - window_start` MUST NOT exceed the `cluster_window_days` threshold
  in effect at the time the cluster was (re)computed — this is the invariant the
  grouping algorithm (research.md §1) guarantees by construction, and is the
  thing that makes two overlapping-in-time groups "the same cluster" or not.

**Identity across recomputation**: a recomputed group is matched to an existing
`ClusterBuyEvent` for the same company by **contributing-transaction-id overlap**
(sharing at least one id), not by company alone — a single company can have
multiple, unrelated `ClusterBuyEvent` rows over time (research.md §5). On each
`classify` run, for any company with new or changed qualifying transactions, a
matched row's membership and aggregate fields are replaced in place (an update,
not a new row, per FR-005); an unmatched group becomes a new row.

## Signal (extended)

| Field | Type | Notes |
|---|---|---|
| signal_type | enum(insider_transaction, buyback, **cluster_buy**) | NEW variant |
| cluster_buy_event_id | UUID (FK, nullable) | NEW. Set when `signal_type = cluster_buy`, parallel to the existing `insider_transaction_id`/`buyback_event_id` |
| is_discretionary | boolean, nullable | null for `cluster_buy` signals too (it's a property of individual transactions, not the cluster as a whole) |

**State transitions**: unchanged from 001 — a cluster `Signal` follows the exact
same `not_applicable`/`pending`/`sent`/`failed` and `is_superseded` lifecycle as
the other two types. Recomputing a cluster's aggregates (research.md §5) does
NOT reset `notification_status` back to `pending` if it was already `sent`
(FR-007/SC-002: no re-notification).

## ThresholdConfiguration (extended)

| Field | Type | Notes |
|---|---|---|
| cluster_window_days | integer | NEW. Default 14 (spec Assumptions). |
| min_cluster_filer_count | integer | NEW. Default 2 (spec Assumptions). |

**Validation rules**: both NEW fields MUST be positive integers
(`cluster_window_days >= 1`, `min_cluster_filer_count >= 2` — a "cluster" of one
filer isn't a cluster).

## Relationships

```text
ClusterBuyEvent 1 --- 0..1 Signal
ClusterBuyEvent *contributing_transaction_ids* --> many InsiderTransaction (by id, JSON list, not a FK constraint)
ThresholdConfiguration (singleton, referenced by value at cluster detection/classification time)
```
