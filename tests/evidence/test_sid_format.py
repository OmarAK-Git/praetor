"""V2-022: SID format vectors and v1 waiver pinning."""

from __future__ import annotations

import pytest
from tests.evidence.test_account_corroboration import _identity

from praetor.policy.identity import is_sid_backed, is_valid_sid_format

VALID_SID_VECTORS = (
    "S-1-5-21-1234567890-123456789-123456789-1001",
    "S-1-5-18",
    "s-1-5-21-1-2-3-4",
)

INVALID_SID_VECTORS = (
    "",
    "   ",
    "not-a-sid",
    "S-1-5",
    "S-1-5-",
    "DOMAIN\\jdoe",
    "S-1-5-21-not-numeric",
)


@pytest.mark.parametrize("sid", VALID_SID_VECTORS)
def test_is_valid_sid_format_accepts_windows_form(sid: str) -> None:
    assert is_valid_sid_format(sid) is True


@pytest.mark.parametrize("sid", INVALID_SID_VECTORS)
def test_is_valid_sid_format_rejects_non_windows_form(sid: str) -> None:
    assert is_valid_sid_format(sid) is False


@pytest.mark.parametrize("sid", VALID_SID_VECTORS)
def test_v1_waiver_is_sid_backed_accepts_valid_and_invalid_nonempty(sid: str) -> None:
    assert is_sid_backed(_identity(sid=sid)) is True


def test_v1_waiver_is_sid_backed_accepts_malformed_nonempty_sid() -> None:
    """DEC-062: eligibility uses presence-only until V2-024 tightens gates."""
    identity = _identity(sid="not-a-sid")

    assert is_valid_sid_format(identity.sid) is False
    assert is_sid_backed(identity) is True


@pytest.mark.parametrize("sid", ("", "   "))
def test_v1_waiver_is_sid_backed_rejects_empty_or_whitespace(sid: str) -> None:
    assert is_sid_backed(_identity(sid=sid)) is False
