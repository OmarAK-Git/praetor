# Verifier result — agentic-judgment-07-org-config-tool

**Verdict:** PASS (claim survives)
**Role:** skeptic-verifier (fresh context; implementer transcript treated as unevidenced)

## Claim under test

Task 7 implements `OrgConfigSectionTool` such that:

1. Named org-config sections return as `OrgConfigSectionResult` text only — **no** `EvidenceFacts`, **not** corroboration / `cited_evidence_refs`.
2. Tool result fields are recordable 1:1 as `OrgConfigCallRecord` payload fields.
3. Focused tools tests (plus scoped ruff/mypy) pass.
4. Production changes for this task stay in `files_allowed`; PolicyGate / single-shot providers untouched by this task.

## Fresh command evidence

Working directory: `C:\Users\oalan\Praetor\.worktrees\agentic-judgment`  
`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`

| Command | Result |
|---------|--------|
| `pytest tests/judgment/agentic/test_tools.py -v` | **9 passed** in 0.64s (exit 0) |
| `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py` | All checks passed (exit 0) |
| `mypy src/praetor/judgment/agentic/tools.py` | Success: no issues found in 1 source file (exit 0) |
| `pytest tests/judgment/agentic/test_registry.py::test_registry_exemplars_and_org_config_tracked_separately -v` | **1 passed** in 0.26s (exit 0) |

## Focus-check evidence

### 1. Non-evidentiary return type — PASS

- `OrgConfigSectionResult` (`tools.py:37-44`): fields `section_name`, `content`, `succeeded`, `error` only — **no** `facts`.
- `OrgConfigSectionTool.invoke` annotated `-> OrgConfigSectionResult` (`tools.py:141`).
- `inspect.getsource(OrgConfigSectionTool.invoke)`: no `EvidenceFact`, no `provenance`, no `facts`.
- Module-level `EvidenceFact` / `LEDGER_HISTORY` imports exist for Task 6 tools only; unused by org-config path.

Independent runtime probe:

```
type OrgConfigSectionResult
has_facts False
isinstance_ToolResult False
isinstance_OrgConfigSectionResult True
succeeded True content_len 156
invoke_has_EvidenceFact False
```

### 2. Section allowlist — PASS

- Unknown / non-str `section_name` rejected via `section_name not in ORG_CONFIG_SNAPSHOT_HASH_KEYS` (`tools.py:143-152`), not ad-hoc strings.
- `snapshot_hash` **not** in `ORG_CONFIG_SNAPSHOT_HASH_KEYS` (`domains.py:25-47`); runtime: `snapshot_hash_in_keys False`; invoke → `succeeded=False`, `content=''`.
- `test_org_config_section_tool_rejects_unknown_section` asserts `succeeded is False` and `content == ""`.

### 3. Content serialization — PASS

- Implementation: `BaseModel` → `model_dump_json()`; else `json.dumps(..., default=str, sort_keys=True)` (`tools.py:153-157`).
- Success test: `containment_policy` → non-empty content; runtime prefix is valid JSON (`{"default_action":"escalate",...}`).

### 4. OrgConfigCallRecord recordability — PASS (structural)

- `OrgConfigCallRecord` (`registry.py:38-48`): `section_name`, `content`, `succeeded`, `error` + call metadata `source`/`tool_name`/`query`.
- Runtime field intersection: shared `['content', 'error', 'section_name', 'succeeded']`; result-only `[]`; record-only metadata `['query', 'source', 'tool_name']`.
- Live construct from tool result succeeded (`record_ok True`).
- Plan Task 11 `run_org_config_source` (`docs/superpowers/plans/2026-07-30-agentic-judgment.md:2106-2114`) maps the same four fields — no rename/type mismatch.
- Registry separation test keeps org-config out of `registry.facts` (`test_registry.py:56-79`, freshly passed).

### 5. Design alignment (`org_config_refs` vs `cited_evidence_refs`) — PASS

- Design spec lines 86–100: org-config informs `org_config_refs` only; not corroboration-eligible (narrowed to `ledger_history`).
- Tool docstring (`tools.py:133-136`) matches: never `cited_evidence_refs`; not evidence; not corroboration-eligible.

### 6. Boundary / untouched paths — PASS (this task)

- Task deliverables: `src/praetor/judgment/agentic/tools.py` (untracked), `tests/judgment/agentic/test_tools.py` (untracked), `.workflow/agentic-judgment-07-org-config-tool/`.
- `src/praetor/policy/*`: status `M` but `git diff --ignore-cr-at-eol --numstat` empty — line-ending noise only; no Task 7 content change.
- No Task 7 edits under `VertexProvider` / `FakeProvider` / policy evaluation logic.

## Acceptance criteria

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Returns section text without producing `EvidenceFacts` | Met | Separate result type; no `facts`; runtime probe; no `EvidenceFact` in invoke body |
| Results recordable as `OrgConfigCallRecord` | Met | 1:1 field map; live construction; Task 11 mapping aligned; registry keeps facts empty |
| Focused tools tests pass | Met | Fresh 9/9 pytest + ruff + mypy |
| Must not feed corroboration / `cited_evidence_refs` | Met | Design-aligned docstring + non-evidentiary type; no provenance path |
| Files allowed / PolicyGate untouched by this task | Met | Only tools.py + test_tools.py; policy EOL noise only |

## Gaps (non-blocking)

1. Suite does not assert `not hasattr(result, "facts")` / `not isinstance(result, ToolResult)` — verified only by independent probe + type annotation.
2. No Task 7 test constructing `OrgConfigCallRecord` from a live `tool.invoke` result (registry Task 2 covers storage separately; wiring is Task 11).
3. `snapshot_hash` exclusion untested in suite (runtime-confirmed reject).
4. Success test asserts `content != ""` only — not JSON shape / section fields.
5. Non-str / missing `section_name` path untested.

None of these refute the acceptance criteria as written.

## Strongest reason the claim survives

Independent read + runtime probe show `OrgConfigSectionTool.invoke` returns only `OrgConfigSectionResult` (no `facts`, not a `ToolResult`), allowlists via `ORG_CONFIG_SNAPSHOT_HASH_KEYS` (including rejecting `snapshot_hash`), and maps 1:1 onto `OrgConfigCallRecord` payload fields — corroborated by fresh 9/9 pytest, ruff, and mypy.
