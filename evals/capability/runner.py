"""Two-path anchor execution for the capability spike.

Path A uses real ``correlate_telemetry`` (Sysmon EventID 1 + Security 4624
only). Path B uses a harness-built all-event-type bundle. Everything
downstream runs for real on both paths.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.capability.bundle import (
    assert_path_b_superset_of_path_a,
    build_spike_bundle_result,
)
from evals.capability.corpus import Anchor
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.contracts.judgment import ModelJudgment
from praetor.correlation.excerpts import build_correlation_prompt_excerpts
from praetor.correlation.window import DEFAULT_CORRELATION_WINDOW_SECONDS
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    process_alert_intake,
)
from praetor.judgment.excerpt import PromptExcerptSet
from praetor.judgment.prompt import build_judgment_prompt_payload_from_excerpt_set
from praetor.judgment.provider import JudgmentProvider, ProviderError
from praetor.metrics.events import OutcomeMatrixFaultFlag
from praetor.state.store import StateStore, open_state_store

PATH_A = "correlation"
PATH_B = "flattened"

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONFIG = _REPO_ROOT / "configs" / "example_org.yaml"
_SOC_LEAD_TOKEN = "soc-lead-token"


@dataclass(frozen=True)
class Observation:
    anchor_id: str
    expected_class: str
    path: str
    run_index: int
    proposed_disposition: str | None
    final_disposition: str | None
    fault_flags: tuple[str, ...]
    citation_count: int
    bundle_fact_count: int
    citations_resolved: bool
    cited_event_ids: tuple[int, ...] = ()
    error: str | None = None
    # Path B cap diagnostics (None on Path A).
    path_b_pre_cap_count: int | None = None
    path_b_cap_bound: bool | None = None
    path_b_seed_retained: bool | None = None
    path_b_cap_policy: str | None = None


def open_spike_store(db_path: Path) -> StateStore:
    """Open a state store with the example org config activated."""
    store = open_state_store(db_path)
    activate_org_config(
        store,
        _EXAMPLE_CONFIG,
        token=_SOC_LEAD_TOKEN,
        verifier=PrincipalMapVerifier(
            {_SOC_LEAD_TOKEN: Principal(identity="spike-soc-lead", role="soc_lead")}
        ),
    )
    return store


def split_events_by_channel(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    sysmon: list[Mapping[str, Any]] = []
    security: list[Mapping[str, Any]] = []
    for event in events:
        channel = str(event.get("Channel", "")).lower()
        if "sysmon" in channel:
            sysmon.append(event)
        elif channel.startswith("security"):
            security.append(event)
    return sysmon, security


_split_events = split_events_by_channel


@dataclass(frozen=True)
class PromptPathStats:
    """Provider-facing size / truncation counters for one path's bundle."""

    prompt_fact_count: int
    excerpt_count: int
    prompt_char_length: int
    omitted_characters_sum: int
    incomplete_excerpt_count: int
    excerpts_per_fact_mean: float
    evidence_ids: frozenset[str]


@dataclass(frozen=True)
class PathBundles:
    """Bundles for both paths before any provider call."""

    path_a: EvidenceBundle
    path_b: EvidenceBundle
    path_b_pre_cap_count: int
    path_b_extras_pre_cap_count: int
    path_b_cap_bound: bool
    path_b_seed_retained: bool
    path_b_cap_policy: str
    path_b_extras_selected: int
    path_a_prompt: PromptPathStats
    path_b_prompt: PromptPathStats
    sysmon: tuple[Mapping[str, Any], ...]
    security: tuple[Mapping[str, Any], ...]
    anchor_host_id: str | None


@dataclass(frozen=True)
class AnchorBundleStats:
    """Per-anchor bundle diagnostics (no judgment)."""

    anchor_id: str
    expected_class: str
    path_a_fact_count: int
    path_b_fact_count: int
    path_a_provenance_paths: frozenset[str]
    path_a_has_4624: bool
    path_b_pre_cap_count: int
    path_b_extras_pre_cap_count: int
    path_b_cap_bound: bool
    path_b_seed_retained: bool
    path_b_superset_ok: bool
    path_b_prompt_superset_ok: bool
    path_a_prompt: PromptPathStats
    path_b_prompt: PromptPathStats


