"""Canonical account identity and containment eligibility.

V1 waiver (DEC-062): ``is_sid_backed`` treats any non-empty, non-whitespace SID
as sufficient for identity eligibility. Strict Windows SID form validation is
exposed via ``is_valid_sid_format`` (contracts §11 pattern) for directive
emission and future gates; it does not yet gate ``is_sid_backed``.

PE-0014 / V2-025: ``evaluate_account_containment_eligibility`` signals
AUTO_CONTAIN eligibility only. Production authorization — including the
``account_containment_disabled`` feature gate — is applied exclusively by
``evaluate_policy_gate`` in ``policy/gate.py``.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.evidence.provenance import meets_account_corroboration

# Windows SID form (docs/contracts.md §11); matches ContainmentDirective validator.
WINDOWS_SID_PATTERN = re.compile(r"^S-1-5(?:-\d+)+$", re.IGNORECASE)

AMBIGUOUS_TARGET_IDENTITY = "ambiguous_target_identity"
AMBIGUOUS_CONTAINMENT_TARGET = "ambiguous_containment_target"
INSUFFICIENT_CORROBORATION = "insufficient_corroboration"
INSUFFICIENT_ENRICHMENT = "insufficient_enrichment"
ACCOUNT_CONTAINMENT_DISABLED = "account_containment_disabled"


@dataclass(frozen=True)
class AccountContainmentEvaluation:
    """Structured account containment eligibility for PolicyGate reuse."""

    authorized: bool
    fault_flag: str | None = None
    system_fault_escalation: bool = False
    final_disposition: Disposition | None = None


def is_valid_sid_format(sid: str) -> bool:
    """Return whether ``sid`` matches the Windows SID form (contracts §11)."""
    stripped = sid.strip()
    return bool(stripped) and bool(WINDOWS_SID_PATTERN.match(stripped))


def is_sid_backed(identity: CanonicalAccountIdentity) -> bool:
    """Return whether the identity has a non-empty SID (v1 waiver; see DEC-062)."""
    return bool(identity.sid.strip())


def evaluate_account_containment_eligibility(
    identity: CanonicalAccountIdentity,
    supporting_facts: Sequence[EvidenceFact],
) -> AccountContainmentEvaluation:
    """Evaluate whether account containment may be authorized."""
    if is_sid_backed(identity) and meets_account_corroboration(supporting_facts):
        # AUTO_CONTAIN means "eligible"; the production account_containment_disabled
        # feature gate (TASK-017) overrides this to escalate until Phase 3 per
        # docs/spec.md:311.
        return AccountContainmentEvaluation(
            authorized=True,
            final_disposition=Disposition.AUTO_CONTAIN,
        )

    # Per Outcome Matrix docs/spec.md:59; ambiguity_flag=true (spec.md:309) is one
    # sufficient trigger, not the only one, so the flag no longer gates this branch.
    # [DECISION: SID-absent] Name-only identities (spec.md:307) escalate here for
    # consistency and to avoid a no-disposition result.
    return AccountContainmentEvaluation(
        authorized=False,
        fault_flag=AMBIGUOUS_TARGET_IDENTITY,
        system_fault_escalation=False,
        final_disposition=Disposition.ESCALATE,
    )


_account_eligibility_helper = "evaluate_account_containment_eligibility"
_host_bundle_corroboration_helper = "meets_host_bundle_corroboration"
_host_enrichment_helper = "meets_host_cited_enrichment"
_host_containment_helpers = (
    _host_bundle_corroboration_helper,
    _host_enrichment_helper,
)

_AUTHORIZED_ACCOUNT_ELIGIBILITY_CALLERS = frozenset(
    {"src/praetor/policy/gate.py"}
)
_AUTHORIZED_HOST_CORROBORATION_CALLERS = frozenset({"src/praetor/policy/gate.py"})
_HELPER_DEFINITION_PATHS = frozenset(
    {
        "src/praetor/policy/identity.py",
        "src/praetor/evidence/provenance.py",
    }
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _relative_repo_path(path: Path) -> str:
    return path.resolve().relative_to(_repo_root()).as_posix()


def _find_direct_helper_calls(source: str, *, helper_name: str) -> list[int]:
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == helper_name:
                hits.append(node.lineno)
    return hits


def collect_unauthorized_containment_helper_calls(
    *,
    repo_root: Path | None = None,
) -> dict[str, list[tuple[str, int]]]:
    """Return helper -> [(path, lineno)] for prod calls outside PolicyGate."""
    root = repo_root or _repo_root()
    src_root = root / "src" / "praetor"
    violations: dict[str, list[tuple[str, int]]] = {
        _account_eligibility_helper: [],
        **{helper: [] for helper in _host_containment_helpers},
    }

    for path in sorted(src_root.rglob("*.py")):
        rel = _relative_repo_path(path)
        if rel in _HELPER_DEFINITION_PATHS:
            continue
        source = path.read_text(encoding="utf-8")
        account_authorized = _AUTHORIZED_ACCOUNT_ELIGIBILITY_CALLERS
        host_authorized = _AUTHORIZED_HOST_CORROBORATION_CALLERS
        if rel not in account_authorized:
            for lineno in _find_direct_helper_calls(
                source, helper_name=_account_eligibility_helper
            ):
                violations[_account_eligibility_helper].append((rel, lineno))
        if rel not in host_authorized:
            for helper_name in _host_containment_helpers:
                for lineno in _find_direct_helper_calls(
                    source, helper_name=helper_name
                ):
                    violations[helper_name].append((rel, lineno))

    return violations


def collect_unauthorized_test_containment_helper_calls(
    *,
    repo_root: Path | None = None,
) -> dict[str, list[tuple[str, int]]]:
    """Return helper calls in tests outside approved policy/contracts tests."""
    root = repo_root or _repo_root()
    approved_roots = ("tests/policy", "tests/contracts")
    violations: dict[str, list[tuple[str, int]]] = {
        _account_eligibility_helper: [],
        **{helper: [] for helper in _host_containment_helpers},
    }
    tests_root = root / "tests"
    if not tests_root.is_dir():
        return violations

    for path in sorted(tests_root.rglob("*.py")):
        rel = _relative_repo_path(path)
        if any(rel.startswith(f"{approved}/") for approved in approved_roots):
            continue
        source = path.read_text(encoding="utf-8")
        helper_names = (_account_eligibility_helper, *_host_containment_helpers)
        for helper_name in helper_names:
            for lineno in _find_direct_helper_calls(source, helper_name=helper_name):
                violations[helper_name].append((rel, lineno))
    return violations


def assert_containment_authorization_routes_through_policy_gate(
    *,
    repo_root: Path | None = None,
) -> None:
    """Fail when production containment helpers are called outside PolicyGate."""
    violations = collect_unauthorized_containment_helper_calls(repo_root=repo_root)
    messages: list[str] = []
    for helper_name, hits in violations.items():
        if not hits:
            continue
        details = ", ".join(f"{path}:{lineno}" for path, lineno in sorted(hits))
        messages.append(f"{helper_name} called outside PolicyGate boundary: {details}")
    if messages:
        raise AssertionError("\n".join(messages))


def assert_test_containment_helper_calls_are_approved(
    *,
    repo_root: Path | None = None,
) -> None:
    """Fail when tests call eligibility helpers outside policy/contracts tests."""
    violations = collect_unauthorized_test_containment_helper_calls(repo_root=repo_root)
    messages: list[str] = []
    for helper_name, hits in violations.items():
        if not hits:
            continue
        details = ", ".join(f"{path}:{lineno}" for path, lineno in sorted(hits))
        messages.append(
            f"{helper_name} called from non-approved test paths: {details}"
        )
    if messages:
        raise AssertionError("\n".join(messages))
