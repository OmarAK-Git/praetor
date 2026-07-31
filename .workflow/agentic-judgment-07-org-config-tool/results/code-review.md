# Code review — agentic-judgment-07-org-config-tool

**Reviewer:** code-reviewer (fresh context)  
**Scope:** Task 7 — `OrgConfigSectionTool` (non-evidentiary `org_config_refs` path)  
**Spec:** `.workflow/agentic-judgment-07-org-config-tool/plan.md`  
**Design:** `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` (tool table, org-config non-evidentiary boundary, DEC-064 corroboration narrowing)

## Verdict: **PASS**

Remediation required before verification: **No**

---

## What was reviewed

| Area | Evidence |
|------|----------|
| Production | `src/praetor/judgment/agentic/tools.py` — `OrgConfigSectionTool` + `OrgConfigSectionResult` (untracked; appended to Task 6 file) |
| Tests | `tests/judgment/agentic/test_tools.py` — two new org-config tests (untracked; appended to Task 6 file) |
| Diff baseline | Matches Task 7 Step 3 in `docs/superpowers/plans/2026-07-30-agentic-judgment.md` verbatim |
| Tests (fresh run) | `pytest tests/judgment/agentic/test_tools.py -v` → **9 passed** in 0.66s |
| Lint/type | `ruff check` and `mypy` on scoped paths — clean |
| Return-type probe | `invoke({"section_name": "containment_policy"})` → `OrgConfigSectionResult`, `hasattr(result, "facts")` is **False**, `isinstance(result, ToolResult)` is **False** |
| PolicyGate / provider | No changes outside `files_allowed` |

---

## Focus-area review

### 1. Non-evidentiary boundary (no EvidenceFacts / corroboration path) — PASS

`OrgConfigSectionTool.invoke` returns `OrgConfigSectionResult` (`tools.py:141-162`), not `ToolResult`. The result dataclass (`tools.py:37-44`) exposes only `section_name`, `content`, `succeeded`, `error` — no `facts` field and no `EvidenceFact` import on this code path.

Docstring (`tools.py:133-136`) states findings inform `ModelJudgment.org_config_refs`, never `cited_evidence_refs`, and org-config content is not corroboration-eligible — aligned with design spec lines 99–100.

No `provenance_path`, no `EvidenceFact(...)` construction, no registry `record_evidence` wiring in this task (deferred to Task 11/12 per plan).

### 2. Section allowlist / content serialization — PASS

Unknown or non-`str` `section_name` → failed `OrgConfigSectionResult` with empty `content` and descriptive `error` (`tools.py:142-152`). Validation uses `ORG_CONFIG_SNAPSHOT_HASH_KEYS` from `praetor.hashing.domains` — the canonical binding-body key set excluding `snapshot_hash` (`domains.py:26-47`).

Known sections serialize via `BaseModel.model_dump_json()` or `json.dumps(..., sort_keys=True)` (`tools.py:153-157`). Matches prescribed plan Step 3.

`test_org_config_section_tool_returns_requested_section` exercises `containment_policy` with non-empty content. `test_org_config_section_tool_rejects_unknown_section` asserts `succeeded is False` and `content == ""`.

### 3. OrgConfigCallRecord recordability — PASS (structural)

`OrgConfigCallRecord` (`registry.py:38-48`) fields: `section_name`, `content`, `succeeded`, `error` plus call metadata (`source`, `tool_name`, `query`). Task 11 `run_org_config_source` maps tool result fields directly (`plan.md:2106-2114`). Field names and types align; no adapter needed.

Registry separation test (`test_registry.py:56-79`) confirms org-config entries do not populate `registry.facts`. No dedicated tool→record construction test in Task 7 scope (plan Step 1 lists only two tests).

### 4. Scope / untouched paths — PASS

Changes confined to `files_allowed`. Fixture uses `preflight_path(EXAMPLE_CONFIG)` per plan fallback when `minimal_org_config_snapshot` is absent. PolicyGate and single-shot provider paths untouched.

---

## Findings

### Critical

None.

### Important

None.

### Minor (non-blocking)

1. **`tests/judgment/agentic/test_tools.py`** — No explicit assertion that `OrgConfigSectionResult` lacks a `.facts` attribute or is not a `ToolResult` subclass. Type separation is enforced by implementation and mypy; plan's placeholder marker was correctly removed per Step 1 instructions.

2. **`tests/judgment/agentic/test_tools.py`** — No test constructing `OrgConfigCallRecord` from a live `tool.invoke` result (registry Task 2 covers `OrgConfigCallRecord` storage separately).

3. **`tests/judgment/agentic/test_tools.py`** — Invalid/missing `section_name` type handling (`tools.py:143-145`) is untested (e.g. `{}` → `section_name="None"` in error result).

4. **`tests/judgment/agentic/test_tools.py`** — `snapshot_hash` exclusion from `ORG_CONFIG_SNAPSHOT_HASH_KEYS` is implied but not explicitly tested.

5. **`tests/judgment/agentic/test_tools.py:195`** — Success test checks `content != ""` only; does not assert JSON shape or section-specific fields.

---

## Spec compliance

| Acceptance criterion | Status |
|---------------------|--------|
| `OrgConfigSectionTool` returns section text for named sections without producing `EvidenceFacts` | Met — `OrgConfigSectionResult` only; no facts field or `EvidenceFact` construction |
| Tool results recordable as `OrgConfigCallRecord` entries | Met structurally — field mapping matches Task 11 wiring |
| Focused tools tests pass | Met — 9/9 pytest, ruff, mypy |
| Must not feed corroboration / `cited_evidence_refs` | Met — separate result type; no provenance path; design-aligned |
| Files allowed only | Met |
| PolicyGate / single-shot provider untouched | Met |

---

## Correctness / security / simplicity

- **Correctness:** Allowlist checked before `getattr(self.snapshot, section_name)`. `ORG_CONFIG_SNAPSHOT_HASH_KEYS` is kept in sync with `OrgConfigSnapshot` binding body per `docs/contracts.md`.
- **Security:** `section_name` is allowlist-gated; no user-controlled attribute access outside hash keys. Serialized output is config data, not prompt injection into evidence paths.
- **Simplicity:** Implementation is plan-prescribed verbatim; no duplicate org-config fetch helpers. Reuses existing `OrgConfigSectionResult` stub from Task 6.

---

## Summary

Task 7 implementation matches the approved plan and design boundary: org-config section fetches are non-evidentiary, never enter the corroboration or `EvidenceFact` path, and map cleanly to `OrgConfigCallRecord`. Minor test gaps do not block verification. Proceed to skeptic verification.
