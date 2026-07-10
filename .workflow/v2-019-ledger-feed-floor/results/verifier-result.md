# Skeptic-Verifier Result — V2-019 Ledger Tip Anchor and Feed Floor Hardening

verifier_model: skeptic-verifier (independent context)
verdict: **survives**
scope: V2-019 acceptance criteria only (not V2 Gate 3 exit)

## Claim Under Test

Implementer claims V2-019 is complete: runbook documents tail-truncation + out-of-band
tip-anchor procedure; optional `verify_ledger_tip_against_anchor` hook added; feed exporter
exposes `reconcile_feed_metadata_against_jsonl` and reconciles the metadata floor against
the on-disk JSONL, marking stale metadata unhealthy; `pytest tests/ledger/ tests/revocation/`
reports 62 passed.

## Evidence Gathered (independent)

**Test run (reproduced myself, not trusted from transcript):**

```text
$ python -m pytest tests/ledger/ tests/revocation/ -q
..............................................................           [100%]
62 passed in 6.59s   (exit 0)
```

All dots — no skips, xfails, or errors. Matches the claimed 62 passed.

**AC1 — runbook + contracts documentation (verified present, substantive):**
- `docs/operator_runbook.md:98-120` — §"Ledger tail truncation and tip anchor (AG-0027)":
  states the hash chain cannot detect tail truncation, gives a 4-step out-of-band
  tip-anchor procedure (record/store/verify/mismatch-response), and states the hook is optional.
- `docs/contracts.md:379-384` — §7a optional tip anchor hook signature.
- `docs/contracts.md:422-424` — §8.3 metadata floor reconciliation (names
  `reconcile_feed_metadata_against_jsonl`, missing/empty/truncated → unhealthy, floor 0 on fresh DB).

**AC2 — optional tip-anchor hook (verified correct + genuinely tested):**
- `src/praetor/ledger/tip_anchor.py:15-29` — returns early when `expected_tip_hash is None`
  (optional), else compares `fetch_ledger_tip_hash` and raises `LedgerTipAnchorMismatchError`
  (subclass of `LedgerChainIntegrityError`).
- Exported: `src/praetor/ledger/__init__.py:19-52`.
- `tests/ledger/test_tip_anchor.py` — 5 tests exercise skip/match/mismatch/subclass/empty-ledger
  paths; assertions bind to real behavior (mismatch message, exception type).

**AC3 — feed metadata floor reconciliation (verified core logic, not a no-op):**
- `src/praetor/revocation/exporter.py:197-212` — `reconcile_feed_metadata_against_jsonl`
  delegates to `validate_feed_file_prefix`; on `FeedPrefixIntegrityError` marks feed unhealthy
  and returns `False`.
- `src/praetor/revocation/feed.py:144-164` — `validate_feed_file_prefix` genuinely reconciles:
  raises when file missing/empty while `last_verified_exported_sequence > 0`, and when
  `last_verified > on_disk_highest` (truncation). Not a stub.
- Called before export drain: `export_next_pending_row` top (`exporter.py:288`) and
  `run_feed_startup_hook` before building the sink (`exporter.py:396`). Ordering claim holds.
- `tests/revocation/test_feed_exporter.py:485-528` — 3 new tests (fresh-DB floor 0,
  stale-metadata→unhealthy+alert, startup-reconciles-before-export).

**Anti-gaming check on the load-bearing new test.** `test_reconcile_marks_unhealthy_on_stale_metadata`
marks seq 1 exported then reconciles with no file present. If `mark_feed_row_exported` did not
advance the floor, `last_verified` would be 0 and reconcile would return `True` (no file, floor 0
is legal), failing the `assert not reconcile_feed_metadata_against_jsonl(...)`. It passes, so the
floor genuinely advanced and reconcile genuinely detected the physical/metadata divergence. Not gamed.

**AC4 — verifier scope.** This verification checked only V2-019 acceptance; no V2 Gate 3 /
sprint-exit checks were run. Implementer packet gates (queue not marked done, gate/sprint exit
not run) are respected.

## Attempts to Refute (all failed)

- Reconcile suspected to be a rename-only no-op → refuted: `validate_feed_file_prefix` contains
  real missing/empty/truncated detection (`feed.py:144-164`).
- New tests suspected to pass without exercising new code → refuted: imports resolve to the new
  symbols; the stale-metadata test is falsifiable as shown above.
- Suspected hidden skips inflating the count → refuted: raw output is 62 dots, exit 0.

## Observations (non-blocking, outside this task's changes)

- `docs/decisions.md` and `docs/proposals/delivery_backlog.md` show as modified in the working
  tree but contain **no** V2-019 references (grep returned nothing) and are **not** in this task's
  disclosed "Files Changed". They are pre-existing dirty state from earlier work, not attributable
  to V2-019 — not a scope violation by this implementer.
- Task-scoped run only; full suite / lint / typecheck not run (correctly out of scope per packet).

## Verdict

**survives.** All four V2-019 acceptance criteria are met by the current code, the reconcile logic
is real and its load-bearing test is not gamed, and the 62-passed result reproduces independently.
