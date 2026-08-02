"""Update memory-bank projections after corroboration-floor gate PASS."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    ac = ROOT / "memory-bank" / "activeContext.md"
    text = ac.read_text(encoding="utf-8")
    marker = "## Current focus"
    next_markers = ("## Build order", "## Recently changed", "## Current blockers")
    if marker not in text:
        raise SystemExit("activeContext missing Current focus")
    pre, rest = text.split(marker, 1)
    cut = None
    for m in next_markers:
        i = rest.find(m)
        if i >= 0 and (cut is None or i < cut):
            cut = i
    if cut is None:
        raise SystemExit("could not find section after Current focus")
    new_focus = """

**2026-07-31 — Corroboration floor temporary (DEC-065) COMPLETE.** Plan
`docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md` drained via GSD sprint
`corroboration-floor` (01–03 + gate). Temporary ≥1 eligible anchoring cite; sole ambiguity
still fails; `ledger_history` not corroboration-eligible; upgrade-to-≥2 flagged for
multi-telemetry. Gate: pytest **1105**, ruff/mypy clean. Evidence:
`.workflow/corroboration-floor-gate/results/verifier-result.md`.

**2026-07-30 — Agentic judgment sprint COMPLETE** — landed as `05e27cd` on `master`.

**2026-07-30 — Reverse-spec RFC remediation COMPLETE.** Plan
`docs/superpowers/plans/2026-07-30-reverse-spec-rfc-remediation.md` drained via GSD.
Gate evidence: `.workflow/rfc-remediation-gate/results/verifier-result.md`.

"""
    ac.write_text(pre + marker + new_focus + rest[cut:], encoding="utf-8")

    prog = ROOT / "memory-bank" / "progress.md"
    p = prog.read_text(encoding="utf-8")
    entry = """## 2026-07-31 — Corroboration floor temporary (DEC-065) COMPLETE

- Plan: `docs/superpowers/plans/2026-07-31-corroboration-floor-temporary.md`
- Sprint `corroboration-floor` drained (01-decision, 02-helpers, 03-gate-harness, gate).
- Temporary host/account floor: ≥1 corroboration-eligible fact; sole `ambiguity_flag=true`
  host cite still fails; `ledger_history` excluded from eligibility.
- DEC-064 corroboration trust extension superseded; agentic OM + session_trace_hash retained.
- Frozen `docs/spec.md` left untouched (contracts §12a SoT until unfreeze).
- Gate: pytest **1105** passed / ruff clean / mypy clean.
- Evidence: `.workflow/corroboration-floor-gate/results/verifier-result.md`.

"""
    if "2026-07-31 — Corroboration floor temporary" not in p:
        if p.startswith("# Progress Log"):
            prog.write_text(
                "# Progress Log\n\n" + entry + p[len("# Progress Log") :].lstrip("\n"),
                encoding="utf-8",
            )
        else:
            prog.write_text(entry + p, encoding="utf-8")
    print("memory-bank updated")


if __name__ == "__main__":
    main()
