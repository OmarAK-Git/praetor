# Praetor implementation decisions

Authoritative product contracts remain in `docs/spec.md` and `docs/contracts.md`.
This file records implementation choices that refine or operationalize those docs.

| ID | Date | Decision | Rationale | Evidence |
|---|---|---|---|---|
| DEC-047 | 2026-06-13 | Task 14 structural prompt isolation is deterministic CI evidence; Task 27 real-provider adversarial excerpt probe is probabilistic and non-gating | Structural tests prove `raw_source` exclusion, excerpt bounds, and omission markers via `build_prompt_excerpt_set` before any live model call. The adversarial probe sends instruction-like normalized-field text to a real provider and logs outcomes only — model compliance cannot be asserted deterministically. Default `pytest` excludes `@pytest.mark.integration` and `@pytest.mark.probabilistic`. | `docs/eval_gates.md`, `evals/real_provider_adversarial.py`, `tests/judgment/test_prompt_isolation.py`, `evals/scenarios/prompt_construction_isolation.yaml` |

Add rows when implementation choices diverge from or refine authoritative docs.
