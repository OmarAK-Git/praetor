"""Path B bundle assembly for the capability spike.

Windowing and anchor-host filtering reuse the real correlation helpers so the
ONLY difference between Path A and Path B is event-type coverage. Do not
reimplement either filter here.

Path B is constructed as a superset of Path A: every in-window Sysmon EventID 1
and Security 4624 is retained uncapped; stratified k-per-EventID + distance fill
applies only to other event types, up to a total ceiling.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from evals.capability.flatten import flatten_event_to_fact, resolve_provenance_path
from praetor.contracts.evidence import EvidenceBundle, EvidenceFact
from praetor.correlation._event_fields import event_timestamp
from praetor.correlation.host_isolation import filter_events_to_anchor_host
from praetor.correlation.security_log import SECURITY_SUCCESSFUL_LOGON_EVENT_ID
from praetor.correlation.sysmon import SYSMON_PROCESS_CREATE_EVENT_ID
from praetor.correlation.window import (
    DEFAULT_CORRELATION_WINDOW_SECONDS,
    filter_events_in_window,
)

# Hard safety ceiling on total Path B facts — should not bind under normal
# Path A density (~max observed 269) + PATH_B_EXTRAS_BUDGET.
PATH_B_MAX_FACTS = 512
# Constant extras increment atop the uncapped {Sysmon 1, Security 4624} floor.
# The A/B delta measures this increment; keep it class-neutral.
PATH_B_EXTRAS_BUDGET = 256
# Stratified take for non-{1,4624} extras only.
PATH_B_MAX_PER_EVENT_ID = 8
PATH_B_CAP_POLICY = (
    f"uncapped_path_a(sysmon_{SYSMON_PROCESS_CREATE_EVENT_ID}"
    f"+security_{SECURITY_SUCCESSFUL_LOGON_EVENT_ID})"
    f";extras_stratified_per_event_id(k={PATH_B_MAX_PER_EVENT_ID})"
    f"+distance_fill;extras_budget={PATH_B_EXTRAS_BUDGET}"
    f";total_ceiling={PATH_B_MAX_FACTS};always_retain_seed"
)


class PathBSupersetError(AssertionError):
    """Path B fact set does not contain Path A's — design invariant broken."""


@dataclass(frozen=True)
class SpikeBundleResult:
    bundle: EvidenceBundle
    pre_cap_count: int
    extras_pre_cap_count: int
    cap_bound: bool
    seed_retained: bool
    path_a_event_count: int
    extras_selected: int
    max_extra_facts: int | None
    cap_policy: str = PATH_B_CAP_POLICY


