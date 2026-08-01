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
from pathlib import Path
from typing import Any

from evals.capability.corpus import load_anchor_manifest
from evals.capability.runner import (
    PATH_A,
    PATH_B,
    Observation,
    open_spike_store,
    run_anchor,
)
from evals.capability.score import ab_delta, score_path
from praetor.judgment.provider import JudgmentProvider
from praetor.judgment.vertex_provider import DEFAULT_GEMINI_MODEL, VertexProvider

SPIKE_ENV_FLAG = "PRAETOR_CAPABILITY_SPIKE"
GEMINI_API_KEY_ENV = "PRAETOR_GEMINI_API_KEY"
GOOGLE_API_KEY_ENV = "GOOGLE_API_KEY"
GEMINI_MODEL_ENV = "PRAETOR_GEMINI_MODEL"


def spike_enabled() -> bool:
    return os.environ.get(SPIKE_ENV_FLAG, "").strip().lower() in {"1", "true", "yes"}


def _resolve_api_key() -> str | None:
    for env_name in (GEMINI_API_KEY_ENV, GOOGLE_API_KEY_ENV):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return None


def resolve_spike_provider() -> JudgmentProvider | None:
    """Return a live provider only when explicitly enabled and configured."""
    if not spike_enabled():
        return None
    api_key = _resolve_api_key()
    if api_key is None:
        return None
    model_name = os.environ.get(GEMINI_MODEL_ENV, DEFAULT_GEMINI_MODEL).strip()
    return VertexProvider(
        api_key=api_key, model_name=model_name or DEFAULT_GEMINI_MODEL
    )


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


def _summarize(observations: Sequence[Observation]) -> str:
    lines: list[str] = ["", "=== capability spike summary ==="]
    for path in (PATH_A, PATH_B):
        score = score_path(observations, path=path)
        rate = score.separation_rate
        rate_text = "n/a" if rate is None else f"{rate:.2%}"
        resolution = score.citation_resolution_rate
        resolution_text = "n/a" if resolution is None else f"{resolution:.2%}"
        lines.append(
            f"path={path} scored={score.scored} correct={score.correct} "
            f"separation={rate_text} citations_resolved={resolution_text} "
            f"excluded_no_judgment={score.excluded_empty_bundle} "
            f"unstable={len(score.unstable_anchors)}"
        )

    lines.append("")
    lines.append("--- A/B delta (path_a, path_b) ---")
    buckets: dict[tuple[str, str], list[str]] = {}
    for anchor_id, pair in ab_delta(observations).items():
        buckets.setdefault(pair, []).append(anchor_id)
    for pair, anchors in sorted(buckets.items()):
        lines.append(f"{pair[0]:>8} / {pair[1]:<8} n={len(anchors):<3} {', '.join(anchors)}")

    lines.append("")
    lines.append(
        "Read ('wrong','right') as coverage-limited; ('wrong','wrong') as "
        "judgment-limited. Gate columns in the JSONL are recorded, not scored."
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    provider = resolve_spike_provider()
    if provider is None:
        if not spike_enabled():
            print(f"capability spike skipped: {SPIKE_ENV_FLAG} not enabled")
        else:
            print(
                "capability spike skipped: no API key in "
                f"{GEMINI_API_KEY_ENV} or {GOOGLE_API_KEY_ENV}"
            )
        return 0

    parser = argparse.ArgumentParser(description="Praetor judgment capability spike")
    parser.add_argument("--manifest", type=Path, help="labeled anchor manifest YAML")
    parser.add_argument("--capture", type=Path, help="JSON-lines telemetry capture")
    parser.add_argument("--out", type=Path, help="JSONL output path")
    parser.add_argument("--runs", type=int, default=3, help="runs per anchor per path")
    args = parser.parse_args(argv)

    if args.manifest is None or args.capture is None:
        print("capability spike skipped: --manifest and --capture are required")
        return 0

    manifest = load_anchor_manifest(args.manifest)
    events = load_capture_events(args.capture)
    print(
        f"capture={manifest.capture_id} anchors={len(manifest.anchors)} "
        f"events={len(events)} runs={args.runs}"
    )

    observations: list[Observation] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        store = open_spike_store(Path(tmpdir) / "spike.db")
        try:
            for anchor in manifest.anchors:
                observations.extend(
                    run_anchor(
                        store,
                        anchor=anchor,
                        events=events,
                        provider=provider,
                        runs=args.runs,
                    )
                )
                print(f"  ran anchor={anchor.anchor_id}")
        finally:
            store.conn.close()

    if args.out is not None:
        with args.out.open("w", encoding="utf-8") as handle:
            for obs in observations:
                handle.write(json.dumps(asdict(obs), sort_keys=True) + "\n")
        print(f"wrote {len(observations)} observations to {args.out}")

    print(_summarize(observations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
