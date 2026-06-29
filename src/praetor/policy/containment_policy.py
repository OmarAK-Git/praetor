"""Containment target resolution and org-config policy evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from praetor.config.live import target_in_never_contain_list
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.org_config_sections import (
    AssetEntry,
    ContainmentRuleAssetScope,
    ContainmentRuleCatchAllScope,
    ContainmentRuleScope,
    ContainmentRuleTargetScope,
)
from praetor.evidence.provenance import (
    WINDOWS_SECURITY_LOG,
    meets_account_corroboration,
)
from praetor.policy.identity import is_sid_backed

HOST_ID_FIELD = "host_id"
DEFAULT_HOST_SCOPE = "host-isolation"
DEFAULT_ACCOUNT_SCOPE = "account-session"

NEVER_CONTAIN_SNAPSHOT = "never_contain_snapshot"
NEVER_CONTAIN_LIVE_CONFLICT = "never_contain_live_conflict"
POLICY_AMBIGUITY = "policy_ambiguity"
CONTAINMENT_POLICY_DENIED = "containment_policy_denied"
CONTAINMENT_POLICY_ESCALATION_REQUIRED = "containment_policy_escalation_required"

_PERMITTING_ACTIONS = frozenset({"allow", "auto_contain"})
_BLOCKING_ACTIONS = frozenset({"deny", "escalate"})


class PolicyAction(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class ContainmentTarget:
    target_type: str
    target_id: str
    scope: str


@dataclass(frozen=True)
class TargetPolicyEvaluation:
    action: PolicyAction
    fault_flag: str | None = None


@dataclass(frozen=True)
class ContainmentTargetResolution:
    """Host/account containment target resolution outcome."""

    target: ContainmentTarget | None = None
    ambiguous: bool = False


def resolve_host_target(bundle: EvidenceBundle) -> ContainmentTarget | None:
    """Return the first host_id in bundle fact order. Not for PolicyGate targeting."""
    for fact in bundle.facts:
        host_id = fact.normalized_fields.get(HOST_ID_FIELD)
        if isinstance(host_id, str) and host_id.strip():
            return ContainmentTarget(
                target_type="host",
                target_id=host_id.strip(),
                scope=DEFAULT_HOST_SCOPE,
            )
    return None


def extract_account_identity(
    facts: list[EvidenceFact],
) -> CanonicalAccountIdentity | None:
    sid: str | None = None
    account_name = ""
    domain = ""
    authority_source = WINDOWS_SECURITY_LOG
    ambiguity_flag = False
    for fact in facts:
        fields = fact.normalized_fields
        candidate_sid = fields.get("target_sid") or fields.get("sid")
        if isinstance(candidate_sid, str) and candidate_sid.strip():
            sid = candidate_sid.strip()
        if isinstance(fields.get("account_name"), str):
            account_name = str(fields["account_name"])
        if isinstance(fields.get("domain"), str):
            domain = str(fields["domain"])
        if fact.ambiguity_flag:
            ambiguity_flag = True
    if sid is None:
        return None
    return CanonicalAccountIdentity(
        sid=sid,
        domain=domain or "UNKNOWN",
        account_name=account_name or "unknown",
        account_type="user",
        authority_source=authority_source,
        ambiguity_flag=ambiguity_flag,
    )


def resolve_account_target(bundle: EvidenceBundle) -> ContainmentTarget | None:
    identity = extract_account_identity(list(bundle.facts))
    if identity is None or not meets_account_corroboration(bundle.facts):
        return None
    return ContainmentTarget(
        target_type="account",
        target_id=identity.sid,
        scope=DEFAULT_ACCOUNT_SCOPE,
    )


def resolve_host_target_from_citations(
    bundle: EvidenceBundle,
    cited_evidence_ids: frozenset[str],
) -> ContainmentTargetResolution:
    """Resolve a host target from cited facts only."""
    cited_host_ids: set[str] = set()
    for fact in bundle.facts:
        if fact.evidence_id not in cited_evidence_ids:
            continue
        host_id = fact.normalized_fields.get(HOST_ID_FIELD)
        if isinstance(host_id, str) and host_id.strip():
            cited_host_ids.add(host_id.strip())
    if len(cited_host_ids) >= 2:
        return ContainmentTargetResolution(ambiguous=True)
    if len(cited_host_ids) == 1:
        host_id = next(iter(cited_host_ids))
        return ContainmentTargetResolution(
            target=ContainmentTarget(
                target_type="host",
                target_id=host_id,
                scope=DEFAULT_HOST_SCOPE,
            )
        )
    return ContainmentTargetResolution(target=None)


def resolve_containment_target(
    bundle: EvidenceBundle,
    cited_evidence_ids: frozenset[str],
) -> ContainmentTargetResolution:
    """Resolve containment target from validated citations.

    Account path blocks host fallback.
    """
    identity = extract_account_identity(list(bundle.facts))
    if identity is not None:
        if is_sid_backed(identity) and meets_account_corroboration(bundle.facts):
            return ContainmentTargetResolution(
                target=ContainmentTarget(
                    target_type="account",
                    target_id=identity.sid,
                    scope=DEFAULT_ACCOUNT_SCOPE,
                )
            )
        return ContainmentTargetResolution(target=None)
    return resolve_host_target_from_citations(bundle, cited_evidence_ids)


def snapshot_never_contain_entries(snapshot: OrgConfigSnapshot) -> list[dict[str, str]]:
    return [
        entry.model_dump(mode="json")
        for entry in snapshot.containment_exclusions.never_contain
    ]


def target_blocked_by_snapshot(
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
) -> bool:
    entries = snapshot_never_contain_entries(snapshot)
    return target_in_never_contain_list(
        target.target_type,
        target.target_id,
        entries,
    )


def target_blocked_by_live(
    live_entries: list[dict[str, object]],
    target: ContainmentTarget,
) -> bool:
    return target_in_never_contain_list(
        target.target_type,
        target.target_id,
        live_entries,
    )


def embedded_entries_for_target(
    live_entries: list[dict[str, object]],
    target: ContainmentTarget,
) -> list[dict[str, object]]:
    embedded: list[dict[str, object]] = []
    for entry in live_entries:
        try:
            tt = entry.get("target_type")
            tid = entry.get("target_id")
        except AttributeError:
            continue
        if tt == target.target_type and tid == target.target_id:
            embedded.append(dict(entry))
    return embedded


def _asset_groups_for_target(
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
) -> list[str]:
    groups: list[str] = []
    for entry in snapshot.assets_and_asset_groups.entries:
        if not isinstance(entry, AssetEntry):
            continue
        if target.target_type == "host" and entry.asset_id == target.target_id:
            groups.append(entry.asset_id)
        elif target.target_type == "host":
            subnet = entry.subnet_membership
            prefix = subnet.split("/")[0].rsplit(".", 1)[0]
            if subnet and target.target_id.startswith(prefix):
                groups.append(entry.asset_id)
    return groups


def _rule_scope_matches_target(
    snapshot: OrgConfigSnapshot,
    scope: ContainmentRuleScope,
    target: ContainmentTarget,
) -> bool:
    if isinstance(scope, ContainmentRuleCatchAllScope):
        return True
    if isinstance(scope, ContainmentRuleTargetScope):
        return (
            scope.target_type == target.target_type
            and scope.target_id == target.target_id
        )
    if isinstance(scope, ContainmentRuleAssetScope):
        return scope.asset_id in _asset_groups_for_target(snapshot, target)
    return False


def evaluate_target_containment_policy(
    snapshot: OrgConfigSnapshot,
    target: ContainmentTarget,
) -> TargetPolicyEvaluation:
    """Evaluate target-scoped containment rules; detect unresolved conflicts."""
    rules = snapshot.containment_policy.rules
    precedence = snapshot.containment_policy.precedence or []
    matched_actions: list[str] = []
    for rule in rules:
        if _rule_scope_matches_target(snapshot, rule.scope, target):
            matched_actions.append(rule.action)
    distinct = {action.lower() for action in matched_actions}
    permitting = distinct & _PERMITTING_ACTIONS
    blocking = distinct & _BLOCKING_ACTIONS
    if permitting and blocking and not precedence:
        return TargetPolicyEvaluation(
            action=PolicyAction.AMBIGUOUS,
            fault_flag=POLICY_AMBIGUITY,
        )
    if "deny" in distinct:
        return TargetPolicyEvaluation(
            action=PolicyAction.DENY,
            fault_flag=CONTAINMENT_POLICY_DENIED,
        )
    if "escalate" in distinct:
        return TargetPolicyEvaluation(
            action=PolicyAction.ESCALATE,
            fault_flag=CONTAINMENT_POLICY_ESCALATION_REQUIRED,
        )
    return TargetPolicyEvaluation(action=PolicyAction.ALLOW)
