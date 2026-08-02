"""Load enrichment-vs-corroboration sprint into autopilot-queue.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".workflow" / "autopilot-queue.json"
PLAN = "docs/superpowers/plans/2026-08-01-enrichment-vs-corroboration.md"
SPEC = "docs/superpowers/specs/2026-08-01-enrichment-vs-corroboration-design.md"
SPRINT = "enrichment-vs-corroboration"
PREFIX = "enrichment-split"


def main() -> None:
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    q["defaults"]["active_sprint"] = SPRINT
    q["defaults"]["source_spec"] = SPEC
    q["defaults"]["source_plan"] = PLAN
    q["defaults"].pop("worktree_path", None)
    q["defaults"].pop("worktree_pythonpath", None)

    items = [
        {
            "id": f"{PREFIX}-01-decision",
            "status": "pending",
            "tier": "T2",
            "depends_on": [],
            "goal": (
                "Ratify DEC-066: split host corroboration (bundle presence) from "
                "enrichment (cited source events); retarget insufficient_corroboration; "
                "add Outcome Matrix row for insufficient_enrichment (decision-only)."
            ),
            "scope": "Docs/decisions/contracts/spec only; no production code or enum member (GR-0012).",
            "files_allowed": [
                "docs/decisions.md",
                "docs/contracts.md",
                "docs/spec.md",
                "docs/architecture.md",
                "docs/superpowers/specs/2026-08-01-enrichment-vs-corroboration-design.md",
                "docs/superpowers/plans/2026-08-01-enrichment-vs-corroboration.md",
                f".workflow/{PREFIX}-01-decision/",
            ],
            "acceptance_criteria": [
                "DEC-066 accepted: host corroboration = >=2 eligible provenance_path in host-scoped bundle; enrichment = >=2 distinct source_event_reference among target-anchoring cites; fault insufficient_enrichment SFE=false.",
                "insufficient_corroboration OM row retargeted to presence failure; insufficient_enrichment OM row added.",
                "DEC-065 host temporary cited floor marked superseded; account DEC-065 temporary floor remains.",
                "No OutcomeMatrixFaultFlag.INSUFFICIENT_ENRICHMENT enum member in this task (GR-0012).",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    'rg -n "DEC-066|insufficient_enrichment|source_event_reference" docs/decisions.md docs/contracts.md docs/spec.md',
                    'rg -n "insufficient_corroboration" docs/contracts.md',
                ],
                "manual_checks": [
                    "Confirm enrichment unit is source_event_reference (not cited provenance_path).",
                    "Confirm host-only enrichment; account stays on DEC-065 temporary floor.",
                    "Confirm sole-ambiguity subsumed by enrichment >=2.",
                    "VERIFY-E01 satisfied.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": f".workflow/{PREFIX}-01-decision",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": (
                "skipped: Approach A prescribed in ratified design "
                "(docs/superpowers/specs/2026-08-01-enrichment-vs-corroboration-design.md); "
                "user locked enrichment unit option 3"
            ),
        },
        {
            "id": f"{PREFIX}-02-helpers",
            "status": "pending",
            "tier": "T2",
            "depends_on": [f"{PREFIX}-01-decision"],
            "goal": (
                "Implement meets_host_bundle_corroboration and meets_host_cited_enrichment "
                "with unit tests; retire host cited-floor helper semantics."
            ),
            "scope": "provenance.py helpers + evidence unit tests only.",
            "files_allowed": [
                "src/praetor/evidence/provenance.py",
                "tests/evidence/test_host_corroboration.py",
                "tests/evidence/test_host_enrichment.py",
                "tests/evidence/test_provenance.py",
                f".workflow/{PREFIX}-02-helpers/",
            ],
            "acceptance_criteria": [
                "Host-scoped bundle with >=2 eligible provenance paths passes corroboration; single path fails; cross-host second path does not count.",
                "Enrichment passes on >=2 distinct source_event_reference among target-anchoring cites (same path allowed); single cite fails; ledger_history excluded.",
                "VERIFY-E02 green.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "pytest tests/evidence/test_host_corroboration.py tests/evidence/test_host_enrichment.py tests/evidence/test_provenance.py -q",
                    "ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_host_enrichment.py tests/evidence/test_provenance.py",
                    "mypy src/praetor/evidence/provenance.py",
                ],
                "manual_checks": [
                    "Confirm helpers match DEC-066 / contracts §12a pins.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": f".workflow/{PREFIX}-02-helpers",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: single prescribed path from ratified design",
        },
        {
            "id": f"{PREFIX}-03-gate-harness",
            "status": "pending",
            "tier": "T2",
            "depends_on": [f"{PREFIX}-02-helpers"],
            "goal": (
                "Wire PolicyGate corroboration-then-enrichment; add INSUFFICIENT_ENRICHMENT "
                "enum with harness scenario (GR-0012); retarget insufficient_corroboration harness."
            ),
            "scope": "Gate + fault enum/maps + harness scenarios/fixtures + policy/engine/eval tests asserting old host floor.",
            "files_allowed": [
                "src/praetor/policy/gate.py",
                "src/praetor/policy/identity.py",
                "src/praetor/metrics/events.py",
                "src/praetor/contracts/fault_flags.py",
                "evals/outcome_matrix.py",
                "evals/scenarios/insufficient_corroboration.yaml",
                "evals/scenarios/insufficient_enrichment.yaml",
                "tests/fixtures/synthetic/",
                "tests/policy/",
                "tests/engine/",
                "tests/evals/",
                "tests/correlation/",
                f".workflow/{PREFIX}-03-gate-harness/",
            ],
            "acceptance_criteria": [
                "Single-path host bundle auto_contain escalates insufficient_corroboration (SFE=false).",
                "Dual-path bundle with single cited source event escalates insufficient_enrichment (SFE=false).",
                "Outcome matrix completeness guard passes with new enum + scenario.",
                "Green-path host auto_contain tests cite >=2 source events and dual-path bundles.",
                "VERIFY-E03 green.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/evals/test_eval_harness.py -q",
                    "ruff check src/praetor/policy src/praetor/metrics/events.py src/praetor/contracts/fault_flags.py tests/policy",
                ],
                "manual_checks": [
                    "Confirm gate order: corroboration then enrichment.",
                    "Confirm sole-ambiguous-cite is no longer the insufficient_corroboration harness case.",
                    "GR-0012: enum landed with companion harness scenario.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": f".workflow/{PREFIX}-03-gate-harness",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: single prescribed path from ratified design",
        },
        {
            "id": f"{PREFIX}-04-demo",
            "status": "pending",
            "tier": "T2",
            "depends_on": [f"{PREFIX}-03-gate-harness"],
            "goal": (
                "Add separate public-demo scenarios for insufficient corroboration (presence) "
                "and insufficient enrichment (citation depth) with SOC-manager copy; rebuild demo page."
            ),
            "scope": "Walkthrough scenario registry + demo page rebuild + notebook check if shared.",
            "files_allowed": [
                "notebooks/walkthrough_scenarios.py",
                "notebooks/check_walkthrough.py",
                "notebooks/_regen_walkthrough.py",
                "notebooks/praetor_walkthrough.ipynb",
                "tools/build_demo_page.py",
                "demo/index.html",
                f".workflow/{PREFIX}-04-demo/",
            ],
            "acceptance_criteria": [
                "Two scenarios with distinct keys/labels/copy; assertions match engine flags.",
                "Green-path host contain demos use enriched multi-cite + dual-path bundles.",
                "python tools/build_demo_page.py --check passes after --write.",
                "VERIFY-E04 green.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "python tools/build_demo_page.py --write",
                    "python tools/build_demo_page.py --check",
                    "python -c \"from notebooks.walkthrough_scenarios import SCENARIOS; keys={s.key for s in SCENARIOS}; assert 'insufficient_corroboration' in keys and 'insufficient_enrichment' in keys, keys\"",
                ],
                "manual_checks": [
                    "SOC copy does not conflate presence corroboration with citation enrichment.",
                    "Panel headings remain What happens / Setup / Why it matters.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": f".workflow/{PREFIX}-04-demo",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: demo copy shape prescribed by public-demo design + this plan",
        },
        {
            "id": f"{PREFIX}-gate",
            "status": "pending",
            "tier": "T3",
            "depends_on": [
                f"{PREFIX}-01-decision",
                f"{PREFIX}-02-helpers",
                f"{PREFIX}-03-gate-harness",
                f"{PREFIX}-04-demo",
            ],
            "goal": (
                "Verify enrichment-vs-corroboration sprint with repository-wide "
                "test, lint, and typecheck gates."
            ),
            "scope": "Verify-only final plan gate; no feature implementation.",
            "files_allowed": [
                f".workflow/{PREFIX}-gate/",
                "memory-bank/tasks.md",
                "memory-bank/progress.md",
                "memory-bank/activeContext.md",
            ],
            "acceptance_criteria": [
                "Full pytest suite passes.",
                "Repository-wide ruff and mypy (src evals consumer_sdk) pass.",
                "All four task verifier artifacts exist and PASS.",
                "DEC-066 reflected in docs and code; account still on DEC-065 temporary floor.",
                "Demo page --check still green.",
            ],
            "verification": {
                "scope": "phase_exit",
                "commands": [
                    "pytest -q",
                    "ruff check src tests evals consumer_sdk",
                    "mypy src evals consumer_sdk",
                    "python tools/build_demo_page.py --check",
                ],
                "manual_checks": [
                    "Confirm gate order corroboration then enrichment.",
                    "Confirm trusted-path table was not silently re-enforced.",
                    "VERIFY-E05 satisfied.",
                ],
            },
            "implementation_agent": "test-runner",
            "verification_agent": "skeptic-verifier",
            "gate_model": "cursor-grok-4.5-high",
            "run_mode": "in_session_grok",
            "run_dir": f".workflow/{PREFIX}-gate",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: gate is verify-only",
        },
    ]

    by_id = {it["id"]: idx for idx, it in enumerate(q["items"])}
    for it in items:
        if it["id"] in by_id:
            q["items"][by_id[it["id"]]] = it
        else:
            q["items"].append(it)

    QUEUE.write_text(json.dumps(q, indent=2) + "\n", encoding="utf-8")
    loaded = [i["id"] for i in q["items"] if i["id"].startswith(PREFIX)]
    statuses = {
        i["id"]: i["status"] for i in q["items"] if i["id"].startswith(PREFIX)
    }
    print("loaded:", loaded)
    print("statuses:", statuses)
    print("active_sprint:", q["defaults"]["active_sprint"])
    print("source_plan:", q["defaults"]["source_plan"])


if __name__ == "__main__":
    main()
