# Interactive Praetor Walkthrough Design

## Goal

Replace the fixed Act I/II notebook sequence with a radio-driven scenario explorer. Selecting a scenario must discard all previous demo state, initialize a fresh temporary SQLite store, run that scenario, and show scenario-specific architecture, wiring, and gotchas beside real engine output.

## Requirements

- REQ-001: Present mutually exclusive radio choices for earned containment, benign review, never-contain, insufficient corroboration, missing allowlist authorization, rate limiting, circuit breaker, progressive reporting, similar-case exemplars, and statute curation.
- REQ-002: A radio selection immediately force-refreshes the output; no separate Run button is required.
- REQ-003: Every selection gets a new activated temporary store so counters, breakers, emergency entries, annotations, and prior decisions cannot leak between scenarios.
- REQ-004: Each output explains the relevant architecture, the concrete setup wiring, and the most important gotcha before displaying the result.
- REQ-005: Gate scenarios execute the real intake engine downstream of the existing scripted provider and stamp stand-ins.
- REQ-006: Reporting, exemplar, and curation scenarios use their real library APIs and seed only the minimum state needed for the demonstration.
- REQ-007: Notebook regeneration executes all scenarios non-interactively so committed outputs and CI verify every path even though the live UI displays one scenario at a time.
- REQ-008: The notebook closes the active scenario store and temporary directory when switching scenarios or completing the non-interactive verification sweep.

## Acceptance Criteria

- AC-001: The generated notebook contains an `ipywidgets.RadioButtons` scenario picker and an output area.
- AC-002: The picker observer calls the selected scenario with a fresh store.
- AC-003: An executed notebook contains all ten scenario completion markers.
- AC-004: Executed output includes `rate_limit_exceeded`, `containment_breaker_open`, `never_contain_live_conflict`, and `insufficient_corroboration`.
- AC-005: Existing positive containment, standard review, progressive report, exemplar block, and proposed-statute refusal pins remain covered.
- AC-006: `notebooks/check_walkthrough.py` fails against the old notebook and passes against the regenerated notebook.

## Constraints

- Python 3.11+.
- `ipywidgets` 8.x is an optional walkthrough dependency, not a runtime dependency of `praetor`.
- No external provider or EDR calls.
- The generator remains the source of truth for `praetor_walkthrough.ipynb`.

## Verification

- VERIFY-001: Run the updated checker against the pre-change notebook and observe missing interactive scenario markers.
- VERIFY-002: Regenerate and execute the notebook with `python notebooks/_regen_walkthrough.py`.
- VERIFY-003: Run `python notebooks/check_walkthrough.py notebooks/praetor_walkthrough.ipynb`.
- VERIFY-004: Inspect the generated notebook for the widget picker and observer wiring.
- VERIFY-005: Run focused project checks for the notebook scripts.
