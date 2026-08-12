#!/usr/bin/env python3
"""One-shot provider smoke probe for Path A or Path B (NOT scored).

Uses the spike-local Vertex wrapper (responseSchema + maxOutputTokens +
thinkingBudget=0 + pinned temperature) over ADC. Records finishReason so
MAX_TOKENS is never collapsed into a JSON parse error.

Pass condition (default): parse + >=2 resolving citations + non-empty
``cited_event_ids`` join. Disposition is recorded but must not be used to
tune prompts or selection.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals.capability.corpus import load_anchor_manifest
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    build_path_bundles,
    cited_event_ids_from_judgment,
    open_spike_store,
)
from evals.capability.spike_vertex_provider import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_SPIKE_MODEL,
    DEFAULT_TEMPERATURE,
    DEFAULT_THINKING_BUDGET,
    ProviderOutputTruncatedError,
    SpikeVertexProvider,
)
from evals.capability_spike import load_capture_events
from praetor.correlation.excerpts import build_correlation_prompt_excerpts
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.evidence.citations import validate_evidence_citations
from praetor.evidence.provenance import distinct_provenance_paths
from praetor.judgment.prompt import build_judgment_prompt_payload_from_excerpt_set
from praetor.judgment.provider import (
    JudgmentRequest,
    ProviderError,
    ProviderMalformedResponseError,
    ProviderRefusalError,
    ProviderUnavailableError,
)


def _project_id() -> str:
    for key in ("GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "PRAETOR_GCP_PROJECT"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    raise SystemExit("set GOOGLE_CLOUD_PROJECT")


def _pick_anchor(
    manifest_path: Path,
    capture_path: Path,
    *,
    anchor_id: str | None,
    max_extra_facts: int | None,
    path: str,
):
    manifest = load_anchor_manifest(manifest_path)
    events = load_capture_events(capture_path)
    by_host: dict[str, list] = {}
    for event in events:
        host = str(event.get("Computer") or "").strip()
        if host:
            by_host.setdefault(host, []).append(event)

    scored = [
        a
        for a in manifest.anchors
        if a.expected_class in {"malicious", "benign"}
    ]
    if anchor_id:
        matches = [a for a in scored if a.anchor_id == anchor_id]
        if not matches:
            raise SystemExit(f"anchor {anchor_id!r} not found")
        candidates = matches
    else:
        candidates = scored

    best = None
    best_built = None
    for anchor in candidates:
        host = (anchor.seed_host_id or "").strip()
        scoped = by_host.get(host, events) if host else events
        built = build_path_bundles(
            anchor=anchor,
            events=scoped,
            max_extra_facts=max_extra_facts,
        )
        size = (
            len(built.path_a.facts) if path == PATH_A else len(built.path_b.facts)
        )
        best_size = (
            0
            if best_built is None
            else (
                len(best_built.path_a.facts)
                if path == PATH_A
                else len(best_built.path_b.facts)
            )
        )
        if best is None or size > best_size:
            best = anchor
            best_built = built
    assert best is not None and best_built is not None
    return best, best_built


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "evals/capability/manifests/atlasv2_attack_day.yaml",
    )
    parser.add_argument(
        "--capture",
        type=Path,
        default=ROOT / "evals/capability/captures/atlasv2_attack_day.jsonl",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    parser.add_argument("--anchor-id", default="ben-06")
    parser.add_argument(
        "--path",
        choices=(PATH_A, PATH_B),
        default=PATH_B,
        help="correlation=Path A, flattened=Path B",
    )
    parser.add_argument("--max-extra-facts", type=int, default=None)
    parser.add_argument(
        "--model",
        default=os.environ.get("PRAETOR_GEMINI_MODEL", DEFAULT_SPIKE_MODEL),
    )
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument(
        "--min-resolving-citations",
        type=int,
        default=2,
        help="Pass threshold for resolving citations (Path A probe uses 2)",
    )
    args = parser.parse_args()
    if args.out is None:
        name = (
            "path_a_smoke_probe.json"
            if args.path == PATH_A
            else "path_b_smoke_probe.json"
        )
        args.out = ROOT / "evals/capability/captures" / name

    print(f"building Path {'A' if args.path == PATH_A else 'B'} bundle...", flush=True)
    anchor, built = _pick_anchor(
        args.manifest,
        args.capture,
        anchor_id=args.anchor_id,
        max_extra_facts=args.max_extra_facts,
        path=args.path,
    )
    bundle = built.path_a if args.path == PATH_A else built.path_b
    prompt_stats = (
        built.path_a_prompt if args.path == PATH_A else built.path_b_prompt
    )
    provenance_paths = sorted(distinct_provenance_paths(bundle.facts))
    print(
        f"probe_anchor={anchor.anchor_id} class={anchor.expected_class} "
        f"path={args.path} "
        f"path_a_facts={len(built.path_a.facts)} "
        f"path_b_facts={len(built.path_b.facts)} "
        f"bundle_facts={len(bundle.facts)} "
        f"provenance_paths={provenance_paths} "
        f"prompt_chars={prompt_stats.prompt_char_length} "
        f"max_extra_facts={args.max_extra_facts}",
        flush=True,
    )

    excerpt_set = build_correlation_prompt_excerpts(bundle)
    payload = build_judgment_prompt_payload_from_excerpt_set(
        excerpt_set=excerpt_set,
        evidence_bundle_hash="smoke-probe",
        org_config_snapshot_hash="smoke-probe",
        org_config_verbatim="",
        exemplar_block=None,
    )
    request = JudgmentRequest(
        scenario_id=f"smoke-probe-{anchor.anchor_id}-{args.path}",
        payload=payload,
        evidence_bundle=bundle,
    )

    provider = SpikeVertexProvider(
        model_name=(args.model or DEFAULT_SPIKE_MODEL).strip(),
        project=_project_id(),
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        thinking_budget=DEFAULT_THINKING_BUDGET,
        temperature=DEFAULT_TEMPERATURE,
        timeout_seconds=args.timeout,
    )
    print(
        f"calling spike Vertex model={provider.model_name} "
        f"temperature={provider.temperature} "
        f"maxOutputTokens={provider.max_output_tokens} "
        f"thinkingBudget={provider.thinking_budget} ...",
        flush=True,
    )

    artifact: dict = {
        "probe": True,
        "scored": False,
        "path": args.path,
        "anchor_id": anchor.anchor_id,
        "expected_class": anchor.expected_class,
        "path_a_fact_count": len(built.path_a.facts),
        "path_b_fact_count": len(built.path_b.facts),
        "bundle_fact_count": len(bundle.facts),
        "provenance_paths": provenance_paths,
        "provenance_path_count": len(provenance_paths),
        "prompt_char_length": prompt_stats.prompt_char_length,
        "excerpts_per_fact_mean": prompt_stats.excerpts_per_fact_mean,
        "model": provider.model_name,
        "temperature": provider.temperature,
        "max_output_tokens": provider.max_output_tokens,
        "thinking_budget": provider.thinking_budget,
        "response_schema": "ModelJudgment",
        "provider": provider.provider_name,
        "max_extra_facts": args.max_extra_facts,
        "timestamp_utc": datetime.now(tz=UTC).isoformat(),
    }

    t0 = datetime.now(tz=UTC)
    judgment = None
    finish_reason = None
    # Path A: exercise the real intake/gate path so fault_flags reflect wiring
    # (insufficient_corroboration on single-provenance is expected, not tuned).
    use_intake = args.path == PATH_A
    try:
        if use_intake:
            import tempfile
            import uuid
            from pathlib import Path as _Path

            with tempfile.TemporaryDirectory() as tmpdir:
                store = open_spike_store(_Path(tmpdir) / "smoke.db")
                try:
                    result = process_alert_intake(
                        store,
                        judgment_provider=provider,
                        stamp_backend=SucceedingStampBackend(),
                        alert_identity=(
                            f"smoke-{anchor.anchor_id}-{args.path}-"
                            f"{uuid.uuid4().hex[:8]}"
                        ),
                        anchor_time=anchor.anchor_time,
                        sysmon_events=list(built.sysmon),
                        security_events=list(built.security),
                    )
                finally:
                    store.conn.close()
            elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
            fault_flags = [str(f) for f in getattr(result, "fault_flags", ())]
            edict = getattr(result, "edict", None)
            if edict is None:
                artifact.update(
                    {
                        "elapsed_seconds": elapsed,
                        "http_status": 200,
                        "finish_reason": None,
                        "judgment_parsed": False,
                        "failure_class": "no_edict",
                        "fault_flags": fault_flags,
                        "parse_error": "process_alert_intake returned no edict",
                    }
                )
            else:
                judgment = edict.model_judgment
                artifact.update(
                    {
                        "elapsed_seconds": elapsed,
                        "http_status": 200,
                        "finish_reason": "STOP",
                        "judgment_parsed": True,
                        "proposed_disposition": judgment.proposed_disposition.value,
                        "citation_count": len(judgment.cited_evidence_refs),
                        "fault_flags": fault_flags,
                        "final_disposition": (
                            result.disposition.value
                            if getattr(result, "disposition", None) is not None
                            else None
                        ),
                    }
                )
                finish_reason = "STOP"
        else:
            detailed = provider.generate_judgment_detailed(request)
            elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
            judgment = detailed["judgment"]
            finish_reason = detailed.get("finish_reason")
            artifact.update(
                {
                    "elapsed_seconds": elapsed,
                    "http_status": 200,
                    "finish_reason": finish_reason,
                    "usage_metadata": detailed.get("usage_metadata") or {},
                    "raw_response_chars": detailed.get("raw_response_chars"),
                    "raw_response_head": detailed.get("raw_response_head"),
                    "raw_response_tail": detailed.get("raw_response_tail"),
                    "judgment_parsed": True,
                    # Recorded for gate-wiring inspection only — do not tune on this.
                    "proposed_disposition": judgment.proposed_disposition.value,
                    "citation_count": len(judgment.cited_evidence_refs),
                }
            )
    except ProviderOutputTruncatedError as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        msg = str(exc)
        if "finishReason=" in msg:
            finish_reason = msg.rsplit("finishReason=", 1)[-1].strip()
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 200,
                "finish_reason": finish_reason or "MAX_TOKENS",
                "judgment_parsed": False,
                "failure_class": "output_truncated",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )
    except ProviderRefusalError as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 200,
                "finish_reason": "REFUSAL",
                "judgment_parsed": False,
                "failure_class": "refusal",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )
    except ProviderMalformedResponseError as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        msg = str(exc)
        if "finishReason=" in msg:
            finish_reason = msg.rsplit("finishReason=", 1)[-1].rstrip(")")
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 200,
                "finish_reason": finish_reason,
                "judgment_parsed": False,
                "failure_class": "malformed_json",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )
    except ProviderUnavailableError as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 0,
                "finish_reason": None,
                "judgment_parsed": False,
                "failure_class": "unavailable",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )
    except ProviderError as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 0,
                "finish_reason": None,
                "judgment_parsed": False,
                "failure_class": "provider_error",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )
    except (RuntimeError, ValueError) as exc:
        elapsed = (datetime.now(tz=UTC) - t0).total_seconds()
        artifact.update(
            {
                "elapsed_seconds": elapsed,
                "http_status": 0,
                "finish_reason": None,
                "judgment_parsed": False,
                "failure_class": "intake_error",
                "parse_error": f"{type(exc).__name__}: {exc}",
            }
        )

    resolved = 0
    citations_valid = False
    cited_event_ids: list[int] = []
    if judgment is not None:
        cite_result = validate_evidence_citations(judgment, bundle)
        citations_valid = bool(cite_result.valid)
        resolved = len(cite_result.resolved)
        facts_by_id = {fact.evidence_id: fact for fact in bundle.facts}
        cited_event_ids = list(cited_event_ids_from_judgment(judgment, facts_by_id))
        artifact["citations_valid"] = citations_valid
        artifact["citations_resolved"] = resolved
        artifact["cited_event_ids"] = cited_event_ids
        artifact["citation_errors"] = list(cite_result.errors)[:20]
        artifact.setdefault("fault_flags", [])
    else:
        artifact["citations_valid"] = False
        artifact["citations_resolved"] = 0
        artifact["cited_event_ids"] = []
        artifact.setdefault("fault_flags", [])

    usage = artifact.get("usage_metadata") or {}
    total_tokens = usage.get("totalTokenCount")
    calls_full = 26 * 2 * 3
    if isinstance(total_tokens, int) and total_tokens > 0:
        artifact["projected_full_run_token_upper_bound"] = total_tokens * calls_full
        artifact["projected_full_run_calls"] = calls_full

    ok = (
        judgment is not None
        and citations_valid
        and resolved >= args.min_resolving_citations
        and len(cited_event_ids) > 0
        and artifact.get("failure_class") is None
    )
    artifact["smoke_pass"] = ok
    reasons: list[str] = []
    if artifact.get("failure_class"):
        reasons.append(str(artifact["failure_class"]))
    if judgment is None:
        reasons.append("judgment_not_parsed")
    if judgment is not None and not citations_valid:
        reasons.append("citations_invalid")
    if judgment is not None and resolved < args.min_resolving_citations:
        reasons.append(
            f"resolving_citations_below_{args.min_resolving_citations}"
        )
    if judgment is not None and len(cited_event_ids) == 0:
        reasons.append("cited_event_ids_empty")
    if finish_reason and not ok:
        reasons.append(f"finish_reason={finish_reason}")
    artifact["failure_reasons"] = reasons
    artifact["finish_reason"] = finish_reason or artifact.get("finish_reason")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8"
    )
    # Print a slim summary — omit disposition from console to reduce temptation.
    summary = {
        k: artifact.get(k)
        for k in (
            "probe",
            "scored",
            "smoke_pass",
            "anchor_id",
            "path",
            "bundle_fact_count",
            "provenance_paths",
            "judgment_parsed",
            "finish_reason",
            "citations_resolved",
            "cited_event_ids",
            "fault_flags",
            "temperature",
            "model",
            "elapsed_seconds",
            "failure_reasons",
        )
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"wrote probe artifact (unscored) -> {args.out}")
    print(f"finishReason={artifact.get('finish_reason')!r} smoke_pass={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
