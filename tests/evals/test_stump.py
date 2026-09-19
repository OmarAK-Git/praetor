from __future__ import annotations

from evals.stump import path_a_fact_count_stump, stump_pair


def test_stump_threshold() -> None:
    assert path_a_fact_count_stump(1) == "benign"
    assert path_a_fact_count_stump(2) == "malicious"


def test_stump_pair_is_mcnemar_ready() -> None:
    pair = stump_pair(
        bag_id="cap.stump_parity_guard",
        frozen_label="malicious",
        path_a_fact_count=2,
        model_proposed="standard_review",
    )
    assert pair["stump_prediction"] == "malicious"
    assert pair["stump_correct"] is True
    assert pair["model_bucket"] == "benign"
    assert pair["model_correct"] is False
    assert pair["quality_win_claimed"] is False
