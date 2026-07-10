"""V2-034 similar-case retrieval and prompt wiring tests."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from tests.ledger.conftest import sample_decision_edict, sample_model_judgment

from praetor.annotations.precedent import fetch_human_confirmed_precedents
from praetor.annotations.store import init_annotation_schema, submit_annotation
from praetor.auth import Principal, PrincipalMapVerifier
from praetor.contracts.disposition import Disposition
from praetor.contracts.judgment import ModelJudgment
from praetor.evidence.citations import validate_evidence_citations
from praetor.judgment.excerpt import MAX_PROMPT_EXEMPLARS
from praetor.judgment.prompt import (
    build_judgment_prompt_payload,
    build_judgment_prompt_payload_with_similar_cases,
)
from praetor.ledger.store import append_ledger_record, init_ledger_schema
from praetor.retrieval.ranking import (
    extract_query_tokens,
    rank_precedents_by_similarity,
)
from praetor.retrieval.similar_cases import retrieve_similar_case_exemplars
from praetor.state.sqlite_guard import create_guarded_connection, critical_transaction
from praetor.state.store import init_state_schema

NOW = datetime(2026, 6, 13, 12, 0, 0, tzinfo=UTC)
ANALYST_TOKEN = "token-analyst"


def _to_primitive(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _to_primitive(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_primitive(item) for item in value]
    return value


def _serialized(value: Any) -> str:
    return json.dumps(_to_primitive(value), sort_keys=True)


def _evidence_facts() -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": "ev-1",
            "normalized_fields": {
                "process_name": "powershell.exe",
                "command_line": "powershell admin tooling script",
                "raw_source": "must not leak into retrieval query",
            },
            "source_event_reference": "sysmon:1",
            "raw_source": "DO-NOT-LEAK raw event body",
            "provenance_path": "sysmon_event_log",
            "ambiguity_flag": False,
        }
    ]


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[Any]:
    from praetor.alerts.outbox import init_health_alert_outbox_schema
    from praetor.state.sqlite_guard import init_state_dir
    from praetor.tickets.outbox import init_stamp_outbox_schema

    db_path = tmp_path / "state.db"
    init_state_dir(db_path)
    connection = create_guarded_connection(db_path)
    connection.row_factory = __import__("sqlite3").Row
    init_state_schema(connection)
    init_stamp_outbox_schema(connection)
    init_health_alert_outbox_schema(connection)
    init_ledger_schema(connection)
    init_annotation_schema(connection)
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def verifier() -> PrincipalMapVerifier:
    return PrincipalMapVerifier(
        {ANALYST_TOKEN: Principal(identity="analyst@example.com", role="analyst")}
    )


def _append_edict(
    conn: Any,
    *,
    decision_id: str,
    alert_reference: str,
    narrative: str,
    final_disposition: Disposition = Disposition.STANDARD_REVIEW,
) -> None:
    judgment = sample_model_judgment()
    judgment = ModelJudgment(
        **{
            **judgment.model_dump(),
            "narrative": narrative,
            "key_tells": narrative.split(),
        }
    )
    edict = sample_decision_edict(decision_id=decision_id)
    edict = edict.model_copy(
        update={
            "alert_reference": alert_reference,
            "model_judgment": judgment,
            "final_disposition": final_disposition,
        }
    )
    with critical_transaction(conn):
        append_ledger_record(conn, edict)
    conn.commit()


def _confirm_decision(
    conn: Any,
    verifier: PrincipalMapVerifier,
    *,
    decision_id: str,
    comment: str,
    disposition_correct: bool = True,
) -> None:
    with critical_transaction(conn):
        submit_annotation(
            conn,
            token=ANALYST_TOKEN,
            verifier=verifier,
            decision_id=decision_id,
            disposition_correct=disposition_correct,
            corrected_disposition=(
                Disposition.ESCALATE if not disposition_correct else None
            ),
            comment=comment,
            timestamp=NOW,
        )
    conn.commit()


class TestHumanConfirmedPrecedentFetch:
    def test_fetch_includes_only_human_confirmed_cases(
        self, conn: Any, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(
            conn,
            decision_id="dec-confirmed",
            alert_reference="ALERT-CONFIRMED",
            narrative="powershell admin tooling precedent",
        )
        _append_edict(
            conn,
            decision_id="dec-rejected",
            alert_reference="ALERT-REJECTED",
            narrative="unconfirmed precedent",
        )
        _confirm_decision(
            conn,
            verifier,
            decision_id="dec-confirmed",
            comment="confirmed correct",
        )
        _confirm_decision(
            conn,
            verifier,
            decision_id="dec-rejected",
            comment="wrong call",
            disposition_correct=False,
        )

        precedents = fetch_human_confirmed_precedents(conn)

        assert [precedent.decision_id for precedent in precedents] == ["dec-confirmed"]
        assert precedents[0].alert_reference == "ALERT-CONFIRMED"
        assert "powershell" in precedents[0].summary


class TestSimilarCaseRanking:
    def test_ranking_prefers_token_overlap_then_recency(
        self, conn: Any, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(
            conn,
            decision_id="dec-old-match",
            alert_reference="ALERT-OLD",
            narrative="powershell admin tooling older case",
        )
        _append_edict(
            conn,
            decision_id="dec-new-match",
            alert_reference="ALERT-NEW",
            narrative="powershell admin tooling newer case",
        )
        _append_edict(
            conn,
            decision_id="dec-unrelated",
            alert_reference="ALERT-OTHER",
            narrative="unrelated malware beacon case",
        )
        _confirm_decision(conn, verifier, decision_id="dec-old-match", comment="old")
        _confirm_decision(conn, verifier, decision_id="dec-new-match", comment="new")
        _confirm_decision(conn, verifier, decision_id="dec-unrelated", comment="other")

        precedents = fetch_human_confirmed_precedents(conn)
        ranked = rank_precedents_by_similarity(
            precedents,
            extract_query_tokens(_evidence_facts()),
        )

        assert [precedent.decision_id for precedent in ranked[:2]] == [
            "dec-new-match",
            "dec-old-match",
        ]
        assert ranked[-1].decision_id == "dec-unrelated"


class TestSimilarCaseRetrievalWiring:
    def test_retrieval_excludes_active_decision_and_caps_results(
        self, conn: Any, verifier: PrincipalMapVerifier
    ) -> None:
        for index in range(MAX_PROMPT_EXEMPLARS + 2):
            decision_id = f"dec-{index}"
            _append_edict(
                conn,
                decision_id=decision_id,
                alert_reference=f"ALERT-{index}",
                narrative=f"powershell admin tooling case {index}",
            )
            _confirm_decision(
                conn,
                verifier,
                decision_id=decision_id,
                comment=f"confirmed {index}",
            )

        exemplars = retrieve_similar_case_exemplars(
            conn,
            evidence_facts=_evidence_facts(),
            exclude_decision_id="dec-0",
        )

        assert len(exemplars) == MAX_PROMPT_EXEMPLARS
        assert all(
            exemplar["source_case_id"].startswith("ALERT-") for exemplar in exemplars
        )
        assert all(
            exemplar["source_case_id"] != "ALERT-0" for exemplar in exemplars
        )

    def test_prompt_payload_wires_retrieved_exemplars_without_hash_change(
        self, conn: Any, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(
            conn,
            decision_id="dec-precedent",
            alert_reference="ALERT-PRECEDENT",
            narrative="powershell admin tooling confirmed precedent",
        )
        _confirm_decision(
            conn,
            verifier,
            decision_id="dec-precedent",
            comment="looks right",
        )

        baseline = build_judgment_prompt_payload(
            evidence_facts=_evidence_facts(),
            evidence_bundle_hash="bundle-hash",
            org_config_snapshot_hash="snapshot-hash",
            org_config_verbatim="config",
        )
        with_retrieval = build_judgment_prompt_payload_with_similar_cases(
            conn,
            evidence_facts=_evidence_facts(),
            evidence_bundle_hash="bundle-hash",
            org_config_snapshot_hash="snapshot-hash",
            org_config_verbatim="config",
        )

        assert (
            baseline["evidence_bundle_hash"] == with_retrieval["evidence_bundle_hash"]
        )
        assert baseline["prompt_excerpt_set"] == with_retrieval["prompt_excerpt_set"]
        assert "prompt_exemplar_block" in with_retrieval
        assert with_retrieval["prompt_exemplar_block"]["exemplars"][0][
            "source_case_id"
        ] == "ALERT-PRECEDENT"

    def test_retrieval_preserves_raw_source_exclusion_and_citation_validity(
        self, conn: Any, verifier: PrincipalMapVerifier
    ) -> None:
        _append_edict(
            conn,
            decision_id="dec-precedent",
            alert_reference="ALERT-PRECEDENT",
            narrative="powershell admin tooling confirmed precedent",
        )
        _confirm_decision(
            conn,
            verifier,
            decision_id="dec-precedent",
            comment="confirmed",
        )

        payload = build_judgment_prompt_payload_with_similar_cases(
            conn,
            evidence_facts=_evidence_facts(),
            evidence_bundle_hash="bundle-hash",
            org_config_snapshot_hash="snapshot-hash",
            org_config_verbatim="config",
        )
        serialized = _serialized(payload)

        assert "raw_source" not in serialized
        assert "DO-NOT-LEAK" not in serialized
        assert "must not leak into retrieval query" not in serialized

        judgment = sample_model_judgment()
        from praetor.contracts.evidence import EvidenceBundle, EvidenceFact

        bundle = EvidenceBundle(
            facts=[
                EvidenceFact(
                    evidence_id="ev-1",
                    normalized_fields=fact["normalized_fields"],
                    source_event_reference=fact["source_event_reference"],
                    raw_source=fact["raw_source"],
                    provenance_path=fact["provenance_path"],
                    ambiguity_flag=fact["ambiguity_flag"],
                    timestamp=NOW,
                )
                for fact in _evidence_facts()
            ]
        )
        result = validate_evidence_citations(judgment, bundle)
        assert result.valid is True
