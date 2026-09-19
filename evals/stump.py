"""path_a_fact_count stump (Sprint 1 honest record; not a quality win)."""

from __future__ import annotations

from typing import Literal

DispositionBucket = Literal["malicious", "benign"]

_MALICIOUS_PROPOSED = frozenset({"escalate", "auto_contain"})


def path_a_fact_count_stump(path_a_fact_count: int) -> DispositionBucket:
    return "malicious" if path_a_fact_count >= 2 else "benign"


def _bucket(proposed: str | None) -> DispositionBucket | None:
    if proposed is None:
        return None
    return "malicious" if proposed in _MALICIOUS_PROPOSED else "benign"


def stump_pair(
    *,
    bag_id: str,
    frozen_label: DispositionBucket,
    path_a_fact_count: int,
    model_proposed: str | None,
) -> dict[str, object]:
    stump_prediction = path_a_fact_count_stump(path_a_fact_count)
    model_bucket = _bucket(model_proposed)
    return {
        "bag_id": bag_id,
        "path_a_fact_count": path_a_fact_count,
        "frozen_label": frozen_label,
        "stump_prediction": stump_prediction,
        "stump_correct": stump_prediction == frozen_label,
        "model_bucket": model_bucket,
        "model_correct": (
            None if model_bucket is None else model_bucket == frozen_label
        ),
        "quality_win_claimed": False,
    }
