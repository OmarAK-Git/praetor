"""TASK-013 provider abstraction and FakeProvider failure modes."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.config.shared import EXAMPLE_CONFIG, SOC_LEAD_TOKEN
from tests.engine.helpers import (
    assert_edict_snapshot_pairing,
    assert_outcome_matrix_edict,
)

from praetor.auth.principal import Principal
from praetor.auth.verifier import PrincipalMapVerifier
from praetor.config.activation import activate_org_config
from praetor.contracts.disposition import Disposition
from praetor.engine.orchestrator import SucceedingStampBackend, process_alert_intake
from praetor.judgment.fake_provider import FakeProvider, FakeProviderMode
from praetor.judgment.provider import (
    JudgmentProvider,
    JudgmentRequest,
    ProviderMalformedResponseError,
    ProviderRefusalError,
    ProviderRetryPolicy,
    ProviderTimeoutError,
    ProviderUnavailableError,
    call_provider_with_retries,
)
from praetor.judgment.vertex_provider import VertexProvider
from praetor.state.store import StateStore, open_state_store


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {SOC_LEAD_TOKEN: Principal(identity="soc-lead-1", role="soc_lead")}
    )


@pytest.fixture
def store(tmp_path: Path) -> Iterator[StateStore]:
    db = tmp_path / "state.db"
    s = open_state_store(db)
    yield s
    s.close()


@pytest.fixture
def activated(store: StateStore, verifier: PrincipalMapVerifier) -> StateStore:
    activate_org_config(store, EXAMPLE_CONFIG, token=SOC_LEAD_TOKEN, verifier=verifier)
    return store


def test_fake_provider_valid_mode_returns_model_judgment() -> None:
    provider = FakeProvider(mode=FakeProviderMode.VALID)

    judgment = provider.generate_judgment(JudgmentRequest(scenario_id="valid"))

    assert judgment.proposed_disposition == Disposition.STANDARD_REVIEW
    assert judgment.provider_name == "fake"
    assert provider.calls == 1


def test_fake_provider_malformed_json_mode_raises_typed_failure() -> None:
    provider = FakeProvider(mode=FakeProviderMode.MALFORMED_JSON)

    with pytest.raises(ProviderMalformedResponseError):
        provider.generate_judgment(JudgmentRequest(scenario_id="malformed_json"))

    assert provider.calls == 1


def test_retry_helper_retries_timeouts_with_bounded_backoff() -> None:
    provider = FakeProvider(mode=FakeProviderMode.TIMEOUT)
    sleeps: list[float] = []

    with pytest.raises(ProviderTimeoutError):
        call_provider_with_retries(
            provider,
            JudgmentRequest(scenario_id="provider_timeout"),
            retry_policy=ProviderRetryPolicy(max_attempts=3, backoff_seconds=0.25),
            sleep=sleeps.append,
        )

    assert provider.calls == 3
    assert sleeps == [0.25, 0.25]


def test_fake_provider_probe_uses_canary_payload() -> None:
    provider = FakeProvider(mode=FakeProviderMode.VALID)

    result = provider.probe({"canary": "synthetic-provider-health-check"})

    assert result.success is True
    assert result.provider_name == "fake"
    assert result.metadata == {"canary_seen": True}


def test_vertex_provider_stub_implements_protocol() -> None:
    provider: JudgmentProvider = VertexProvider(model_name="gemini-test")

    assert isinstance(provider, JudgmentProvider)
    result = provider.probe({"canary": "synthetic"})
    assert result.success is False
    assert result.provider_name == "vertex"
    assert result.metadata["status"] == "stub"


def test_provider_timeout_escalates_after_bounded_retry(
    activated: StateStore,
) -> None:
    provider = FakeProvider(mode=FakeProviderMode.TIMEOUT)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-PROVIDER-TIMEOUT",
        provider_retry_policy=ProviderRetryPolicy(max_attempts=2, backoff_seconds=0.0),
    )

    assert result.edict is not None
    assert provider.calls == 2
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_timeout"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_fake_provider_modes_are_selected_by_scenario_id(
    activated: StateStore,
) -> None:
    provider = FakeProvider(
        mode=FakeProviderMode.VALID,
        scenario_modes={"ALERT-SCENARIO-TIMEOUT": FakeProviderMode.TIMEOUT},
    )

    valid = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-SCENARIO-VALID",
    )
    timeout = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-SCENARIO-TIMEOUT",
        provider_retry_policy=ProviderRetryPolicy(max_attempts=1),
    )

    assert valid.edict is not None
    assert valid.disposition == Disposition.STANDARD_REVIEW
    assert timeout.edict is not None
    assert_outcome_matrix_edict(
        timeout.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_timeout"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert provider.calls == 2


def test_provider_refusal_escalates(
    activated: StateStore,
) -> None:
    provider = FakeProvider(mode=FakeProviderMode.REFUSAL)

    with pytest.raises(ProviderRefusalError):
        provider.generate_judgment(JudgmentRequest(scenario_id="provider_refusal"))

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-PROVIDER-REFUSAL",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_refusal"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_provider_unavailable_escalates(
    activated: StateStore,
) -> None:
    provider = FakeProvider(mode=FakeProviderMode.UNAVAILABLE)

    with pytest.raises(ProviderUnavailableError):
        provider.generate_judgment(JudgmentRequest(scenario_id="provider_unavailable"))

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-PROVIDER-UNAVAILABLE",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_unavailable"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_provider_malformed_json_escalates(
    activated: StateStore,
) -> None:
    provider = FakeProvider(mode=FakeProviderMode.MALFORMED_JSON)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-PROVIDER-MALFORMED",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["provider_malformed_json"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_provider_fabricated_citation_flows_to_citation_validator(
    activated: StateStore,
) -> None:
    provider = FakeProvider(mode=FakeProviderMode.FABRICATED_CITATION)

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-PROVIDER-FABRICATED-CITATION",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["invalid_model_citation"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.STANDARD_REVIEW,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)


def test_auto_contain_fabricated_citation_escalates_before_policy_downgrade(
    activated: StateStore,
) -> None:
    provider = FakeProvider(
        mode=FakeProviderMode.FABRICATED_CITATION,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )

    result = process_alert_intake(
        activated,
        judgment_provider=provider,
        stamp_backend=SucceedingStampBackend(),
        alert_identity="ALERT-AUTO-CONTAIN-FABRICATED-CITATION",
    )

    assert result.edict is not None
    assert_outcome_matrix_edict(
        result.edict,
        final_disposition=Disposition.ESCALATE,
        fault_flags=["invalid_model_citation"],
        system_fault_escalation=True,
        proposed_disposition=Disposition.AUTO_CONTAIN,
    )
    assert_edict_snapshot_pairing(activated.conn, result.edict)
