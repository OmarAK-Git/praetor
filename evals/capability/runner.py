"""Two-path anchor execution for the capability spike.

Path A uses real ``correlate_telemetry`` (Sysmon EventID 1 + Security 4624
only). Path B uses a harness-built all-event-type bundle. Everything
downstream runs for real on both paths.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evals.capability.bundle import build_spike_bundle
from evals.capability.corpus import Anchor
from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.correlation.host_isolation import resolve_anchor_host_id
from praetor.engine.orchestrator import (
    SucceedingStampBackend,
    process_alert_intake,
)
from praetor.judgment.provider import JudgmentProvider
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
    error: str | None = None


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


def _split_events(
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


def _observe(
    *,
    anchor: Anchor,
    path: str,
    run_index: int,
    result: Any,
    bundle_fact_count: int,
) -> Observation:
    edict = getattr(result, "edict", None)
    fault_flags = tuple(str(flag) for flag in getattr(result, "fault_flags", ()))
    proposed: str | None = None
    citation_count = 0
    if edict is not None:
        proposed = edict.model_judgment.proposed_disposition.value
        citation_count = len(edict.model_judgment.cited_evidence_refs)
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
    )


def run_anchor(
    store: StateStore,
    *,
    anchor: Anchor,
    events: Sequence[Mapping[str, Any]],
    provider: JudgmentProvider,
    runs: int = 3,
    window_seconds: int | None = None,
) -> list[Observation]:
    """Run one anchor through both paths ``runs`` times each."""
    sysmon, security = _split_events(events)
    anchor_host = resolve_anchor_host_id(
        sysmon_events=sysmon,
        security_events=security,
        anchor_time=anchor.anchor_time,
    )
    bundle_kwargs: dict[str, Any] = {
        "anchor_time": anchor.anchor_time,
        "anchor_host_id": anchor_host,
    }
    if window_seconds is not None:
        bundle_kwargs["window_seconds"] = window_seconds
    spike_bundle = build_spike_bundle(events, **bundle_kwargs)

    # Both counts are deterministic given (events, anchor), so compute once.
    fact_counts = {
        PATH_A: _path_a_fact_count(sysmon, security, anchor, anchor_host),
        PATH_B: len(spike_bundle.facts),
    }

    observations: list[Observation] = []
    stamp_backend = SucceedingStampBackend()

    for run_index in range(runs):
        for path in (PATH_A, PATH_B):
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
            except (RuntimeError, ValueError) as exc:
                observations.append(
                    Observation(
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
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )
                continue

            observations.append(
                _observe(
                    anchor=anchor,
                    path=path,
                    run_index=run_index,
                    result=result,
                    bundle_fact_count=bundle_fact_count,
                )
            )

    return observations


def _path_a_fact_count(
    sysmon: Sequence[Mapping[str, Any]],
    security: Sequence[Mapping[str, Any]],
    anchor: Anchor,
    anchor_host: str | None,
) -> int:
    """Count facts correlation would build, for A/B coverage comparison."""
    from praetor.correlation import correlate_telemetry

    correlated = correlate_telemetry(
        sysmon_events=list(sysmon),
        security_events=list(security),
        anchor_time=anchor.anchor_time,
        anchor_host_id=anchor_host,
    )
    return len(correlated.bundle.facts)
