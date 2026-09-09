# Web API Contract Delta: Cluster Buying Detection

Deltas against specs/001-insider-buyback-tracker/contracts/api.md. Everything not
mentioned here is unchanged.

## `GET /api/signals`

`signal_type` query param now also accepts `cluster_buy`. A `cluster_buy` item in
the response has this shape (in place of the insider_transaction/buyback shapes
from 001, selected by `signal_type`):

```json
{
  "id": "uuid",
  "signal_type": "cluster_buy",
  "is_notable": true,
  "is_discretionary": null,
  "company_name": "string",
  "ticker": "string|null",
  "summary": "3 insiders bought between 2026-08-01 and 2026-08-10",
  "amount": 350000.0,
  "event_date": "2026-08-10",
  "source_url": null,
  "notification_status": "sent"
}
```

`event_date` is the cluster's `window_end`. `source_url` is `null` for a cluster
signal — there's no single source filing for a group; the detail endpoint
(below) links to each contributing transaction's own source instead.

## `GET /api/signals/{id}`

For a `cluster_buy` signal, `record` is the `ClusterBuyEvent`, including
`window_start`, `window_end`, `distinct_filer_count`, `total_value`, and
`contributing_transaction_ids`. Unlike the other two signal types, a client
that wants each contributing transaction's own detail (including its
`source_url`) follows up with `GET /api/signals/{id}` for each contributing
transaction's own signal, if one exists, or fetches the transaction directly —
this contract does not add a new endpoint for that in v1 (Simplicity: the
dashboard's own use of this data, sketched in quickstart.md, doesn't need it).

## `GET /api/thresholds` / `PUT /api/thresholds`

Both now include two new fields:

```json
{
  "min_insider_buy_value": 1000000,
  "min_notable_role_buy_value": 100000,
  "notable_filer_roles": ["officer", "director"],
  "min_buyback_amount": 50000000,
  "cluster_window_days": 14,
  "min_cluster_filer_count": 2
}
```

`PUT` validation: `cluster_window_days >= 1` and `min_cluster_filer_count >= 2`,
each rejected with **422** otherwise (a "cluster" of fewer than 2 filers isn't
a cluster, per FR-003).
