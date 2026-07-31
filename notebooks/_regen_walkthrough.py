"""Regenerate the interactive Praetor walkthrough with executed CI outputs."""

from __future__ import annotations

from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "praetor_walkthrough.ipynb"

HIDDEN = {"jupyter": {"source_hidden": True, "outputs_hidden": True}}


def md(source: str) -> object:
    return new_markdown_cell(source.strip() + "\n")


def code(source: str, *, metadata: dict | None = None) -> object:
    return new_code_cell(source.strip() + "\n", metadata=metadata or {})


def build() -> nbformat.NotebookNode:
    cells = [
        md(
            """
# Praetor interactive walkthrough

**Post-detection disposition engine.** An alert already fired; Praetor decides what happens next.

> The model recommends. The system authorizes.

Run the cells below, then use the dial to pick a mechanism. Every selection
destroys the previous throwaway SQLite store, activates a clean org config,
wires exactly one precondition, and runs only that scenario. The model provider
and ticket stamp are deterministic stand-ins; **everything downstream is the
real engine.**

Prefer a zero-setup version? The same ten scenarios are pre-rendered as a
clickable page under `demo/index.html`.
"""
        ),
        code(
            """
# Setup (hidden): make notebooks/ importable and load the shared scenario registry.
import sys
from pathlib import Path


def find_repo_root() -> Path:
    for candidate in (Path.cwd().resolve(), *Path.cwd().resolve().parents):
        if (candidate / "configs" / "example_org.yaml").exists():
            return candidate
    raise RuntimeError("run this notebook from inside the Praetor repo")


REPO = find_repo_root()
sys.path.insert(0, str(REPO / "notebooks"))

import ipywidgets as widgets
from IPython.display import Markdown, clear_output, display

from walkthrough_scenarios import (
    SCENARIOS,
    close_scenario_store,
    run_scenario,
    scenario_session,
)

print("Praetor repo:", REPO)
print(f"scenarios loaded: {len(SCENARIOS)}")
""",
            metadata=HIDDEN,
        ),
        md(
            """
## Pick a mechanism
"""
        ),
        code(
            """
scenario_picker = widgets.RadioButtons(
    options=[(scenario.label, key) for key, scenario in SCENARIOS.items()],
    value=next(iter(SCENARIOS)),
    description="Scenario:",
    layout=widgets.Layout(width="max-content"),
    style={"description_width": "initial"},
)
scenario_output = widgets.Output()


def refresh_selected_scenario(change) -> None:
    if change.get("name") != "value" or change.get("new") is None:
        return
    with scenario_output:
        clear_output(wait=True)
        run_scenario(change["new"], show=lambda text: display(Markdown(text)))


scenario_picker.observe(refresh_selected_scenario, names="value")
display(widgets.VBox([scenario_picker, scenario_output]))
with scenario_output:
    run_scenario(scenario_picker.value, show=lambda text: display(Markdown(text)))
print("INTERACTIVE PICKER READY")
"""
        ),
        md(
            """
## Scenario reference

Full setup wiring and engine code for every dial lives in
`notebooks/walkthrough_scenarios.py`. Each scenario asserts its own expected
disposition and fault flags, so a behavior change fails CI rather than quietly
rewriting the demo.
"""
        ),
        code(
            """
for key, scenario in SCENARIOS.items():
    display(Markdown(f"**`{key}`** — {scenario.headline}"))
"""
        ),
        code(
            """
print("CI SCENARIO SWEEP START")
with scenario_session():
    for scenario_name in SCENARIOS:
        run_scenario(scenario_name, show=lambda text: None)
    print("CI SCENARIO SWEEP COMPLETE")
""",
            metadata={**HIDDEN, "tags": ["ci-verification"]},
        ),
        code(
            """
close_scenario_store()
print("walkthrough scenario store closed")
""",
            metadata=HIDDEN,
        ),
    ]

    notebook = new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
        },
    )
    notebook.nbformat = 4
    notebook.nbformat_minor = 5
    return notebook


def main() -> None:
    notebook = build()
    client = NotebookClient(notebook, timeout=240, kernel_name="python3")
    client.execute()
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.metadata.pop("execution", None)
    nbformat.write(notebook, OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
