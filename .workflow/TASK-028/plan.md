# Workflow Plan: TASK-028

## Goal

Implement correlation normalization for Windows Sysmon and Security telemetry, producing valid `EvidenceBundle` and bounded `PromptExcerptSet` from fixture events with process relationships and time-window filtering.

## Scope

### In scope

- Normalize Sysmon process-creation events with `provenance_path=sysmon_event_log`.
- Normalize Windows Security logon events with `provenance_path=windows_security_log`.
- Require `raw_source` on every normalized fact.
- Build `PromptExcerptSet` alongside `EvidenceBundle` via Task 14 excerpt hygiene.
- Assemble parent/child process relationships from Sysmon process GUIDs.
- Filter correlated events by configurable time window around an anchor timestamp.
- Add Sysmon/security fixtures and register them in `tests/fixtures/fixture_manifest.yaml`.
- Add `tests/correlation/test_sysmon_normalization.py`.

### Out of scope

- Wire correlation into `process_alert_intake` (Task 28a / DEC-048).
- Identity compliance on real OTRF fixtures (Task 29).
- Correlation accuracy gate (Task 30).
- Modify `docs/`.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Sysmon fixture events normalize to typed `EvidenceFact` rows with `provenance_path=sysmon_event_log`. |
| REQ-002 | Security log events normalize with `provenance_path=windows_security_log`. |
| REQ-003 | Every normalized fact includes non-empty `raw_source`. |
| REQ-004 | Correlation output includes bounded, raw-source-free `PromptExcerptSet`. |
| REQ-005 | Parent/child process relationships are assembled from Sysmon GUID fields. |
| REQ-006 | Time-window filtering retains in-window events and excludes noise. |
| REQ-007 | `ambiguity_flag` reflects ambiguous identity/process linkage on fixtures. |
| REQ-008 | Fixture manifest registers Sysmon/security fixture paths and checksums. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Tests assert Sysmon facts validate as `EvidenceFact` with expected normalized fields and provenance. |
| AC-002 | REQ-002 | Tests assert Security facts validate with account/logon normalized fields. |
| AC-003 | REQ-003 | Tests assert every fact has `raw_source` populated from source event JSON. |
| AC-004 | REQ-004 | Tests assert excerpt payload has no `raw_source`, excerpts ≤200 chars, incomplete flag when truncated. |
| AC-005 | REQ-005 | Tests assert process graph links child `parent_process_guid` to parent entity. |
| AC-006 | REQ-006 | Tests assert out-of-window noise event is excluded from correlated bundle. |
| AC-007 | REQ-007 | Tests assert ambiguous Sysmon user fixture sets `ambiguity_flag=true`. |
| AC-008 | REQ-008 | Smoke/manifest tests load registered fixture entries with matching checksums. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Derive stable `evidence_id` from `provenance_path` + `source_event_reference` via domain-separated hash. | No contract pin exists; stable IDs required for citation validation. |
| DEC-002 | Support Winlogbeat-style events with nested `EventData` plus flat field aliases. | OTRF/Mordor fixtures commonly nest under `EventData`. |
| DEC-003 | Reuse `praetor.judgment.excerpt.build_prompt_excerpt_set` from `correlation/excerpts.py`. | Task 14 owns excerpt hygiene; avoid duplication. |
| DEC-004 | Default correlation window ±300 seconds around anchor timestamp. | Minimal v1 window policy; Task 30 can tighten via gate config. |
| DEC-005 | Set `ambiguity_flag` when Sysmon `User` lacks domain separator or parent GUID missing while parent image present. | Aligns with spec identity ambiguity without over-interpreting attacker-controlled strings. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing normalization, window, relationship, and excerpt tests. | `tests/correlation/test_sysmon_normalization.py`, fixtures | complete |
| TASK-002 | Implement normalization, entities, window, excerpts modules. | `src/praetor/correlation/*.py` | complete |
| TASK-003 | Register fixtures in manifest; allow `correlation` package in scope guard. | `tests/fixtures/*`, `tests/contracts/test_scope_guard.py` | complete |
| TASK-004 | Run verification and update workflow + Memory Bank artifacts. | `.workflow/TASK-028/*`, `memory-bank/*` | complete |
