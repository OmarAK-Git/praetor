"""Load judgment capability spike sprint into autopilot-queue.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / ".workflow" / "autopilot-queue.json"
PLAN = "docs/superpowers/plans/2026-08-01-judgment-capability-spike.md"
SPEC = "docs/superpowers/specs/2026-08-01-capability-spike-design.md"
SPRINT = "judgment-capability-spike"
PREFIX = "capability-spike"


def _task(
    *,
    num: str,
    slug: str,
    depends: list[str],
    goal: str,
    scope: str,
    files_allowed: list[str],
    acceptance_criteria: list[str],
    commands: list[str],
    manual_checks: list[str],
) -> dict:
    tid = f"{PREFIX}-{num}-{slug}"
    return {
        "id": tid,
        "status": "pending",
        "tier": "T2",
        "depends_on": depends,
        "goal": goal,
        "scope": scope,
        "files_allowed": files_allowed + [f".workflow/{tid}/"],
        "acceptance_criteria": acceptance_criteria,
        "verification": {
            "scope": "task",
            "commands": commands,
            "manual_checks": manual_checks,
        },
        "implementation_agent": "implementer",
        "verification_agent": "skeptic-verifier",
        "implementation_model": "composer-2.5",
        "verification_model": "cursor-grok-4.5-high",
        "run_dir": f".workflow/{tid}",
        "attempts": 0,
        "max_retries": 1,
        "evidence": [],
        "source_plan": PLAN,
        "researcher_decision": (
            "skipped: Approach A prescribed in ratified design "
            f"({SPEC}); measurement-only spike with fixed Path A/B harness"
        ),
    }


def main() -> None:
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    q["defaults"]["active_sprint"] = SPRINT
    q["defaults"]["source_spec"] = SPEC
    q["defaults"]["source_plan"] = PLAN
    q["defaults"]["gate_item_id"] = f"{PREFIX}-gate"
    q["defaults"].pop("worktree_path", None)
    q["defaults"].pop("worktree_pythonpath", None)

    items = [
        _task(
            num="01",
            slug="corpus",
            depends=[],
            goal=(
                "Add labeled anchor manifest schema/loader for the judgment "
                "capability spike (balanced malicious/benign corpus)."
            ),
            scope=(
                "evals/capability corpus loader + unit tests/fixtures only; "
                "no src/praetor changes; no evals/harness.py changes."
            ),
            files_allowed=[
                "evals/capability/__init__.py",
                "evals/capability/corpus.py",
                "tests/evals/capability/__init__.py",
                "tests/evals/capability/test_corpus.py",
                "tests/evals/capability/fixtures/",
            ],
            acceptance_criteria=[
                "load_anchor_manifest loads valid YAML into frozen Anchor/AnchorManifest.",
                "Naive timestamps coerced to UTC; duplicate ids, unbalanced classes, "
                "invalid expected_class, and empty rationale raise ManifestError.",
                "Committed tests pass offline with FakeProvider-free fixtures.",
            ],
            commands=[
                "pytest tests/evals/capability/test_corpus.py -q",
                "ruff check evals/capability tests/evals/capability",
                "mypy evals/capability",
            ],
            manual_checks=[
                "No imports from praetor.judgment.agentic.",
                "Nothing in evals/capability is imported by evals/harness.py.",
                "No src/praetor/ edits.",
            ],
        ),
        _task(
            num="02",
            slug="flatten",
            depends=[f"{PREFIX}-01-corpus"],
            goal=(
                "Add generic mechanical event flattener for Path B evidence facts "
                "(no hand-tuned per-event-type extraction)."
            ),
            scope="evals/capability/flatten.py + unit tests only.",
            files_allowed=[
                "evals/capability/flatten.py",
                "tests/evals/capability/test_flatten.py",
            ],
            acceptance_criteria=[
                "flatten_event_to_fact emits EvidenceFact with flattened normalized_fields.",
                "resolve_provenance_path labels known sources; unknown uses SPIKE_UNKNOWN_SOURCE.",
                "Flattener stays mechanical (no per-EventID hand extraction).",
            ],
            commands=[
                "pytest tests/evals/capability/test_flatten.py -q",
                "ruff check evals/capability/flatten.py tests/evals/capability/test_flatten.py",
                "mypy evals/capability/flatten.py",
            ],
            manual_checks=[
                "Confirm flattener does not reimplement correlation window/host filters.",
                "No src/praetor/ edits.",
            ],
        ),
        _task(
            num="03",
            slug="bundle",
            depends=[f"{PREFIX}-02-flatten"],
            goal=(
                "Add Path B bundle builder that reuses correlation window and "
                "host filters, then flattens all event types."
            ),
            scope="evals/capability/bundle.py + unit tests only.",
            files_allowed=[
                "evals/capability/bundle.py",
                "tests/evals/capability/test_bundle.py",
            ],
            acceptance_criteria=[
                "build_spike_bundle calls filter_events_in_window and "
                "filter_events_to_anchor_host from praetor.correlation.",
                "Non-1/4624 events appear in Path B bundles when in window/host.",
                "Window/host filtering matches production correlation helpers.",
            ],
            commands=[
                "pytest tests/evals/capability/test_bundle.py -q",
                "ruff check evals/capability/bundle.py tests/evals/capability/test_bundle.py",
                "mypy evals/capability/bundle.py",
            ],
            manual_checks=[
                "No reimplementation of window/host filtering.",
                "No src/praetor/ edits.",
            ],
        ),
        _task(
            num="04",
            slug="runner",
            depends=[f"{PREFIX}-03-bundle"],
            goal=(
                "Add Observation record and two-path runner that exercises "
                "process_alert_intake for Path A (correlate) and Path B (bundle)."
            ),
            scope="evals/capability/runner.py + unit tests with FakeProvider only.",
            files_allowed=[
                "evals/capability/runner.py",
                "tests/evals/capability/test_runner.py",
            ],
            acceptance_criteria=[
                "run_anchor produces Observations for PATH_A and PATH_B.",
                "proposed_disposition read from result.edict.model_judgment when present.",
                "final_disposition/fault_flags recorded but not scored here.",
                "Offline FakeProvider tests pass with no API key.",
            ],
            commands=[
                "pytest tests/evals/capability/test_runner.py -q",
                "ruff check evals/capability/runner.py tests/evals/capability/test_runner.py",
                "mypy evals/capability/runner.py",
            ],
            manual_checks=[
                "Never imports praetor.judgment.agentic.",
                "Uses single-shot GenAI wrapper path only.",
                "No src/praetor/ edits; no evals/harness.py edits.",
            ],
        ),
        _task(
            num="05",
            slug="score",
            depends=[f"{PREFIX}-04-runner"],
            goal=(
                "Add scoring, A/B delta attribution, and same-capture confound check "
                "for the capability spike."
            ),
            scope="evals/capability/score.py + unit tests only.",
            files_allowed=[
                "evals/capability/score.py",
                "tests/evals/capability/test_score.py",
            ],
            acceptance_criteria=[
                "Malicious correct on escalate/auto_contain; benign on standard_review.",
                "Empty/missing proposed_disposition excluded from score and counted separately.",
                "ab_delta attributes A-wrong/B-right vs both-wrong vs dilution cases.",
                "confound_check flags trivial heuristics that separate classes.",
            ],
            commands=[
                "pytest tests/evals/capability/test_score.py -q",
                "ruff check evals/capability/score.py tests/evals/capability/test_score.py",
                "mypy evals/capability/score.py",
            ],
            manual_checks=[
                "PolicyGate outcomes are not folded into the capability score.",
                "No src/praetor/ edits.",
            ],
        ),
        _task(
            num="06",
            slug="cli",
            depends=[f"{PREFIX}-05-score"],
            goal=(
                "Add offline-safe capability spike CLI and document it as non-gating "
                "in docs/eval_gates.md."
            ),
            scope=(
                "evals/capability_spike.py + CLI tests + eval_gates.md append only; "
                "must not be imported by evals/harness.py."
            ),
            files_allowed=[
                "evals/capability_spike.py",
                "tests/evals/capability/test_cli.py",
                "docs/eval_gates.md",
            ],
            acceptance_criteria=[
                "main() exits 0 with skip message when PRAETOR_CAPABILITY_SPIKE unset.",
                "Enabled without API key still skips (no network).",
                "load_capture_events reads JSONL and skips blank/malformed lines.",
                "Harness source does not import the spike module.",
                "Non-gating section appended to docs/eval_gates.md.",
            ],
            commands=[
                "pytest tests/evals/capability/test_cli.py -q",
                "ruff check evals/capability_spike.py tests/evals/capability/test_cli.py",
                "mypy evals/capability_spike.py",
                "python -m evals.capability_spike",
            ],
            manual_checks=[
                "Spike remains opt-in via env flag + key; not a CI gate.",
                "No src/praetor/ edits; no evals/harness.py or scenarios edits.",
            ],
        ),
        {
            "id": f"{PREFIX}-gate",
            "status": "pending",
            "tier": "T3",
            "depends_on": [
                f"{PREFIX}-01-corpus",
                f"{PREFIX}-02-flatten",
                f"{PREFIX}-03-bundle",
                f"{PREFIX}-04-runner",
                f"{PREFIX}-05-score",
                f"{PREFIX}-06-cli",
            ],
            "goal": (
                "Verify judgment capability spike sprint with repository-wide "
                "test, lint, typecheck, and mandatory harness gates."
            ),
            "scope": "Verify-only final plan gate; no feature implementation.",
            "files_allowed": [
                f".workflow/{PREFIX}-gate/",
                "memory-bank/tasks.md",
                "memory-bank/progress.md",
                "memory-bank/activeContext.md",
                "IMPLEMENTATION_PLAN.md",
            ],
            "acceptance_criteria": [
                "Full pytest suite passes (startup_guard race flake: re-run alone if needed).",
                "Repository-wide ruff and mypy pass on src/tests/evals/consumer_sdk.",
                "python -m evals.harness still reports 33 scenarios green.",
                "python -m evals.capability_spike exits 0 skipped offline.",
                "All six task verifier artifacts exist and PASS.",
                "No src/praetor/ changes from this sprint; harness/scenarios untouched.",
            ],
            "verification": {
                "scope": "phase_exit",
                "commands": [
                    "pytest -q",
                    "ruff check src tests evals consumer_sdk",
                    "mypy src evals consumer_sdk",
                    "python -m evals.harness",
                    "python -m evals.capability_spike",
                ],
                "manual_checks": [
                    "Confirm measurement-only: no production code changes for this spike.",
                    "Confirm agentic judgment path was not imported.",
                    "Confirm gating suite is still offline/network-free.",
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
    print("gate_item_id:", q["defaults"].get("gate_item_id"))


if __name__ == "__main__":
    main()
