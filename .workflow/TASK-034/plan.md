# Workflow Plan: TASK-034

## Goal

Deliver an empirical org-config sweep prototype that summarizes observed principals, assets, and admin patterns from Windows telemetry, emits a review-only proposed config artifact, and documents coverage limits plus absence-of-evidence risks for SOC lead review before activation.

## Scope

### In scope

- `src/praetor/codification/sweep.py` — telemetry sweep, summary aggregation, proposed artifact builder.
- `src/praetor/codification/report.py` — coverage limits and absence-of-evidence risk report.
- `tests/codification/test_sweep.py` — tests-first criteria from `docs/plan.md`.
- Preflight guard rejecting `artifact_kind: proposed_org_config` from activation.
- Scope guard allowlist update for `codification` package.

### Out of scope

- Modify `docs/`.
- Tasks 35+ (production benchmark, operator runbooks).
- Automatic config activation or SOC UI.
- Cloud/Linux telemetry or subnet inference from IP.

## Requirements

| ID | Requirement |
|---|---|
| REQ-001 | Sweep summarizes observed principals, assets, admin patterns, and frequency counts from normalized telemetry. |
| REQ-002 | Output is a proposed org-config artifact marked non-activatable; preflight rejects activation. |
| REQ-003 | Report documents telemetry coverage limits (supported sources, counts, time span). |
| REQ-004 | Report documents absence-of-evidence risks (unobserved subnets, empty never-contain, unvalidated admin patterns). |
| REQ-005 | SOC lead can review proposed YAML artifact and markdown report before any activation path. |

## Acceptance Criteria

| ID | Requirement | Acceptance Criterion |
|---|---|---|
| AC-001 | REQ-001 | Fixture sweep lists CORP\\jdoe, WORKSTATION1, process-chain admin patterns with correct counts. |
| AC-002 | REQ-002 | `version_metadata.artifact_kind == proposed_org_config`; `run_preflight` raises `proposed_artifact_not_activatable`. |
| AC-003 | REQ-003 | Report includes supported EventID coverage and normalized/skipped event counts. |
| AC-004 | REQ-004 | Report warns subnet_membership unobserved, never-contain not inferred, admin patterns heuristic-only. |
| AC-005 | REQ-005 | Sweep exposes `proposed_config` dict + rendered markdown report suitable for human review. |

## Decisions

| ID | Decision | Rationale |
|---|---|---|
| DEC-001 | Reuse Task 28 sysmon/security normalizers; no correlation window filter. | Sweep should observe full supplied corpus, not anchor-window slice. |
| DEC-002 | `artifact_kind: proposed_org_config` in `version_metadata`. | Explicit non-activatable marker; preflight fail-closed. |
| DEC-003 | Policy sections copied from `configs/example_org.yaml` defaults with sweep notes in report. | v1 sweep only empirically proposes principals/assets/patterns; statute sections remain placeholders. |
| DEC-004 | Admin patterns keyed by `parent_process_name -> process_name` per host/user. | Minimal heuristic aligned with Sysmon process-create facts. |

## Implementation Plan

| Task | Description | Files likely affected | Status |
|---|---|---|---|
| TASK-001 | Workflow + failing tests. | `.workflow/TASK-034/*`, `tests/codification/*` | pending |
| TASK-002 | Sweep + report + preflight guard + scope guard. | `src/praetor/codification/*`, `src/praetor/config/preflight.py` | pending |
| TASK-003 | Verification + Memory Bank updates. | `.workflow/TASK-034/*`, `memory-bank/*` | pending |

## Risks

- Proposed artifact shape may diverge from final human-authored YAML — report must state review requirement.
- Principal merge heuristics (domain\\user vs SID) may double-count without careful normalization — tests lock expected fixture behavior.
