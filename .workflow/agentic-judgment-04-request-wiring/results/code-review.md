# Code review — agentic-judgment-04-request-wiring

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 4 — optional `JudgmentRequest.evidence_bundle` + orchestrator wiring  
**Spec:** `.workflow/agentic-judgment-04-request-wiring/plan.md`

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Diff | `provider.py` (+optional field), `orchestrator.py` (+1 wiring line), `test_provider_failures.py` (+backward-compat test), new `test_agentic_request_evidence_bundle_wiring.py` (untracked) |
| PolicyGate boundary | `git diff HEAD -- src/praetor/policy/` — no content changes (CRLF warnings only) |
| `JudgmentRequest` call sites | Grep across worktree — all existing constructions use `scenario_id` / `payload` only; default `None` preserves compatibility |
| Tests (fresh run) | `pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q` → 144 passed |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`src/praetor/judgment/provider.py:49-51`** — Docstring placed after `evidence_bundle` field is a discarded class-body string literal, not a field docstring. Move to a `#` comment or `field(metadata=...)` if documentation is needed at runtime.

2. **`tests/engine/test_agentic_request_evidence_bundle_wiring.py:50-51`** — Asserts `facts` equality, not `is bundle`. Sufficient for this task because `_resolve_intake_evidence_bundle` returns the caller-supplied object when `evidence_bundle=` is set; identity assertion would be slightly stronger.

3. **`tests/engine/test_agentic_request_evidence_bundle_wiring.py`** — File is untracked (`??`); expected per standing order not to commit.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `JudgmentRequest.evidence_bundle` defaults to `None`, backward compatible | Met — dataclass field with default; `test_judgment_request_evidence_bundle_defaults_to_none` passes; all existing `JudgmentRequest(scenario_id=...)` sites unchanged |
| `process_alert_intake` passes resolved `EvidenceBundle` on `JudgmentRequest` | Met — `evidence_bundle=resolved_bundle` at orchestrator construction site after `assert resolved_bundle is not None` |
| Existing judgment/engine tests remain green | Met — 144 passed in scoped pytest run |
| Single-shot path unchanged | Met — no edits to `FakeProvider`, `VertexProvider`, or provider retry/latency helpers; field documented as unused by single-shot providers |
| PolicyGate evaluation logic untouched | Met — no `src/praetor/policy/` content diff; `evaluate_policy_gate(...)` call site and arguments unchanged |
| Files allowed only | Met — changes confined to plan allow-list + workflow artifacts |

---

## Correctness / security / simplicity

- **Wiring correctness:** `resolved_bundle` is the same object used for excerpt building, citation validation, and policy-gate evaluation; threading it into `JudgmentRequest` is the correct single source of truth for agentic providers.
- **Early-exit paths:** Correlation failure, config over-budget, and provider-fault paths never construct `JudgmentRequest` — unchanged and correct.
- **Request passthrough:** `call_provider_with_latency_tracking` → `call_provider_with_retries` forwards the `JudgmentRequest` unchanged.
- **Security:** No new deserialization, injection, or permission surface; optional typed reference only.
- **Simplicity:** Minimal 3-line production diff; no duplicate bundle resolution or policy coupling.

---

## Summary

Implementation matches plan Task 4. Optional field is backward compatible, orchestrator wires the resolved bundle at the sole intake provider call site, and PolicyGate remains untouched. Proceed to skeptic verification.
