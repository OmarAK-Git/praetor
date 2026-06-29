"""Shared constants for org config tests (importable module, not conftest)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
EXAMPLE_SNAPSHOT_HASH = (
    "b91161d38293d9350dd44fc7f5f257eba17301c6f3ecb6f0fbc6984e7c8f5d76"
)
SOC_LEAD_TOKEN = "soc-lead-token"