def measure_prompt_path_stats(bundle: EvidenceBundle) -> PromptPathStats:
    """Measure excerpt/prompt size for a path (no provider call)."""
    excerpt_set: PromptExcerptSet = build_correlation_prompt_excerpts(bundle)
    excerpt_count = 0
    omitted = 0
    incomplete = 0
    for fact in excerpt_set.facts:
        for excerpt in fact.excerpts:
            excerpt_count += 1
            omitted += int(excerpt.omitted_characters)
            if excerpt.incomplete:
                incomplete += 1
    payload = build_judgment_prompt_payload_from_excerpt_set(
        excerpt_set=excerpt_set,
        evidence_bundle_hash="bundles-only",
        org_config_snapshot_hash="bundles-only",
        org_config_verbatim="",
        exemplar_block=None,
    )
    n_facts = len(excerpt_set.facts)
    return PromptPathStats(
        prompt_fact_count=n_facts,
        excerpt_count=excerpt_count,
        prompt_char_length=len(json.dumps(payload, sort_keys=True, default=str)),
        omitted_characters_sum=omitted,
        incomplete_excerpt_count=incomplete,
        excerpts_per_fact_mean=(excerpt_count / n_facts) if n_facts else 0.0,
        evidence_ids=frozenset(fact.evidence_id for fact in excerpt_set.facts),
    )


def build_path_bundles(
    *,
    anchor: Anchor,
    events: Sequence[Mapping[str, Any]],
    window_seconds: int | None = None,
    max_extra_facts: int | None = None,
    max_facts: int | None = None,
) -> PathBundles:
    """Build Path A/B bundles exactly as ``run_anchor`` does before intake."""
    from evals.capability.bundle import PATH_B_EXTRAS_BUDGET, PATH_B_MAX_FACTS
    from praetor.correlation import correlate_telemetry

    sysmon, security = _split_events(events)
    window = (
        DEFAULT_CORRELATION_WINDOW_SECONDS
        if window_seconds is None
        else window_seconds
    )
    anchor_host = (anchor.seed_host_id or "").strip() or None
    path_b = build_spike_bundle_result(
        events,
        anchor_time=anchor.anchor_time,
        anchor_host_id=anchor_host,
        window_seconds=window,
        seed_event_record_id=anchor.seed_event_record_id,
        seed_host_id=anchor.seed_host_id,
        max_facts=PATH_B_MAX_FACTS if max_facts is None else max_facts,
        max_extra_facts=(
            PATH_B_EXTRAS_BUDGET if max_extra_facts is None else max_extra_facts
        ),
    )
    path_a_bundle = correlate_telemetry(
        sysmon_events=list(sysmon),
        security_events=list(security),
        anchor_time=anchor.anchor_time,
        anchor_host_id=anchor_host,
        window_seconds=window,
    ).bundle
    assert_path_b_superset_of_path_a(
        path_a_bundle, path_b.bundle, anchor_id=anchor.anchor_id
    )
    path_a_prompt = measure_prompt_path_stats(path_a_bundle)
    path_b_prompt = measure_prompt_path_stats(path_b.bundle)
    missing_prompt = sorted(path_a_prompt.evidence_ids - path_b_prompt.evidence_ids)
    if missing_prompt:
        from evals.capability.bundle import PathBSupersetError

        msg = (
            f"anchor {anchor.anchor_id}: Path B prompt facts not a superset of "
            f"Path A — missing {len(missing_prompt)} evidence_id(s)"
        )
        raise PathBSupersetError(msg)
    return PathBundles(
        path_a=path_a_bundle,
        path_b=path_b.bundle,
        path_b_pre_cap_count=path_b.pre_cap_count,
        path_b_extras_pre_cap_count=path_b.extras_pre_cap_count,
        path_b_cap_bound=path_b.cap_bound,
        path_b_seed_retained=path_b.seed_retained,
        path_b_cap_policy=path_b.cap_policy,
        path_b_extras_selected=path_b.extras_selected,
        path_a_prompt=path_a_prompt,
        path_b_prompt=path_b_prompt,
        sysmon=tuple(sysmon),
        security=tuple(security),
        anchor_host_id=anchor_host,
    )


