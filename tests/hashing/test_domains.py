"""Unit tests for the session-trace hash domain (DEC-064)."""

from __future__ import annotations

from praetor.hashing.domains import compute_session_trace_hash


def test_session_trace_hash_is_deterministic() -> None:
    evidence = [{"source": "ledger_history", "succeeded": True}]
    org_config = [{"section_name": "containment_policy", "succeeded": True}]
    exemplars = [{"exemplar_id": "precedent-1", "succeeded": True}]
    first = compute_session_trace_hash(evidence, org_config, exemplars)
    second = compute_session_trace_hash(evidence, org_config, exemplars)
    assert first == second
    assert len(first) == 64


def test_session_trace_hash_changes_with_content() -> None:
    base = compute_session_trace_hash([{"a": 1}], [], [])
    changed = compute_session_trace_hash([{"a": 2}], [], [])
    assert base != changed


def test_session_trace_hash_empty_session() -> None:
    empty_hash = compute_session_trace_hash([], [], [])
    assert isinstance(empty_hash, str)
    assert len(empty_hash) == 64
