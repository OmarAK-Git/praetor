"""Task 4 auth primitives — tests first per docs/plan.md."""

from __future__ import annotations

import pytest

from praetor.auth import (
    EXTERNAL_WRITE_SURFACES,
    INTERNAL_OPERATIONS,
    InsufficientRoleError,
    InternalOnlyOperationError,
    InternalOperation,
    MissingTokenError,
    Principal,
    PrincipalMapVerifier,
    SelfAssertedIdentityError,
    WriteSurface,
    authenticate_annotation_submission,
    authenticate_emergency_never_contain,
    authenticate_external_write,
    authenticate_org_config_activation,
    guard_internal_only,
    verified_record_identity,
)

SOC_LEAD = Principal(identity="lead@example.com", role="soc_lead")
ANALYST = Principal(identity="analyst@example.com", role="analyst")

SOC_LEAD_TOKEN = "token-soc-lead"
ANALYST_TOKEN = "token-analyst"


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {
            SOC_LEAD_TOKEN: SOC_LEAD,
            ANALYST_TOKEN: ANALYST,
        }
    )


class TestSocLeadSurfaces:
    @pytest.mark.parametrize(
        "authenticate",
        [
            authenticate_org_config_activation,
            authenticate_emergency_never_contain,
        ],
    )
    def test_soc_lead_token_accepted(
        self, verifier: PrincipalMapVerifier, authenticate
    ) -> None:
        principal = authenticate(SOC_LEAD_TOKEN, verifier)
        assert principal is SOC_LEAD
        assert principal.identity == "lead@example.com"
        assert principal.role == "soc_lead"

    @pytest.mark.parametrize(
        "authenticate",
        [
            authenticate_org_config_activation,
            authenticate_emergency_never_contain,
        ],
    )
    def test_analyst_token_rejected(
        self, verifier: PrincipalMapVerifier, authenticate
    ) -> None:
        with pytest.raises(InsufficientRoleError) as exc_info:
            authenticate(ANALYST_TOKEN, verifier)
        assert exc_info.value.required_role == "soc_lead"
        assert exc_info.value.actual_role == "analyst"


class TestAnalystSurface:
    def test_analyst_token_accepted(self, verifier: PrincipalMapVerifier) -> None:
        principal = authenticate_annotation_submission(ANALYST_TOKEN, verifier)
        assert principal is ANALYST
        assert principal.identity == "analyst@example.com"
        assert principal.role == "analyst"

    def test_soc_lead_token_rejected(self, verifier: PrincipalMapVerifier) -> None:
        with pytest.raises(InsufficientRoleError) as exc_info:
            authenticate_annotation_submission(SOC_LEAD_TOKEN, verifier)
        assert exc_info.value.required_role == "analyst"
        assert exc_info.value.actual_role == "soc_lead"


class TestMissingToken:
    @pytest.mark.parametrize(
        "authenticate",
        [
            authenticate_org_config_activation,
            authenticate_emergency_never_contain,
            authenticate_annotation_submission,
        ],
    )
    def test_missing_token_rejected(
        self, verifier: PrincipalMapVerifier, authenticate
    ) -> None:
        with pytest.raises(MissingTokenError):
            authenticate(None, verifier)

    @pytest.mark.parametrize(
        "authenticate",
        [
            authenticate_org_config_activation,
            authenticate_emergency_never_contain,
            authenticate_annotation_submission,
        ],
    )
    def test_blank_token_rejected(
        self, verifier: PrincipalMapVerifier, authenticate
    ) -> None:
        with pytest.raises(MissingTokenError):
            authenticate("   ", verifier)


class TestPrincipalIdentityForRecords:
    def test_verified_identity_available(self, verifier: PrincipalMapVerifier) -> None:
        principal = authenticate_annotation_submission(ANALYST_TOKEN, verifier)
        reviewer_identity = principal.identity
        assert reviewer_identity == "analyst@example.com"
        assert reviewer_identity != ANALYST_TOKEN

    def test_record_identity_uses_verified_principal_only(
        self, verifier: PrincipalMapVerifier
    ) -> None:
        principal = authenticate_annotation_submission(ANALYST_TOKEN, verifier)
        assert verified_record_identity(principal) == "analyst@example.com"

    def test_caller_supplied_identity_cannot_override_verified_principal(
        self, verifier: PrincipalMapVerifier
    ) -> None:
        principal = authenticate_annotation_submission(ANALYST_TOKEN, verifier)
        attacker_identity = "soc-lead@evil.com"
        with pytest.raises(SelfAssertedIdentityError) as exc_info:
            verified_record_identity(
                principal, caller_supplied_identity=attacker_identity
            )
        assert exc_info.value.verified_identity == "analyst@example.com"
        assert exc_info.value.caller_supplied_identity == attacker_identity

    @pytest.mark.parametrize(
        "authenticate",
        [
            authenticate_org_config_activation,
            authenticate_emergency_never_contain,
        ],
    )
    def test_emergency_and_activation_reject_self_asserted_added_by(
        self, verifier: PrincipalMapVerifier, authenticate
    ) -> None:
        principal = authenticate(SOC_LEAD_TOKEN, verifier)
        with pytest.raises(SelfAssertedIdentityError):
            verified_record_identity(
                principal, caller_supplied_identity="other@evil.com"
            )


class TestInternalOperationsNotExternal:
    def test_three_external_surfaces_only(self) -> None:
        assert len(EXTERNAL_WRITE_SURFACES) == 3
        assert WriteSurface.ORG_CONFIG_ACTIVATION in EXTERNAL_WRITE_SURFACES
        assert WriteSurface.EMERGENCY_NEVER_CONTAIN in EXTERNAL_WRITE_SURFACES
        assert WriteSurface.ANNOTATION_SUBMISSION in EXTERNAL_WRITE_SURFACES

    @pytest.mark.parametrize(
        "operation",
        [
            InternalOperation.LEDGER_APPEND,
            InternalOperation.DIRECTIVE_EMISSION,
            InternalOperation.FEED_EXPORT,
        ],
    )
    def test_internal_operations_not_external_surfaces(
        self, operation: InternalOperation
    ) -> None:
        assert operation not in EXTERNAL_WRITE_SURFACES
        assert operation in INTERNAL_OPERATIONS

    @pytest.mark.parametrize(
        "operation",
        [
            InternalOperation.LEDGER_APPEND,
            InternalOperation.DIRECTIVE_EMISSION,
            InternalOperation.FEED_EXPORT,
        ],
    )
    def test_guard_internal_only_rejects_external_access(
        self, operation: InternalOperation
    ) -> None:
        with pytest.raises(InternalOnlyOperationError):
            guard_internal_only(operation)

    @pytest.mark.parametrize(
        "operation",
        [
            InternalOperation.LEDGER_APPEND,
            InternalOperation.DIRECTIVE_EMISSION,
            InternalOperation.FEED_EXPORT,
        ],
    )
    def test_external_authentication_router_rejects_internal_operations(
        self, verifier: PrincipalMapVerifier, operation: InternalOperation
    ) -> None:
        with pytest.raises(InternalOnlyOperationError):
            authenticate_external_write(
                token=SOC_LEAD_TOKEN,
                target=operation,
                verifier=verifier,
            )

    def test_auth_module_does_not_expose_internal_callables(self) -> None:
        import praetor.auth as auth

        forbidden = {
            "append_ledger",
            "emit_directive",
            "export_feed",
            "ledger_append",
            "directive_emission",
            "feed_export",
        }
        assert forbidden.isdisjoint(set(auth.__all__))
