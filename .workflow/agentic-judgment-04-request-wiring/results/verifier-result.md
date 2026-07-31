# Verifier result — agentic-judgment-04-request-wiring

**Verdict: PASS (survives)**

Adversarial skeptic-verify against plan acceptance criteria and focus checks.
Claimant transcripts treated as unevidenced until independently checked.

---

## Claim restated

Task 4 threads an optional `JudgmentRequest.evidence_bundle` (default `None`) and wires `process_alert_intake` to pass the resolved `EvidenceBundle` on that request, without changing PolicyGate / single-shot provider behavior, with judgment+engine tests green.

---

## Evidence gathered (fresh)

### Commands

```text
$env:PYTHONPATH = "C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src"

python -c "from praetor.judgment.provider import JudgmentRequest; r = JudgmentRequest(scenario_id='x'); print(repr(r.evidence_bundle))"
→ None

pytest tests/engine/test_agentic_request_evidence_bundle_wiring.py tests/judgment tests/engine -q
→ 144 passed in 14.21s

ruff check src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py tests/engine/test_agentic_request_evidence_bundle_wiring.py
→ All checks passed!

mypy src/praetor/judgment/provider.py src/praetor/engine/orchestrator.py
→ Success: no issues found in 2 source files

git diff HEAD --ignore-cr-at-eol -- src/praetor/policy/
→ no content hunks (CRLF warnings only; --numstat empty)

git diff HEAD --ignore-cr-at-eol -- src/praetor/judgment/fake_provider.py src/praetor/judgment/vertex_provider.py
→ no content hunks
```

### Focus checks

| Check | Result | Evidence |
|-------|--------|----------|
| Backward compat default `None` | Pass | Live construct `JudgmentRequest(scenario_id="x")` → `evidence_bundle is None`; `test_judgment_request_evidence_bundle_defaults_to_none` present at `tests/judgment/test_provider_failures.py:56-58`; existing `JudgmentRequest(scenario_id=...)` call sites in that file unchanged |
| Orchestrator wiring | Pass | Diff is sole `+ evidence_bundle=resolved_bundle` at `orchestrator.py:370` inside `JudgmentRequest(...)`; new test captures provider request, asserts non-`None` and `facts == bundle.facts` (`test_agentic_request_evidence_bundle_wiring.py:49-51`); `process_intake` delegates to `process_alert_intake` with `evidence_bundle=` (`orchestrator.py:235-245`) |
| PolicyGate untouched | Pass | `git diff HEAD --ignore-cr-at-eol -- src/praetor/policy/` empty of content; orchestrator diff does not touch `evaluate_policy_gate(...)` call (`orchestrator.py:434-442`) |
| FakeProvider / VertexProvider untouched | Pass | No content diff on those files; `generate_judgment` still ignores/uses request without reading `evidence_bundle` |
| Scope vs allow-list (this task's content delta) | Pass | Content delta confined to `provider.py` (+field), `orchestrator.py` (+1 line), `test_provider_failures.py` (+compat test), new untracked wiring test |

### Identity spot-check (stronger than test)

`_resolve_intake_evidence_bundle(correlate=True, evidence_bundle=SKELETON_EVIDENCE_BUNDLE, ...)` returns `(SKELETON_EVIDENCE_BUNDLE, False)` with `b is SKELETON_EVIDENCE_BUNDLE` → True. So for the test's supplied-bundle path, the object on the request is the resolved object; the test's facts-equality assertion is weaker than identity but not false.

---

## Attack angles considered (not refuting)

1. **Weak assertion (`facts ==` not `is`)** — True weakness relative to strongest proof, but resolution path returns the caller-supplied object; acceptance criterion ("passes the resolved EvidenceBundle") is met. Non-blocking gap.
2. **Discarded class-body docstring** after `evidence_bundle` field (`provider.py:50-51`) — style/doc hygiene only; does not break default or typing.
3. **Dirty worktree / many `M` files** — prior sprint/task residue and line-ending noise; task-scoped content diffs match allow-list. Not used to broaden "done" beyond Task 4 criteria.
4. **Stale implementer counts** — re-ran pytest/ruff/mypy; results match claimant (144 passed; lint/type clean).

---

## Gaps (non-blocking)

- Wiring test does not assert `provider.captured[0].evidence_bundle is bundle` (identity).
- Field "docstring" is a discarded string literal, not attached documentation.
- New test file remains untracked (`??`) — expected under standing order not to commit.

---

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| `JudgmentRequest.evidence_bundle` defaults to `None`, backward compatible | Met |
| `process_alert_intake` passes resolved `EvidenceBundle` on `JudgmentRequest` | Met |
| Existing judgment/engine tests remain green | Met (fresh 144 passed) |

**Strongest reason it survives:** Fresh scoped pytest (144), ruff, and mypy are green; the only orchestrator content change is wiring `evidence_bundle=resolved_bundle` onto `JudgmentRequest`; PolicyGate and single-shot providers show no content diffs; default `None` confirmed by live construction.
