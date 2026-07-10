"""Provider-facing evidence excerpts with raw-source isolation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MAX_PROMPT_EXCERPT_CHARS = 200
MAX_PROMPT_EXEMPLARS = 3
MAX_PROMPT_EXEMPLAR_CHARS = 400
_RAW_SOURCE_KEY = "raw_source"
_RESERVED_FACT_KEYS = frozenset(
    {
        "evidence_id",
        "normalized_fields",
        "source_event_reference",
        _RAW_SOURCE_KEY,
        "provenance_path",
        "ambiguity_flag",
        "timestamp",
        "entity_references",
    }
)


@dataclass(frozen=True)
class PromptExcerpt:
    field_path: str
    text: str
    incomplete: bool
    omitted_characters: int = 0

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "field_path": self.field_path,
            "text": self.text,
            "incomplete": self.incomplete,
            "omitted_characters": self.omitted_characters,
        }


@dataclass(frozen=True)
class PromptFact:
    evidence_id: str
    provenance_path: str
    ambiguity_flag: bool
    excerpts: tuple[PromptExcerpt, ...]

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "provenance_path": self.provenance_path,
            "ambiguity_flag": self.ambiguity_flag,
            "excerpts": [excerpt.as_provider_payload() for excerpt in self.excerpts],
        }


@dataclass(frozen=True)
class PromptExcerptSet:
    facts: tuple[PromptFact, ...]

    @property
    def has_incomplete_content(self) -> bool:
        return any(
            excerpt.incomplete
            for fact in self.facts
            for excerpt in fact.excerpts
        )

    def as_provider_payload(self) -> dict[str, object]:
        return {"facts": [fact.as_provider_payload() for fact in self.facts]}


@dataclass(frozen=True)
class PromptExemplar:
    exemplar_id: str
    source_case_id: str
    summary: str
    disposition: str | None = None
    incomplete: bool = False
    omitted_characters: int = 0

    def as_provider_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "exemplar_id": self.exemplar_id,
            "source_case_id": self.source_case_id,
            "summary": self.summary,
            "incomplete": self.incomplete,
            "omitted_characters": self.omitted_characters,
        }
        if self.disposition is not None:
            payload["disposition"] = self.disposition
        return payload


@dataclass(frozen=True)
class PromptExemplarBlock:
    exemplars: tuple[PromptExemplar, ...]

    @property
    def has_incomplete_content(self) -> bool:
        return any(exemplar.incomplete for exemplar in self.exemplars)

    def as_provider_payload(self) -> dict[str, object]:
        return {
            "exemplars": [
                exemplar.as_provider_payload() for exemplar in self.exemplars
            ]
        }


def build_prompt_excerpt_set(
    evidence_facts: Iterable[Mapping[str, Any]],
) -> PromptExcerptSet:
    return PromptExcerptSet(
        facts=tuple(_build_prompt_fact(fact) for fact in evidence_facts)
    )


def build_prompt_exemplar_block(
    exemplars: Iterable[Mapping[str, Any]] | None,
) -> PromptExemplarBlock | None:
    if exemplars is None:
        return None

    built = tuple(_build_prompt_exemplar(exemplar) for exemplar in exemplars)
    if not built:
        return None

    return PromptExemplarBlock(exemplars=built[:MAX_PROMPT_EXEMPLARS])


def _build_prompt_exemplar(exemplar: Mapping[str, Any]) -> PromptExemplar:
    summary_text = str(exemplar["summary"])
    summary, omitted = _head_tail_truncate(summary_text, MAX_PROMPT_EXEMPLAR_CHARS)
    disposition = exemplar.get("disposition")
    return PromptExemplar(
        exemplar_id=str(exemplar["exemplar_id"]),
        source_case_id=str(exemplar["source_case_id"]),
        summary=summary,
        disposition=str(disposition) if disposition is not None else None,
        incomplete=omitted > 0,
        omitted_characters=omitted,
    )


def _build_prompt_fact(fact: Mapping[str, Any]) -> PromptFact:
    evidence_id = str(fact["evidence_id"])
    provenance_path = str(fact.get("provenance_path", ""))
    ambiguity_flag = bool(fact.get("ambiguity_flag", False))
    excerpts: list[PromptExcerpt] = []

    normalized_fields = fact.get("normalized_fields")
    if isinstance(normalized_fields, Mapping):
        for field_name, value in sorted(normalized_fields.items()):
            if field_name == _RAW_SOURCE_KEY:
                continue
            excerpts.append(
                _excerpt_for_value(f"normalized_fields.{field_name}", value)
            )

    for field_path, value in sorted(fact.items()):
        if field_path in _RESERVED_FACT_KEYS:
            continue
        excerpts.append(_excerpt_for_value(field_path, value))

    for field_path in ("source_event_reference", "provenance_path"):
        if field_path in fact:
            excerpts.append(_excerpt_for_value(field_path, fact[field_path]))

    return PromptFact(
        evidence_id=evidence_id,
        provenance_path=provenance_path,
        ambiguity_flag=ambiguity_flag,
        excerpts=tuple(excerpts),
    )


def _excerpt_for_value(field_path: str, value: Any) -> PromptExcerpt:
    text = _stringify_prompt_value(_without_raw_source(value))
    excerpt_text, omitted = _head_tail_truncate(text, MAX_PROMPT_EXCERPT_CHARS)
    return PromptExcerpt(
        field_path=field_path,
        text=excerpt_text,
        incomplete=omitted > 0,
        omitted_characters=omitted,
    )


def _stringify_prompt_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _without_raw_source(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _without_raw_source(item)
            for key, item in value.items()
            if key != _RAW_SOURCE_KEY
        }
    if isinstance(value, list | tuple):
        return [_without_raw_source(item) for item in value]
    return value


def _head_tail_truncate(text: str, max_chars: int) -> tuple[str, int]:
    if len(text) <= max_chars:
        return text, 0

    omitted = len(text)
    while True:
        marker = f"[...omitting {omitted} characters]"
        available = max_chars - len(marker)
        if available < 2:
            msg = "max_chars is too small for head+tail truncation"
            raise ValueError(msg)
        head_chars = available // 2
        tail_chars = available - head_chars
        next_omitted = len(text) - head_chars - tail_chars
        if next_omitted == omitted:
            return (
                f"{text[:head_chars]}{marker}{text[len(text) - tail_chars:]}",
                omitted,
            )
        omitted = next_omitted
