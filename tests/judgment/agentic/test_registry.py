"""Unit tests for SessionEvidenceRegistry.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

from datetime import UTC, datetime

from praetor.contracts.evidence import EvidenceFact
from praetor.judgment.agentic.registry import (
    ExemplarCallRecord,
    OrgConfigCallRecord,
    SessionEvidenceRegistry,
    ToolCallRecord,
)


def _fact(evidence_id: str, provenance_path: str) -> EvidenceFact:
    return EvidenceFact(
        evidence_id=evidence_id,
        normalized_fields={"host_id": "HOST-1"},
        source_event_reference="ref-1",
        raw_source="raw",
        provenance_path=provenance_path,
        ambiguity_flag=False,
        timestamp=datetime(2026, 7, 30, tzinfo=UTC),
    )


def test_registry_collects_only_successful_facts() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={"target_ids": ["HOST-1"]},
            facts=(_fact("ev-1", "ledger_history"),),
            succeeded=True,
        )
    )
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={"target_ids": ["HOST-2"]},
            facts=(),
            succeeded=False,
            error="scope violation",
        )
    )
    assert len(registry.facts) == 1
    assert registry.facts[0].evidence_id == "ev-1"


def test_registry_exemplars_and_org_config_tracked_separately() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_exemplars(
        ExemplarCallRecord(
            source="similar_cases",
            tool_name="similar_cases",
            query={"limit": 3},
            exemplars=({"exemplar_id": "precedent-1"},),
            succeeded=True,
        )
    )
    registry.record_org_config(
        OrgConfigCallRecord(
            source="org_config_section",
            tool_name="org_config_section",
            query={"section_name": "containment_policy"},
            section_name="containment_policy",
            content="{}",
            succeeded=True,
        )
    )
    assert registry.exemplars == ({"exemplar_id": "precedent-1"},)
    assert len(registry.org_config_findings) == 1
    assert registry.facts == ()


def test_registry_session_trace_hash_is_order_stable_and_nonempty() -> None:
    registry = SessionEvidenceRegistry()
    registry.record_evidence(
        ToolCallRecord(
            source="ledger_history",
            tool_name="ledger_history",
            query={},
            facts=(_fact("ev-1", "ledger_history"),),
            succeeded=True,
        )
    )
    first = registry.session_trace_hash()
    second = registry.session_trace_hash()
    assert first == second
    assert len(first) == 64
