# Web API Contract: Dashboard Service

Served by the `web` container. The dashboard's own HTML pages are server-rendered
via these same underlying queries; the JSON endpoints below are the contract
surface used by tests and any future client.

## `GET /api/signals`

Lists signals, most recent first (FR-009, FR-010).

**Query params**: `notable_only` (bool, default `true`), `signal_type`
(`insider_transaction` | `buyback`, optional), `since` (date, optional), `limit`
(int, default 100), `offset` (int, default 0)

Signals with `is_superseded = true` are always excluded — there is no query
parameter to include them, since a superseded signal is never useful to a viewer
(FR-016): the current signal for that event is what should be shown instead.

**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "signal_type": "insider_transaction",
      "is_notable": true,
      "is_discretionary": true,
      "company_name": "string",
      "ticker": "string|null",
      "summary": "string",
      "amount": 1234567.0,
      "event_date": "2026-09-01",
      "source_url": "https://...",
      "notification_status": "sent"
    }
  ],
  "total": 42
}
```

`is_discretionary` is `true`/`false` for `insider_transaction` signals (per
SC-006 — lets the dashboard distinguish a discretionary buy from a routine/10b5-1
transaction without opening the source filing) and `null` for `buyback` signals.

## `GET /api/signals/{id}`

Returns full detail for one signal, including the underlying `InsiderTransaction` or
`BuybackEvent` record and its provenance fields. Unlike the list endpoint, this MAY
return a superseded signal (e.g., reached via an old notification link) — the
response includes `is_superseded` so a caller can tell.

**Response 200**: signal + nested underlying record. **404** if not found.

## `GET /api/thresholds`

Returns the current `ThresholdConfiguration` (FR-014).

## `PUT /api/thresholds`

Updates the current `ThresholdConfiguration`. Takes effect for all classification
runs from that point forward (SC-005) — does not retroactively reclassify existing
signals unless the caller separately triggers `classify --reclassify` via the CLI.

**Request body**:
```json
{
  "min_insider_buy_value": 1000000,
  "min_notable_role_buy_value": 100000,
  "notable_filer_roles": ["officer", "director"],
  "min_buyback_amount": 50000000
}
```

`min_notable_role_buy_value` is the dollar threshold applied when the filer's role
is in `notable_filer_roles`; `min_insider_buy_value` applies to everyone else. Role
alone never makes a transaction notable — both the role-appropriate threshold and
the dollar amount must be met (FR-004).

**Response 200**: the updated configuration. **422** on invalid values (e.g.,
negative amounts).

## `GET /healthz`

Liveness check for Compose/orchestration. **Response 200**: `{"status": "ok"}` —
verifies DB connectivity.
