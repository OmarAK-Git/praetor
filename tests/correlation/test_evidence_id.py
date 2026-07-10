"""V2-021: evidence_id contract pin (docs/contracts.md §3b)."""

from __future__ import annotations

from praetor.correlation.ids import derive_evidence_id, source_event_reference
from praetor.hashing.canonical import delimited, sha256_hex
from praetor.hashing.domains import DOMAIN_EVIDENCE_ID

_VECTOR_PROVENANCE = "sysmon_event_log"
_VECTOR_SOURCE_REF = "microsoft-windows-sysmon:1:12345"
_VECTOR_EVIDENCE_ID = "ev-d874f190dca015a7ba7235e2e933fbd2"


class TestEvidenceId:
    def test_evidence_id_contract_vector(self) -> None:
        assert (
            derive_evidence_id(
                provenance_path=_VECTOR_PROVENANCE,
                source_event_reference=_VECTOR_SOURCE_REF,
            )
            == _VECTOR_EVIDENCE_ID
        )

    def test_evidence_id_uses_length_delimited_ordering(self) -> None:
        provenance = "windows_security_log"
        source_ref = "security:4624:98765"
        digest = sha256_hex(
            delimited([DOMAIN_EVIDENCE_ID, provenance, source_ref])
        )
        assert (
            derive_evidence_id(
                provenance_path=provenance,
                source_event_reference=source_ref,
            )
            == f"ev-{digest[:32]}"
        )

    def test_source_event_reference_canonical_form(self) -> None:
        assert (
            source_event_reference(
                channel="Microsoft-Windows-Sysmon/Operational",
                event_id=1,
                record_id="12345",
            )
            == _VECTOR_SOURCE_REF
        )
