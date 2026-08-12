"""Scoring for the capability spike.

Scores ``ModelJudgment.proposed_disposition`` only. PolicyGate output is
recorded elsewhere but never folded into the capability number: the gate
controls authority, not judgment quality.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from evals.capability.corpus import (
    BENIGN,
    MALICIOUS,
    UNRESOLVED,
    AnchorManifest,
)
from evals.capability.runner import PATH_A, PATH_B, Observation

_MALICIOUS_CORRECT = frozenset({"escalate", "auto_contain"})
_BENIGN_CORRECT = frozenset({"standard_review"})

# Pre-registered before any live tie is seen — do not revise post-hoc.
AB_TIE_SEPARATION_EPSILON = 0.05
PATH_A_VISIBLE_EVENT_IDS = frozenset({1, 4624})
PATH_A_CITATION_CONCENTRATION_THRESHOLD = 0.80

TieInterpretation = Literal[
    "not_a_tie",
    "prompt_constrained",
    "coverage_not_bottleneck",
    "citations_unavailable",
]


@dataclass(frozen=True)
class PathScore:
    path: str
    scored: int
    correct: int
    excluded_empty_bundle: int
    excluded_unresolved: int
    citation_resolution_rate: float | None
    unstable_anchors: tuple[str, ...]

    @property
    def separation_rate(self) -> float | None:
        if self.scored == 0:
            return None
        return self.correct / self.scored


@dataclass(frozen=True)
class LabelQuality:
    n_unresolved: int
    n_malicious: int
    n_benign: int
    emulation_steps_total: int | None
    unchained_steps: int | None
    unchained_step_share: float | None


@dataclass(frozen=True)
class CitationMixRead:
    path_b_path_a_concentration: float | None
    tie_interpretation: TieInterpretation
    separation_a: float | None
    separation_b: float | None


def _is_correct(expected_class: str, proposed: str) -> bool:
    if expected_class == MALICIOUS:
        return proposed in _MALICIOUS_CORRECT
    if expected_class == BENIGN:
        return proposed in _BENIGN_CORRECT
    return False


def score_path(observations: Sequence[Observation], *, path: str) -> PathScore:
    """Score one path's observations against their labels."""
    subset = [obs for obs in observations if obs.path == path]
    unresolved = [obs for obs in subset if obs.expected_class == UNRESOLVED]
    candidates = [obs for obs in subset if obs.expected_class != UNRESOLVED]
    scorable = [obs for obs in candidates if obs.proposed_disposition is not None]
    excluded_empty = len(candidates) - len(scorable)

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
        excluded_empty_bundle=excluded_empty,
        excluded_unresolved=len(unresolved),
        citation_resolution_rate=resolution_rate,
        unstable_anchors=unstable,
    )


