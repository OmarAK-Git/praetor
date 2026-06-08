"""Canonical serialization for hashes and ledger records (docs/contracts.md §1)."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

# Sentinel preimage for correlation-failure substitution (docs/contracts.md §7).
EMPTY_BUNDLE_SENTINEL = "praetor:v1:empty_bundle"


class CanonicalSerializationError(ValueError):
    """Raised when input cannot be serialized under canonical rules."""


_RFC3339_MICROS_Z = __import__("re").compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def delimited(parts: Sequence[str | bytes]) -> bytes:
    """Length-delimited concatenation (docs/contracts.md §1.1)."""
    chunks: list[bytes] = []
    for part in parts:
        part_bytes = part.encode("utf-8") if isinstance(part, str) else part
        prefix = f"{len(part_bytes)}:".encode("ascii")
        chunks.append(prefix)
        chunks.append(part_bytes)
    return b"".join(chunks)


def _format_datetime_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise CanonicalSerializationError("datetime must be timezone-aware")
    utc = value.astimezone(UTC)
    base = utc.strftime("%Y-%m-%dT%H:%M:%S")
    micros = utc.microsecond
    return f"{base}.{micros:06d}Z"


def _validate_rfc3339_micros_z(value: str) -> None:
    if not _RFC3339_MICROS_Z.match(value):
        raise CanonicalSerializationError(
            "timestamp strings must be UTC RFC3339 with exactly six "
            "fractional digits and Z suffix"
        )


def _looks_like_rfc3339_timestamp(value: str) -> bool:
    return len(value) >= 20 and value[10] == "T" and value.endswith("Z")


def _serialize_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if _looks_like_rfc3339_timestamp(value):
            _validate_rfc3339_micros_z(value)
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CanonicalSerializationError("NaN and Infinity are not allowed")
        raise CanonicalSerializationError(
            "float values are not allowed in canonical serialization"
        )
    if isinstance(value, datetime):
        return _format_datetime_utc(value)
    if isinstance(value, Mapping):
        return {key: _serialize_value(value[key]) for key in sorted(value.keys())}
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    raise CanonicalSerializationError(
        f"unsupported type for canonical serialization: {type(value)!r}"
    )


def canonical_serialize(
    value: Any,
    *,
    allowed_keys: frozenset[str] | None = None,
) -> bytes:
    """Serialize to canonical UTF-8 JSON bytes."""
    if allowed_keys is not None:
        if not isinstance(value, Mapping):
            raise CanonicalSerializationError("allowed_keys requires a mapping value")
        unknown = set(value.keys()) - allowed_keys
        if unknown:
            raise CanonicalSerializationError(f"unknown fields: {sorted(unknown)}")

    payload = _serialize_value(value)

    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=isinstance(payload, dict),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalSerializationError(str(exc)) from exc

    return text.encode("utf-8")


def canonical_hash(
    value: Any,
    *,
    allowed_keys: frozenset[str] | None = None,
) -> str:
    """SHA-256 lowercase hex over canonical serialization bytes."""
    return sha256_hex(canonical_serialize(value, allowed_keys=allowed_keys))


EMPTY_BUNDLE: str = canonical_hash(EMPTY_BUNDLE_SENTINEL)
