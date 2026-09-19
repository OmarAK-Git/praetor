"""Named theater detectors (spec §8)."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from evals.e2e_scenario import THEATER_DETECTOR_NAMES

_LEAK_NEEDLES = ("expected_class", "EventRecordID", "ground-truth", "ground_truth")
_UNEARNED_CLAIM = re.compile(
    r"judgment works|trustworthy judgment|production-ready judgment",
    re.IGNORECASE,
)
_PATH_B_MODULES = frozenset({"evals.capability.flatten", "evals.capability.bundle"})


@dataclass(frozen=True)
class TheaterContext:
    scenario_id: str
    realm: str
    arm: str
    alert_identity: str
    excerpt_blob: str
    scorecard_status: str | None
    scorecard_is_quality_pass: bool
    src_root: Path
    copy_roots: tuple[Path, ...]
    cite_to_subject_primary_earned: bool


@dataclass(frozen=True)
class TheaterFinding:
    detector: str
    tripped: bool
    message: str


def _clean(detector: str, message: str = "") -> TheaterFinding:
    return TheaterFinding(detector=detector, tripped=False, message=message)


def _trip(detector: str, message: str) -> TheaterFinding:
    return TheaterFinding(detector=detector, tripped=True, message=message)


def _label_leak(ctx: TheaterContext) -> TheaterFinding:
    blob = f"{ctx.alert_identity}\n{ctx.excerpt_blob}"
    for needle in _LEAK_NEEDLES:
        if needle in blob:
            return _trip("label_leak", f"{needle} visible in excerpts or alert_identity")
    return _clean("label_leak")


def _stipulated_capability(ctx: TheaterContext) -> TheaterFinding:
    if ctx.scorecard_is_quality_pass:
        return _trip(
            "stipulated_capability",
            "FakeProvider proposed_disposition scored as capability quality pass",
        )
    return _clean("stipulated_capability")


def _unearned_demo_claim(ctx: TheaterContext) -> TheaterFinding:
    if ctx.cite_to_subject_primary_earned:
        return _clean("unearned_demo_claim")
    for root in ctx.copy_roots:
        for path in root.rglob("*"):
            if path.suffix.lower() not in {".md", ".html", ".py", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            if _UNEARNED_CLAIM.search(text):
                return _trip(
                    "unearned_demo_claim",
                    f"{path} claims judgment while cite-to-subject primary is unearned",
                )
    return _clean("unearned_demo_claim")


def _path_b_in_src(ctx: TheaterContext) -> TheaterFinding:
    if not ctx.src_root.exists():
        return _clean("path_b_in_src")
    for path in ctx.src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in _PATH_B_MODULES:
                return _trip("path_b_in_src", f"{path} imports {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in _PATH_B_MODULES:
                        return _trip("path_b_in_src", f"{path} imports {alias.name}")
    return _clean("path_b_in_src")


def _post_hoc_protocol(ctx: TheaterContext) -> TheaterFinding:
    if "post_hoc_relabel" in ctx.excerpt_blob or "prompt_changed_after_score" in ctx.excerpt_blob:
        return _trip("post_hoc_protocol", "protocol mutation marker present")
    return _clean("post_hoc_protocol")


def _gate_scored_as_judgment(ctx: TheaterContext) -> TheaterFinding:
    if ctx.scorecard_is_quality_pass and "scored_layer=policy_gate" in ctx.excerpt_blob:
        return _trip(
            "gate_scored_as_judgment",
            "PolicyGate outcome used as the capability number",
        )
    return _clean("gate_scored_as_judgment")


DETECTORS: dict[str, Callable[[TheaterContext], TheaterFinding]] = {
    "label_leak": _label_leak,
    "stipulated_capability": _stipulated_capability,
    "unearned_demo_claim": _unearned_demo_claim,
    "path_b_in_src": _path_b_in_src,
    "post_hoc_protocol": _post_hoc_protocol,
    "gate_scored_as_judgment": _gate_scored_as_judgment,
}


def run_theater_detector(name: str, ctx: TheaterContext) -> TheaterFinding:
    if name not in THEATER_DETECTOR_NAMES or name not in DETECTORS:
        raise KeyError(f"unknown theater detector: {name!r}")
    return DETECTORS[name](ctx)
