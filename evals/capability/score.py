"""Scoring for the capability spike.

Scores ``ModelJudgment.proposed_disposition`` only. PolicyGate output is
recorded elsewhere but never folded into the capability number: the gate
controls authority, not judgment quality.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from evals.capability.corpus import BENIGN, MALICIOUS
from evals.capability.runner import PATH_A, PATH_B, Observation

_MALICIOUS_CORRECT = frozenset({"escalate", "auto_contain"})
_BENIGN_CORRECT = frozenset({"standard_review"})


@dataclass(frozen=True)
class PathScore:
    path: str
    scored: int
    correct: int
    excluded_empty_bundle: int
    citation_resolution_rate: float | None
    unstable_anchors: tuple[str, ...]

    @property
    def separation_rate(self) -> float | None:
        if self.scored == 0:
            return None
        return self.correct / self.scored


def _is_correct(expected_class: str, proposed: str) -> bool:
    if expected_class == MALICIOUS:
        return proposed in _MALICIOUS_CORRECT
    if expected_class == BENIGN:
        return proposed in _BENIGN_CORRECT
    return False


def score_path(observations: Sequence[Observation], *, path: str) -> PathScore:
    """Score one path's observations against their labels."""
    subset = [obs for obs in observations if obs.path == path]
    scorable = [obs for obs in subset if obs.proposed_disposition is not None]
    excluded = len(subset) - len(scorable)

    correct = sum(
        1
        for obs in scorable
        if _is_correct(obs.expected_class, str(obs.proposed_disposition))
    )

    resolution_rate: float | None = None
    if scorable:
        resolution_rate = sum(
            1 for obs in scorable if obs.citations_resolved
        ) / len(scorable)

    by_anchor: dict[str, set[str]] = defaultdict(set)
    for obs in scorable:
        by_anchor[obs.anchor_id].add(str(obs.proposed_disposition))
    unstable = tuple(
        sorted(anchor for anchor, values in by_anchor.items() if len(values) > 1)
    )

    return PathScore(
        path=path,
        scored=len(scorable),
        correct=correct,
        excluded_empty_bundle=excluded,
        citation_resolution_rate=resolution_rate,
        unstable_anchors=unstable,
    )


def _majority_correct(observations: Sequence[Observation]) -> str:
    """Return 'right', 'wrong', or 'excluded' for one anchor on one path."""
    scorable = [obs for obs in observations if obs.proposed_disposition is not None]
    if not scorable:
        return "excluded"
    hits = sum(
        1
        for obs in scorable
        if _is_correct(obs.expected_class, str(obs.proposed_disposition))
    )
    return "right" if hits * 2 > len(scorable) else "wrong"


def ab_delta(observations: Sequence[Observation]) -> dict[str, tuple[str, str]]:
    """Map anchor_id to (path_a_outcome, path_b_outcome).

    ('wrong', 'right') means the model can judge but correlation starved it —
    fix coverage. ('wrong', 'wrong') means judgment failed with full evidence —
    fix prompt, config, or model.
    """
    grouped: dict[str, dict[str, list[Observation]]] = defaultdict(
        lambda: {PATH_A: [], PATH_B: []}
    )
    for obs in observations:
        if obs.path in (PATH_A, PATH_B):
            grouped[obs.anchor_id][obs.path].append(obs)

    return {
        anchor_id: (
            _majority_correct(paths[PATH_A]),
            _majority_correct(paths[PATH_B]),
        )
        for anchor_id, paths in sorted(grouped.items())
    }


def confound_check(
    anchor_features: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> dict[str, bool]:
    """Flag features that perfectly separate malicious from benign anchors.

    A True value means the corpus is contaminated: a trivial heuristic could
    score well without judging anything.
    """
    by_feature: dict[str, dict[str, set[Any]]] = defaultdict(
        lambda: {MALICIOUS: set(), BENIGN: set()}
    )
    for expected_class, features in anchor_features.values():
        if expected_class not in (MALICIOUS, BENIGN):
            continue
        for name, value in features.items():
            by_feature[name][expected_class].add(value)

    flags: dict[str, bool] = {}
    for name, classes in by_feature.items():
        malicious_values = classes[MALICIOUS]
        benign_values = classes[BENIGN]
        both_present = bool(malicious_values) and bool(benign_values)
        flags[name] = both_present and not (malicious_values & benign_values)
    return flags
