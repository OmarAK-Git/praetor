"""V2-031 — consumer policy and feed roadmap boundary tests."""

from __future__ import annotations

import inspect

from consumer_sdk.reference_verifier import (
    CONSUMER_OWNED_PROTOCOL_ITEM,
    IMPLEMENTS_PROTOCOL_ITEMS,
    verify_directive_pre_actuation,
)

from consumer_sdk import reference_verifier


def test_module_documents_consumer_owned_local_policy() -> None:
    doc = reference_verifier.__doc__ or ""
    assert "§10 item 6" in doc or "§10.6" in doc
    lowered = doc.lower()
    assert "consumer-owned" in lowered or "consumer owned" in lowered


def test_protocol_coverage_constants() -> None:
    assert IMPLEMENTS_PROTOCOL_ITEMS == (1, 2, 3, 4, 5)
    assert CONSUMER_OWNED_PROTOCOL_ITEM == 6
    assert CONSUMER_OWNED_PROTOCOL_ITEM not in IMPLEMENTS_PROTOCOL_ITEMS


def test_verify_docstring_excludes_local_policy() -> None:
    doc = inspect.getdoc(verify_directive_pre_actuation) or ""
    lowered = doc.lower()
    assert "§10" in doc
    assert "local" in lowered and "consumer" in lowered
    assert "6" in doc or "§10.6" in doc
