"""Regression coverage for config.live never-contain matcher skip visibility."""

from __future__ import annotations

import logging

import pytest

from praetor.config.live import directive_matches_entry, target_in_never_contain_list
from praetor.contracts.containment import ContainmentDirective, TargetType


def _directive() -> ContainmentDirective:
    return ContainmentDirective.model_construct(
        target_type=TargetType.HOST,
        target_id="host-1",
    )


def test_target_in_never_contain_list_skips_malformed_entry_and_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    malformed = {"target_type": "host"}  # missing target_id: fails canonicalization
    valid = {"target_type": "host", "target_id": "host-1"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = target_in_never_contain_list("host", "host-1", [malformed, valid])

    assert result is True
    assert any(
        "malformed never-contain entry" in record.message for record in caplog.records
    )


def test_target_in_never_contain_list_no_log_when_all_entries_valid(
    caplog: pytest.LogCaptureFixture,
) -> None:
    valid = {"target_type": "host", "target_id": "host-1"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = target_in_never_contain_list("host", "host-2", [valid])

    assert result is False
    assert caplog.records == []


def test_directive_matches_entry_returns_false_and_logs_on_malformed_entry(
    caplog: pytest.LogCaptureFixture,
) -> None:
    malformed = {"target_type": "host"}

    with caplog.at_level(logging.WARNING, logger="praetor.config.live"):
        result = directive_matches_entry(_directive(), malformed)

    assert result is False
    assert any(
        "malformed never-contain entry" in record.message for record in caplog.records
    )
