"""Pure-Python evaluator for committed detections/spl/*.spl search predicates."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_TOKEN_PATTERN = re.compile(
    r'(\w+)=(?:"((?:[^"\\]|\\.)*)"|(\S+))',
)


@dataclass(frozen=True)
class SplPredicate:
    field: str
    op: str  # eq | endswith | contains
    literal: str | int


class SplParseError(ValueError):
    """Raised when a committed SPL string uses unsupported predicate syntax."""


def _unescape_spl_string(value: str) -> str:
    return value.replace("\\\\", "\\")


def _parse_token(token: str) -> SplPredicate:
    match = _TOKEN_PATTERN.fullmatch(token.strip())
    if not match:
        raise SplParseError(f"unsupported SPL token: {token!r}")
    field, quoted, bare = match.groups()
    raw = quoted if quoted is not None else bare
    if raw is None:
        raise SplParseError(f"missing value in SPL token: {token!r}")

    if field == "EventCode" and quoted is None and bare.isdigit():
        return SplPredicate(field=field, op="eq", literal=int(bare))

    if quoted is None:
        return SplPredicate(field=field, op="eq", literal=bare)

    text = _unescape_spl_string(quoted)
    if text.startswith("*") and text.endswith("*") and len(text) >= 3:
        return SplPredicate(field=field, op="contains", literal=text[1:-1])
    if text.startswith("*"):
        return SplPredicate(field=field, op="endswith", literal=text[1:])
    return SplPredicate(field=field, op="eq", literal=text)


def parse_spl_predicates(spl: str) -> tuple[SplPredicate, ...]:
    spl = spl.strip()
    if not spl:
        raise SplParseError("empty SPL query")
    tokens = spl.split()
    try:
        return tuple(_parse_token(token) for token in tokens)
    except SplParseError:
        raise
    except Exception as exc:
        raise SplParseError(f"failed to parse SPL: {spl!r}") from exc


def _field_value(event: dict[str, Any], field: str) -> Any:
    if field not in event:
        return None
    return event[field]


def _coerce_equal(actual: Any, expected: str | int) -> bool:
    if actual == expected:
        return True
    if isinstance(expected, int):
        try:
            return int(actual) == expected
        except (TypeError, ValueError):
            return False
    return str(actual) == str(expected)


def _eval_predicate(predicate: SplPredicate, event: dict[str, Any]) -> bool:
    actual = _field_value(event, predicate.field)
    if actual is None:
        return False
    if predicate.op == "eq":
        return _coerce_equal(actual, predicate.literal)
    actual_text = str(actual)
    literal = str(predicate.literal)
    if predicate.op == "endswith":
        return actual_text.casefold().endswith(literal.casefold())
    if predicate.op == "contains":
        return literal.casefold() in actual_text.casefold()
    raise SplParseError(f"unknown predicate op: {predicate.op!r}")


def spl_matches_event(spl: str, event: dict[str, Any]) -> bool:
    """Return True when every predicate in committed SPL matches the flattened event."""
    return all(_eval_predicate(pred, event) for pred in parse_spl_predicates(spl))


def matching_record_ids(spl: str, events: dict[str, dict[str, Any]]) -> set[str]:
    return {
        record_id
        for record_id, flat in events.items()
        if spl_matches_event(spl, flat)
    }


def collapse_duplicate_source_terms(query: str) -> str:
    """Collapse consecutive identical source=\"...\" terms in savedsearch queries."""
    pattern = re.compile(r'(source="[^"]+")\s+\1')
    normalized = query.strip()
    while pattern.search(normalized):
        normalized = pattern.sub(r"\1", normalized)
    return normalized
