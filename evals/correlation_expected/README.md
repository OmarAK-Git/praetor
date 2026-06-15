# Correlation expected scenario schema (Task 30)

Human-authored YAML consumed by `evals/correlation_gate.py`. Each file describes
one OTRF-style correlation accuracy scenario.

## Top-level keys

| Key | Required | Description |
|---|---|---|
| `schema_version` | yes | Currently `"1"`. |
| `scenario_id` | yes | Stable identifier printed by the gate CLI. |
| `description` | no | Free-text scenario summary. |
| `inputs` | yes | Telemetry inputs and manifest path (see below). |
| `expectations` | yes | Pass criteria after `correlate_telemetry` (see below). |

## `inputs`

| Key | Required | Description |
|---|---|---|
| `anchor_time` | yes | ISO-8601 anchor for ±`window_seconds` filtering. |
| `window_seconds` | no | Default `300`. |
| `sysmon_fixtures` | no | Repo-relative JSON fixture paths loaded as Sysmon events. |
| `security_fixtures` | no | Repo-relative JSON fixture paths loaded as Security events. |
| `noise_fixtures` | no | Fixture paths whose `record_id`s count toward noise overcollection when collected. Must not overlap `required_record_ids`. |
| `fixture_manifest` | no | Default `tests/fixtures/fixture_manifest.yaml`. Every referenced fixture path must appear in this manifest. |

## `expectations`

| Key | Required | Description |
|---|---|---|
| `required_record_ids` | no | `record_id` values that must appear in the correlated bundle. |
| `excluded_record_ids` | no | `record_id` values that must not be collected. |
| `required_process_relationships` | no | Parent/child `process_guid` pairs from Sysmon facts. |
| `min_collected_facts` / `max_collected_facts` | no | Fact-count bounds (use a range so noise threshold is not redundant). |
| `max_noise_overcollection` | no | Max collected facts whose `record_id` is listed in `noise_fixtures`. Fail cites specific noise `record_id`s. |
| `require_account_corroboration` | no | When `true`, `meets_account_corroboration` must pass on correlated facts. |
| `required_provenance_paths` | no | Every listed provenance path must appear among correlated facts. |
| `required_ambiguity_flag_record_ids` | no | Listed `record_id`s must have `ambiguity_flag=true`. |

## Noise role separation

A `record_id` must play **one** role: either required signal or noise overcollection.
Do not list the same `record_id` in both `required_record_ids` and `noise_fixtures`.
