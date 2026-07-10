# Verifier Result — V2-033 Judgment Prompt Exemplar Slot

**Role:** Adversarial skeptic-verifier (fresh context, independent evidence).
**Overall verdict:** PASS

## Evidence gathered (run by verifier)

- `python -m pytest tests/judgment/test_prompt_isolation.py -q` → `9 passed in 0.55s` (exit 0).
- `python -m pytest tests/judgment/ -q` → `59 passed in 4.33s` (exit 0) — confirms no regression in the broader judgment suite, including the pre-existing excerpt-truncation and engine-isolation tests.
- Read of `src/praetor/judgment/excerpt.py`, `src/praetor/judgment/prompt.py`, `tests/judgment/test_prompt_isolation.py`.
- `git status --porcelain` for `src/praetor/judgment/` and `tests/judgment/` — the three declared files are modified.
- Grep for `hash|sha|digest` in `excerpt.py` → no matches (no hashing logic in the excerpt module).

(Note: `git diff` invocations hung in this PowerShell session and produced no output; verdict relies on direct file reads + executed tests instead, which are sufficient.)

## Per-criterion verdict

### 1. Prompt template accepts an optional exemplar block — PASS
- `build_judgment_prompt_payload(..., exemplars: Iterable | None = None)` (`prompt.py:48`) and `build_judgment_prompt_payload_from_excerpt_set(..., exemplar_block: PromptExemplarBlock | None = None)` (`prompt.py:67`) both default to no exemplars.
- Block is omitted entirely when absent: `payload["prompt_exemplar_block"]` and the `exemplar_scope`/`exemplar_notice` instructions are only added when `exemplar_block is not None` (`prompt.py:82-99`).
- `test_prompt_payload_omits_exemplar_block_when_absent` asserts absence when no exemplars supplied. Passed.

### 2. Exemplar rendering bounded, auditable, separated from cited evidence — PASS
- **Bounded:** `MAX_PROMPT_EXEMPLARS=3` enforced via `built[:MAX_PROMPT_EXEMPLARS]` (`excerpt.py:132`); `MAX_PROMPT_EXEMPLAR_CHARS=400` enforced via shared `_head_tail_truncate` (`excerpt.py:137`).
- **Auditable:** each `PromptExemplar` carries `exemplar_id`, `source_case_id`, optional `disposition`, `incomplete`, and `omitted_characters` (`excerpt.py:76-95`).
- **Separated:** exemplars live under a distinct `prompt_exemplar_block` payload key, and `EXEMPLAR_SCOPE_INSTRUCTIONS` explicitly forbids citing `exemplar_id`/`source_case_id` as evidence (`prompt.py:28-32`).
- `test_prompt_exemplar_block_bounded_and_auditable` verifies the 3-item cap, 400-char truncation with omission marker, and stable IDs. `test_prompt_exemplar_block_separated_from_cited_evidence` asserts `exemplar_id` does not appear in the serialized `prompt_excerpt_set` and the do-not-cite instruction is present. Both passed.

### 3. Evidence hash and PromptExcerptSet behavior unchanged — PASS
- `evidence_bundle_hash` is a pass-through string; it is not computed in either changed module (grep confirms no hashing in `excerpt.py`; `prompt.py` only assigns the caller-provided value at `prompt.py:92`). Exemplars never enter any hash input.
- `build_prompt_excerpt_set` and the fact/excerpt/truncation logic are untouched by exemplar handling; exemplars are built by a separate `build_prompt_exemplar_block` and never passed into `build_prompt_excerpt_set`.
- `test_prompt_excerpt_set_unchanged_with_exemplars` directly asserts `prompt_excerpt_set` and `evidence_bundle_hash` are byte-identical with vs. without exemplars. Passed.
- The pre-existing pinned tests (`test_prompt_excerpt_set_caps_text_and_uses_stable_evidence_ids`, `test_unbounded_field_truncation_keeps_head_tail_and_omission_count`, `test_engine_provider_request_uses_prompt_excerpt_set_only`) still pass, confirming the shared `_head_tail_truncate` refactor did not alter excerpt (max-200) behavior and that raw_source isolation is intact.

### 4. V2-033 scope only — PASS (with note)
- The three declared files are the only judgment files this task touches. `git status` also shows `vertex_provider.py`, `test_provider_failures.py`, and `test_vertex_provider.py` as modified/untracked, but those are pre-existing changes from prior tasks (V2-028), not introduced by V2-033, and are outside this task's evidence set. No autopilot-queue mutation was observed.

## Attempted refutations that failed
- *"The shared truncation refactor could have changed excerpt (200-char) output."* → Refuted: pinned excerpt/truncation tests pass unchanged; `test_prompt_excerpt_set_unchanged_with_exemplars` proves identical output.
- *"Exemplars could leak into evidence or affect the hash."* → Refuted: exemplars occupy a separate payload key, are excluded from `prompt_excerpt_set`, and no hashing occurs in the changed modules; test asserts equality of hash and excerpt set.
- *"Block might not be bounded if many exemplars are passed."* → Refuted: output is sliced to `MAX_PROMPT_EXEMPLARS=3`; test with `MAX_PROMPT_EXEMPLARS + 2` inputs confirms a 3-item result. (All exemplars are built before slicing — a minor inefficiency, not a correctness or acceptance defect.)

## Conclusion
All four acceptance criteria are satisfied with independently reproduced evidence. **Overall: PASS.**
