# Review: TASK-028

## Scope adherence

- Implemented only Task 28 correlation normalization per `docs/plan.md`.
- Did not wire into `process_alert_intake` (Task 28a / DEC-048).
- Did not modify `docs/`.

## Design notes

- `evidence_id` derived from domain-separated hash of provenance + source reference (no contracts pin; stable for citations).
- Reuses Task 14 `build_prompt_excerpt_set` via `correlation/excerpts.py`.
- Default correlation window ±300s; noise fixture at +2h excluded.
- `ambiguity_flag` when Sysmon user lacks domain separator.

## Gaps

- Fixtures are minimal committed JSON, not full OTRF/Mordor datasets (Task 29/30 scope).
- Only Sysmon EventID 1 and Security EventID 4624 supported in v1 normalizers.
- Orchestrator still uses walking-skeleton bundle until Task 28a.

## safe_to_commit

yes — pending final verification re-run
