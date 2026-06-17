"""CI guard for the Praetor walkthrough notebook.

Reads an *executed* copy of ``notebooks/praetor_walkthrough.ipynb`` and fails if
either the notebook raised in any cell or the engine no longer produces the three
decisions the notebook documents. This turns the committed walkthrough into a
self-verifying doc: an API break or a change in gate behavior fails CI.

Usage: ``python notebooks/check_walkthrough.py <executed_notebook.ipynb>``
"""

from __future__ import annotations

import sys

import nbformat

# Substrings that must appear in the executed stdout. Chosen to be insensitive to
# label spacing while still pinning the actual decisions:
#   - uppercase AUTO_CONTAIN appears only in Case 1's final decision line
#   - the directive banner proves a containment directive was emitted
#   - STANDARD_REVIEW / ESCALATE pin Cases 2 and 3
#   - never_contain_live_conflict proves the gate refused to contain the DC
REQUIRED = (
    "AUTO_CONTAIN",
    "CONTAINMENT DIRECTIVE EMITTED",
    "STANDARD_REVIEW",
    "ESCALATE",
    "never_contain_live_conflict",
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
