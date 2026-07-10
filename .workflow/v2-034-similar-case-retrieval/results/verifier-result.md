# Verifier Result — V2-034 Similar-Case Retrieval

**Verdict: SURVIVES (all acceptance criteria pass)**
**Role:** skeptic-verifier (independent, adversarial). Evidence gathered by reading source and running the task command myself; the implementer transcript was not accepted as evidence.

## Verification command (run by verifier)

```text
$ python -m pytest tests/judgment/ tests/annotations/ -q
........................................................................ [ 94%]
....                                                                     [100%]
76 passed in 5.51s
```

Exit code 0. Matches the plan/packet command.

## Per-criterion findings

### 1. Retrieval selects only human-confirmed cases per documented ranking contract — PASS

- Eligibility filter is enforced in SQL: `fetch_human_confirmed_precedents`
  joins on `json_extract(annotation_json,'$.disposition_correct') IN (1,'true')`
  (`src/praetor/annotations/precedent.py:37-42`).
- `TestHumanConfirmedPrecedentFetch` proves a `disposition_correct=false`
  decision is excluded while the confirmed one is returned
  (`tests/judgment/test_similar_case_retrieval.py:147-181`).
- Ranking contract is documented in the module docstring
  (`src/praetor/retrieval/ranking.py:1-12`) and `docs/eval_gates.md:23-40`:
  eligibility → token overlap → recency of confirmation → `decision_id`
  tie-break → bound of 3.
- Adversarial check on the ranking test (`test_ranking_prefers_token_overlap_
  then_recency`): I confirmed recency is genuinely load-bearing, not masked by
  the tie-break. `stored_at = datetime.now(UTC)` in `submit_annotation`
  (`src/praetor/annotations/store.py:172`), so the sequentially-inserted
  `dec-old-match`/`dec-new-match` get distinct wall-clock confirmation times;
  recency (sort-key position 2) dominates the `decision_id` tie-break
  (position 3). A broken recency rule would flip the asserted order and fail
  the test. Overlap dominance is also proven (the most-recent but zero-overlap
  `dec-unrelated` is ranked last).

  **Caveat (not a failure):** eligibility selects `MAX(annotation_id)` among
  *confirmed* annotations only, so a decision that has any prior confirmed
  annotation remains retrievable even if a later annotation flips it to
  `disposition_correct=false`. This complies with the documented
  "at least one confirmed annotation" contract but is a latent staleness
  edge worth tracking.

### 2. Exemplar payloads bounded and excluded from evidence hash derivation — PASS

- **Bounded:** `retrieve_similar_case_exemplars` caps at
  `MAX_PROMPT_EXEMPLARS` (3) (`similar_cases.py:35`); `build_prompt_exemplar_block`
  re-caps to 3 (`excerpt.py:132`); summaries truncate to
  `MAX_PROMPT_EXEMPLAR_CHARS` (400) via `_head_tail_truncate` (`excerpt.py:137`).
  `test_retrieval_excludes_active_decision_and_caps_results` seeds 5 confirmed
  cases and asserts exactly 3 returned with the active id excluded.
- **Excluded from evidence hash:** the evidence hash is derived upstream over
  the evidence bundle in `engine/edict.py` (`resolved_evidence_bundle_hash` →
  `derive_decision_id`, `edict.py:91-105`) and passed into the prompt builder as
  a plain string; `build_judgment_prompt_payload_with_similar_cases` never
  recomputes it and exemplars have no path into it. `hashing/domains.py` shows
  no exemplar input to any hash. `test_prompt_payload_wires_retrieved_exemplars_
  without_hash_change` asserts `evidence_bundle_hash` and `prompt_excerpt_set`
  are byte-identical with vs. without retrieval, while the exemplar block is
  added.

### 3. Contract eval/tests prove retrieval wired without changing citation validity or raw-source exclusion — PASS

- Wiring proven: `test_prompt_payload_wires_retrieved_exemplars_without_hash_change`
  asserts `prompt_exemplar_block.exemplars[0].source_case_id == "ALERT-PRECEDENT"`.
- Raw-source exclusion proven: `test_retrieval_preserves_raw_source_exclusion_
  and_citation_validity` serializes the full payload and asserts absence of
  `raw_source`, the fact-level `DO-NOT-LEAK` body, and the normalized-field
  leak string. The retrieval query builder also strips the `raw_source` key
  before tokenizing (`ranking.py:49-55`).
- Citation validity proven: same test builds an `EvidenceBundle` and asserts
  `validate_evidence_citations(...).valid is True`.

### 4. V2-034 scope only — PASS

- Queue entry `v2-034-similar-case-retrieval` status is `verifying`, not `done`
  (`.workflow/autopilot-queue.json:1203-1204`).
- Task-attributable changes are confined to the allowed surface: new
  `src/praetor/retrieval/` (ranking, similar_cases, `__init__`), new
  `src/praetor/annotations/precedent.py`, `annotations/__init__.py` export,
  `judgment/prompt.py` wiring function, `tests/judgment/test_similar_case_
  retrieval.py`, and `docs/eval_gates.md`. No out-of-scope module was modified
  by this task. (The repo carries a large pre-existing uncommitted tree from
  earlier V2 tasks; those are not introduced by V2-034.)

## Strongest attempt to refute

The most promising refutation was that the ranking test proves recency only by
coincidental alignment with the `decision_id` tie-break. It was refuted:
`stored_at` is wall-clock (`datetime.now(UTC)`), not the fixed `NOW` fixture, so
confirmation timestamps differ and recency sits ahead of the tie-break in the
sort key — the recency rule is actually exercised.

## Overall verdict

**SURVIVES.** All four acceptance criteria are satisfied with test-backed and
source-backed evidence. One non-blocking caveat noted under criterion 1
(confirmed-then-reverted decisions remain retrievable per the documented
"at least one confirmed" contract).
