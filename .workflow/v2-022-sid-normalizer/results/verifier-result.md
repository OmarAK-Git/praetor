# Verifier Result — V2-022 SID and Normalizer Conformance

**verdict:** survives
**verifier_role:** skeptic-verifier (adversarial, independent evidence)
**scope:** task-scoped only (V2-022); V2 Gate 3 exit not run

## Claim under test

Implementer claims the three goal criteria are met and `pytest tests/evidence/ tests/correlation/ -q` yields `105 passed` (exit 0):
1. SID validation vectors or documented waiver.
2. Malformed domain-separator accounts set `ambiguity_flag=true` in test helpers.
3. Existing Sysmon and Security behavior stays pinned.

## Evidence gathered

### Verification command (reproduced independently)
```
pytest tests/evidence/ tests/correlation/ -q  ->  105 passed in 0.75s (exit 0)
```
Matches implementer claim exactly. The 25 task-relevant tests were run in isolation with `-v -p no:cacheprovider` and all **collected and PASSED — none skipped/xfailed**.

### Criterion 1 — SID vectors + waiver (SURVIVES)
- `src/praetor/policy/identity.py:39-42` `is_valid_sid_format` uses `WINDOWS_SID_PATTERN = ^S-1-5(?:-\d+)+$` (IGNORECASE, identity.py:21).
- Pattern is byte-for-byte identical to the ContainmentDirective validator `_SID_PATTERN` (`contracts/containment.py:17`) and `config/live.py:14` — parity claim confirmed.
- `tests/evidence/test_sid_format.py` pins 3 valid + 7 invalid vectors. Invalid set genuinely discriminates: `S-1-5`, `S-1-5-`, `not-a-sid`, `DOMAIN\jdoe`, `S-1-5-21-not-numeric`, empty, whitespace all rejected; these are real assertions, not tautologies.
- DEC-062 waiver recorded in `memory-bank/decisions.md:68`; `is_sid_backed` (identity.py:45-47) is presence-only and tests pin that a malformed-but-nonempty SID is accepted while empty/whitespace is rejected.

### Criterion 2 — domain-separator ambiguity helper (SURVIVES)
- `correlation/normalizer_conformance.py:19-30` `require_domain_separator_ambiguity_flag` raises `AssertionError` when `malformed_domain_separator_ambiguity(account_repr)` is True and `ambiguity_flag` is False.
- Helper vectors pinned (`CORP\jdoe`→False, ``→False, `jdoe`→True, `jdoe@corp.example`→True); raise-path exercised by `test_require_domain_separator_ambiguity_flag_raises_on_malformed`.
- DEC-063 (`memory-bank/decisions.md:69`) records the forward requirement for future normalizers.

### Criterion 3 — Sysmon/Security pinned (SURVIVES)
- `sysmon.py:121` now delegates to the shared helper; `_sysmon_ambiguity_flag` behavior verified equivalent.
- **Regression-guard check:** `tests/fixtures/sysmon/ambiguous_user.json` has `User: "jdoe"` (no separator) AND a populated `ParentProcessGuid`, so the second ambiguity branch (`parent_image and not parent_process_guid`) is False. The asserted `ambiguity_flag is True` is therefore driven **solely** by the domain-separator branch — if that helper regressed, the test would flip to False and fail. Genuine guard, not gamed by an unrelated branch.
- Security pin (`test_security_logon_behavior_unchanged`) asserts `ambiguity_flag False`, `account_name=jdoe`, `domain=CORP`, `target_sid` starts `S-1-5-21-`; fixture `security/successful_logon_4624.json` matches.

## Attempts to refute (all failed)
- Tests skipped/not running new code? No — 25/25 collected + passed under verbose, cache disabled.
- Malformed-user test passing via an unrelated branch? No — parent branch is inactive in that fixture (see above).
- SID pattern inconsistent with directive validator? No — identical regex in all three modules.
- Waiver undocumented? No — DEC-062/DEC-063 present in `memory-bank/decisions.md`.

## Residual notes (non-blocking; do NOT affect verdict)
- `is_valid_sid_format` docstring claims it is "exposed for directive emission," but directive emission (`contracts/containment.py:69`) uses its own local `_SID_PATTERN`, not this function. The new function is currently exercised only by tests. Aspirational wording; outside the stated goal.
- `docs/decisions.md` not updated (write-scope limitation acknowledged by implementer); waiver lives only in `memory-bank/decisions.md`. Acceptable for "documented waiver."

## Verdict
**survives** — all three goal criteria are backed by independently reproduced, non-gamed test evidence; the verification command result (`105 passed`, exit 0) is confirmed.
