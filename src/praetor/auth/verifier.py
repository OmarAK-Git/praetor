"""Token verification and external write surface authentication."""

from __future__ import annotations

from enum import StrEnum
from typing import NoReturn, Protocol

from praetor.auth.principal import (
    AuthError,
    InsufficientRoleError,
    InvalidTokenError,
    MissingTokenError,
    Principal,
    Role,
    SelfAssertedIdentityError,
)


class WriteSurface(StrEnum):
    """Externally callable authenticated write surfaces."""

    ORG_CONFIG_ACTIVATION = "org_config_activation"
    EMERGENCY_NEVER_CONTAIN = "emergency_never_contain"
    ANNOTATION_SUBMISSION = "annotation_submission"


class InternalOperation(StrEnum):
    """Internal-only operations; not authenticated external write surfaces."""

    LEDGER_APPEND = "ledger_append"
    DIRECTIVE_EMISSION = "directive_emission"
    FEED_EXPORT = "feed_export"


SURFACE_REQUIRED_ROLE: dict[WriteSurface, Role] = {
    WriteSurface.ORG_CONFIG_ACTIVATION: "soc_lead",
    WriteSurface.EMERGENCY_NEVER_CONTAIN: "soc_lead",
    WriteSurface.ANNOTATION_SUBMISSION: "analyst",
}

EXTERNAL_WRITE_SURFACES: frozenset[WriteSurface] = frozenset(WriteSurface)
INTERNAL_OPERATIONS: frozenset[InternalOperation] = frozenset(InternalOperation)


class InternalOnlyOperationError(AuthError):
    """External authentication attempted for an internal-only operation."""


class TokenVerifier(Protocol):
    """Operator-supplied token verification; issuance and IdP are out of scope."""

    def verify(self, token: str) -> Principal:
        """Return a verified principal or raise InvalidTokenError."""


class PrincipalMapVerifier:
    """Test and development verifier mapping opaque tokens to verified principals."""

    def __init__(self, principals_by_token: dict[str, Principal]) -> None:
        self._principals_by_token = dict(principals_by_token)

    def verify(self, token: str) -> Principal:
        try:
            return self._principals_by_token[token]
        except KeyError as exc:
            raise InvalidTokenError(f"unrecognized token: {token!r}") from exc


def guard_internal_only(operation: InternalOperation) -> NoReturn:
    """Enforce that internal operations have no external authentication entry point."""
    raise InternalOnlyOperationError(
        f"{operation.value} is internal-only and cannot be accessed "
        "via external authentication"
    )


def verified_record_identity(
    principal: Principal,
    *,
    caller_supplied_identity: str | None = None,
) -> str:
    """Return verified identity for audit fields; reject self-asserted overrides."""
    if (
        caller_supplied_identity is not None
        and caller_supplied_identity != principal.identity
    ):
        raise SelfAssertedIdentityError(
            verified_identity=principal.identity,
            caller_supplied_identity=caller_supplied_identity,
        )
    return principal.identity


def authenticate_write(
    *,
    token: str | None,
    surface: WriteSurface,
    verifier: TokenVerifier,
) -> Principal:
    """Authenticate and authorize a caller for an external write surface."""
    if token is None or not token.strip():
        raise MissingTokenError("bearer token required")

    try:
        principal = verifier.verify(token.strip())
    except AuthError:
        raise
    except Exception as exc:
        raise InvalidTokenError("token verification failed") from exc

    required_role = SURFACE_REQUIRED_ROLE[surface]
    if principal.role != required_role:
        raise InsufficientRoleError(
            required_role=required_role,
            actual_role=principal.role,
        )
    return principal


def authenticate_external_write(
    *,
    token: str | None,
    target: WriteSurface | InternalOperation,
    verifier: TokenVerifier,
) -> Principal:
    """Route external authentication; reject internal-only operations."""
    if isinstance(target, InternalOperation):
        guard_internal_only(target)
    return authenticate_write(token=token, surface=target, verifier=verifier)


def authenticate_org_config_activation(
    token: str | None,
    verifier: TokenVerifier,
) -> Principal:
    return authenticate_write(
        token=token,
        surface=WriteSurface.ORG_CONFIG_ACTIVATION,
        verifier=verifier,
    )


def authenticate_emergency_never_contain(
    token: str | None,
    verifier: TokenVerifier,
) -> Principal:
    return authenticate_write(
        token=token,
        surface=WriteSurface.EMERGENCY_NEVER_CONTAIN,
        verifier=verifier,
    )


def authenticate_annotation_submission(
    token: str | None,
    verifier: TokenVerifier,
) -> Principal:
    return authenticate_write(
        token=token,
        surface=WriteSurface.ANNOTATION_SUBMISSION,
        verifier=verifier,
    )
