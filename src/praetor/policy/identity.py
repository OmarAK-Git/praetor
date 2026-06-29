"""Canonical account identity and containment eligibility."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from praetor.contracts.disposition import Disposition
from praetor.contracts.evidence import EvidenceFact
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.evidence.provenance import meets_account_corroboration

AMBIGUOUS_TARGET_IDENTITY = "ambiguous_target_identity"
AMBIGUOUS_CONTAINMENT_TARGET = "ambiguous_containment_target"
INSUFFICIENT_CORROBORATION = "insufficient_corroboration"
ACCOUNT_CONTAINMENT_DISABLED = "account_containment_disabled"


@dataclass(frozen=True)
class AccountContainmentEvaluation:
    """Structured account containment eligibility for PolicyGate reuse."""

    authorized: bool
    fault_flag: str | None = None
    system_fault_escalation: bool = False
    final_disposition: Disposition | None = None


def is_sid_backed(identity: CanonicalAccountIdentity) -> bool:
    """Return whether the identity has a non-empty SID.

    SID format validation (e.g. rejecting ``not-a-sid``) is deferred; any
    non-empty/non-whitespace string is treated as SID-backed for synthetic v1.
    """
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
