# Workflow Plan: TASK-033

## Goal

Compile Task 32 Sigma rules to deterministic Splunk SPL, generate saved-search definitions, and provide a reproducible Splunk Free demo harness with checksum-verified fixture ingest.

## Scope

### In scope

- `tools/compile_sigma.py` — pySigma Splunk backend compile + `--check` / `--write`.
- `detections/spl/*.spl` — committed plain SPL per rule.
- `splunk/savedsearches.conf`, `splunk/props.conf`, `splunk/README.md`.
- `tools/splunk_ingest_demo.ps1` — validate fixture manifest paths + sha256; optional HEC ingest.
- `tests/splunk/test_savedsearch_generation.py` — deterministic compile, savedsearch generation, unsupported-feature errors, ingest validation.
- `pysigma-backend-splunk` dev dependency.

### Out of scope

- Modify `docs/`.
- Tasks 34+.
- Bulk OTRF download or production Splunk deployment.
- Live Splunk integration in default CI (integration marker only).

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Sigma rules compile to deterministic SPL via pySigma Splunk backend + Windows pipeline. |
| REQ-002 | Unsupported Sigma features (correlation rules, disallowed modifiers) fail with clear errors. |
| REQ-003 | `savedsearches.conf` generated with one stanza per committed rule. |
| REQ-004 | `splunk_ingest_demo.ps1` validates fixture paths and sha256 checksums from manifest. |
| REQ-005 | Splunk demo path documented; integration tests skip when Splunk/fixtures unavailable. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Re-running compiler yields byte-identical `detections/spl/*.spl`; `--check` passes. |
| AC-002 | REQ-002 | Correlation rule or unsupported modifier raises `UnsupportedSigmaFeatureError` with rule id/title. |
| AC-003 | REQ-003 | `savedsearches.conf` stanzas match compiler output; each Task 32 rule represented. |
| AC-004 | REQ-004 | `-ValidateOnly` exits 0 on committed fixtures; non-zero on tampered/missing path. |
| AC-005 | REQ-005 | `splunk/README.md` documents Splunk Free steps; integration test marked and excluded from default suite. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Use `SplunkBackend(processing_pipeline=splunk_windows_pipeline())`. | Official backend; maps EventID→EventCode and Windows log sources. |
| DEC-002 | Allow modifiers `contains`, `endswith`, and unmodified equality only. | Matches Task 32 rule set; explicit preflight before compile. |
| DEC-003 | Ingest script flattens EventData and sets WinEventLog `source` values. | Saved searches target pipeline `source=` terms. |
| DEC-004 | Commit generated SPL + savedsearches; CI uses `--check`. | Deterministic reproducibility per Phase 4 gate. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Workflow + failing tests. | `.workflow/TASK-033/*`, `tests/splunk/*` | pending |
| TASK-002 | Compiler + Splunk artifacts + ingest script. | `tools/*`, `detections/spl/*`, `splunk/*`, `pyproject.toml` | pending |
| TASK-003 | Verification + Memory Bank updates. | `.workflow/TASK-033/*`, `memory-bank/*` | pending |

## Risks

- pySigma backend version drift — pin `pysigma-backend-splunk>=1.1,<3` and golden `--check`.
- Windows-only PowerShell ingest test — skip on non-Windows or invoke validation logic from Python mirror test.
