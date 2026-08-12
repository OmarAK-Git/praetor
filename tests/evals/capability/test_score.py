from __future__ import annotations

from evals.capability.runner import PATH_A, PATH_B, Observation
from evals.capability.score import (
    CONFOUND_GRADED_WARN_THRESHOLD,
    PATH_A_CITATION_CONCENTRATION_THRESHOLD,
    ab_delta,
    citation_mix_read,
    confound_check,
    confound_report,
    interpret_ab_tie,
    path_b_path_a_citation_concentration,
    score_path,
)


def _obs(
    anchor_id: str,
    expected_class: str,
    path: str,
    proposed: str | None,
    *,
    run_index: int = 0,
    citations_resolved: bool = True,
    facts: int = 3,
    cited_event_ids: tuple[int, ...] = (),
) -> Observation:
    return Observation(
        anchor_id=anchor_id,
        expected_class=expected_class,
        path=path,
        run_index=run_index,
        proposed_disposition=proposed,
        final_disposition="escalate",
        fault_flags=(),
        citation_count=2,
        bundle_fact_count=facts,
        citations_resolved=citations_resolved,
        cited_event_ids=cited_event_ids,
    )


def test_malicious_correct_on_escalate_or_auto_contain() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate"),
        _obs("m2", "malicious", PATH_B, "auto_contain"),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 2
    assert score.correct == 2


def test_malicious_incorrect_on_standard_review() -> None:
    observations = [_obs("m1", "malicious", PATH_B, "standard_review")]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 1
    assert score.correct == 0


def test_benign_correct_only_on_standard_review() -> None:
    observations = [
        _obs("b1", "benign", PATH_B, "standard_review"),
        _obs("b2", "benign", PATH_B, "escalate"),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 2
    assert score.correct == 1


def test_missing_judgment_excluded_not_counted_wrong() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, None),
        _obs("m2", "malicious", PATH_A, "escalate"),
    ]
    score = score_path(observations, path=PATH_A)
    assert score.scored == 1
    assert score.correct == 1
    assert score.excluded_empty_bundle == 1


def test_other_paths_are_ignored() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, "standard_review"),
        _obs("m1", "malicious", PATH_B, "escalate"),
    ]
    assert score_path(observations, path=PATH_B).correct == 1
    assert score_path(observations, path=PATH_A).correct == 0


def test_unstable_anchor_detected_across_runs() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate", run_index=0),
        _obs("m1", "malicious", PATH_B, "standard_review", run_index=1),
        _obs("m2", "malicious", PATH_B, "escalate", run_index=0),
        _obs("m2", "malicious", PATH_B, "escalate", run_index=1),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.unstable_anchors == ("m1",)


def test_citation_resolution_rate() -> None:
    observations = [
        _obs("m1", "malicious", PATH_B, "escalate", citations_resolved=True),
        _obs("m2", "malicious", PATH_B, "escalate", citations_resolved=False),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.citation_resolution_rate == 0.5


def test_ab_delta_classifies_each_anchor() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, "standard_review"),
        _obs("m1", "malicious", PATH_B, "escalate"),
        _obs("m2", "malicious", PATH_A, "escalate"),
        _obs("m2", "malicious", PATH_B, "escalate"),
        _obs("m3", "malicious", PATH_A, "standard_review"),
        _obs("m3", "malicious", PATH_B, "standard_review"),
        _obs("m4", "malicious", PATH_A, "escalate"),
        _obs("m4", "malicious", PATH_B, "standard_review"),
    ]
    delta = ab_delta(observations)
    assert delta["m1"] == ("wrong", "right")
    assert delta["m2"] == ("right", "right")
    assert delta["m3"] == ("wrong", "wrong")
    assert delta["m4"] == ("right", "wrong")


def test_confound_check_flags_perfectly_separating_host() -> None:
    anchor_events = {
        "m1": ("malicious", {"host_id": "attacker-box", "event_count": 5}),
        "m2": ("malicious", {"host_id": "attacker-box", "event_count": 6}),
        "b1": ("benign", {"host_id": "clean-box", "event_count": 5}),
        "b2": ("benign", {"host_id": "clean-box", "event_count": 6}),
    }
    flags = confound_check(anchor_events)
    assert flags["host_id"] is True
    assert flags["event_count"] is False


def test_confound_check_passes_on_shared_hosts() -> None:
    anchor_events = {
        "m1": ("malicious", {"host_id": "ws-01"}),
        "b1": ("benign", {"host_id": "ws-01"}),
    }
    assert confound_check(anchor_events)["host_id"] is False


def test_confound_graded_flags_near_perfect_separator() -> None:
    """Boolean misses shared values; graded stump catches 95%-style splits."""
    anchors: dict[str, tuple[str, dict[str, object]]] = {}
    for i in range(19):
        anchors[f"m{i}"] = ("malicious", {"host_id": "attacker-box"})
    anchors["m_shared"] = ("malicious", {"host_id": "shared"})
    for i in range(19):
        anchors[f"b{i}"] = ("benign", {"host_id": "clean-box"})
    anchors["b_shared"] = ("benign", {"host_id": "shared"})

    report = confound_report(anchors)
    assert report.perfect_separation["host_id"] is False
    assert report.graded_separation["host_id"] >= CONFOUND_GRADED_WARN_THRESHOLD
    assert "host_id" in report.warned_features


