"""Shared constants for org config tests (importable module, not conftest)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
EXAMPLE_SNAPSHOT_HASH = (
    "8b694ab5aea32db12b6a0b89000ecb34fd1bfe8a7c70489396c18c3b9607d7d3"
)
SOC_LEAD_TOKEN = "soc-lead-token"
