# Interactive Praetor Walkthrough

**Tier:** T2  
**Goal:** Replace the fixed Act I/II notebook with an isolated radio-driven scenario explorer and retain deterministic all-scenario CI coverage.  
**Status:** complete  
**Updated:** 2026-07-31

## Sources

- Design: `docs/superpowers/specs/2026-07-31-interactive-walkthrough-design.md`
- Detailed plan: `docs/superpowers/plans/2026-07-31-interactive-walkthrough.md`

## Checklist

1. Pin all scenario markers in `notebooks/check_walkthrough.py` — done
2. Build fresh-store scenario registry in `notebooks/_regen_walkthrough.py` — done
3. Add radio picker and deterministic scenario sweep — done
4. Regenerate notebook and run semantic checker — done
5. Fresh-context review and Memory Bank sync — done

## Verification

- Red: checker failed against the pre-change notebook (missing interactive markers).
- Green: `python notebooks/_regen_walkthrough.py` then `python notebooks/check_walkthrough.py notebooks/praetor_walkthrough.ipynb` → OK.
- Generated notebook has `RadioButtons`, observer wiring, ten `SCENARIO COMPLETE` markers, rate-limit and breaker pins.
