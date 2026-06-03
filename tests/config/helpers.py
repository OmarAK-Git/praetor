"""Test helpers for org config preflight."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from praetor.config.loader import LoadedOrgConfig, load_org_config_source
from praetor.config.preflight import run_preflight
from praetor.contracts.org_config import OrgConfigSnapshot


def preflight_loaded(loaded: LoadedOrgConfig) -> OrgConfigSnapshot:
    return run_preflight(loaded.document, verbatim_text=loaded.verbatim_text)


def preflight_path(path: Path) -> OrgConfigSnapshot:
    return preflight_loaded(load_org_config_source(path))


def preflight_document(
    document: dict[str, Any],
    *,
    verbatim_text: str | None = None,
) -> OrgConfigSnapshot:
    text = verbatim_text if verbatim_text is not None else yaml.dump(document)
    return run_preflight(document, verbatim_text=text)
