# Final Report: TASK-028

## Summary

Implemented Windows telemetry correlation normalization: Sysmon process-creation and Security logon events normalize into validated `EvidenceBundle` facts with `raw_source`, provenance paths, and `ambiguity_flag`; parent/child process relationships assembled from GUID fields; time-window filtering excludes out-of-window noise; `PromptExcerptSet` built via Task 14 excerpt hygiene.

## Files changed

### Source

- `src/praetor/correlation/__init__.py` — `correlate_telemetry`, `load_fixture_events`, `CorrelationResult`
- `src/praetor/correlation/_event_fields.py` — shared field/timestamp/raw_source helpers
- `src/praetor/correlation/ids.py` — stable `evidence_id` derivation
- `src/praetor/correlation/sysmon.py` — Sysmon EventID 1 normalization
- `src/praetor/correlation/security_log.py` — Security EventID 4624 normalization
- `src/praetor/correlation/window.py` — anchor ± window filtering
- `src/praetor/correlation/entities.py` — process relationship graph
- `src/praetor/correlation/excerpts.py` — bundle → `PromptExcerptSet`

### Tests & fixtures

- `tests/correlation/test_sysmon_normalization.py` — 9 tests
- `tests/fixtures/sysmon/*.json` — process chain, ambiguous user, noise
- `tests/fixtures/security/successful_logon_4624.json`
- `tests/fixtures/fixture_manifest.yaml` — 4 entries with SHA256
- `tests/test_smoke.py` — manifest no longer empty stub
- `tests/contracts/test_scope_guard.py` — allow `correlation` package

### Workflow / Memory Bank

- `.workflow/TASK-028/*`
- `memory-bank/{tasks,activeContext,progress}.md`

## Verification performed

```
python -m pytest -q tests/correlation/test_sysmon_normalization.py
9 passed in 0.21s

python -m pytest -q
638 passed, 1 deselected, 3 xfailed in 45.39s

python -m mypy src evals consumer_sdk
Success: no issues found in 110 source files

python -m ruff check src tests consumer_sdk evals
All checks passed!
```

## Known gaps

- No OTRF/Mordor bulk fixtures (Task 29 identity compliance, Task 30 accuracy gate).
- Orchestrator intake still uses skeleton bundle (Task 28a).
- `evidence_id` derivation not pinned in `docs/contracts.md` (minimal v1; record if future task requires pin).

## safe_to_commit

yes — full gate re-verified 2026-06-15