def _datable(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Drop events without a parseable timestamp or record id."""
    usable: list[Mapping[str, Any]] = []
    for event in events:
        try:
            event_timestamp(event)
        except (ValueError, TypeError):
            continue
        usable.append(event)
    return usable


def _event_id(event: Mapping[str, Any]) -> int:
    try:
        return int(event.get("EventID") or 0)
    except (TypeError, ValueError):
        return 0


def is_path_a_event(event: Mapping[str, Any]) -> bool:
    """True for events correlation Path A would accept (Sysmon 1 / Security 4624)."""
    channel = str(event.get("Channel") or "").lower()
    eid = _event_id(event)
    if "sysmon" in channel and eid == SYSMON_PROCESS_CREATE_EVENT_ID:
        return True
    if channel.startswith("security") and eid == SECURITY_SUCCESSFUL_LOGON_EVENT_ID:
        return True
    return False


def _is_seed_event(
    event: Mapping[str, Any],
    *,
    seed_event_record_id: str | None,
    seed_host_id: str | None,
) -> bool:
    if not seed_event_record_id:
        return False
    rid = str(event.get("EventRecordID") or event.get("record_id") or "")
    if rid != seed_event_record_id:
        return False
    if seed_host_id:
        host = str(event.get("Computer") or "").strip()
        if host and host != seed_host_id:
            return False
    return True


def _rank_key(
    event: Mapping[str, Any], *, anchor_time: datetime
) -> tuple[float, str] | None:
    try:
        ts = event_timestamp(event)
        rid = str(event.get("EventRecordID") or event.get("record_id") or "")
        return (abs((ts - anchor_time).total_seconds()), rid)
    except (ValueError, TypeError):
        return None


def _select_events(
    windowed: Sequence[Mapping[str, Any]],
    *,
    anchor_time: datetime,
    seed_event_record_id: str | None,
    seed_host_id: str | None,
    max_facts: int,
    max_extra_facts: int | None,
    max_per_event_id: int,
) -> tuple[list[Mapping[str, Any]], bool, int, int, int]:
    """Select Path B events: uncapped Path-A types + stratified extras.

    Returns (selected, seed_retained, path_a_count, extras_pre_cap, extras_selected).
    """
    path_a_events: list[Mapping[str, Any]] = []
    extras: list[Mapping[str, Any]] = []
    seed_event: Mapping[str, Any] | None = None

    for event in windowed:
        if _is_seed_event(
            event,
            seed_event_record_id=seed_event_record_id,
            seed_host_id=seed_host_id,
        ):
            seed_event = event
        if is_path_a_event(event):
            path_a_events.append(event)
        else:
            extras.append(event)

    selected: list[Mapping[str, Any]] = list(path_a_events)
    selected_ids = {id(event) for event in selected}
    seed_retained = False
    if seed_event is not None:
        if id(seed_event) in selected_ids:
            seed_retained = True
        else:
            selected.append(seed_event)
            selected_ids.add(id(seed_event))
            seed_retained = True
            # Seed is not a Path-A type (e.g. 4688) — counts against extras.
            if seed_event in extras:
                extras = [event for event in extras if id(event) != id(seed_event)]

    path_a_count = len(path_a_events)
    extras_pre_cap = len(extras)
    if len(selected) > max_facts:
        msg = (
            f"Path A uncapped events ({len(selected)}) exceed Path B total "
            f"ceiling ({max_facts}); raise PATH_B_MAX_FACTS"
        )
        raise PathBSupersetError(msg)

    seed_extra = (
        1
        if (
            seed_retained
            and seed_event is not None
            and not is_path_a_event(seed_event)
        )
        else 0
    )
    room_by_total = max_facts - len(selected)
    if max_extra_facts is None:
        room = room_by_total
    else:
        room = min(room_by_total, max(0, max_extra_facts - seed_extra))

    by_eid: dict[int, list[tuple[float, str, Mapping[str, Any]]]] = defaultdict(list)
    for event in extras:
        ranked = _rank_key(event, anchor_time=anchor_time)
        if ranked is None:
            continue
        by_eid[_event_id(event)].append((ranked[0], ranked[1], event))
    for rows in by_eid.values():
        rows.sort(key=lambda row: (row[0], row[1]))

    stratified: list[tuple[float, str, Mapping[str, Any]]] = []
    for rows in by_eid.values():
        stratified.extend(rows[:max_per_event_id])
    stratified.sort(key=lambda row: (row[0], row[1]))

    extras_selected = 0
    for _dist, _rid, event in stratified:
        if extras_selected >= room:
            break
        if id(event) in selected_ids:
            continue
        selected.append(event)
        selected_ids.add(id(event))
        extras_selected += 1

    if extras_selected < room:
        leftovers: list[tuple[float, str, Mapping[str, Any]]] = []
        for rows in by_eid.values():
            for row in rows[max_per_event_id:]:
                if id(row[2]) not in selected_ids:
                    leftovers.append(row)
        leftovers.sort(key=lambda row: (row[0], row[1]))
        for _dist, _rid, event in leftovers:
            if extras_selected >= room:
                break
            selected.append(event)
            selected_ids.add(id(event))
            extras_selected += 1

    return selected, seed_retained, path_a_count, extras_pre_cap, extras_selected


def build_spike_bundle(
    events: Sequence[Mapping[str, Any]],
    *,
    anchor_time: datetime,
    anchor_host_id: str | None = None,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
    seed_event_record_id: str | None = None,
    seed_host_id: str | None = None,
    max_facts: int = PATH_B_MAX_FACTS,
    max_extra_facts: int | None = PATH_B_EXTRAS_BUDGET,
    max_per_event_id: int = PATH_B_MAX_PER_EVENT_ID,
) -> EvidenceBundle:
    """Build an all-event-type bundle scoped exactly as correlation would."""
    return build_spike_bundle_result(
        events,
        anchor_time=anchor_time,
        anchor_host_id=anchor_host_id,
        window_seconds=window_seconds,
        seed_event_record_id=seed_event_record_id,
        seed_host_id=seed_host_id,
        max_facts=max_facts,
        max_extra_facts=max_extra_facts,
        max_per_event_id=max_per_event_id,
    ).bundle


def build_spike_bundle_result(
    events: Sequence[Mapping[str, Any]],
    *,
    anchor_time: datetime,
    anchor_host_id: str | None = None,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
    seed_event_record_id: str | None = None,
    seed_host_id: str | None = None,
    max_facts: int = PATH_B_MAX_FACTS,
    max_extra_facts: int | None = PATH_B_EXTRAS_BUDGET,
    max_per_event_id: int = PATH_B_MAX_PER_EVENT_ID,
) -> SpikeBundleResult:
    """Build Path B bundle and report pre-cap / binding / seed-retention stats."""
    windowed = filter_events_in_window(
        _datable(events),
        anchor_time=anchor_time,
        window_seconds=window_seconds,
        timestamp_of=event_timestamp,
    )
    if anchor_host_id is not None:
        windowed = filter_events_to_anchor_host(
            windowed, anchor_host_id=anchor_host_id
        )

    pre_cap_count = len(windowed)
    selected, seed_retained, path_a_count, extras_pre_cap, extras_selected = (
        _select_events(
            windowed,
            anchor_time=anchor_time,
            seed_event_record_id=seed_event_record_id,
            seed_host_id=seed_host_id or anchor_host_id,
            max_facts=max_facts,
            max_extra_facts=max_extra_facts,
            max_per_event_id=max_per_event_id,
        )
    )

    facts: list[EvidenceFact] = []
    for event in selected:
        try:
            facts.append(
                flatten_event_to_fact(
                    event, provenance_path=resolve_provenance_path(event)
                )
            )
        except (ValueError, TypeError):
            continue

    extras_budget = (
        max_extra_facts
        if max_extra_facts is not None
        else max(0, max_facts - path_a_count)
    )
    policy = (
        f"uncapped_path_a(sysmon_{SYSMON_PROCESS_CREATE_EVENT_ID}"
        f"+security_{SECURITY_SUCCESSFUL_LOGON_EVENT_ID})"
        f";extras_stratified_per_event_id(k={max_per_event_id})"
        f"+distance_fill;extras_budget={extras_budget};total_ceiling={max_facts}"
        f";always_retain_seed"
    )
    return SpikeBundleResult(
        bundle=EvidenceBundle(facts=facts),
        pre_cap_count=pre_cap_count,
        extras_pre_cap_count=extras_pre_cap,
        cap_bound=extras_pre_cap > extras_selected,
        seed_retained=seed_retained,
        path_a_event_count=path_a_count,
        extras_selected=extras_selected,
        max_extra_facts=max_extra_facts,
        cap_policy=policy,
    )


def assert_path_b_superset_of_path_a(
    path_a: EvidenceBundle,
    path_b: EvidenceBundle,
    *,
    anchor_id: str,
) -> None:
    """Fail loudly if any Path A evidence_id is missing from Path B."""
    a_ids = {fact.evidence_id for fact in path_a.facts}
    b_ids = {fact.evidence_id for fact in path_b.facts}
    missing = sorted(a_ids - b_ids)
    if missing:
        msg = (
            f"anchor {anchor_id}: Path B is not a superset of Path A — "
            f"missing {len(missing)} evidence_id(s), e.g. {missing[:3]}"
        )
        raise PathBSupersetError(msg)
