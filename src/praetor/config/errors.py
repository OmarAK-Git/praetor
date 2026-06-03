"""Org config loader and preflight errors."""

from __future__ import annotations


class ConfigError(Exception):
    """Base error for org config operations."""


class PreflightError(ConfigError):
    """Preflight validation failed."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ActivationError(ConfigError):
    """Config activation failed."""

    def __init__(self, preflight: PreflightError) -> None:
        self.code = preflight.code
        super().__init__(str(preflight))


class ConfigLoadError(ConfigError):
    """YAML load failed."""


class SnapshotHashConflictError(ConfigError):
    """Same snapshot_hash with different binding body."""


class SnapshotTamperError(ConfigError):
    """Stored snapshot row fails hash verification."""


class InternalOnlyConfigOperationError(ConfigError):
    """Caller attempted an internal-only config operation."""
