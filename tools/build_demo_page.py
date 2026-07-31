"""Build the static, clickable Praetor demo page.

Executes every walkthrough scenario against the real engine and embeds the
captured output into a self-contained HTML page. The page needs no kernel and
no network, so it can be served directly from GitHub Pages.

Usage:
    python tools/build_demo_page.py            # write demo/index.html
    python tools/build_demo_page.py --check    # fail if the committed page is stale
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "notebooks"))

from walkthrough_scenarios import (  # noqa: E402
    SCENARIO_LIST,
    Scenario,
    capture_scenario,
    close_scenario_store,
)

OUT = ROOT / "demo" / "index.html"

_DECISION_RE = re.compile(r"^PRAETOR DECIDED\s+:\s+(\S+)", re.MULTILINE)
_FLAGS_RE = re.compile(r"^fault_flags\s+:\s+(.+)$", re.MULTILINE)

_VOLATILE_PATTERNS = (
    re.compile(r"^(decision_id\s+:\s+).*$", re.MULTILINE),
    re.compile(r"^(\s+idempotency_key\s+:\s+).*$", re.MULTILINE),
)


def _outcome_badges(output: str) -> list[tuple[str, str]]:
    """Return (kind, text) badges summarizing an engine result."""
    badges: list[tuple[str, str]] = []
    decision = _DECISION_RE.search(output)
    if decision:
        verdict = decision.group(1)
        kind = "contain" if verdict == "AUTO_CONTAIN" else "blocked"
        if verdict == "STANDARD_REVIEW":
            kind = "review"
        badges.append((kind, verdict))
    flags = _FLAGS_RE.search(output)
    if flags:
        raw = flags.group(1).strip()
        if raw not in {"[]", "'[]'"}:
            for flag in re.findall(r"[a-z_]{4,}", raw):
                badges.append(("flag", flag))
    if "CONTAINMENT DIRECTIVE EMITTED" in output:
        badges.append(("directive", "directive emitted"))
    elif "no containment directive" in output:
        badges.append(("none", "no directive"))
    return badges


def _panel(scenario: Scenario, output: str, *, index: int) -> str:
    chips = "".join(
        f'<span class="badge badge-{kind}">{html.escape(text)}</span>'
        for kind, text in _outcome_badges(output)
    )
    badges = f'\n        <div class="badges">{chips}</div>' if chips else ""
    return f"""
      <section class="panel" id="panel-{scenario.key}" role="tabpanel"
               aria-labelledby="dial-{scenario.key}"{"" if index == 0 else " hidden"}>
        <h2>{html.escape(scenario.label)}</h2>
        <p class="headline">{html.escape(scenario.headline)}</p>{badges}
        <div class="notes">
          <div class="note">
            <h3>What happens</h3>
            <p>{html.escape(scenario.architecture)}</p>
          </div>
          <div class="note">
            <h3>Setup</h3>
            <p>{html.escape(scenario.wiring)}</p>
          </div>
          <div class="note note-gotcha">
            <h3>Why it matters</h3>
            <p>{html.escape(scenario.gotcha)}</p>
          </div>
        </div>
        <h3 class="output-title">What the engine printed</h3>
        <pre class="output"><code>{html.escape(output.strip())}</code></pre>
      </section>"""


def _dial(scenario: Scenario, *, index: int) -> str:
    checked = " checked" if index == 0 else ""
    return f"""
        <label class="dial">
          <input type="radio" name="scenario" value="{scenario.key}"
                 id="dial-{scenario.key}"{checked}>
          <span class="dial-label">{html.escape(scenario.label)}</span>
        </label>"""


def render_page(results: list[tuple[Scenario, str]], *, built_at: str) -> str:
    dials = "".join(_dial(scenario, index=i) for i, (scenario, _) in enumerate(results))
    panels = "".join(
        _panel(scenario, output, index=i)
        for i, (scenario, output) in enumerate(results)
    )
    keys = json.dumps([scenario.key for scenario, _ in results])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Praetor - post-detection disposition engine</title>
<meta name="description" content="Interactive tour of Praetor: when an alert
already fired, see when the system authorizes containment — and when it
refuses.">
<style>
  :root {{
    --bg: #0b0f17;
    --surface: #131a26;
    --surface-2: #1a2332;
    --line: #263248;
    --text: #e6edf7;
    --muted: #93a4bf;
    --accent: #5b9dff;
    --contain: #f0a742;
    --blocked: #ff6b6b;
    --review: #46d19b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font: 16px/1.6 ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto,
          Helvetica, Arial, sans-serif;
  }}
  .wrap {{ max-width: 1080px; margin: 0 auto; padding: 40px 20px 80px; }}
  header h1 {{ margin: 0 0 6px; font-size: 30px; letter-spacing: -0.02em; }}
  header .tagline {{ margin: 0 0 4px; color: var(--accent); font-weight: 600; }}
  header .sub {{ margin: 0 0 22px; color: var(--muted); max-width: 70ch; }}
  .picker {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 18px 18px 8px;
    margin-bottom: 26px;
  }}
  .picker h2 {{
    margin: 0 0 12px;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted);
  }}
  .dials {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .dial {{ cursor: pointer; }}
  .dial input {{ position: absolute; opacity: 0; pointer-events: none; }}
  .dial-label {{
    display: inline-block;
    padding: 9px 14px;
    margin-bottom: 10px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--muted);
    font-size: 14px;
    transition: all .15s ease;
  }}
  .dial:hover .dial-label {{ color: var(--text); border-color: #3a4a68; }}
  .dial input:checked + .dial-label {{
    background: var(--accent);
    border-color: var(--accent);
    color: #08121f;
    font-weight: 650;
  }}
  .dial input:focus-visible + .dial-label {{ outline: 2px solid var(--accent); outline-offset: 3px; }}
  .panel {{
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 24px;
  }}
  .panel h2 {{ margin: 0 0 6px; font-size: 22px; }}
  .headline {{ margin: 0 0 14px; color: var(--muted); }}
  .badges {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
  .badge {{
    font: 600 12px/1 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    padding: 6px 10px;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: var(--surface-2);
    color: var(--muted);
  }}
  .badge-contain {{ color: var(--contain); border-color: #5a4526; }}
  .badge-blocked {{ color: var(--blocked); border-color: #5c2b2b; }}
  .badge-review {{ color: var(--review); border-color: #235142; }}
  .badge-flag {{ color: var(--accent); border-color: #27436e; }}
  .badge-directive {{ color: var(--contain); border-color: #5a4526; }}
  .notes {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 14px;
    margin-bottom: 22px;
  }}
  .note {{
    background: var(--surface-2);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 14px 16px;
  }}
  .note-gotcha {{ border-color: #4a3a24; }}
  .note h3 {{
    margin: 0 0 6px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted);
  }}
  .note-gotcha h3 {{ color: var(--contain); }}
  .note p {{ margin: 0; font-size: 14px; }}
  .output-title {{
    margin: 0 0 8px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--muted);
  }}
  .output {{
    margin: 0;
    padding: 16px;
    background: #080c14;
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow-x: auto;
    font: 13px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    color: #cdd9ec;
  }}
  footer {{
    margin-top: 30px;
    color: var(--muted);
    font-size: 14px;
    border-top: 1px solid var(--line);
    padding-top: 18px;
  }}
  footer code {{
    background: var(--surface-2);
    border: 1px solid var(--line);
    border-radius: 5px;
    padding: 1px 6px;
    font-size: 13px;
  }}
  a {{ color: var(--accent); }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Praetor</h1>
    <p class="tagline">The model recommends. The system authorizes.</p>
    <p class="sub">
      Detection already fired. Praetor decides what happens next: isolate the
      host, escalate to a human, or refuse auto-contain for a safety reason.
      Pick a scenario. Each panel below is a real engine run — only the model
      and the ticketing step are stubbed.
    </p>
  </header>

  <div class="picker">
    <h2>Pick a scenario</h2>
    <div class="dials" role="tablist">{dials}
    </div>
  </div>
{panels}

  <footer>
    <p>
      Praetor never auto-closes alerts — when it is unsure, a human still sees
      the ticket. Prefer a live kernel?
      <code>notebooks/praetor_walkthrough.ipynb</code>. Regenerate this page with
      <code>python tools/build_demo_page.py</code>.
    </p>
    <p>Generated {built_at} from the live engine.</p>
  </footer>
</div>
<script>
  const keys = {keys};
  for (const key of keys) {{
    document.getElementById("dial-" + key).addEventListener("change", () => {{
      for (const other of keys) {{
        document.getElementById("panel-" + other).hidden = other !== key;
      }}
    }});
  }}
</script>
</body>
</html>
"""


def _strip_volatile(text: str) -> str:
    """Remove per-run identifiers so --check does not flag stable content."""
    for pattern in _VOLATILE_PATTERNS:
        text = pattern.sub(r"\1<run-specific>", text)
    return re.sub(r"Generated .*? from the live engine\.", "", text)


def build_page() -> str:
    results: list[tuple[Scenario, str]] = []
    try:
        for scenario in SCENARIO_LIST:
            results.append((scenario, capture_scenario(scenario.key)))
    finally:
        close_scenario_store()
    built_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return render_page(results, built_at=built_at)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when the committed page differs from a fresh build",
    )
    args = parser.parse_args()

    page = build_page()
    if args.check:
        if not OUT.exists():
            print(f"FAIL: {OUT} does not exist; run python tools/build_demo_page.py")
            return 1
        current = OUT.read_text(encoding="utf-8")
        if _strip_volatile(current) != _strip_volatile(page):
            print(f"FAIL: {OUT} is stale; run python tools/build_demo_page.py")
            return 1
        print(f"OK: {OUT} matches a fresh build")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(SCENARIO_LIST)} scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
