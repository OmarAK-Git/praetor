"""Static guards for PolicyGate containment authorization boundary (V2-025)."""

from __future__ import annotations

from pathlib import Path

from praetor.policy.identity import (
    assert_containment_authorization_routes_through_policy_gate,
    collect_unauthorized_containment_helper_calls,
    collect_unauthorized_test_containment_helper_calls,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_ACCOUNT_ELIGIBILITY_HELPER = "evaluate_account_containment_eligibility"
_HOST_BUNDLE_CORROBORATION_HELPER = "meets_host_bundle_corroboration"
_HOST_ENRICHMENT_HELPER = "meets_host_cited_enrichment"

# Grandfathered unit tests that exercise helper semantics, not authorization.
KNOWN_LEGACY_TEST_HELPER_CALLS: frozenset[tuple[str, str, int]] = frozenset(
    {
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/correlation/test_correlator_identity_compliance.py",
            163,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/correlation/test_correlator_identity_compliance.py",
            354,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/correlation/test_correlator_identity_compliance.py",
            362,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            109,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            131,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            140,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            202,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            217,
        ),
        (
            _ACCOUNT_ELIGIBILITY_HELPER,
            "tests/evidence/test_account_corroboration.py",
            245,
        ),
        (
            _HOST_BUNDLE_CORROBORATION_HELPER,
            "tests/evidence/test_host_corroboration.py",
            39,
        ),
        (
            _HOST_ENRICHMENT_HELPER,
            "tests/evidence/test_host_enrichment.py",
            58,
        ),
    }
)


def _flatten_violations(
    violations: dict[str, list[tuple[str, int]]],
) -> set[tuple[str, str, int]]:
    return {
        (helper, path, lineno)
        for helper, hits in violations.items()
        for path, lineno in hits
    }


def test_production_containment_helpers_only_called_from_policy_gate() -> None:
    assert_containment_authorization_routes_through_policy_gate(repo_root=REPO_ROOT)


def test_policy_gate_is_sole_production_account_eligibility_caller() -> None:
    violations = collect_unauthorized_containment_helper_calls(repo_root=REPO_ROOT)
    assert violations[_ACCOUNT_ELIGIBILITY_HELPER] == []


def test_policy_gate_is_sole_production_host_corroboration_caller() -> None:
    violations = collect_unauthorized_containment_helper_calls(repo_root=REPO_ROOT)
    assert violations[_HOST_BUNDLE_CORROBORATION_HELPER] == []


def test_policy_gate_is_sole_production_host_enrichment_caller() -> None:
    violations = collect_unauthorized_containment_helper_calls(repo_root=REPO_ROOT)
    assert violations[_HOST_ENRICHMENT_HELPER] == []


def test_non_approved_test_helper_calls_are_stable_legacy_set() -> None:
    """Guard detects helper calls outside tests/policy and tests/contracts."""
    observed = _flatten_violations(
        collect_unauthorized_test_containment_helper_calls(repo_root=REPO_ROOT)
    )
    assert observed == KNOWN_LEGACY_TEST_HELPER_CALLS, (
        "unexpected containment helper calls outside approved test paths: "
        f"new={observed - KNOWN_LEGACY_TEST_HELPER_CALLS}, "
        f"removed={KNOWN_LEGACY_TEST_HELPER_CALLS - observed}"
    )
