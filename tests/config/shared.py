"""Shared constants for org config tests (importable module, not conftest)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
EXAMPLE_SNAPSHOT_HASH = (
    "3bf840a8c3b5c4fcd4070f22c604d765ec4d69d9da8441d55e7ffed56e972d2e"
)
SOC_LEAD_TOKEN = "soc-lead-token"
