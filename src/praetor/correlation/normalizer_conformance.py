"""Normalizer conformance helpers for Windows telemetry (PE-0024)."""

from __future__ import annotations

WINDOWS_DOMAIN_SEPARATOR = "\\"


def malformed_domain_separator_ambiguity(account_repr: str) -> bool:
    """Return whether a non-empty account field lacks ``DOMAIN\\user`` separator.

    Sysmon and future Windows normalizers that emit a combined account string
    must set ``ambiguity_flag=true`` when this returns ``True`` (PE-0024).
    """
    if not account_repr:
        return False
    return WINDOWS_DOMAIN_SEPARATOR not in account_repr


def require_domain_separator_ambiguity_flag(
    *,
    account_repr: str,
    ambiguity_flag: bool,
) -> None:
    """Assert PE-0024: malformed domain-separator accounts set ambiguity_flag=true."""
    if malformed_domain_separator_ambiguity(account_repr) and not ambiguity_flag:
        msg = (
            f"account_repr {account_repr!r} lacks domain separator; "
            "ambiguity_flag must be true (PE-0024)"
        )
        raise AssertionError(msg)
