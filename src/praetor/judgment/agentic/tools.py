"""Read-only, scope-bounded tools for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.evidence.provenance import LEDGER_HISTORY
from praetor.hashing.domains import ORG_CONFIG_SNAPSHOT_HASH_KEYS
from praetor.judgment.excerpt import MAX_PROMPT_EXEMPLARS
from praetor.ledger.store import fetch_edicts_for_target_history
from praetor.retrieval.similar_cases import retrieve_similar_case_exemplars


class ScopeViolationError(ValueError):
    """Raised when a tool call requests a target outside the alert's own scope."""


@dataclass(frozen=True)
class ToolResult:
    """Result of a tool invocation producing citable EvidenceFacts."""

    facts: tuple[EvidenceFact, ...]
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True)
class OrgConfigSectionResult:
    """Result of an OrgConfigSectionTool invocation. Never citable evidence."""

    section_name: str
    content: str
    succeeded: bool
    error: str | None = None


@dataclass(frozen=True)
class ExemplarToolResult:
    """Result of a SimilarCaseTool invocation. Non-evidentiary."""

    exemplars: tuple[dict[str, Any], ...]
    succeeded: bool
    error: str | None = None


def _edict_to_history_fact(edict: DecisionEdict) -> EvidenceFact:
    directive = edict.containment_directive
    normalized_fields: dict[str, Any] = {
        "decision_id": edict.decision_id,
        "alert_reference": edict.alert_reference,
        "final_disposition": edict.final_disposition.value,
        "fault_flags": list(edict.fault_flags),
    }
    if directive is not None:
        normalized_fields["target_type"] = directive.target_type.value
        normalized_fields["target_id"] = directive.target_id
    return EvidenceFact(
        evidence_id=f"ledger-history-{edict.decision_id}",
        normalized_fields=normalized_fields,
        source_event_reference=edict.decision_id,
        raw_source=edict.model_dump_json(),
        provenance_path=LEDGER_HISTORY,
        ambiguity_flag=False,
        timestamp=edict.decided_at,
    )


@dataclass(frozen=True)
class LedgerHistoryTool:
    """Past decisions matching this alert's own alert_reference or a past
    containment target within this alert's own host/account scope."""

    conn: sqlite3.Connection
    alert_reference: str
    allowed_target_ids: frozenset[str]
    name: str = "ledger_history"

    def invoke(self, arguments: Mapping[str, Any]) -> ToolResult:
        requested = arguments.get("target_ids", [])
        if not isinstance(requested, Sequence) or isinstance(requested, str):
            return ToolResult(
                facts=(), succeeded=False, error="target_ids must be a list"
            )
        unknown = set(requested) - self.allowed_target_ids
        if unknown:
            msg = f"target_ids outside alert scope: {sorted(unknown)}"
            raise ScopeViolationError(msg)
        target_ids = tuple(requested) if requested else tuple(self.allowed_target_ids)
        edicts = fetch_edicts_for_target_history(
            self.conn, alert_reference=self.alert_reference, target_ids=target_ids
        )
        facts = tuple(_edict_to_history_fact(edict) for edict in edicts)
        return ToolResult(facts=facts, succeeded=True)


@dataclass(frozen=True)
class WiderTelemetryTool:
    """Untruncated re-fetch of facts already in this alert's correlated
    EvidenceBundle (see spec's WiderTelemetryTool rescoping note)."""

    facts_by_id: Mapping[str, EvidenceFact]
    name: str = "wider_telemetry"

    def invoke(self, arguments: Mapping[str, Any]) -> ToolResult:
        requested = arguments.get("evidence_ids", [])
        if not isinstance(requested, Sequence) or isinstance(requested, str):
            return ToolResult(
                facts=(), succeeded=False, error="evidence_ids must be a list"
            )
        if not requested:
            return ToolResult(facts=tuple(self.facts_by_id.values()), succeeded=True)
        unknown = [eid for eid in requested if eid not in self.facts_by_id]
        if unknown:
            return ToolResult(
                facts=(), succeeded=False, error=f"unknown evidence_id(s): {unknown}"
            )
        facts = tuple(self.facts_by_id[eid] for eid in requested)
        return ToolResult(facts=facts, succeeded=True)


@dataclass(frozen=True)
class OrgConfigSectionTool:
    """Fetch one named org-config section instead of the whole verbatim
    render (this spec's original motivating complaint). Findings inform
    ModelJudgment.org_config_refs — never cited_evidence_refs; org-config
    content is not evidence and is not corroboration-eligible."""

    snapshot: OrgConfigSnapshot
    name: str = "org_config_section"

    def invoke(self, arguments: Mapping[str, Any]) -> OrgConfigSectionResult:
        section_name = arguments.get("section_name")
        if (
            not isinstance(section_name, str)
            or section_name not in ORG_CONFIG_SNAPSHOT_HASH_KEYS
        ):
            return OrgConfigSectionResult(
                section_name=str(section_name),
                content="",
                succeeded=False,
                error=f"unknown org-config section: {section_name!r}",
            )
        value = getattr(self.snapshot, section_name)
        if isinstance(value, BaseModel):
            content = value.model_dump_json()
        else:
            content = json.dumps(value, default=str, sort_keys=True)
        return OrgConfigSectionResult(
            section_name=section_name,
            content=content,
            succeeded=True,
        )


@dataclass(frozen=True)
class SimilarCaseTool:
    """Human-confirmed similar cases, agent-queried instead of pre-injected.
    Same source as today's fixed top-3 exemplars — non-evidentiary."""

    conn: sqlite3.Connection
    evidence_facts: tuple[Mapping[str, Any], ...]
    name: str = "similar_cases"

    def invoke(self, arguments: Mapping[str, Any]) -> ExemplarToolResult:
        limit = arguments.get("limit", MAX_PROMPT_EXEMPLARS)
        if not isinstance(limit, int) or limit < 1:
            return ExemplarToolResult(
                exemplars=(), succeeded=False, error="limit must be a positive int"
            )
        exemplars = retrieve_similar_case_exemplars(
            self.conn, evidence_facts=self.evidence_facts, limit=limit
        )
        return ExemplarToolResult(exemplars=tuple(exemplars), succeeded=True)
