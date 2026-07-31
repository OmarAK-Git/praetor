# Verifier packet — agentic-judgment-07-org-config-tool

## Goal
Implement `OrgConfigSectionTool` — non-evidentiary org-config section fetch for `org_config_refs`, **never** the corroboration / `cited_evidence_refs` path.

## Acceptance criteria
- `OrgConfigSectionTool` returns section text for named sections **without** producing `EvidenceFacts`.
- Tool results are recordable as `OrgConfigCallRecord` entries.
- Focused tools tests pass.

## Changed files
- `src/praetor/judgment/agentic/tools.py` — `OrgConfigSectionTool` appended (file also contains Task 6 tools)
- `tests/judgment/agentic/test_tools.py` — two org-config tests appended (file also contains Task 6 tests)

## Commands (`PYTHONPATH=C:\Users\oalan\Praetor\.worktrees\agentic-judgment\src`)
- `pytest tests/judgment/agentic/test_tools.py -v`
- `ruff check src/praetor/judgment/agentic/tools.py tests/judgment/agentic/test_tools.py`
- `mypy src/praetor/judgment/agentic/tools.py`

## Focus checks (skeptic)

### 1. Non-evidentiary return type (CRITICAL — no corroboration path)
In `src/praetor/judgment/agentic/tools.py`, confirm `OrgConfigSectionTool.invoke` return annotation is `OrgConfigSectionResult`, **not** `ToolResult`.

Confirm `OrgConfigSectionResult` (`tools.py:37-44`) has fields `section_name`, `content`, `succeeded`, `error` only — **no** `facts` field.

Confirm `OrgConfigSectionTool.invoke` body contains **no** `EvidenceFact(...)` construction, **no** `provenance_path` assignment, and **no** import/use of evidence provenance constants for this tool.

Runtime spot-check (optional):
```python
from praetor.judgment.agentic.tools import OrgConfigSectionTool, OrgConfigSectionResult, ToolResult
# after building a valid snapshot fixture:
r = tool.invoke({"section_name": "containment_policy"})
assert type(r).__name__ == "OrgConfigSectionResult"
assert not hasattr(r, "facts")
assert not isinstance(r, ToolResult)
```

**Do not** treat org-config output as citable evidence or corroboration-eligible in verification reasoning.

### 2. Section allowlist
Confirm unknown `section_name` values are rejected via `ORG_CONFIG_SNAPSHOT_HASH_KEYS` (`tools.py:145`), not ad-hoc string checks.

Confirm `snapshot_hash` is **not** in `ORG_CONFIG_SNAPSHOT_HASH_KEYS` (`src/praetor/hashing/domains.py`) — requesting it must fail like any unknown section.

`test_org_config_section_tool_rejects_unknown_section` must assert `succeeded is False` and `content == ""`.

### 3. Content serialization
For a known section (test uses `containment_policy`), confirm successful invoke returns non-empty `content` (`test_org_config_section_tool_returns_requested_section`).

Inspect implementation: `BaseModel` sections use `model_dump_json()`; other values use `json.dumps(..., sort_keys=True)` (`tools.py:154-157`).

### 4. OrgConfigCallRecord recordability
Read `OrgConfigCallRecord` in `src/praetor/judgment/agentic/registry.py:38-48`. Confirm tool result fields map 1:1 to `section_name`, `content`, `succeeded`, `error` (call metadata `source`/`tool_name`/`query` added by Task 11 provider wiring, not this task).

Cross-check plan Task 11 `run_org_config_source` mapping (`docs/superpowers/plans/2026-07-30-agentic-judgment.md` ~2106-2114). No field rename or type mismatch.

Registry test `test_registry_exemplars_and_org_config_tracked_separately` (`tests/judgment/agentic/test_registry.py`) confirms org-config entries stay out of `registry.facts`.

### 5. Design alignment (org_config_refs vs cited_evidence_refs)
Read design spec `docs/superpowers/specs/2026-07-30-agentic-judgment-design.md` lines 86–100. Confirm implementation docstring and result type match: org-config informs `org_config_refs` only; **not** corroboration-eligible (narrowed to `ledger_history` only per DEC-064 intent).

### 6. Boundary / untouched paths
- No changes under `src/praetor/policy/`.
- No changes to `VertexProvider` / `FakeProvider` single-shot behavior.
- Production changes for this task confined to `files_allowed`.

## Implementer result
`.workflow/agentic-judgment-07-org-config-tool/results/implementer-result.md`

## Code review
`.workflow/agentic-judgment-07-org-config-tool/results/code-review.md` — **PASS**

Treat claims as unevidenced until checked. Write `results/verifier-result.md` with PASS/BLOCK and command evidence.
