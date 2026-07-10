# Verifier Result — V2-023 Contract Scope Guard and Generated Artifact Hygiene

## Verdict: **survives**

The three task claims hold under independent verification. I gathered my own
evidence (ran the suite, exercised the CLI and library directly, enumerated the
real package tree) rather than trusting the implementer transcript.

## Claims restated and tested

### Claim 1 — "scope guard allowlist strict" — SURVIVES
- `test_only_expected_top_level_packages` asserts `children == ALLOWED_PACKAGES`
  (exact set equality, not subset), so both unexpected and missing packages fail.
- Independently listed `src/praetor` dirs: the 19 real packages (`alerts` …
  `tickets`) match `ALLOWED_PACKAGES` exactly. The `startswith("_")` filter only
  excludes `__pycache__`, which is legitimate.
- Caveat (does not refute claim): `test_docs_changes_limited_to_sanctioned_v2_paths`
  uses `git diff --name-only docs/` — unstaged, tracked files only. It will not
  catch **staged** or **untracked/new** docs additions. The path allowlist itself
  is exact and correct, but the git-diff enforcement is narrower than "strict"
  implies. `test_spec_md_not_sanctioned_doc` is a tautology (asserts a literal set
  lacks a string never added); harmless but non-load-bearing.

### Claim 2 — "generated schema artifacts deterministic" — SURVIVES
- `test_schema_export_is_byte_stable`: two exports produce identical bytes
  (`json.dumps(sort_keys=True, indent=2, ensure_ascii=True)` + trailing newline).
- `test_committed_schemas_match_export`: committed `schemas/` bytes equal a fresh
  export for all 14 files.
- Independently confirmed via `--write` to a scratch dir: 14 files produced, all
  byte-identical to committed (`diffs=[]`).

### Claim 3 — "generators expose --check and --write" — SURVIVES
- `--help` advertises both flags (mutually exclusive, `required=True` group).
- `--check` (default schemas-dir) exits 0 in sync: confirmed directly (exit 0).
- Drift negative paths confirmed by me (not covered by any CLI test):
  - missing files → 14 mismatches, `main(--check)` returns non-zero.
  - one-byte content mutation → `schema drift: …`, `main(--check)` returns 1.
  - `--write` returns 0 and writes correct artifacts.

## Evidence
- `pytest tests/contracts/test_scope_guard.py -q` → `9 passed in 0.98s`.
- `python tools/schema_export.py --check` → exit 0.
- Direct calls: `check_schemas` (missing case = 14; content-drift `main` rc=1),
  `main(['--write',...])` rc=0 with 0 diffs vs committed.
- `src/praetor` dir enumeration vs `ALLOWED_PACKAGES` → exact match (19 packages).

## Non-blocking defects found (do not refute the three claims)
1. **`check_schemas` crashes on out-of-repo schemas-dir when a file is missing.**
   `committed_path.relative_to(REPO_ROOT)` (schema_export.py:26) raises
   `ValueError` if `--schemas-dir` is outside `REPO_ROOT` and a schema is absent.
   The error-message path assumes the committed path is under the repo. Default
   usage is unaffected (default dir is `REPO_ROOT/schemas`), and no test exercises
   this, so it does not touch the task claims — but it is a latent bug in the new
   generator.
2. Drift/negative CLI paths and `--write` correctness are **untested** by the
   committed suite; I verified them manually. Recommend adding a drift-detection
   and `--write` round-trip test.

## Scope
Task-scoped only. Did not run V2 Gate 3 exit. No files modified; all Bash use was
read-only evidence gathering (scratch dirs created under a temp path were removed).
