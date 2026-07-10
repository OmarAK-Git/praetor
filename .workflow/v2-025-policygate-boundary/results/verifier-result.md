# Verifier Result — V2-025 All Containment Through PolicyGate

## Outcome

**pass** (with 2 advisory notes; none block acceptance)

Scope: V2-025 acceptance criteria only. V2 Gate 4 exit was NOT evaluated (AC4).

## Method

Treated all implementer claims as unevidenced. Re-ran commands fresh, re-read
all changed source, and independently exercised the guard machinery against
synthetic and real inputs to disprove vacuity. Did not modify any repo/git state.

## Fresh verification evidence

### Verification command (fresh run)

```text
python -m pytest tests/contracts/ tests/policy/ -q
128 passed in 11.76s
```

Matches implementer's claimed `128 passed`.

### New test files execute (not skipped)

```text
python -m pytest tests/contracts/test_policygate_boundary_guard.py \
                 tests/policy/test_policygate_containment_boundary.py -v
8 passed  (4 guard + 4 integration)
```

## Acceptance criteria

### AC1 — No production caller authorizes account/host containment via lower eligibility helpers directly → SURVIVES

- Independent grep over `src/`: `evaluate_account_containment_eligibility` is
  *called* only at `src/praetor/policy/gate.py:372`; `meets_host_cited_corroboration`
  only at `src/praetor/policy/gate.py:354`. All other src hits are the definition
  (`identity.py`, `provenance.py`) or a re-export (`policy/__init__.py`), not calls.
- Ran the real collector: `collect_unauthorized_containment_helper_calls()` →
  `{'evaluate_account_containment_eligibility': [], 'meets_host_cited_corroboration': []}`.
- Checked adjacent lower helpers (`meets_account_corroboration`, `is_sid_backed`):
  used inside `containment_policy.resolve_containment_target`, which is called
  ONLY from `gate.py:340` (target resolution within the gate flow, not a separate
  authorization path). `resolve_account_target` has no production caller. No bypass.

### AC2 — Static guard catches direct calls outside approved tests/policy code → SURVIVES

Proved the guard is non-vacuous (not merely passing on an empty world):

- `_find_direct_helper_calls("...evaluate_account_containment_eligibility(a,b)...")`
  → `[2]` (detects a direct name call).
- `collect_unauthorized_test_containment_helper_calls()` returns 10 real hits
  (9 account + 1 host) matching `KNOWN_LEGACY_TEST_HELPER_CALLS` exactly.
- `assert_test_containment_helper_calls_are_approved()` **raises** on those real
  violations — confirming the assert-on-nonempty path genuinely fires.
- Stable-set test (`test_non_approved_test_helper_calls_are_stable_legacy_set`)
  fails on both new and removed violations, so new unauthorized test callers are caught.

### AC3 — Integration tests prove the feature gate cannot be bypassed → SURVIVES

Tests are meaningful, not gamed:

- `test_direct_eligibility_signals_auto_contain_without_feature_gate`: eligibility
  helper returns `authorized=True`/`AUTO_CONTAIN` (i.e. a direct bypass WOULD contain).
- `test_policy_gate_blocks_bypass_of_account_containment_disabled`: same
  `account_bundle()` through `evaluate_policy_gate` with the default snapshot
  escalates with exactly `[ACCOUNT_CONTAINMENT_DISABLED]`, directive `None`.
- `test_policy_gate_authorizes_when_feature_gate_enabled`: flipping only
  `account_auto_contain_enabled=True` yields `AUTO_CONTAIN` + a directive. The
  paired off/on cases prove the feature gate is the sole blocker and lives in the gate.
- `test_host_corroboration_helper_alone_does_not_authorize_containment`: helper
  returns `True`, but the gate escalates `INSUFFICIENT_CORROBORATION` when citations
  are incomplete. Verified the default `org_snapshot` has the flag off (otherwise
  the disabled-path assertion could not pass).

### AC4 — Verifier checks only V2-025, not V2 Gate 4 → HONORED

Only the scoped `tests/contracts/ tests/policy/` command was run. No gate-exit evaluation.

## Advisory notes (do not block acceptance)

1. **Attribute-style calls evade the AST guard.** `_find_direct_helper_calls`
   matches only `ast.Call` with `func` an `ast.Name`. A call written as
   `module.evaluate_account_containment_eligibility(...)` is NOT detected
   (verified: attr-call → `[]`). AC2 is scoped to "direct calls," and the
   idiomatic `from ... import <helper>` pattern IS caught, so this is a known
   limitation rather than a criterion failure. Consider also matching
   `ast.Attribute` targets to fully close the boundary.
2. **`repo_root` parameter is only usable for the real repo.** The collectors
   accept `repo_root`, but `_relative_repo_path` computes against the hardcoded
   `_repo_root()` (`parents[3]`), so passing any other root raises
   `ValueError: ... not in the subpath of ...`. Harmless today (tests pass the
   real `REPO_ROOT`), but the parameter is effectively non-functional/misleading.

## Verdict

The completion claim **survives** adversarial verification. All four task-scoped
acceptance criteria hold with fresh, independently reproduced evidence. The two
advisory items are hardening opportunities, not violations of the stated criteria.
