# CLI Contract Delta: Cluster Buying Detection

Deltas against specs/001-insider-buyback-tracker/contracts/cli.md. Everything not
mentioned here is unchanged — no new subcommand is introduced.

## `classify`

Unchanged interface (`python -m insideoutside classify [--reclassify]`),
but its JSON summary gains cluster counts:

```json
{"evaluated": 12, "notable": 5, "clusters_detected": 1, "clusters_notable": 1}
```

`--reclassify` also re-runs cluster detection from scratch across all companies
with qualifying transactions, not just per-record classification.

## `thresholds`

`show` and `set` gain two new fields/flags:

```text
python -m insideoutside thresholds set --cluster-window-days 14
python -m insideoutside thresholds set --min-cluster-filer-count 2
```

Same rules as the existing flags: omitted flags keep their current value;
invalid values (non-positive, or `min-cluster-filer-count < 2`) are rejected
with a non-zero exit and an error on stderr.
