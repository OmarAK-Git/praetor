"""Load corroboration-floor sprint into autopilot-queue.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".workflow" / "autopilot-queue.json"
PLAN = "docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md"


def main() -> None:
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    q["defaults"]["active_sprint"] = "corroboration-floor"
    q["defaults"]["source_spec"] = PLAN
    q["defaults"]["source_plan"] = PLAN
    q["defaults"].pop("worktree_path", None)
    q["defaults"].pop("worktree_pythonpath", None)

    items = [
        {
            "id": "corroboration-floor-01-decision",
            "status": "pending",
            "tier": "T2",
            "depends_on": [],
            "goal": (
                "Ratify DEC-065 temporary corroboration floor and update "
                "contracts/spec; supersede DEC-064 ledger_history corroboration eligibility."
            ),
            "scope": "Docs/decisions only; no production code changes.",
            "files_allowed": [
                "docs/decisions.md",
                "docs/contracts.md",
                "docs/spec.md",
                "docs/architecture.md",
                "docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md",
                ".workflow/corroboration-floor-01-decision/",
            ],
            "acceptance_criteria": [
                "DEC-065 accepted: temporary >=1 anchoring cited fact (any provenance); sole ambiguity still fails; upgrade-to->=2 flagged for multi-telemetry.",
                "contracts.md §12a and spec.md host/account corroboration pins match DEC-065.",
                "DEC-064 corroboration trust extension marked superseded; agentic OM row and session_trace_hash remain.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "rg -n \"DEC-065\" docs/decisions.md docs/contracts.md docs/spec.md",
                    "rg -n \"ledger_history\" docs/decisions.md docs/contracts.md",
                ],
                "manual_checks": [
                    "Confirm ledger_history is documented as not corroboration-eligible.",
                    "Confirm temporary >=1 floor and upgrade-to->=2 flag are explicit.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": ".workflow/corroboration-floor-01-decision",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: single prescribed path from user-locked decisions",
        },
        {
            "id": "corroboration-floor-02-helpers",
            "status": "pending",
            "tier": "T2",
            "depends_on": ["corroboration-floor-01-decision"],
            "goal": (
                "Relax meets_host_cited_corroboration and meets_account_corroboration "
                "to temporary >=1 floor; remove ledger_history from non-attacker set."
            ),
            "scope": "provenance.py helpers + evidence unit tests only.",
            "files_allowed": [
                "src/praetor/evidence/provenance.py",
                "tests/evidence/test_host_corroboration.py",
                "tests/evidence/test_account_corroboration.py",
                "tests/evidence/test_provenance.py",
                ".workflow/corroboration-floor-02-helpers/",
            ],
            "acceptance_criteria": [
                "Host: >=1 target-anchoring cite passes; zero anchors fails; sole ambiguity_flag=true cite fails; no >=2 path or trusted-path requirement.",
                "Account: >=1 fact of any provenance passes; empty fails.",
                "LEDGER_HISTORY constant may remain; is_attacker_controllable_provenance(LEDGER_HISTORY) is True.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "pytest tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py -q",
                    "ruff check src/praetor/evidence/provenance.py tests/evidence/test_host_corroboration.py tests/evidence/test_account_corroboration.py tests/evidence/test_provenance.py",
                    "mypy src/praetor/evidence/provenance.py",
                ],
                "manual_checks": [],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": ".workflow/corroboration-floor-02-helpers",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: single prescribed path from user-locked decisions",
        },
        {
            "id": "corroboration-floor-03-gate-harness",
            "status": "pending",
            "tier": "T2",
            "depends_on": ["corroboration-floor-02-helpers"],
            "goal": (
                "Retarget insufficient_corroboration harness and PolicyGate/engine tests "
                "to sole-ambiguous / zero-anchor failures under the temporary floor."
            ),
            "scope": "Harness scenario + policy/engine/correlation tests that assert old >=2 semantics.",
            "files_allowed": [
                "evals/scenarios/insufficient_corroboration.yaml",
                "tests/policy/",
                "tests/engine/test_gate_target_ownership.py",
                "tests/evals/",
                "tests/correlation/",
                ".workflow/corroboration-floor-03-gate-harness/",
            ],
            "acceptance_criteria": [
                "Harness insufficient_corroboration covers OM row via sole ambiguous host citation (escalate, flag, SFE=false).",
                "Single-provenance host auto_contain no longer escalates solely for insufficient_corroboration.",
                "Touched policy/engine/eval/correlation tests updated and green.",
            ],
            "verification": {
                "scope": "task",
                "commands": [
                    "pytest tests/policy/test_host_corroboration_gate.py tests/policy/test_policy_gate.py tests/engine/test_gate_target_ownership.py tests/evals/test_eval_harness.py -q",
                    "ruff check tests/policy tests/engine/test_gate_target_ownership.py",
                ],
                "manual_checks": [
                    "Confirm scenario YAML description matches sole-ambiguous failure mode.",
                ],
            },
            "implementation_agent": "implementer",
            "verification_agent": "skeptic-verifier",
            "implementation_model": "composer-2.5",
            "verification_model": "cursor-grok-4.5-high",
            "run_dir": ".workflow/corroboration-floor-03-gate-harness",
            "attempts": 0,
            "max_retries": 1,
            "evidence": [],
            "source_plan": PLAN,
            "researcher_decision": "skipped: single prescribed path from user-locked decisions",
        },
        {
            "id": "corroboration-floor-gate",
            "status": "pending",
            "tier": "T3",
            "depends_on": [
                "corroboration-floor-01-decision",
                "corroboration-floor-02-helpers",
                "corroboration-floor-03-gate-harness",
            ],
            "goal": (
                "Verify temporary corroboration floor sprint with repository-wide "
                "test, lint, and typecheck gates."
            ),
            "scope": "Verify-only final plan gate; no feature implementation.",
            "files_allowed": [
                ".workflow/corroboration-floor-gate/",
                "memory-bank/tasks.md",
                "memory-bank/progress.md",
                "memory-bank/activeContext.md",
            ],
            "acceptance_criteria": [
                "Full pytest suite passes.",
                "Repository-wide ruff and mypy (src evals consumer_sdk) pass.",
                "All three task verifier artifacts exist and PASS.",
                "DEC-065 temporary floor is reflected in docs and code; ledger_history not trusted for corroboration.",
                "No AgenticJudgmentProvider runtime default wiring added.",
            ],
            "verification": {
                "scope": "phase_exit",
                "commands": [
                    "pytest -q",
                    "ruff check src tests evals consumer_sdk",
                    "mypy src evals consumer_sdk",
                ],
                "manual_checks": [
                    "Confirm sole ambiguity still fails host corroboration.",
                    "Confirm upgrade-to->=2 flag is documented in DEC-065 / contracts §12a.",
                ],
            },
            "implementation_agent": "test-runner",
            "verification_agent": "skeptic-verifier",
            "gate_model": "cursor-grok-4.5-high",
            "run_mode": "in_session_grok",
            "run_dir": ".workflow/corroboration-floor-gate",
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
    loaded = [i["id"] for i in q["items"] if i["id"].startswith("corroboration-floor")]
    print("loaded:", loaded)
    print("active_sprint:", q["defaults"]["active_sprint"])


if __name__ == "__main__":
    main()
