"""Session-scoped evidence registry for the agentic judgment pipeline.

See docs/superpowers/specs/2026-07-30-agentic-judgment-design.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from praetor.contracts.evidence import EvidenceFact
from praetor.hashing.domains import compute_session_trace_hash


@dataclass(frozen=True)
class ToolCallRecord:
    """One evidentiary (citable) tool invocation and its result."""

    source: str
    tool_name: str
    query: dict[str, Any]
    facts: tuple[EvidenceFact, ...]
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "facts": [fact.model_dump(mode="python") for fact in self.facts],
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass(frozen=True)
class OrgConfigCallRecord:
    """One OrgConfigSectionTool invocation. Never citable evidence — informs
    ModelJudgment.org_config_refs, not cited_evidence_refs."""

    source: str
    tool_name: str
    query: dict[str, Any]
    section_name: str
    content: str
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "section_name": self.section_name,
            "content": self.content,
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass(frozen=True)
class ExemplarCallRecord:
    """One SimilarCaseTool invocation. Non-evidentiary (illustration only)."""

    source: str
    tool_name: str
    query: dict[str, Any]
    exemplars: tuple[dict[str, Any], ...]
    succeeded: bool
    error: str | None = None

    def as_hashable(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "tool_name": self.tool_name,
            "query": self.query,
            "exemplars": list(self.exemplars),
            "succeeded": self.succeeded,
            "error": self.error,
        }


@dataclass
class SessionEvidenceRegistry:
    """Accumulates every tool call/result across all three phases for one
    agentic judgment session, in a fixed deterministic append order."""

    evidence_entries: list[ToolCallRecord] = field(default_factory=list)
    org_config_entries: list[OrgConfigCallRecord] = field(default_factory=list)
    exemplar_entries: list[ExemplarCallRecord] = field(default_factory=list)

    def record_evidence(self, record: ToolCallRecord) -> None:
        self.evidence_entries.append(record)

    def record_org_config(self, record: OrgConfigCallRecord) -> None:
        self.org_config_entries.append(record)

    def record_exemplars(self, record: ExemplarCallRecord) -> None:
        self.exemplar_entries.append(record)

    @property
    def facts(self) -> tuple[EvidenceFact, ...]:
        return tuple(
            fact
            for entry in self.evidence_entries
            if entry.succeeded
            for fact in entry.facts
        )

    @property
    def exemplars(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            exemplar
            for entry in self.exemplar_entries
            if entry.succeeded
            for exemplar in entry.exemplars
        )

    @property
    def org_config_findings(self) -> tuple[OrgConfigCallRecord, ...]:
        return tuple(entry for entry in self.org_config_entries if entry.succeeded)

    @property
    def any_evidence_source_succeeded(self) -> bool:
        return any(entry.succeeded for entry in self.evidence_entries)

    def session_trace_hash(self) -> str:
        return compute_session_trace_hash(
            [entry.as_hashable() for entry in self.evidence_entries],
            [entry.as_hashable() for entry in self.org_config_entries],
            [entry.as_hashable() for entry in self.exemplar_entries],
        )
