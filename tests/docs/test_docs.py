"""Task 35 — operator documentation checks."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"
SCHEMAS = REPO_ROOT / "schemas"

OPERATOR_RUNBOOK = DOCS / "operator_runbook.md"
ARCHITECTURE = DOCS / "architecture.md"
EVAL_GATES = DOCS / "eval_gates.md"
CONTRACTS = DOCS / "contracts.md"


@pytest.fixture
def operator_runbook_text() -> str:
    return OPERATOR_RUNBOOK.read_text(encoding="utf-8")


@pytest.fixture
def architecture_text() -> str:
    return ARCHITECTURE.read_text(encoding="utf-8")


def test_operator_runbook_exists() -> None:
    assert OPERATOR_RUNBOOK.is_file()


def test_architecture_exists() -> None:
    assert ARCHITECTURE.is_file()


def test_operator_runbook_documents_throughput_ceiling(
    operator_runbook_text: str,
) -> None:
    assert "Production throughput ceiling" in operator_runbook_text
    assert "benchmarks/serialized_path.py" in operator_runbook_text
    assert "provisional_alert_rate_targets" in operator_runbook_text
    assert "persist_directive=False" in operator_runbook_text


def test_operator_runbook_transaction_count_matches_benchmark(
    operator_runbook_text: str,
) -> None:
    from benchmarks.serialized_path import (
        PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION,
    )

    assert (
        "**two** `BEGIN IMMEDIATE` transactions"
        in operator_runbook_text
    )
    assert str(PRODUCTION_PATH_CRITICAL_TRANSACTIONS_PER_ITERATION) == "2"
    assert "No automated revocation" in operator_runbook_text


def test_operator_runbook_required_topics(operator_runbook_text: str) -> None:
    required_phrases = [
        "LLM failure recovery",
        "Provider-health breaker",
        "half-open probes",
        "Containment breaker",
        "Ledger integrity failure",
        "Revocation-feed unhealthy",
        "Feed ACLs",
        "Feed lag metrics",
        "Append-only JSONL capacity planning",
        "retention floor",
        "Hash chain as revocation system of record",
        "Never-contain conflict after emission",
        "Emergency never-contain race responsibility boundary",
        "Stamp recovery",
        "Non-compliant consumer residual risk",
        "Consumer pre-actuation protocol",
        "Clock skew",
        "SQLite deployment requirements",
        "WAL",
        "singleton",
        "Account containment production feature gate",
        "no rotation machinery",
        "segmented rotation is deferred",
        "standard_review",
    ]
    missing = [
        phrase for phrase in required_phrases if phrase not in operator_runbook_text
    ]
    assert missing == [], f"missing runbook topics: {missing}"


def test_operator_runbook_rejects_pass_disposition(operator_runbook_text: str) -> None:
    assert "legacy `pass` label is rejected" in operator_runbook_text
    assert "`standard_review`" in operator_runbook_text


def test_architecture_references_schemas(architecture_text: str) -> None:
    assert "schemas/" in architecture_text
    assert "docs/contracts.md" in architecture_text
    assert "standard_review" in architecture_text
    sample_schemas = [
        "schemas/evidence_bundle.json",
        "schemas/decision_edict.json",
        "schemas/containment_directive.json",
    ]
    for path in sample_schemas:
        assert path in architecture_text


def test_eval_gates_documents_phase_gates() -> None:
    text = EVAL_GATES.read_text(encoding="utf-8")
    assert "Phase 1" in text
    assert "Phase 5" in text
    assert "evals.harness" in text
    assert "evals.run_phase3_gate" in text


def test_contracts_references_schemas_and_throughput() -> None:
    text = CONTRACTS.read_text(encoding="utf-8")
    assert "schemas/org_config_snapshot.json" in text
    assert "benchmarks/serialized_path.py" in text
    assert "docs/operator_runbook.md" in text


def test_generated_schema_index_files_exist() -> None:
    listed = [
        "alert_envelope.json",
        "evidence_bundle.json",
        "org_config_snapshot.json",
        "decision_edict.json",
        "containment_directive.json",
        "revocation_feed_record.json",
    ]
    for name in listed:
        assert (SCHEMAS / name).is_file(), f"missing schema {name}"