def inspect_anchor_bundles(
    *,
    anchor: Anchor,
    events: Sequence[Mapping[str, Any]],
    window_seconds: int | None = None,
    max_extra_facts: int | None = None,
    max_facts: int | None = None,
) -> AnchorBundleStats:
    """Return Path A/B fact counts without calling a judgment provider."""
    built = build_path_bundles(
        anchor=anchor,
        events=events,
        window_seconds=window_seconds,
        max_extra_facts=max_extra_facts,
        max_facts=max_facts,
    )
    provenances = frozenset(fact.provenance_path for fact in built.path_a.facts)
    has_4624 = any(
        event_id_from_fact(fact) == 4624 for fact in built.path_a.facts
    )
    return AnchorBundleStats(
        anchor_id=anchor.anchor_id,
        expected_class=anchor.expected_class,
        path_a_fact_count=len(built.path_a.facts),
        path_b_fact_count=len(built.path_b.facts),
        path_a_provenance_paths=provenances,
        path_a_has_4624=has_4624,
        path_b_pre_cap_count=built.path_b_pre_cap_count,
        path_b_extras_pre_cap_count=built.path_b_extras_pre_cap_count,
        path_b_cap_bound=built.path_b_cap_bound,
        path_b_seed_retained=built.path_b_seed_retained,
        path_b_superset_ok=True,
        path_b_prompt_superset_ok=True,
        path_a_prompt=built.path_a_prompt,
        path_b_prompt=built.path_b_prompt,
    )


def event_id_from_fact(fact: EvidenceFact) -> int | None:
    """Resolve EventID from a bundle fact (normalized_fields, then source ref)."""
    raw = fact.normalized_fields.get("EventID")
    if raw is not None and not isinstance(raw, bool):
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    parts = str(fact.source_event_reference).split(":")
    if len(parts) >= 2:
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


def cited_event_ids_from_judgment(
    judgment: ModelJudgment,
    facts_by_id: Mapping[str, EvidenceFact],
) -> tuple[int, ...]:
    """Join resolved citation evidence_ids to EventIDs via the path's bundle."""
    collected: list[int] = []
    for ref in judgment.cited_evidence_refs:
        fact = facts_by_id.get(ref.evidence_id)
        if fact is None:
            continue
        event_id = event_id_from_fact(fact)
        if event_id is not None:
            collected.append(event_id)
    return tuple(collected)


def _observe(
    *,
    anchor: Anchor,
    path: str,
    run_index: int,
    result: Any,
    bundle_fact_count: int,
    facts_by_id: Mapping[str, EvidenceFact],
    path_b_pre_cap_count: int | None = None,
    path_b_cap_bound: bool | None = None,
    path_b_seed_retained: bool | None = None,
    path_b_cap_policy: str | None = None,
) -> Observation:
    edict = getattr(result, "edict", None)
    fault_flags = tuple(str(flag) for flag in getattr(result, "fault_flags", ()))
    proposed: str | None = None
    citation_count = 0
    cited_event_ids: tuple[int, ...] = ()
    if edict is not None:
        judgment = edict.model_judgment
        proposed = judgment.proposed_disposition.value
        citation_count = len(judgment.cited_evidence_refs)
        cited_event_ids = cited_event_ids_from_judgment(judgment, facts_by_id)
    final = getattr(result, "disposition", None)
    return Observation(
        anchor_id=anchor.anchor_id,
        expected_class=anchor.expected_class,
        path=path,
        run_index=run_index,
        proposed_disposition=proposed,
        final_disposition=final.value if final is not None else None,
        fault_flags=fault_flags,
        citation_count=citation_count,
        bundle_fact_count=bundle_fact_count,
        citations_resolved=(
            OutcomeMatrixFaultFlag.INVALID_MODEL_CITATION.value not in fault_flags
        ),
        cited_event_ids=cited_event_ids,
        path_b_pre_cap_count=path_b_pre_cap_count if path == PATH_B else None,
        path_b_cap_bound=path_b_cap_bound if path == PATH_B else None,
        path_b_seed_retained=path_b_seed_retained if path == PATH_B else None,
        path_b_cap_policy=path_b_cap_policy if path == PATH_B else None,
    )


