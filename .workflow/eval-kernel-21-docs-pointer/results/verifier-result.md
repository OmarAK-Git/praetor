# Verifier result — eval-kernel-21-docs-pointer (Task 21)

## Outcome

**pass**

Task-scoped verification only. Sprint 1 / phase-exit gaps ignored.

Claim restated: Task 21 is done — `docs/eval_gates.md` points at the Sprint 1 plan and `eval-kernel.yml`; memory-bank Current focus / Next up point at that plan instead of CBC AlertEnvelope spike as the next authorized step; CBC queue items are not fully retired.

Implementer results (`2 passed`, commit `c4191ab`, “did not retire CBC / did not rewrite spec or plan”) were treated as unevidenced until re-run and re-read this session.

Skeptic verdict on the completion claim: **survives**.

## Acceptance criteria

| Criterion | Verdict | Evidence |
|---|---|---|
| `docs/eval_gates.md` points at the Sprint 1 plan and the new workflow | **met** | Live file `docs/eval_gates.md:210-233` is the prescribed `## Sprint 1 eval kernel (gating, FakeProvider)` section, appended after `## Non-gating: judgment capability spike` (`:192-208`). Contains `2026-09-07-eval-kernel-sprint1.md` (`:212`), `.github/workflows/eval-kernel.yml` (`:219`), `FakeProvider` (`:210`, `:219`), and `cite-to-subject` (`:223-224`). Relative links resolve under `docs/superpowers/`. |
| memory-bank current-focus / next-up point here instead of CBC AlertEnvelope spike as the next authorized step | **met** | `memory-bank/activeContext.md:5` is the prescribed 2026-09-07 paragraph at the top of Current focus (plan path + FakeProvider workflow + cite-to-subject + Sprint 3 CBC retire). `memory-bank/tasks.md:50-58` Next up leads with the eval-kernel Sprint 1 drain, then the prescribed **Also queued** paragraph naming `2026-09-07-eval-kernel-sprint1.md`. CBC is deferred, not the leading authorized next. |
| CBC queue items are not fully retired (Sprint 3) | **met** | CBC AlertEnvelope-spike lines remain: Current focus `activeContext.md:9-11` (2026-09-02 spike-spec “Next” / “Authorized next”); Next up `tasks.md:52-54` (adapter remains **rejected**; retire waits); follow-on AlertEnvelope-population spike `tasks.md:154`. `memory-bank/progress.md` untouched (`:8` retire waits; `:16` still records CBC as next authorized on 2026-09-02). Commit `c4191ab` is insert-only on those memory-bank files. |
| Verifier checks only Task 21 acceptance, not Sprint 1 gate completion | **met** | Commands limited to the packet pytest. No Sprint 1 gate, no full harness, no phase-exit. |

## Commands run

| Command | Exit code | Summary |
|---|---|---|
| `pytest tests/docs/test_eval_kernel_pointer.py -q` | **0** | `..` — 2 passed in 0.02s (no skips) |

Re-run in this session against `C:\Users\oalan\Praetor` working tree. Implementer transcript was not treated as evidence.

Pytest duration (0.02s) is consistent with two UTF-8 file reads, not a skipped or mocked suite. Count is from the live `-q` run. Both tests read live paths via `Path(__file__).resolve().parents[2]` (`tests/docs/test_eval_kernel_pointer.py:5-20`).

## Manual checks

| Check | Verdict | Evidence |
|---|---|---|
| `eval_gates` contains `2026-09-07-eval-kernel-sprint1.md`, `eval-kernel.yml`, `FakeProvider`, `cite-to-subject` | **met** | Confirmed in `docs/eval_gates.md:210-224` (not only via pytest). |
| `activeContext.md` and `tasks.md` both contain `2026-09-07-eval-kernel-sprint1.md` | **met** | `activeContext.md:5`; `tasks.md:57`. |
| CBC AlertEnvelope-spike items still exist in memory-bank | **met** | `activeContext.md:5,9-11`; `tasks.md:52-54,58,154`; `progress.md:8,16`. None marked retired/done by `c4191ab`. |
| `docs/superpowers` spec/plan not rewritten | **met** | `git show --name-only c4191ab` lists only `docs/eval_gates.md`, `memory-bank/activeContext.md`, `memory-bank/tasks.md`, `tests/docs/test_eval_kernel_pointer.py`. Empty pathspec for `docs/superpowers`. Working tree clean for `docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md` and `docs/superpowers/specs/2026-09-06-eval-kernel-judgment-readiness-design.md`. Last SoT touch remains `db5d196` (demo-honesty scan exclude; earlier sprint, not this task). |
| OM / capability-spike text not deleted | **met** | `## Non-gating: judgment capability spike` intact at `docs/eval_gates.md:192-208` (`capability_spike` CLI, `PRAETOR_CAPABILITY_SPIKE=1`, Path A/B scoring, 2026-08-01 design pointer). Diff of `c4191ab` on `eval_gates.md` is append-after-spike plus a trailing newline after the preserved design line. Outcome Matrix prose earlier in the file is untouched. |

## Independent probes (not in packet)

- `c4191ab` (`docs: point eval_gates and memory-bank at Sprint 1 eval-kernel plan`) is 4 files / +52 −1. The single deletion is the pre-existing missing newline at EOF of `eval_gates.md`; spike design line is kept. Working tree `git diff HEAD` is empty for the four product files.
- Appended eval_gates section matches Task 21 Step 3 snippet (`docs/superpowers/plans/2026-09-07-eval-kernel-sprint1.md:3550-3574`).
- `tests/docs/test_eval_kernel_pointer.py` matches Task 21 Step 1 test bodies (`:3518-3538`): `REPO` parents[2], four eval_gates pins, two memory-bank pins.
- `activeContext.md` insert and `tasks.md` **Also queued** block match Step 3 wording (`:3577-3588`). CBC lines were not deleted.
- Queue item `eval-kernel-21-docs-pointer` in `.workflow/autopilot-queue.json` is still `in_progress` (implementer packet: do not mark done). Not a Task 21 product AC.

## Gaps

None that fail Task 21 acceptance.

Residual (non-blocking, not Task 21 AC failures):

- Pointer tests are substring-only (`tests/docs/test_eval_kernel_pointer.py:8-20`). A comment-only copy of the needles would satisfy the prescribed tests. Inspection this session found the strings in the approved sections. Track only; do not expand beyond the plan.
- `memory-bank/progress.md` still says next is Task 21 (`:7`) and records CBC as “Next authorized” under the 2026-09-02 heading (`:16`). That file is in workflow `files_allowed` but not in the Sprint 1 Task 21 Files list; leaving it alone is correct. Sprint 3 still owns CBC retire.
- Current focus still carries the Task 20 drain line “Next runnable: `eval-kernel-21-docs-pointer`” (`activeContext.md:7`) and dated 2026-09-02 CBC “Authorized next” lines (`:9-11`). Task 21 required inserting one prescribed line and not deleting CBC lines; it did not require rewriting older status sentences.

Queue item status was not updated (implementer packet: do not mark done).
