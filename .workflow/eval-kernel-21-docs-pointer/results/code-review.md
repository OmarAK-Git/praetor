# Code review — eval-kernel-21-docs-pointer (Task 21)

**Verdict:** approve

**Reviewer:** code-reviewer (fresh context)
**Scope:** Task 21 only (docs pointer: eval_gates + memory-bank). Sprint 1 gate ignored.
**Diff reviewed:** commit `c4191ab` (`docs/eval_gates.md`, `memory-bank/activeContext.md`, `memory-bank/tasks.md`, `tests/docs/test_eval_kernel_pointer.py`). Implementer result: `.workflow/eval-kernel-21-docs-pointer/results/implementer-result.md`.

**Spec / plan used:**
- `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` Task 21 (through commit, before Self-review)
- `.workflow/eval-kernel-21-docs-pointer/packets/code-reviewer.md`
- `.workflow/eval-kernel-21-docs-pointer/plan.md` acceptance and `files_allowed`
- `.workflow/eval-kernel-21-docs-pointer/results/implementer-result.md`

## Blocking findings

None.

## Confirmations (packet)

| Required pin | Result |
|---|---|
| `docs/eval_gates.md` points at the Sprint 1 plan and `eval-kernel.yml` | **Confirmed.** New section `## Sprint 1 eval kernel (gating, FakeProvider)` after the capability-spike Non-gating section. Contains `2026-09-07-eval-kernel-sprint1.md`, `.github/workflows/eval-kernel.yml`, `FakeProvider`, and `cite-to-subject`. Relative links resolve to existing SoT files. |
| memory-bank current-focus / next-up contain `2026-09-07-eval-kernel-sprint1.md` | **Confirmed.** `activeContext.md` Current focus leads with the prescribed 2026-09-07 paragraph (plan path + FakeProvider workflow + cite-to-subject + Sprint 3 CBC retire). `tasks.md` adds the prescribed **Also queued** paragraph immediately under the existing **Next up** CBC block. |
| CBC queue items are NOT fully retired | **Confirmed.** CBC AlertEnvelope-spike lines remain in Current focus (`2026-09-02` spike-spec items) and **Next up** (`adapter remains rejected`; retire waits). Follow-on AlertEnvelope-population spike row in `tasks.md` is intact. `memory-bank/progress.md` untouched (still records CBC as not retired). No CBC item marked retired/done by this commit. |
| OM / capability-spike text was not deleted | **Confirmed.** `## Non-gating: judgment capability spike` is intact (`capability_spike` CLI, `PRAETOR_CAPABILITY_SPIKE=1`, Path A/B scoring, 2026-08-01 design pointer). Outcome Matrix mentions in eval harness / phase-gate sections unchanged. The only eval_gates “deletion” is adding a newline after the preserved spike design line. |
| SoT spec/plan under `docs/superpowers` were not rewritten | **Confirmed.** `c4191ab` does not touch `docs/superpowers/**`. Working tree has no SoT edits. Plan (`2026-09-07-eval-kernel-sprint1.md`) and design (`2026-09-06-eval-kernel-judgment-readiness-design.md`) exist and were not rewritten. |
| Files stayed in allowed scope | **Confirmed.** `c4191ab` is 4 files / +52 −1, all in Task 21 Files + `files_allowed`: `docs/eval_gates.md`, `memory-bank/activeContext.md`, `memory-bank/tasks.md`, `tests/docs/test_eval_kernel_pointer.py`. No `src/`, no workflow YAML, no queue `done`, no `progress.md` rewrite (allowed but not required; plan Files list omits it). |

## Checks

| Check | Result |
|---|---|
| eval_gates append vs Task 21 Step 3 snippet | New section matches the approved markdown (heading, plan/design links, What it gates / does not prove, CI powershell, notebook/Vertex caveat). |
| activeContext insert | Prescribed paragraph inserted at top of Current focus. Pre-existing 2026-09-19 drain line and CBC 2026-09-02 lines retained. |
| tasks.md insert | Prescribed **Also queued** block sits directly under the Next up CBC paragraph. CBC lines not deleted. |
| Prescribed tests vs Step 1 | `tests/docs/test_eval_kernel_pointer.py` matches the plan test bodies (REPO parents[2], four eval_gates pins, two memory-bank pins). |
| Extra product scope | None. Pointers only. |
| Verification (this review) | `pytest tests/docs/test_eval_kernel_pointer.py -q` → 2 passed in 0.02s. |

## Findings

### Critical

None.

### Important

None.

### Minor

1. **Pointer tests are substring-only** (`tests/docs/test_eval_kernel_pointer.py:8-20`). The prescribed tests would still pass if the required strings lived anywhere in those files, including a comment. Inspection shows they sit in the approved sections. Track only; do not expand beyond the plan.

2. **`docs/eval_gates.md` still has no trailing newline** (pre-existing; commit preserved the style). Not a Task 21 acceptance miss.

3. **`memory-bank/progress.md` still says next is Task 21 and CBC retire “waits for Task 21 / Sprint 3”.** That file is in workflow `files_allowed` but not in the Sprint 1 Task 21 Files list; implementer correctly left it alone. Sprint 3 still owns CBC retire.

## Verdict rationale

Task 21 is pointers only. `c4191ab` appends the approved eval_gates section, inserts the prescribed Current focus and Next up lines, and lands the exact TDD guard. CBC AlertEnvelope-spike queue text is not retired. OM / capability-spike prose is preserved. SoT under `docs/superpowers` is untouched. No `files_allowed` breach. **approve**.
