"""TASK-003: canonical serialization and hash constants."""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from praetor.hashing.canonical import (
    EMPTY_BUNDLE,
    EMPTY_BUNDLE_SENTINEL,
    CanonicalSerializationError,
    canonical_hash,
    canonical_serialize,
    delimited,
    sha256_hex,
)
from praetor.hashing.domains import (
    DOMAIN_DECISION_ID,
    DOMAIN_IDEMPOTENCY_KEY,
    DOMAIN_STAMP_ID,
    compute_feed_record_checksum,
    compute_never_contain_entries_hash,
    derive_decision_id,
    derive_idempotency_key,
    derive_stamp_id,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src" / "praetor"
UTC = timezone.utc

RFC3339_MICROS_Z = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)


class TestCanonicalSerialize:
    def test_stable_hash_across_calls(self) -> None:
        value = {"b": 2, "a": 1, "nested": {"z": True, "m": None}}
        first = canonical_hash(value)
        second = canonical_hash(value)
        assert first == second
        assert len(first) == 64
        assert first == first.lower()

    def test_keys_sorted_by_unicode_code_point(self) -> None:
        payload = {"b": 1, "a": 2, "aa": 3}
        serialized = canonical_serialize(payload).decode("utf-8")
        assert serialized == '{"a":2,"aa":3,"b":1}'

    def test_datetime_serialized_utc_rfc3339_six_fractional_digits(self) -> None:
        dt = datetime(2026, 5, 31, 20, 45, 0, 123456, tzinfo=UTC)
        payload = {"ts": dt}
        serialized = canonical_serialize(payload).decode("utf-8")
        assert serialized == '{"ts":"2026-05-31T20:45:00.123456Z"}'
        assert RFC3339_MICROS_Z.match("2026-05-31T20:45:00.123456Z")

    def test_datetime_string_with_wrong_fractional_digits_rejected(self) -> None:
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize({"ts": "2026-05-31T20:45:00.123Z"})
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize({"ts": "2026-05-31T20:45:00.1234567Z"})

    def test_nan_raises(self) -> None:
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize({"x": math.nan})

    def test_infinity_raises(self) -> None:
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize({"x": math.inf})
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize({"x": -math.inf})

    def test_unknown_fields_raise_with_allowed_keys(self) -> None:
        with pytest.raises(CanonicalSerializationError):
            canonical_serialize(
                {"known": 1, "extra": 2},
                allowed_keys=frozenset({"known"}),
            )

    def test_absent_vs_null_distinct(self) -> None:
        with_null = canonical_serialize({"field": None})
        without = canonical_serialize({})
        assert with_null != without
        assert with_null.decode("utf-8") == '{"field":null}'

    def test_delimited_distinct_from_raw_concatenation(self) -> None:
        assert delimited(["ab", "c"]) == b"2:ab1:c"
        assert delimited(["a", "bc"]) == b"1:a2:bc"
        assert delimited(["ab", "c"]) != delimited(["a", "bc"])


class TestDomainConstants:
    def test_domain_constants_exact_bytes(self) -> None:
        assert DOMAIN_DECISION_ID == "praetor:v1:decision_id"
        assert DOMAIN_IDEMPOTENCY_KEY == "praetor:v1:idempotency_key"
        assert DOMAIN_STAMP_ID == "praetor:v1:stamp_id"

    def test_no_inline_domain_literals_outside_domains_module(self) -> None:
        literals = (
            "praetor:v1:decision_id",
            "praetor:v1:idempotency_key",
            "praetor:v1:stamp_id",
        )
        domains_file = SRC / "hashing" / "domains.py"
        for path in SRC.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for literal in literals:
                if literal not in text:
                    continue
                if path.resolve() == domains_file.resolve():
                    continue
                pytest.fail(f"inline domain literal {literal!r} in {path.relative_to(REPO_ROOT)}")

    def test_derived_hashes_use_distinct_domains(self) -> None:
        alert = "ALERT-001"
        bundle_hash = "abc123"
        org_hash = "def456"
        attempt = "7"
        decision = derive_decision_id(alert, bundle_hash, org_hash, attempt)
        stamp = derive_stamp_id(alert, bundle_hash, org_hash)
        idem = derive_idempotency_key(alert, "host", "host-01", "host-isolation")
        assert len({decision, stamp, idem}) == 3


