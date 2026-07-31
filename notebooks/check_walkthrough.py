"""CI guard for the Praetor walkthrough notebook.

Reads an *executed* copy of ``notebooks/praetor_walkthrough.ipynb`` and fails if
either the notebook raised in any cell or the engine no longer produces the
decisions the notebook documents. This turns the committed walkthrough into a
self-verifying doc: an API break or a change in gate behavior fails CI.

Usage: ``python notebooks/check_walkthrough.py <executed_notebook.ipynb>``
"""

from __future__ import annotations

import sys

import nbformat

# Substrings that must appear in the executed stdout. The generator performs a
# deterministic all-scenario sweep because a live widget displays only one
# selection at a time.
REQUIRED = (
    "INTERACTIVE PICKER READY",
    "SCENARIO COMPLETE: earned_auto_contain",
    "SCENARIO COMPLETE: benign_review",
    "SCENARIO COMPLETE: never_contain",
    "SCENARIO COMPLETE: insufficient_corroboration",
    "SCENARIO COMPLETE: not_allowlisted",
    "SCENARIO COMPLETE: rate_limit",
    "SCENARIO COMPLETE: circuit_breaker",
    "SCENARIO COMPLETE: progressive_report",
    "SCENARIO COMPLETE: similar_case_exemplars",
    "SCENARIO COMPLETE: statute_curation",
    "CI SCENARIO SWEEP COMPLETE",
    "AUTO_CONTAIN",
    "CONTAINMENT DIRECTIVE EMITTED",
    "STANDARD_REVIEW",
    "ESCALATE",
    "never_contain_live_conflict",
    "insufficient_corroboration",
    "rate_limit_exceeded",
    "containment_breaker_open",
    "containment not granted by omission",
    "PROGRESSIVE AUTHORIZATION REPORT",
    "prompt_exemplar_block",
    "proposed_for_review_only",
)


def main(path: str) -> int:
    nb = nbformat.read(path, as_version=4)
    text_parts: list[str] = []
    errors = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                errors += 1
                print(f"ERROR cell output: {out.get('ename')}: {out.get('evalue')}")
            elif out.get("output_type") == "stream":
                text = out.get("text", "")
                text_parts.append("".join(text) if isinstance(text, list) else text)

    blob = "".join(text_parts)
    missing = [needle for needle in REQUIRED if needle not in blob]

    if errors:
        print(f"FAIL: {errors} error output(s) in the executed notebook")
    if missing:
        print("FAIL: engine no longer produces the documented decisions; missing:")
        for needle in missing:
            print(f"  - {needle!r}")
    if errors or missing:
        return 1

    print("OK: walkthrough executed cleanly and all documented decisions are present")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python notebooks/check_walkthrough.py <executed_notebook.ipynb>")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
