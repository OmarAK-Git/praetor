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


def test_operator_runbook_pins_example_org_rate_targets(
    operator_runbook_text: str,
) -> None:
    import yaml
    from tests.config.shared import REPO_ROOT

    config = yaml.safe_load(
        (REPO_ROOT / "configs" / "example_org.yaml").read_text(encoding="utf-8")
    )
    sustained = config["provisional_alert_rate_targets"]["sustained_alerts_per_minute"]
    burst = config["provisional_alert_rate_targets"]["burst_alerts_per_minute"]
    assert sustained == 30
    assert burst == 60
    assert f"sustained **{sustained}**/min" in operator_runbook_text
    assert f"burst **{burst}**/min" in operator_runbook_text


def test_operator_runbook_pins_burst_not_separately_measured(
    operator_runbook_text: str,
) -> None:
    assert "burst_separately_measured=false" in operator_runbook_text
    assert (
        "does **not** measure burst in a separate time window"
        in operator_runbook_text
    )


def test_operator_runbook_documents_measurement_context_emission(
    operator_runbook_text: str,
) -> None:
    assert "measurement_context" in operator_runbook_text
    assert "informational_only" in operator_runbook_text
    assert "uncontended_distinct_host" in operator_runbook_text
    assert "not production SLAs" in operator_runbook_text


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


def test_contracts_documents_feed_v2_boundaries() -> None:
    text = CONTRACTS.read_text(encoding="utf-8")
    assert "append-only JSONL" in text
    for phrase in (
        "no rotation machinery",
        "feed segment registry",
        "consumer cursor registration",
        "multi-feed",
    ):
        assert phrase in text.lower(), f"missing feed boundary phrase: {phrase}"


def test_operator_runbook_documents_consumer_residual_risk_detail(
    operator_runbook_text: str,
) -> None:
    assert "Non-compliant consumer residual risk" in operator_runbook_text
    assert "consumer-local policy" in operator_runbook_text.lower()
    assert "never-contain addition after emission" in operator_runbook_text
    assert "reference verifier implements §10 items 1" in operator_runbook_text


def test_delivery_backlog_promotes_feed_roadmap_items() -> None:
    backlog = (DOCS / "proposals" / "delivery_backlog.md").read_text(encoding="utf-8")
    assert (
        "Feed segment registry, rotation machinery, consumer cursor registration"
        in backlog
    )
    assert "Multi-feed deployments and `revocation_feed_id` on directives" in backlog
    assert "§10.6 local consumer policy check" in backlog
    assert "consumer-owned" in backlog.lower()


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
