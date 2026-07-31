# Interactive Praetor Walkthrough Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the linear Praetor walkthrough with an isolated, radio-driven scenario explorer whose complete scenario set remains executable in CI.

**Architecture:** The notebook generator defines a scenario registry containing display metadata and callables. A scenario session manager owns exactly one temporary store and replaces it whenever the selected radio value changes. Live execution renders one selected scenario through `ipywidgets`; generator execution separately sweeps all registered scenarios to preserve deterministic semantic pins.

**Tech Stack:** Python 3.11+, nbformat/nbclient, ipywidgets 8.x, SQLite, Praetor engine APIs.

## Global Constraints

- Do not change production policy behavior.
- Keep the scripted provider and stamp; exercise the real engine downstream.
- Every scenario starts from a newly activated store.
- The generator remains the notebook source of truth.

---

### Task 1: Pin the interactive CI contract

**Files:**
- Modify: `notebooks/check_walkthrough.py`

**Interfaces:**
- Consumes: executed notebook stream outputs.
- Produces: required markers for all scenario IDs and key fault flags.

- [ ] Add required markers for picker initialization, all ten scenario IDs, rate limiting, and circuit breaker behavior.
- [ ] Run the checker against the existing notebook.
- [ ] Confirm it fails because the new scenario markers do not yet exist.

### Task 2: Build the scenario registry and isolated session runner

**Files:**
- Modify: `notebooks/_regen_walkthrough.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `SCENARIOS`, `fresh_store()`, `close_scenario_store()`, `run_scenario(name)`, and scenario callables.

- [ ] Add `walkthrough = ["ipywidgets>=8,<9"]` as an optional dependency.
- [ ] Add imports for widget display and policy-state setup.
- [ ] Refactor fixed cases into ten scenario callables.
- [ ] Add rich `architecture`, `wiring`, and `gotcha` metadata for each scenario.
- [ ] Ensure `run_scenario` closes prior state, creates a new store, prints the selected explainer, and invokes the scenario.
- [ ] Assert expected disposition/fault behavior inside each scenario.

### Task 3: Add the live picker and deterministic verification sweep

**Files:**
- Modify: `notebooks/_regen_walkthrough.py`
- Regenerate: `notebooks/praetor_walkthrough.ipynb`

**Interfaces:**
- Consumes: `SCENARIOS` and `run_scenario`.
- Produces: `RadioButtons` observer UI and non-interactive all-scenario output.

- [ ] Add a `RadioButtons` widget whose `value` observer clears the output and calls `run_scenario`.
- [ ] Render the initial selection immediately.
- [ ] Add a generator-only verification cell that executes every registry entry and prints stable markers.
- [ ] Regenerate the notebook.

### Task 4: Verify and review

**Files:**
- Modify: `memory-bank/activeContext.md`
- Modify: `memory-bank/tasks.md`
- Modify: `memory-bank/progress.md`

**Interfaces:**
- Consumes: generated notebook and checker.
- Produces: fresh verification evidence and durable completion state.

- [ ] Run `python notebooks/check_walkthrough.py notebooks/praetor_walkthrough.ipynb`; expect success.
- [ ] Run focused lint/syntax checks for notebook scripts.
- [ ] Inspect notebook JSON for widget and observer wiring.
- [ ] Ask a fresh-context reviewer to check isolation, coverage, and resource cleanup.
- [ ] Record files changed, commands, results, and any skipped checks.

## Self-Review

- Spec coverage: Tasks 1–4 cover REQ-001 through REQ-008.
- Placeholder scan: no deferred implementation placeholders.
- Type consistency: scenario registry values are consumed by both the live picker and verification sweep; `run_scenario(name)` is the single execution boundary.
