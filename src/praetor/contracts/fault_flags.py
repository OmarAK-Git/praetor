"""Outcome Matrix fault-flag validation for contracts and edict construction."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from praetor.contracts.disposition import Disposition
from praetor.metrics.events import (
    InvalidMetricFaultFlagError,
    OutcomeMatrixFaultFlag,
    normalize_fault_flag,
)

OUTCOME_MATRIX_SFE: dict[OutcomeMatrixFaultFlag, bool] = {
    OutcomeMatrixFaultFlag.CORRELATION_FAILURE: True,
    OutcomeMatrixFaultFlag.CONFIG_OVER_BUDGET: True,
    OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION: True,
    OutcomeMatrixFaultFlag.PROVIDER_MALFORMED_JSON: True,
    OutcomeMatrixFaultFlag.PROVIDER_TIMEOUT: True,
    OutcomeMatrixFaultFlag.PROVIDER_REFUSAL: True,
    OutcomeMatrixFaultFlag.PROVIDER_UNAVAILABLE: True,
    OutcomeMatrixFaultFlag.AGENTIC_EVIDENCE_GATHERING_FAILED: True,
    OutcomeMatrixFaultFlag.NEVER_CONTAIN_SNAPSHOT: False,
    OutcomeMatrixFaultFlag.NEVER_CONTAIN_LIVE_CONFLICT: False,
    OutcomeMatrixFaultFlag.AMBIGUOUS_TARGET_IDENTITY: False,
    OutcomeMatrixFaultFlag.AMBIGUOUS_CONTAINMENT_TARGET: False,
    OutcomeMatrixFaultFlag.INSUFFICIENT_CORROBORATION: False,
    OutcomeMatrixFaultFlag.INSUFFICIENT_ENRICHMENT: False,
    OutcomeMatrixFaultFlag.ACCOUNT_CONTAINMENT_DISABLED: False,
    OutcomeMatrixFaultFlag.POLICY_AMBIGUITY: False,
    OutcomeMatrixFaultFlag.CONTAINMENT_POLICY_DENIED: False,
    OutcomeMatrixFaultFlag.CONTAINMENT_POLICY_ESCALATION_REQUIRED: False,
    OutcomeMatrixFaultFlag.RATE_LIMIT_EXCEEDED: False,
    OutcomeMatrixFaultFlag.CONTAINMENT_BREAKER_OPEN: False,
    OutcomeMatrixFaultFlag.PROVIDER_HEALTH_BREAKER_OPEN: True,
    OutcomeMatrixFaultFlag.REVOCATION_FEED_UNHEALTHY: True,
    OutcomeMatrixFaultFlag.LATENCY_SLA_EXCEEDED: True,
    OutcomeMatrixFaultFlag.QUEUE_AGING_EXCEEDED: True,
    OutcomeMatrixFaultFlag.TICKET_STAMP_FAILED: False,
    OutcomeMatrixFaultFlag.LEDGER_CHAIN_INTEGRITY_FAILURE: False,
}

CANONICAL_FAULT_FLAG_VALUES = frozenset(flag.value for flag in OutcomeMatrixFaultFlag)

_POLICY_ENGINE_SCAN_ROOTS = (
    Path(__file__).resolve().parents[1] / "policy",
    Path(__file__).resolve().parents[1] / "engine",
)

_POLICY_ENGINE_LITERAL_EXCLUSIONS = frozenset(
    {
        "HOST_ID_FIELD",
        "DEFAULT_HOST_SCOPE",
        "DEFAULT_ACCOUNT_SCOPE",
        "CONTAINMENT_BREAKER_ALERT_CODE",
    }
)


class InvalidDecisionEdictFaultFlagError(ValueError):
    """Raised when DecisionEdict fault flags or SFE polarity are invalid."""


def expected_system_fault_escalation(fault_flags: list[str]) -> bool:
    if not fault_flags:
        return False
    return any(
        OUTCOME_MATRIX_SFE[normalize_fault_flag(flag)] for flag in fault_flags
    )


def validate_decision_edict_fault_flags(
    *,
    fault_flags: list[str],
    system_fault_escalation: bool,
    final_disposition: Disposition,
) -> None:
    """Reject unknown flags and SFE polarity drift at edict construction time."""
    for flag in fault_flags:
        try:
            normalize_fault_flag(flag)
        except InvalidMetricFaultFlagError as exc:
            msg = f"decision edict fault flag {flag!r} is not in OutcomeMatrixFaultFlag"
            raise InvalidDecisionEdictFaultFlagError(msg) from exc

    if final_disposition == Disposition.ESCALATE and fault_flags:
        expected = expected_system_fault_escalation(fault_flags)
        if system_fault_escalation is not expected:
            msg = (
                "decision edict system_fault_escalation "
                f"{system_fault_escalation!r} does not match Outcome Matrix polarity "
                f"for fault_flags={fault_flags!r} (expected {expected!r})"
            )
            raise InvalidDecisionEdictFaultFlagError(msg)
    if not fault_flags and system_fault_escalation:
        msg = "decision edict cannot set system_fault_escalation without fault_flags"
        raise InvalidDecisionEdictFaultFlagError(msg)


def _module_level_string_constants(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant) or not isinstance(
            node.value.value, str
        ):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                constants[target.id] = node.value.value
    return constants


def collect_policy_engine_fault_flag_literals() -> dict[str, str]:
    """Map constant name -> string literal from policy/ and engine/ modules."""
    literals: dict[str, str] = {}
    for root in _POLICY_ENGINE_SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if path.name.startswith("__"):
                continue
            literals.update(_module_level_string_constants(path))
    return {
        name: value
        for name, value in literals.items()
        if name not in _POLICY_ENGINE_LITERAL_EXCLUSIONS
        and _looks_like_fault_flag_literal(value)
    }


def _looks_like_fault_flag_literal(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", value))


def assert_policy_engine_fault_literals_are_canonical() -> None:
    literals = collect_policy_engine_fault_flag_literals()
    unknown = {
        name: value
        for name, value in literals.items()
        if value not in CANONICAL_FAULT_FLAG_VALUES
    }
    if unknown:
        details = ", ".join(
            f"{name}={value!r}" for name, value in sorted(unknown.items())
        )
        msg = (
            "policy/engine fault-flag literals not in "
            f"OutcomeMatrixFaultFlag: {details}"
        )
        raise AssertionError(msg)
