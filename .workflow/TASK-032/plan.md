# Workflow Plan: TASK-032

## Goal

Package portable Sigma detection content for committed OTRF-style fixtures, independent of Splunk (Task 33).

## Scope

### In scope

- Add `detections/sigma/windows/*.yml` — Windows/Sysmon and Security rules aligned with committed fixtures.
- Add `detections/attack_mapping.yaml` — ATT&CK technique mapping per rule.
- Add `tests/detections/test_sigma_rules.py` — test-first syntax validation, ATT&CK mapping, fixture match.
- Add `pysigma` to dev dependencies for rule parsing/validation.

### Out of scope

- Modify `docs/`.
- SPL compilation, Splunk demo harness (TASK-033).
- Bulk OTRF/Mordor download.
- Tasks 33+.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Sigma rule YAML parses via pySigma without rule-level parse errors. |
| REQ-002 | Rules pass core pySigma validation (excluding stylistic logsource-only warnings). |
| REQ-003 | Each rule has ATT&CK mapping in `attack_mapping.yaml` and `attack.t*` tags. |
| REQ-004 | Every event in committed sysmon/security fixture JSON matches at least one rule. |
| REQ-005 | Portable detection content lives under `detections/` independently of Splunk. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | `SigmaCollection.from_yaml` loads all rules; `rule.errors` empty for each. |
| AC-002 | REQ-002 | Core validators emit no high-severity issues (logsource style excluded). |
| AC-003 | REQ-003 | `attack_mapping.yaml` entry per rule file with ≥1 technique ID; rule tags include `attack.t*`. |
| AC-004 | REQ-004 | Flattened fixture events each match ≥1 loaded rule detection. |
| AC-005 | REQ-005 | `detections/sigma/windows/` and `detections/attack_mapping.yaml` committed. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Use pySigma 1.x for syntax validation. | Spec names pysigma; Task 33 reuses same stack. |
| DEC-002 | Exclude `specific_instead_of_generic_logsource` validator. | Stylistic HIGH on category+service combo; not syntax failure. |
| DEC-003 | Five rules cover cmd, powershell -enc, notepad, calc, Security 4624. | Maps every event in manifest-listed sysmon/security fixtures. |
| DEC-004 | Fixture match uses flattened EventData + top-level fields. | Matches Sysmon/Sigma field conventions for committed JSON shape. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Write failing sigma rule tests. | `tests/detections/test_sigma_rules.py` | complete |
| TASK-002 | Add sigma rules + attack mapping. | `detections/sigma/windows/*.yml`, `detections/attack_mapping.yaml` | complete |
| TASK-003 | Add pysigma dev dep; run verification; update Memory Bank. | `pyproject.toml`, `.workflow/TASK-032/*`, `memory-bank/*` | complete |

## Risks

- pySigma validator set may flag new rules — mitigated by curated exclusions and simple detections.
- Windows path escaping in Sigma YAML — use standard Sigma backslash conventions and verify in tests.
