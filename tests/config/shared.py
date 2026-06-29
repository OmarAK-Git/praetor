"""Shared constants for org config tests (importable module, not conftest)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_CONFIG = REPO_ROOT / "configs" / "example_org.yaml"
EXAMPLE_SNAPSHOT_HASH = (
    "fe7421df481f7afa9a922e4edd05a9715c341aa57a7b0febfaf0a35662e06153"
)
SOC_LEAD_TOKEN = "soc-lead-token"
