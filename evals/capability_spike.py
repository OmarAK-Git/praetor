"""Judgment capability spike CLI (non-gating, opt-in, network-using).

Measures whether the single-shot judgment layer separates malicious from
benign telemetry, and how much of any failure is caused by correlation's
two-event-type coverage limit.

NOT a CI gate. Never import this from ``evals/harness.py``.

Enable a live run::

    set PRAETOR_CAPABILITY_SPIKE=1
    set PRAETOR_GEMINI_API_KEY=<key>
    python -m evals.capability_spike --manifest <manifest.yaml> \
        --capture <capture.jsonl> --out <results.jsonl>
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC
from pathlib import Path
from typing import Any

from evals.capability.bundle import build_spike_bundle_result
from evals.capability.corpus import AnchorManifest, load_anchor_manifest
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    AnchorBundleStats,
    Observation,
    inspect_anchor_bundles,
    open_spike_store,
    run_anchor,
)
from evals.capability.score import (
    CONFOUND_GRADED_WARN_THRESHOLD,
    PATH_A_CITATION_CONCENTRATION_THRESHOLD,
    ConfoundReport,
    LabelQuality,
    ab_delta,
    citation_mix_read,
    confound_report,
    label_quality,
    score_path,
)
from praetor.judgment.provider import JudgmentProvider
from praetor.judgment.vertex_provider import DEFAULT_GEMINI_MODEL, VertexProvider

SPIKE_ENV_FLAG = "PRAETOR_CAPABILITY_SPIKE"
GEMINI_API_KEY_ENV = "PRAETOR_GEMINI_API_KEY"
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_ENV = "PRAETOR_GEMINI_MODEL"
GCP_PROJECT_ENVS = (
    "GOOGLE_CLOUD_PROJECT",
    "GCLOUD_PROJECT",
    "PRAETOR_GCP_PROJECT",
)


def spike_enabled() -> bool:
    return os.environ.get(SPIKE_ENV_FLAG, "").strip().lower() in {"1", "true", "yes"}


def _resolve_api_key() -> str | None:
    for env_name in (GEMINI_API_KEY_ENV, GOOGLE_API_KEY_ENV):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def _resolve_gcp_project() -> str | None:
    for env_name in GCP_PROJECT_ENVS:
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def resolve_spike_provider() -> JudgmentProvider | None:
    """Return a live provider only when explicitly enabled and configured.

    Prefers the spike-local Vertex ADC wrapper (schema + thinkingBudget +
    pinned temperature) when a GCP project is set; falls back to API-key
    VertexProvider for environments that only have a Gemini API key.
    """
    if not spike_enabled():
        return None
    project = _resolve_gcp_project()
    if project is not None:
        from evals.capability.spike_vertex_provider import (
            DEFAULT_SPIKE_MODEL,
            DEFAULT_TEMPERATURE,
            SpikeVertexProvider,
        )

        model_name = os.environ.get(GEMINI_MODEL_ENV, DEFAULT_SPIKE_MODEL).strip()
        return SpikeVertexProvider(
            project=project,
            model_name=model_name or DEFAULT_SPIKE_MODEL,
            temperature=DEFAULT_TEMPERATURE,
        )
    api_key = _resolve_api_key()
    if api_key is None:
        return None
    model_name = os.environ.get(GEMINI_MODEL_ENV, DEFAULT_GEMINI_MODEL).strip()
    return VertexProvider(
        api_key=api_key, model_name=model_name or DEFAULT_GEMINI_MODEL
    )


def load_completed_observation_keys(
    path: Path,
) -> set[tuple[str, str, int]]:
    """Load ``(anchor_id, path, run_index)`` triples already present in JSONL."""
    done: set[tuple[str, str, int]] = set()
    if not path.is_file():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                row = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, Mapping):
                continue
            try:
                key = (
                    str(row["anchor_id"]),
                    str(row["path"]),
                    int(row["run_index"]),
                )
            except (KeyError, TypeError, ValueError):
                continue
            done.add(key)
    return done


def _load_observations_jsonl(path: Path) -> list[Observation]:
    """Rehydrate Observation rows from an incremental JSONL file."""
    rows: list[Observation] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                continue
            if not isinstance(raw, Mapping):
                continue
            data = dict(raw)
            if isinstance(data.get("fault_flags"), list):
                data["fault_flags"] = tuple(data["fault_flags"])
            if isinstance(data.get("cited_event_ids"), list):
                data["cited_event_ids"] = tuple(int(x) for x in data["cited_event_ids"])
            try:
                rows.append(Observation(**data))  # type: ignore[arg-type]
            except TypeError:
                continue
    return rows


def load_capture_events(path: Path) -> list[Mapping[str, Any]]:
    """Read a JSON-lines telemetry capture, skipping blank/malformed lines."""
    events: list[Mapping[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, Mapping):
                events.append(parsed)
    return events


def build_anchor_confound_features(
    manifest: AnchorManifest,
    events: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, tuple[str, dict[str, Any]]]:
    """Derive Guard #2 features from the manifest (+ capture when available).

    Always includes ``seed_event_id`` / ``seed_channel`` / ``seed_subject_sid``
    from the manifest so seed-kind and SID class correlation are visible before
    a capture exists. Continuous counts from capture are quantile-binned before
    the disjointness / majority-stump tests so distinct raw values cannot FLAG
    by construction.
    """
    from statistics import quantiles

    from evals.capability.runner import split_events_by_channel
    from praetor.correlation import correlate_telemetry

    features: dict[str, tuple[str, dict[str, Any]]] = {}
    raw_a: dict[str, int] = {}
    raw_pre: dict[str, int] = {}

    by_host: dict[str, list[Mapping[str, Any]]] | None = None
    if events is not None:
        by_host = {}
        for event in events:
            host_key = str(event.get("Computer") or "").strip()
            if host_key:
                by_host.setdefault(host_key, []).append(event)

    for anchor in manifest.anchors:
        if anchor.expected_class not in {"malicious", "benign"}:
            continue
        moment = anchor.anchor_time
        feat: dict[str, Any] = {
            "seed_event_id": (
                anchor.seed_event_id if anchor.seed_event_id is not None else ""
            ),
            "seed_channel": anchor.seed_channel or "",
            "seed_subject_sid": anchor.seed_subject_sid or "",
            "calendar_day": moment.date().isoformat(),
            "hour_utc": moment.astimezone(UTC).strftime("%H"),
        }
        if events is not None and by_host is not None:
            host = anchor.seed_host_id
            scoped = by_host.get(host or "", events) if host else events
            sysmon, security = split_events_by_channel(scoped)
            path_a = correlate_telemetry(
                sysmon_events=sysmon,
                security_events=security,
                anchor_time=anchor.anchor_time,
                anchor_host_id=host,
            ).bundle
            result = build_spike_bundle_result(
                scoped,
                anchor_time=anchor.anchor_time,
                anchor_host_id=host,
                seed_event_record_id=anchor.seed_event_record_id,
                seed_host_id=anchor.seed_host_id,
            )
            feat["host_id"] = host or ""
            feat["path_b_cap_bound"] = int(result.cap_bound)
            raw_a[anchor.anchor_id] = len(path_a.facts)
            raw_pre[anchor.anchor_id] = result.pre_cap_count
        features[anchor.anchor_id] = (anchor.expected_class, feat)

    def _bin(raw: dict[str, int], *, n_bins: int = 4) -> dict[str, str]:
        if not raw:
            return {}
        values = list(raw.values())
        if len(set(values)) == 1:
            return {aid: "q1" for aid in raw}
        if len(values) < n_bins:
            # Too few points for n bins — use unique rank labels.
            ordered = sorted(set(values))
            return {
                aid: f"v{ordered.index(val)}" for aid, val in raw.items()
            }
        cuts = quantiles(values, n=n_bins, method="inclusive")

        def label(val: int) -> str:
            for idx, cut in enumerate(cuts):
                if val <= cut:
                    return f"q{idx + 1}"
            return f"q{len(cuts) + 1}"

        return {aid: label(val) for aid, val in raw.items()}

    a_bins = _bin(raw_a)
    pre_bins = _bin(raw_pre)
    for aid, bin_label in a_bins.items():
        features[aid][1]["path_a_fact_count"] = bin_label
    for aid, bin_label in pre_bins.items():
        features[aid][1]["path_b_pre_cap_count"] = bin_label
    return features


def _format_confound(report: ConfoundReport) -> list[str]:
    lines = ["", "--- confound check (guard #2) ---"]
    if not report.perfect_separation and not report.graded_separation:
        lines.append("confound: no scored-anchor features available")
        return lines
    perfect_bits = " ".join(
        f"{name}={'FLAG' if flag else 'ok'}"
        for name, flag in sorted(report.perfect_separation.items())
    )
    graded_bits = " ".join(
        f"{name}={score:.2f}"
        for name, score in sorted(report.graded_separation.items())
    )
    lines.append(f"confound perfect_separation {perfect_bits}")
    lines.append(
        f"confound graded_separation (majority-stump accuracy; "
        f"warn>={CONFOUND_GRADED_WARN_THRESHOLD:.0%}) {graded_bits}"
    )
    stump_a = report.graded_separation.get("path_a_fact_count")
    stump_b = report.graded_separation.get("path_b_pre_cap_count")
    if stump_a is not None or stump_b is not None:
        lines.append(
            "trivial_stump_baselines (judgment must beat these) "
            f"path_a_fact_count="
            f"{'n/a' if stump_a is None else f'{stump_a:.2%}'} "
            f"path_b_pre_cap_count="
            f"{'n/a' if stump_b is None else f'{stump_b:.2%}'}"
        )
    if report.warned_features:
        lines.append(
            "confound WARN near/perfect separators: "
            + ", ".join(report.warned_features)
        )
    else:
        lines.append("confound WARN none")
    return lines


def _summarize(
    observations: Sequence[Observation],
    *,
    quality: LabelQuality,
    confound: ConfoundReport | None = None,
) -> str:
    lines: list[str] = ["", "=== capability spike summary ==="]

    share = quality.unchained_step_share
    share_text = "n/a" if share is None else f"{share:.2%}"
    steps_text = (
        "n/a"
        if quality.emulation_steps_total is None
        else str(quality.emulation_steps_total)
    )
    unchained_text = (
        "n/a" if quality.unchained_steps is None else str(quality.unchained_steps)
    )
    lines.append(
        f"label_quality n_unresolved={quality.n_unresolved} "
        f"n_malicious={quality.n_malicious} n_benign={quality.n_benign} "
        f"emulation_steps_total={steps_text} unchained_steps={unchained_text} "
        f"unchained_step_share={share_text}"
    )

    stump_a = (
        None
        if confound is None
        else confound.graded_separation.get("path_a_fact_count")
    )
    stump_b = (
        None
        if confound is None
        else confound.graded_separation.get("path_b_pre_cap_count")
    )
    stump_a_text = "n/a" if stump_a is None else f"{stump_a:.2%}"
    stump_b_text = "n/a" if stump_b is None else f"{stump_b:.2%}"
    lines.append("")
    lines.append(
        "trivial_stump_baselines (majority-stump accuracy; judgment must beat these) "
        f"path_a_fact_count={stump_a_text} path_b_pre_cap_count={stump_b_text}"
    )

    for path in (PATH_A, PATH_B):
        score = score_path(observations, path=path)
        rate = score.separation_rate
        rate_text = "n/a" if rate is None else f"{rate:.2%}"
        resolution = score.citation_resolution_rate
        resolution_text = "n/a" if resolution is None else f"{resolution:.2%}"
        baseline = stump_a if path == PATH_A else stump_b
        baseline_text = "n/a" if baseline is None else f"{baseline:.2%}"
        beats = ""
        if rate is not None and baseline is not None:
            if rate > baseline:
                beats = " BEATS_baseline"
            elif rate < baseline:
                beats = " BELOW_baseline"
            else:
                beats = " TIES_baseline"
        lines.append(
            f"path={path} scored={score.scored} correct={score.correct} "
            f"separation={rate_text} baseline_stump={baseline_text}{beats} "
            f"citations_resolved={resolution_text} "
            f"excluded_no_judgment={score.excluded_empty_bundle} "
            f"excluded_unresolved={score.excluded_unresolved} "
            f"unstable={len(score.unstable_anchors)}"
        )

    mix = citation_mix_read(observations)
    conc = mix.path_b_path_a_concentration
    conc_text = "n/a" if conc is None else f"{conc:.2%}"
    lines.append("")
    lines.append(
        f"citation_mix path_b_path_a_concentration={conc_text} "
        f"(threshold={PATH_A_CITATION_CONCENTRATION_THRESHOLD:.0%}) "
        f"tie_interpretation={mix.tie_interpretation}"
    )

    lines.append("")
    lines.append("--- A/B delta (path_a, path_b) ---")
    buckets: dict[tuple[str, str], list[str]] = {}
    for anchor_id, pair in ab_delta(observations).items():
        buckets.setdefault(pair, []).append(anchor_id)
    for pair, anchors in sorted(buckets.items()):
        lines.append(f"{pair[0]:>8} / {pair[1]:<8} n={len(anchors):<3} {', '.join(anchors)}")

    if confound is not None:
        lines.extend(_format_confound(confound))

    lines.append("")
    lines.append(
        "Read ('wrong','right') as coverage-limited; ('wrong','wrong') as "
        "judgment-limited. On A~B ties, prompt_constrained means Path B cites "
        "still concentrate on EventID 1/4624; coverage_not_bottleneck means the "
        "model used richer facts and still tied. Gate columns in the JSONL are "
        "recorded, not scored."
    )
    return "\n".join(lines)

def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def format_bundle_stats_report(stats: Sequence[AnchorBundleStats]) -> str:
    """Summarize Path A/B bundle sizes split by expected_class (no provider)."""
    lines = ["", "--- bundle stats (no provider) ---"]
    scored = [row for row in stats if row.expected_class in {"malicious", "benign"}]
    if not scored:
        lines.append("no scored anchors")
        return "\n".join(lines)

    for label in ("malicious", "benign", "all_scored"):
        rows = (
            scored
            if label == "all_scored"
            else [row for row in scored if row.expected_class == label]
        )
        if not rows:
            lines.append(f"{label}: n=0")
            continue
        a_counts = [row.path_a_fact_count for row in rows]
        b_counts = [row.path_b_fact_count for row in rows]
        a_empty = sum(1 for count in a_counts if count == 0)
        b_empty = sum(1 for count in b_counts if count == 0)
        a_4624 = sum(1 for row in rows if row.path_a_has_4624)
        prov_counts = [len(row.path_a_provenance_paths) for row in rows]
        b_gt_a = sum(1 for row in rows if row.path_b_fact_count > row.path_a_fact_count)
        lines.append(
            f"{label}: n={len(rows)} "
            f"path_a_facts min/median/max="
            f"{min(a_counts)}/{_median(a_counts):.1f}/{max(a_counts)} "
            f"path_a_empty={a_empty} "
            f"path_a_with_4624={a_4624} "
            f"path_a_provenance_paths min/median/max="
            f"{min(prov_counts)}/{_median(prov_counts):.1f}/{max(prov_counts)} "
            f"path_b_facts min/median/max="
            f"{min(b_counts)}/{_median(b_counts):.1f}/{max(b_counts)} "
            f"path_b_empty={b_empty} "
            f"path_b_gt_path_a={b_gt_a}/{len(rows)}"
        )

    lines.append("")
    lines.append(
        "per_anchor a_facts b_facts b>a superset a_chars b_chars "
        "a_excerpts/fact b_excerpts/fact a_omit b_omit a_incomplete b_incomplete"
    )
    for row in sorted(scored, key=lambda r: r.anchor_id):
        ap = row.path_a_prompt
        bp = row.path_b_prompt
        lines.append(
            f"  {row.anchor_id} {row.expected_class} "
            f"a={row.path_a_fact_count} b={row.path_b_fact_count} "
            f"b_gt_a={int(row.path_b_fact_count > row.path_a_fact_count)} "
            f"superset={int(row.path_b_superset_ok and row.path_b_prompt_superset_ok)} "
            f"a_chars={ap.prompt_char_length} b_chars={bp.prompt_char_length} "
            f"a_ex/f={ap.excerpts_per_fact_mean:.1f} "
            f"b_ex/f={bp.excerpts_per_fact_mean:.1f} "
            f"a_omit={ap.omitted_characters_sum} b_omit={bp.omitted_characters_sum} "
            f"a_inc={ap.incomplete_excerpt_count} b_inc={bp.incomplete_excerpt_count}"
        )

    mal_empty = sum(
        1
        for row in scored
        if row.expected_class == "malicious" and row.path_a_fact_count == 0
    )
    ben_empty = sum(
        1
        for row in scored
        if row.expected_class == "benign" and row.path_a_fact_count == 0
    )
    n_mal = sum(1 for row in scored if row.expected_class == "malicious")
    n_ben = sum(1 for row in scored if row.expected_class == "benign")
    b_gt_a_all = sum(
        1 for row in scored if row.path_b_fact_count > row.path_a_fact_count
    )
    lines.append("")
    lines.append(
        f"path_a_empty_by_class malicious={mal_empty}/{n_mal} "
        f"benign={ben_empty}/{n_ben}"
    )
    lines.append(
        f"path_b_gt_path_a={b_gt_a_all}/{len(scored)} "
        f"superset_ok="
        f"{sum(1 for r in scored if r.path_b_superset_ok)}/{len(scored)} "
        f"prompt_superset_ok="
        f"{sum(1 for r in scored if r.path_b_prompt_superset_ok)}/{len(scored)}"
    )
    if mal_empty != ben_empty:
        lines.append(
            "WARNING: Path A empty-bundle counts differ by class — "
            "A separation / A/B delta will be on an unbalanced survivor set."
        )
    else:
        lines.append(
            "Path A empty-bundle counts are balanced across classes "
            f"(each side {mal_empty})."
        )
    if b_gt_a_all < len(scored):
        lines.append(
            "WARNING: Path B is not strictly larger than Path A on all anchors."
        )
    else:
        lines.append("Path B fact counts strictly exceed Path A on all scored anchors.")

    # A/B excerpt asymmetry (constant per-field truncation; scales with fields/fact).
    a_ex = [row.path_a_prompt.excerpts_per_fact_mean for row in scored]
    b_ex = [row.path_b_prompt.excerpts_per_fact_mean for row in scored]
    a_omit = [row.path_a_prompt.omitted_characters_sum for row in scored]
    b_omit = [row.path_b_prompt.omitted_characters_sum for row in scored]
    a_chars = [row.path_a_prompt.prompt_char_length for row in scored]
    b_chars = [row.path_b_prompt.prompt_char_length for row in scored]
    lines.append("")
    lines.append(
        "prompt_size path_a_chars min/median/max="
        f"{min(a_chars)}/{_median(a_chars):.0f}/{max(a_chars)} "
        f"path_b_chars min/median/max="
        f"{min(b_chars)}/{_median(b_chars):.0f}/{max(b_chars)}"
    )
    lines.append(
        "excerpt_asymmetry path_a excerpts/fact "
        f"min/median/max={min(a_ex):.1f}/{sorted(a_ex)[len(a_ex)//2]:.1f}/{max(a_ex):.1f} "
        "path_b excerpts/fact "
        f"min/median/max={min(b_ex):.1f}/{sorted(b_ex)[len(b_ex)//2]:.1f}/{max(b_ex):.1f}"
    )
    lines.append(
        "excerpt_truncation omitted_chars path_a "
        f"min/median/max={min(a_omit)}/{_median(a_omit):.0f}/{max(a_omit)} "
        f"path_b min/median/max={min(b_omit)}/{_median(b_omit):.0f}/{max(b_omit)}"
    )
    return "\n".join(lines)


def _run_bundles_only(*, manifest_path: Path, capture_path: Path) -> int:
    from evals.capability.bundle import PATH_B_MAX_FACTS

    manifest = load_anchor_manifest(manifest_path)
    print(f"loading capture {capture_path} ...", flush=True)
    events = load_capture_events(capture_path)
    print(
        f"capture={manifest.capture_id} anchors={len(manifest.anchors)} "
        f"events={len(events)} mode=bundles-only "
        f"path_b_total_max={PATH_B_MAX_FACTS}",
        flush=True,
    )
    by_host: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        host = str(event.get("Computer") or "").strip()
        if host:
            by_host.setdefault(host, []).append(event)

    stats: list[AnchorBundleStats] = []
    for anchor in manifest.anchors:
        if anchor.expected_class not in {"malicious", "benign"}:
            continue
        host = (anchor.seed_host_id or "").strip()
        scoped = by_host.get(host, events) if host else events
        row = inspect_anchor_bundles(anchor=anchor, events=scoped)
        stats.append(row)
        print(
            f"  {row.anchor_id} a={row.path_a_fact_count} b={row.path_b_fact_count} "
            f"b>a={int(row.path_b_fact_count > row.path_a_fact_count)} "
            f"superset={int(row.path_b_superset_ok)} "
            f"b_chars={row.path_b_prompt.prompt_char_length} "
            f"b_ex/f={row.path_b_prompt.excerpts_per_fact_mean:.1f}",
            flush=True,
        )
    print(format_bundle_stats_report(stats))
    confound = confound_report(build_anchor_confound_features(manifest, events))
    for line in _format_confound(confound):
        if line:
            print(line)
    return 0


def _run_extras_sensitivity(*, manifest_path: Path, capture_path: Path) -> int:
    """Compare Path B extras budgets 64 vs 256 on a 6+6 subset (no provider)."""
    from evals.capability.bundle import PATH_B_MAX_FACTS

    levels = (64, 256)
    manifest = load_anchor_manifest(manifest_path)
    print(f"loading capture {capture_path} ...", flush=True)
    events = load_capture_events(capture_path)
    mals = [a for a in manifest.anchors if a.expected_class == "malicious"][:6]
    bens = [a for a in manifest.anchors if a.expected_class == "benign"][:6]
    subset = mals + bens
    print(
        f"extras_sensitivity n={len(subset)} levels={list(levels)} "
        f"total_max={PATH_B_MAX_FACTS} cap_policy=uncapped_path_a+stratified_extras",
        flush=True,
    )
    by_host: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        host = str(event.get("Computer") or "").strip()
        if host:
            by_host.setdefault(host, []).append(event)

    # aid -> extras_budget -> stats
    by_level: dict[int, list[AnchorBundleStats]] = {level: [] for level in levels}
    for anchor in subset:
        host = (anchor.seed_host_id or "").strip()
        scoped = by_host.get(host, events) if host else events
        for level in levels:
            row = inspect_anchor_bundles(
                anchor=anchor, events=scoped, max_extra_facts=level
            )
            by_level[level].append(row)
            print(
                f"  extras={level} {row.anchor_id} a={row.path_a_fact_count} "
                f"b={row.path_b_fact_count} extras_est="
                f"{row.path_b_fact_count - row.path_a_fact_count} "
                f"b_chars={row.path_b_prompt.prompt_char_length}",
                flush=True,
            )

    lines = ["", "--- extras-budget sensitivity (6 mal + 6 ben) ---"]
    for level in levels:
        rows = by_level[level]
        b_counts = [r.path_b_fact_count for r in rows]
        chars = [r.path_b_prompt.prompt_char_length for r in rows]
        extras = [r.path_b_fact_count - r.path_a_fact_count for r in rows]
        lines.append(
            f"extras_budget={level}: path_b_facts "
            f"min/median/max={min(b_counts)}/{_median(b_counts):.1f}/{max(b_counts)} "
            f"extras_selected min/median/max="
            f"{min(extras)}/{_median(extras):.1f}/{max(extras)} "
            f"prompt_chars min/median/max="
            f"{min(chars)}/{_median(chars):.0f}/{max(chars)}"
        )
    # Pairwise delta per anchor
    lines.append("per_anchor delta (extras=256 minus extras=64)")
    for low, high in zip(by_level[64], by_level[256], strict=True):
        assert low.anchor_id == high.anchor_id
        lines.append(
            f"  {low.anchor_id} "
            f"b_facts {low.path_b_fact_count}->{high.path_b_fact_count} "
            f"(d{high.path_b_fact_count - low.path_b_fact_count}) "
            f"chars {low.path_b_prompt.prompt_char_length}"
            f"->{high.path_b_prompt.prompt_char_length} "
            f"(d{high.path_b_prompt.prompt_char_length - low.path_b_prompt.prompt_char_length})"
        )
    # Does richness composition change? Cap still binds on extras pre-cap.
    bound_64 = sum(1 for r in by_level[64] if r.path_b_cap_bound)
    bound_256 = sum(1 for r in by_level[256] if r.path_b_cap_bound)
    lines.append(
        f"extras_cap_bound rate: budget_64={bound_64}/{len(by_level[64])} "
        f"budget_256={bound_256}/{len(by_level[256])}"
    )
    fact_moved = any(
        hi.path_b_fact_count != lo.path_b_fact_count
        for lo, hi in zip(by_level[64], by_level[256], strict=True)
    )
    if fact_moved:
        lines.append(
            "FINDING: Path B fact counts move with extras budget — "
            "record both levels in the artifact; A/B delta may be cap-sensitive."
        )
    else:
        lines.append(
            "Path B fact counts identical at extras 64 and 256 on this subset "
            "(unexpected if extras_pre_cap > 256)."
        )
    print("\n".join(lines))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Praetor judgment capability spike")
    parser.add_argument("--manifest", type=Path, help="labeled anchor manifest YAML")
    parser.add_argument("--capture", type=Path, help="JSON-lines telemetry capture")
    parser.add_argument("--out", type=Path, help="JSONL output path")
    parser.add_argument("--runs", type=int, default=3, help="runs per anchor per path")
    parser.add_argument(
        "--bundles-only",
        action="store_true",
        help="Build Path A/B bundles and print stats; no provider / no API key",
    )
    parser.add_argument(
        "--extras-sensitivity",
        action="store_true",
        help=(
            "Compare Path B extras budgets 64 vs 256 on 6 mal + 6 ben "
            "(no provider)"
        ),
    )
    args = parser.parse_args(argv)

    if args.manifest is None or args.capture is None:
        print("capability spike skipped: --manifest and --capture are required")
        return 0

    if args.bundles_only:
        return _run_bundles_only(
            manifest_path=args.manifest, capture_path=args.capture
        )
    if args.extras_sensitivity:
        return _run_extras_sensitivity(
            manifest_path=args.manifest, capture_path=args.capture
        )

    provider = resolve_spike_provider()
    if provider is None:
        if not spike_enabled():
            print(f"capability spike skipped: {SPIKE_ENV_FLAG} not enabled")
        else:
            print(
                "capability spike skipped: no GCP project "
                f"({', '.join(GCP_PROJECT_ENVS)}) and no API key in "
                f"{GEMINI_API_KEY_ENV} or {GOOGLE_API_KEY_ENV}"
            )
        return 0

    manifest = load_anchor_manifest(args.manifest)
    events = load_capture_events(args.capture)
    by_host: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        host_key = str(event.get("Computer") or "").strip()
        if host_key:
            by_host.setdefault(host_key, []).append(event)

    quality = label_quality(manifest)
    confound = confound_report(build_anchor_confound_features(manifest, events))
    print(
        f"capture={manifest.capture_id} anchors={len(manifest.anchors)} "
        f"events={len(events)} runs={args.runs} "
        f"n_unresolved={quality.n_unresolved}"
    )
    for line in _format_confound(confound):
        if line:
            print(line)

    provider_meta: dict[str, Any] = {
        "provider_name": getattr(provider, "provider_name", type(provider).__name__),
        "model_name": getattr(provider, "model_name", None),
        "temperature": getattr(provider, "temperature", None),
        "max_output_tokens": getattr(provider, "max_output_tokens", None),
        "thinking_budget": getattr(provider, "thinking_budget", None),
    }
    print(
        "provider="
        f"{provider_meta['provider_name']} model={provider_meta['model_name']} "
        f"temperature={provider_meta['temperature']}"
    )

    done_keys: set[tuple[str, str, int]] = set()
    prior_count = 0
    out_handle = None
    if args.out is not None:
        done_keys = load_completed_observation_keys(args.out)
        prior_count = len(done_keys)
        if prior_count:
            print(
                f"resume: skipping {prior_count} completed "
                f"(anchor_id, path, run_index) triples from {args.out}"
            )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        meta_path = args.out.with_suffix(args.out.suffix + ".meta.json")
        meta_path.write_text(
            json.dumps(
                {
                    "capture_id": manifest.capture_id,
                    "runs": args.runs,
                    **provider_meta,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        out_handle = args.out.open("a", encoding="utf-8")

    observations: list[Observation] = []

    def _flush_observation(obs: Observation) -> None:
        observations.append(obs)
        if out_handle is not None:
            out_handle.write(json.dumps(asdict(obs), sort_keys=True) + "\n")
            out_handle.flush()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = open_spike_store(Path(tmpdir) / "spike.db")
            try:
                for anchor in manifest.anchors:
                    host = (anchor.seed_host_id or "").strip()
                    scoped = by_host.get(host, events) if host else events
                    new_obs = run_anchor(
                        store,
                        anchor=anchor,
                        events=scoped,
                        provider=provider,
                        runs=args.runs,
                        skip_keys=done_keys,
                        on_observation=_flush_observation,
                    )
                    print(
                        f"  ran anchor={anchor.anchor_id} "
                        f"new_observations={len(new_obs)}"
                    )
            finally:
                store.conn.close()
    finally:
        if out_handle is not None:
            out_handle.close()

    # Resume summaries need prior rows too (scoring uses full matrix).
    if args.out is not None and args.out.is_file():
        all_obs = _load_observations_jsonl(args.out)
        if all_obs:
            observations = all_obs

    if args.out is not None:
        print(
            f"wrote/flushed observations to {args.out} "
            f"(total_rows={len(observations)}, new_this_session={len(observations) - prior_count})"
        )

    print(_summarize(observations, quality=quality, confound=confound))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
