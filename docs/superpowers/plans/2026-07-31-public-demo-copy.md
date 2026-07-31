# Public Demo Copy Implementation Plan

> **For agentic workers:** implement task-by-task. Steps use checkbox syntax.

**Goal:** Rewrite Praetor demo copy for SOC managers and republish the Pages demo.

**Architecture:** Single source of truth remains `notebooks/walkthrough_scenarios.py`. Display labels change in the HTML builder and notebook explainer. Engine behavior and scenario keys stay unchanged.

**Tech Stack:** Python, existing walkthrough registry, `tools/build_demo_page.py`, GitHub Pages.

## Global Constraints

- Audience: security leader / SOC manager
- Scenario keys and assertions must not change
- Rebuild `demo/index.html` and regenerate notebook after copy changes
- Verify with `check_walkthrough.py` and `build_demo_page.py --check`

---

### Task 1: Rewrite scenario public copy

**Files:** `notebooks/walkthrough_scenarios.py`, `tools/build_demo_page.py`, `notebooks/_regen_walkthrough.py` if needed

- [ ] Rename display headings to What happens / Setup / Why it matters
- [ ] Rewrite all ten labels, headlines, and explanation strings
- [ ] Soften page header/footer for the same audience
- [ ] Rebuild demo page and regenerate notebook
- [ ] Run checker + `--check`
- [ ] Commit and push to master
