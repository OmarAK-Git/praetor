"""TASK-014 prompt construction and excerpt hygiene."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from typing import Any
from unittest.mock import patch

from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.engine.helpers import assert_outcome_matrix_edict

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.engine.skeleton import (
    SKELETON_BUNDLE_HASH,
    SKELETON_EVIDENCE_ID,
    skeleton_model_judgment,
)
from praetor.judgment.excerpt import (
    MAX_PROMPT_EXCERPT_CHARS,
    build_prompt_excerpt_set,
)
from praetor.judgment.prompt import build_judgment_prompt_payload
from praetor.judgment.provider import JudgmentRequest, ProviderProbeResult
from praetor.state.store import open_state_store

OMISSION_RE = re.compile(r"\[\.\.\.omitting (?P<count>\d+) characters\]")


def _to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return {key: _to_primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_primitive(item) for item in value]
    return value


def _serialized(value: Any) -> str:
    return json.dumps(_to_primitive(value), sort_keys=True)


def _evidence_facts() -> list[dict[str, Any]]:
    long_command = "head-" + ("A" * 120) + "-middle-" + ("B" * 120) + "-tail"
    return [
        {
            "evidence_id": "ev-1",
            "normalized_fields": {
                "process_name": "powershell.exe",
                "command_line": long_command,
                "raw_source": "normalized raw source must not leak",
                "details": {
                    "safe": "retained",
                    "raw_source": "nested raw source must not leak",
                },
            },
            "source_event_reference": "sysmon:1",
            "raw_source": "DO-NOT-LEAK raw event body with instructions",
            "provenance_path": "sysmon_event_log",
            "ambiguity_flag": False,
        },
        {
            "evidence_id": "ev-2",
            "normalized_fields": {
                "unicode_payload": "π" * 260,
            },
            "source_event_reference": "security:2",
            "raw_source": "another raw source that must stay isolated",
            "provenance_path": "windows_security_log",
            "ambiguity_flag": True,
        },
    ]


def test_prompt_excerpt_set_caps_text_and_uses_stable_evidence_ids() -> None:
    excerpt_set = build_prompt_excerpt_set(_evidence_facts())

    assert [fact.evidence_id for fact in excerpt_set.facts] == ["ev-1", "ev-2"]
    assert all(
        len(excerpt.text) <= MAX_PROMPT_EXCERPT_CHARS
        for fact in excerpt_set.facts
        for excerpt in fact.excerpts
    )
    assert "raw_source" not in _serialized(excerpt_set)
    assert "DO-NOT-LEAK" not in _serialized(excerpt_set)
    assert "normalized raw source" not in _serialized(excerpt_set)
    assert "nested raw source" not in _serialized(excerpt_set)


def test_unbounded_field_truncation_keeps_head_tail_and_omission_count() -> None:
    excerpt_set = build_prompt_excerpt_set(_evidence_facts())
    command_excerpt = next(
        excerpt
        for fact in excerpt_set.facts
        for excerpt in fact.excerpts
        if excerpt.field_path == "normalized_fields.command_line"
    )

    assert command_excerpt.incomplete is True
    assert command_excerpt.text.startswith("head-")
    assert command_excerpt.text.endswith("-tail")
    marker = OMISSION_RE.search(command_excerpt.text)
    assert marker is not None
    head, tail = command_excerpt.text.split(marker.group(0))
    original = _evidence_facts()[0]["normalized_fields"]["command_line"]
    assert int(marker.group("count")) == len(original) - len(head) - len(tail)


def test_prompt_payload_warns_on_incomplete_content_and_structured_output() -> None:
    org_config_verbatim = "containment_policy:\n  default: escalate\n"
    payload = build_judgment_prompt_payload(
        evidence_facts=_evidence_facts(),
        evidence_bundle_hash="bundle-hash",
        org_config_snapshot_hash="snapshot-hash",
        org_config_verbatim=org_config_verbatim,
    )

    serialized = _serialized(payload)
    assert payload["org_config_verbatim"] == org_config_verbatim
    assert "Some evidence excerpts are incomplete" in serialized
    assert "JSON" in serialized
    assert "ModelJudgment" in serialized
    assert "raw_source" not in serialized
    assert "prompt_excerpt_set" in payload


class _CapturingProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.request: JudgmentRequest | None = None

    def generate_judgment(self, request: JudgmentRequest) -> ModelJudgment:
        self.calls += 1
        self.request = request
        return skeleton_model_judgment()

    def probe(self, canary_payload: Mapping[str, Any]) -> ProviderProbeResult:
        return ProviderProbeResult(
            success=True,
            provider_name="capture",
            model_name="capture",
            metadata={"canary_seen": bool(canary_payload)},
        )


def test_engine_provider_request_uses_prompt_excerpt_set_only(tmp_path) -> None:
    store = open_state_store(tmp_path / "state.db")
    verifier = PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )
    try:
        activate_org_config(
            store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
        )
        provider = _CapturingProvider()

        result = process_alert_intake(
            store,
            judgment_provider=provider,
            stamp_backend=SucceedingStampBackend(),
            alert_identity="ALERT-PROMPT-ISOLATION",
        )

        assert result.edict is not None
        assert provider.calls == 1
        assert provider.request is not None
        payload = provider.request.payload
        assert payload["evidence_bundle_hash"] == SKELETON_BUNDLE_HASH
        assert payload["org_config_verbatim"] == EXAMPLE_CONFIG.read_text(
            encoding="utf-8"
        )
        assert (
            payload["prompt_excerpt_set"]["facts"][0]["evidence_id"]
            == SKELETON_EVIDENCE_ID
        )
        field_paths = {
            excerpt["field_path"]
            for excerpt in payload["prompt_excerpt_set"]["facts"][0]["excerpts"]
        }
        assert "normalized_fields.process_name" in field_paths
        assert "raw_source" not in _serialized(payload)
        assert "facts" not in payload
    finally:
        store.close()


def test_config_budget_blocks_provider_before_prompt_construction(tmp_path) -> None:
    store = open_state_store(tmp_path / "state.db")
    verifier = PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )
    try:
        activate_org_config(
            store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier
        )
        provider = _CapturingProvider()
        with patch(
            "praetor.engine.orchestrator.fetch_verbatim_render_text",
            return_value="x" * 500_000,
        ):
            result = process_alert_intake(
                store,
                judgment_provider=provider,
                stamp_backend=SucceedingStampBackend(),
                alert_identity="ALERT-PROMPT-BUDGET",
            )

        assert result.edict is not None
        assert provider.calls == 0
        assert_outcome_matrix_edict(
            result.edict,
            final_disposition=Disposition.ESCALATE,
            fault_flags=["config_over_budget"],
            system_fault_escalation=True,
            proposed_disposition=Disposition.STANDARD_REVIEW,
        )
    finally:
        store.close()
