from __future__ import annotations

from evals.capability.runner import PATH_A, PATH_B, Observation
from evals.capability.score import ab_delta, confound_check, score_path


def _obs(
    anchor_id: str,
    expected_class: str,
    path: str,
    proposed: str | None,
    *,
    run_index: int = 0,
    citations_resolved: bool = True,
    facts: int = 3,
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