def run_anchor(
    store: StateStore,
    *,
    anchor: Anchor,
    events: Sequence[Mapping[str, Any]],
    provider: JudgmentProvider,
    runs: int = 3,
    window_seconds: int | None = None,
    skip_keys: set[tuple[str, str, int]] | None = None,
    on_observation: Any | None = None,
) -> list[Observation]:
    """Run one anchor through both paths ``runs`` times each.

    ``skip_keys`` may contain ``(anchor_id, path, run_index)`` triples already
    present in an output JSONL so a crashed run can resume. ``on_observation``
    is invoked after each Observation is produced (for incremental flush).
    """
    built = build_path_bundles(
        anchor=anchor, events=events, window_seconds=window_seconds
    )
    path_a_bundle = built.path_a
    spike_bundle = built.path_b
    sysmon = list(built.sysmon)
    security = list(built.security)

    fact_counts = {
        PATH_A: len(path_a_bundle.facts),
        PATH_B: len(spike_bundle.facts),
    }
    facts_by_path = {
        PATH_A: {fact.evidence_id: fact for fact in path_a_bundle.facts},
        PATH_B: {fact.evidence_id: fact for fact in spike_bundle.facts},
    }

    observations: list[Observation] = []
    stamp_backend = SucceedingStampBackend()
    done = skip_keys or set()

    for run_index in range(runs):
        for path in (PATH_A, PATH_B):
            key = (anchor.anchor_id, path, run_index)
            if key in done:
                continue
            # Unique identity per (anchor, path, run) so idempotency never
            # collapses two observations into one decision.
            alert_identity = (
                f"spike-{anchor.anchor_id}-{path}-{run_index}-{uuid.uuid4().hex[:8]}"
            )
            intake_kwargs: dict[str, Any] = {
                "judgment_provider": provider,
                "stamp_backend": stamp_backend,
                "alert_identity": alert_identity,
                "anchor_time": anchor.anchor_time,
            }
            if path == PATH_A:
                intake_kwargs["sysmon_events"] = sysmon
                intake_kwargs["security_events"] = security
            else:
                intake_kwargs["evidence_bundle"] = spike_bundle
            bundle_fact_count = fact_counts[path]

            try:
                result = process_alert_intake(store, **intake_kwargs)
            except (RuntimeError, ValueError, ProviderError) as exc:
                obs = Observation(
                    anchor_id=anchor.anchor_id,
                    expected_class=anchor.expected_class,
                    path=path,
                    run_index=run_index,
                    proposed_disposition=None,
                    final_disposition=None,
                    fault_flags=(),
                    citation_count=0,
                    bundle_fact_count=bundle_fact_count,
                    citations_resolved=False,
                    cited_event_ids=(),
                    error=f"{type(exc).__name__}: {exc}",
                    path_b_pre_cap_count=(
                        built.path_b_pre_cap_count if path == PATH_B else None
                    ),
                    path_b_cap_bound=(
                        built.path_b_cap_bound if path == PATH_B else None
                    ),
                    path_b_seed_retained=(
                        built.path_b_seed_retained if path == PATH_B else None
                    ),
                    path_b_cap_policy=(
                        built.path_b_cap_policy if path == PATH_B else None
                    ),
                )
                observations.append(obs)
                if on_observation is not None:
                    on_observation(obs)
                continue

            obs = _observe(
                anchor=anchor,
                path=path,
                run_index=run_index,
                result=result,
                bundle_fact_count=bundle_fact_count,
                facts_by_id=facts_by_path[path],
                path_b_pre_cap_count=built.path_b_pre_cap_count,
                path_b_cap_bound=built.path_b_cap_bound,
                path_b_seed_retained=built.path_b_seed_retained,
                path_b_cap_policy=built.path_b_cap_policy,
            )
            observations.append(obs)
            if on_observation is not None:
                on_observation(obs)

    return observations
