"""Shared constants for org config tests (importable module, not conftest)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
EXAMPLE_SNAPSHOT_HASH = (
    "427ad8e63cb7fbcbe8c1b9aba8d442a3a4243fa0ce5b5bbd431f9d757084b2b5"
)
SOC_LEAD_TOKEN = "soc-lead-token"