def test_confound_seed_event_id_flags_class_correlated_seed_kind() -> None:
    """Replica of the ATLAS 4624-vs-4663/4688 seed-kind confound."""
    anchors = {
        f"m{i}": ("malicious", {"seed_event_id": 4663 if i % 2 else 4688})
        for i in range(5)
    }
    anchors.update(
        {f"b{i}": ("benign", {"seed_event_id": 4624}) for i in range(5)}
    )
    report = confound_report(anchors)
    assert report.perfect_separation["seed_event_id"] is True
    assert "seed_event_id" in report.warned_features


def test_confound_seed_subject_sid_flags_class_correlated_sid() -> None:
    """Replica of SYSTEM-vs-user 4688 SID confound after EventID neutrality."""
    user = "S-1-5-21-450080267-1945256726-3465656282-1000"
    system = "S-1-5-18"
    anchors = {
        f"m{i}": ("malicious", {"seed_subject_sid": user}) for i in range(5)
    }
    anchors.update(
        {f"b{i}": ("benign", {"seed_subject_sid": system}) for i in range(5)}
    )
    report = confound_report(anchors)
    assert report.perfect_separation["seed_subject_sid"] is True
    assert "seed_subject_sid" in report.warned_features


def test_confound_graded_low_on_balanced_overlap() -> None:
    anchors = {
        "m1": ("malicious", {"host_id": "ws-01"}),
        "m2": ("malicious", {"host_id": "ws-02"}),
        "b1": ("benign", {"host_id": "ws-01"}),
        "b2": ("benign", {"host_id": "ws-02"}),
    }
    report = confound_report(anchors)
    assert report.perfect_separation["host_id"] is False
    assert report.graded_separation["host_id"] == 0.5
    assert report.warned_features == ()


def test_unresolved_excluded_from_score_and_delta() -> None:
    observations = [
        _obs("m1", "malicious", PATH_A, "escalate"),
        _obs("m1", "malicious", PATH_B, "escalate"),
        _obs("u1", "unresolved", PATH_A, "escalate"),
        _obs("u1", "unresolved", PATH_B, "escalate"),
    ]
    score = score_path(observations, path=PATH_B)
    assert score.scored == 1
    assert score.excluded_unresolved == 1
    assert "u1" not in ab_delta(observations)


def test_path_b_citation_concentration_and_tie_reads() -> None:
    # Tie at 100% separation; Path B cites only 1/4624 → prompt_constrained.
    concentrated = [
        _obs("m1", "malicious", PATH_A, "escalate", cited_event_ids=(1,)),
        _obs(
            "m1",
            "malicious",
            PATH_B,
            "escalate",
            cited_event_ids=(1, 4624, 1, 4624, 1),
        ),
        _obs("b1", "benign", PATH_A, "standard_review", cited_event_ids=(4624,)),
        _obs(
            "b1",
            "benign",
            PATH_B,
            "standard_review",
            cited_event_ids=(1, 4624, 1, 4624, 1),
        ),
    ]
    conc = path_b_path_a_citation_concentration(concentrated)
    assert conc is not None
    assert conc > PATH_A_CITATION_CONCENTRATION_THRESHOLD
    read = citation_mix_read(concentrated)
    assert read.tie_interpretation == "prompt_constrained"

    # Same tie, but majority non-1/4624 cites → coverage_not_bottleneck.
    diverse = [
        _obs("m1", "malicious", PATH_A, "escalate"),
        _obs(
            "m1",
            "malicious",
            PATH_B,
            "escalate",
            cited_event_ids=(3, 11, 13, 10, 1),
        ),
        _obs("b1", "benign", PATH_A, "standard_review"),
        _obs(
            "b1",
            "benign",
            PATH_B,
            "standard_review",
            cited_event_ids=(3, 11, 13, 10, 7),
        ),
    ]
    assert citation_mix_read(diverse).tie_interpretation == "coverage_not_bottleneck"

    # Not a tie when rates diverge.
    divergent = [
        _obs("m1", "malicious", PATH_A, "standard_review"),
        _obs("m1", "malicious", PATH_B, "escalate", cited_event_ids=(3, 11)),
        _obs("b1", "benign", PATH_A, "standard_review"),
        _obs("b1", "benign", PATH_B, "standard_review", cited_event_ids=(3,)),
    ]
    assert citation_mix_read(divergent).tie_interpretation == "not_a_tie"

    score_a = score_path(concentrated, path=PATH_A)
    score_b = score_path(concentrated, path=PATH_B)
    assert (
        interpret_ab_tie(score_a, score_b, concentration=None) == "citations_unavailable"
    )
