"""Authenticated write surface primitives (Task 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Role = Literal["soc_lead", "analyst"]


@dataclass(frozen=True, slots=True)
class Principal:
    """Verified caller identity from operator-supplied token verification."""

    identity: str
    role: Role


class AuthError(Exception):
    """Base class for authentication and authorization failures."""


class MissingTokenError(AuthError):
    """Raised when a required bearer token is absent or blank."""


class InvalidTokenError(AuthError):
    """Raised when token verification fails."""


class InsufficientRoleError(AuthError):
    """Raised when the verified principal lacks the required surface role."""

    def __init__(self, *, required_role: Role, actual_role: Role) -> None:
        self.required_role = required_role
        self.actual_role = actual_role
        super().__init__(
            f"role {actual_role!r} insufficient for surface requiring {required_role!r}"
        )


class SelfAssertedIdentityError(AuthError):
    """Raised when caller identity differs from the verified principal."""

    def __init__(
        self,
        *,
        verified_identity: str,
        caller_supplied_identity: str,
    ) -> None:
        self.verified_identity = verified_identity
        self.caller_supplied_identity = caller_supplied_identity
        super().__init__(
            "record identity must come from the verified principal, "
            "not a caller-supplied value"
        )