def _majority_correct(observations: Sequence[Observation]) -> str:
    """Return 'right', 'wrong', or 'excluded' for one anchor on one path."""
    if any(obs.expected_class == UNRESOLVED for obs in observations):
        return "excluded"
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
    fix prompt, config, or model. ``unresolved`` anchors are omitted.
    """
    grouped: dict[str, dict[str, list[Observation]]] = defaultdict(
        lambda: {PATH_A: [], PATH_B: []}
    )
    for obs in observations:
        if obs.expected_class == UNRESOLVED:
            continue
        if obs.path in (PATH_A, PATH_B):
            grouped[obs.anchor_id][obs.path].append(obs)

    return {
        anchor_id: (
            _majority_correct(paths[PATH_A]),
            _majority_correct(paths[PATH_B]),
        )
        for anchor_id, paths in sorted(grouped.items())
    }


def path_b_path_a_citation_concentration(
    observations: Sequence[Observation],
) -> float | None:
    """Share of Path B resolved cited EventIDs that are Path-A-visible ({1, 4624})."""
    cited: list[int] = []
    for obs in observations:
        if obs.path != PATH_B:
            continue
        if not obs.citations_resolved:
            continue
        cited.extend(obs.cited_event_ids)
    if not cited:
        return None
    path_a_hits = sum(1 for event_id in cited if event_id in PATH_A_VISIBLE_EVENT_IDS)
    return path_a_hits / len(cited)


def interpret_ab_tie(
    score_a: PathScore,
    score_b: PathScore,
    *,
    concentration: float | None,
) -> TieInterpretation:
    """Pre-registered A≈B disambiguation via Path B citation mix."""
    rate_a = score_a.separation_rate
    rate_b = score_b.separation_rate
    if rate_a is None or rate_b is None:
        return "not_a_tie"
    if score_a.scored == 0 or score_b.scored == 0:
        return "not_a_tie"
    if abs(rate_a - rate_b) > AB_TIE_SEPARATION_EPSILON:
        return "not_a_tie"
    if concentration is None:
        return "citations_unavailable"
    if concentration > PATH_A_CITATION_CONCENTRATION_THRESHOLD:
        return "prompt_constrained"
    return "coverage_not_bottleneck"


def citation_mix_read(observations: Sequence[Observation]) -> CitationMixRead:
    score_a = score_path(observations, path=PATH_A)
    score_b = score_path(observations, path=PATH_B)
    concentration = path_b_path_a_citation_concentration(observations)
    return CitationMixRead(
        path_b_path_a_concentration=concentration,
        tie_interpretation=interpret_ab_tie(
            score_a, score_b, concentration=concentration
        ),
        separation_a=score_a.separation_rate,
        separation_b=score_b.separation_rate,
    )


def label_quality(manifest: AnchorManifest) -> LabelQuality:
    return LabelQuality(
        n_unresolved=len(manifest.unresolved),
        n_malicious=len(manifest.malicious),
        n_benign=len(manifest.benign),
        emulation_steps_total=manifest.emulation_steps_total,
        unchained_steps=manifest.unchained_steps,
        unchained_step_share=manifest.unchained_step_share,
    )


# Warn when a one-feature majority stump exceeds this accuracy.
# Perfect (disjoint) separation is still reported separately as a hard flag.
CONFOUND_GRADED_WARN_THRESHOLD = 0.90


@dataclass(frozen=True)
class ConfoundReport:
    """Guard #2: trivial feature separation on scored anchors.

    ``perfect_separation[name]`` is True when malicious and benign value sets
    are non-empty and disjoint (a trivial exact heuristic exists).

    ``graded_separation[name]`` is the accuracy of a majority-label-per-value
    stump on that feature — catches near-perfect separators (e.g. 95%) that
    the boolean miss.
    """

    perfect_separation: dict[str, bool]
    graded_separation: dict[str, float]

    @property
    def warned_features(self) -> tuple[str, ...]:
        warned = {
            name
            for name, perfect in self.perfect_separation.items()
            if perfect
        }
        warned.update(
            name
            for name, score in self.graded_separation.items()
            if score >= CONFOUND_GRADED_WARN_THRESHOLD
        )
        return tuple(sorted(warned))


def confound_check(
    anchor_features: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> dict[str, bool]:
    """Flag features that perfectly separate malicious from benign anchors.

    A True value means the corpus is contaminated: a trivial heuristic could
    score well without judging anything. ``unresolved`` anchors are ignored.

    Prefer :func:`confound_report` when graded near-separation also matters.
    """
    return confound_report(anchor_features).perfect_separation


def confound_graded_separation(
    anchor_features: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> dict[str, float]:
    """Majority-label-per-value stump accuracy per feature on scored anchors."""
    return confound_report(anchor_features).graded_separation


def confound_report(
    anchor_features: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> ConfoundReport:
    """Boolean perfect separation plus graded stump accuracy per feature."""
    by_feature_values: dict[str, dict[str, set[Any]]] = defaultdict(
        lambda: {MALICIOUS: set(), BENIGN: set()}
    )
    by_feature_rows: dict[str, list[tuple[Any, str]]] = defaultdict(list)

    for expected_class, features in anchor_features.values():
        if expected_class not in (MALICIOUS, BENIGN):
            continue
        for name, value in features.items():
            by_feature_values[name][expected_class].add(value)
            by_feature_rows[name].append((value, expected_class))

    perfect: dict[str, bool] = {}
    graded: dict[str, float] = {}
    for name, classes in by_feature_values.items():
        malicious_values = classes[MALICIOUS]
        benign_values = classes[BENIGN]
        both_present = bool(malicious_values) and bool(benign_values)
        perfect[name] = both_present and not (malicious_values & benign_values)

        rows = by_feature_rows[name]
        if not rows:
            graded[name] = 0.0
            continue
        value_counts: dict[Any, dict[str, int]] = defaultdict(
            lambda: {MALICIOUS: 0, BENIGN: 0}
        )
        for value, expected_class in rows:
            value_counts[value][expected_class] += 1
        correct = 0
        for value, expected_class in rows:
            counts = value_counts[value]
            predicted = (
                MALICIOUS if counts[MALICIOUS] >= counts[BENIGN] else BENIGN
            )
            if predicted == expected_class:
                correct += 1
        graded[name] = correct / len(rows)

    return ConfoundReport(perfect_separation=perfect, graded_separation=graded)
