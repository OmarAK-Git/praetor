# Implementer Result — V2-033 Judgment Prompt Exemplar Slot

## Summary

Added an optional, bounded `prompt_exemplar_block` to judgment prompt payloads. Exemplars are auditable (stable IDs, source case references, truncation metadata) and clearly separated from cited evidence via a distinct payload key and `exemplar_scope` instructions. `PromptExcerptSet` construction and `evidence_bundle_hash` passthrough are unchanged.

## Files changed

| File | Rationale |
|------|-----------|
| `src/praetor/judgment/excerpt.py` | Added `PromptExemplar`, `PromptExemplarBlock`, bounds (`MAX_PROMPT_EXEMPLARS=3`, `MAX_PROMPT_EXEMPLAR_CHARS=400`), and `build_prompt_exemplar_block()` with head-tail truncation reuse. |
| `src/praetor/judgment/prompt.py` | Added optional `exemplars` / `exemplar_block` parameters; renders `prompt_exemplar_block` and `exemplar_scope` / `exemplar_notice` instructions when present; omits block when absent. |
| `tests/judgment/test_prompt_isolation.py` | Added four tests: absent-block default, bounded/auditable rendering, separation from cited evidence, unchanged excerpt set and hash with exemplars. |

## Acceptance criteria

1. **Optional exemplar block** — `build_judgment_prompt_payload(..., exemplars=...)` and `build_judgment_prompt_payload_from_excerpt_set(..., exemplar_block=...)` accept optional exemplars; block omitted when `None`/empty.
2. **Bounded, auditable, separated** — max 3 exemplars, 400-char summary cap with omission metadata; each exemplar carries `exemplar_id` and `source_case_id`; separate `prompt_exemplar_block` key and `exemplar_scope` instruction forbids citing exemplars as evidence.
3. **Evidence hash and PromptExcerptSet unchanged** — excerpt set built only from `evidence_facts`; `evidence_bundle_hash` passed through unchanged; exemplars do not enter `build_prompt_excerpt_set`.
4. **Queue not marked done** — `autopilot-queue.json` untouched.

## Verification

```text
$ python -m pytest tests/judgment/test_prompt_isolation.py -q
.........                                                                [100%]
9 passed in 0.57s
```

## Unresolved

None.