class TestDecisionId:
    def test_decision_id_uses_length_delimited_ordering(self) -> None:
        alert = "ALERT-001"
        bundle = "bundle-hash"
        org = "org-hash"
        attempt = "42"
        expected_input = delimited(
            [
                DOMAIN_DECISION_ID,
                alert,
                bundle,
                org,
                attempt,
            ]
        )
        assert derive_decision_id(alert, bundle, org, attempt) == sha256_hex(expected_input)


class TestIdempotencyKey:
    def test_idempotency_key_uses_length_delimited_ordering(self) -> None:
        alert = "ALERT-001"
        target_type = "host"
        target_id = "host-01"
        scope = "host-isolation"
        expected_input = delimited(
            [
                DOMAIN_IDEMPOTENCY_KEY,
                alert,
                target_type,
                target_id,
                scope,
            ]
        )
        assert (
            derive_idempotency_key(alert, target_type, target_id, scope)
            == sha256_hex(expected_input)
        )


class TestStampId:
    def test_stamp_id_uses_length_delimited_ordering(self) -> None:
        alert = "ALERT-001"
        bundle = "bundle-hash"
        org = "org-hash"
        expected_input = delimited(
            [
                DOMAIN_STAMP_ID,
                alert,
                bundle,
                org,
            ]
        )
        assert derive_stamp_id(alert, bundle, org) == sha256_hex(expected_input)

    def test_stamp_id_stable_across_processing_attempts(self) -> None:
        alert = "ALERT-001"
        bundle = "bundle-hash"
        org = "org-hash"
        stamp = derive_stamp_id(alert, bundle, org)
        decision_a = derive_decision_id(alert, bundle, org, "1")
        decision_b = derive_decision_id(alert, bundle, org, "2")
        assert derive_stamp_id(alert, bundle, org) == stamp
        assert decision_a != decision_b
        assert stamp != decision_a


class TestEmptyBundle:
    def test_empty_bundle_sentinel_preimage_matches_contract(self) -> None:
        assert EMPTY_BUNDLE_SENTINEL == "praetor:v1:empty_bundle"

    def test_empty_bundle_is_deterministic_module_constant(self) -> None:
        assert EMPTY_BUNDLE == canonical_hash(EMPTY_BUNDLE_SENTINEL)
        assert EMPTY_BUNDLE == canonical_hash(EMPTY_BUNDLE_SENTINEL)

    def test_empty_bundle_not_empty_string_or_empty_object_hash(self) -> None:
        assert EMPTY_BUNDLE != ""
        assert EMPTY_BUNDLE != sha256_hex(canonical_serialize({}))
        assert EMPTY_BUNDLE != sha256_hex(b"")


class TestFeedRecordChecksum:
    def test_record_checksum_excludes_checksum_field(self) -> None:
        record = {
            "schema_version": "1",
            "sequence_number": 1,
            "directive_id": "dir-1",
            "revocation_id": "rev-1",
            "reason_code": "manual_revocation",
            "revoked_at": datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
            "ledger_commit_at": datetime(2026, 6, 1, 12, 0, 1, tzinfo=UTC),
            "record_checksum": "must-be-excluded",
            "public_detail": None,
        }
        checksum = compute_feed_record_checksum(record)
        assert checksum != "must-be-excluded"
        assert checksum == sha256_hex(
            canonical_serialize(
                {k: v for k, v in record.items() if k != "record_checksum"},
                allowed_keys=frozenset(
                    {
                        "schema_version",
                        "sequence_number",
                        "directive_id",
                        "revocation_id",
                        "reason_code",
                        "revoked_at",
                        "ledger_commit_at",
                        "public_detail",
                    }
                ),
            )
        )

    def test_checksum_is_corruption_detection_not_tamper_evidence(self) -> None:
        """Documented intent: recomputing checksum detects truncation/corruption only."""
        record = {
            "schema_version": "1",
            "sequence_number": 2,
            "directive_id": "dir-2",
            "revocation_id": "rev-2",
            "reason_code": "supersession",
            "revoked_at": datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC),
            "ledger_commit_at": datetime(2026, 6, 1, 12, 0, 1, tzinfo=UTC),
        }
        checksum = compute_feed_record_checksum(record)
        tampered = {**record, "reason_code": "manual_revocation", "record_checksum": checksum}
        assert compute_feed_record_checksum(tampered) != checksum


class TestNeverContainEntriesHash:
    def test_embedded_entries_hash_matches_section_eight(self) -> None:
        entries = [{"target_type": "host", "target_id": "host-01"}]
        assert compute_never_contain_entries_hash(entries) == canonical_hash(entries)
