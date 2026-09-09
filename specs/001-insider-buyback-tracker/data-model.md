# Phase 1 Data Model: Insider Trading & Buyback Signal Tracker

Entities correspond to the Key Entities section of [spec.md](./spec.md). All
persisted records carry provenance fields to satisfy Constitution Principle II and
spec FR-008.

## InsiderTransaction

Represents one disclosed trade by a company insider.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| company_name | string | |
| ticker | string | nullable — some filers/issuers lack a public ticker |
| cik | string | SEC Central Index Key of the issuer |
| filer_name | string | |
| filer_role | enum(officer, director, ten_percent_owner, other) | drives role-based notability (FR-004) |
| transaction_type | enum(buy, sell) | |
| transaction_code | string | raw SEC Form 4 transaction code (e.g., P, S, F, A) |
| is_discretionary | boolean | derived from transaction_code + 10b5-1 footnote presence (FR-006) |
| share_count | decimal | |
| price_per_share | decimal | nullable — some codes (e.g., gifts) have no price |
| total_value | decimal | `share_count * price_per_share`, or null if price is null |
| transaction_date | date | |
| filing_date | date | |
| source | enum(sec_edgar, openinsider) | |
| source_ref | string | SEC accession number, or OpenInsider record identifier |
| source_url | string | |
| fetched_at | timestamp | |
| superseded_by_id | UUID (FK, nullable) | set when a later amendment replaces this record (edge case: amended filings) |

**Validation rules**: `transaction_type`, `share_count`, `transaction_date`,
`filing_date`, `source`, `source_ref` are required; a record failing schema
validation is rejected and logged, never partially persisted (Constitution
Principle II).

**Uniqueness**: `(source, source_ref)` unique for `sec_edgar`-sourced rows (accession
number + line index, per research.md §6); `openinsider`-sourced rows are linked to an
existing `sec_edgar` row via fuzzy match where possible instead of creating a
duplicate `InsiderTransaction`.

## BuybackEvent

Represents one disclosed corporate stock repurchase action.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| company_name | string | |
| ticker | string | |
| cik | string | |
| disclosure_type | enum(authorized, executed) | distinguishes announcement vs. actual repurchase (edge case) |
| amount | decimal | dollar amount authorized or repurchased in the disclosed period |
| disclosure_date | date | |
| source | enum(sec_edgar) | v1 sources buybacks from SEC only (research.md §4) |
| source_ref | string | SEC accession number + item reference |
| source_url | string | |
| fetched_at | timestamp | |
| superseded_by_id | UUID (FK, nullable) | |

**Validation rules**: `amount`, `disclosure_date`, `disclosure_type`, `source_ref`
required.

**Uniqueness**: `(source, source_ref)` unique.

## Signal

Wraps an `InsiderTransaction` or `BuybackEvent` once evaluated against the current
threshold configuration. One signal per underlying record.

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| signal_type | enum(insider_transaction, buyback) | |
| insider_transaction_id | UUID (FK, nullable) | set when signal_type = insider_transaction |
| buyback_event_id | UUID (FK, nullable) | set when signal_type = buyback |
| is_notable | boolean | result of classification (FR-004, FR-005) |
| is_discretionary | boolean (nullable) | mirrors the underlying `InsiderTransaction.is_discretionary` at evaluation time; null for buyback signals (SC-006 — lets the dashboard/API show this without a join) |
| is_superseded | boolean | default false; set true when the underlying record this signal wraps is later superseded (see below) |
| evaluated_threshold_snapshot | JSON | the threshold values used at evaluation time, for auditability |
| notification_status | enum(not_applicable, pending, sent, failed) | not_applicable when is_notable = false |
| notified_at | timestamp | nullable |
| created_at | timestamp | |

**State transitions**: `not_applicable` (not notable) is terminal.
`pending → sent` on successful email delivery; `pending → failed` on delivery error
(FR-013: the signal remains visible regardless of this transition). Re-processing
the same underlying record MUST NOT create a second `Signal` row (FR-012) — it
updates the existing one only if reclassification is triggered by a threshold
change (User Story 3). `is_superseded` transitions `false → true` (terminal) at the
moment de-duplication marks the underlying `InsiderTransaction`/`BuybackEvent` as
superseded by an amendment; a new `Signal` is created for the superseding record
through the normal classification path. Callers (the dashboard and `/api/signals`)
MUST exclude `is_superseded = true` signals by default, so an amended filing never
shows as two conflicting entries (spec Edge Cases, FR-016).

## ThresholdConfiguration

Single current configuration row (v1 is single-user, so this is not a list of
per-user configs — see spec Assumptions).

| Field | Type | Notes |
|---|---|---|
| id | UUID (PK) | |
| min_insider_buy_value | decimal | default 1,000,000 (spec Assumptions); applies to filers whose role is NOT in `notable_filer_roles` |
| min_notable_role_buy_value | decimal | default 100,000 (spec Assumptions); applies to filers whose role IS in `notable_filer_roles` — always AND'd with role, never role-alone (FR-004) |
| notable_filer_roles | array(enum) | default [officer, director] |
| min_buyback_amount | decimal | default 50,000,000 |
| updated_at | timestamp | |

**Validation rules**: exactly one row exists; updates replace the row's values and
timestamp rather than inserting a new row (FR-014). `min_insider_buy_value` and
`min_notable_role_buy_value` are independently validated non-negative.

## Relationships

```text
InsiderTransaction 1 --- 0..1 Signal
BuybackEvent       1 --- 0..1 Signal
InsiderTransaction 0..1 --- 0..1 InsiderTransaction   (superseded_by_id, self-referential)
BuybackEvent       0..1 --- 0..1 BuybackEvent         (superseded_by_id, self-referential)
ThresholdConfiguration (singleton, referenced by value at Signal evaluation time)
```
