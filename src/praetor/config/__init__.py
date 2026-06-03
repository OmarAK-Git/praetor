"""Org config loader, preflight, activation, and emergency never-contain."""

from praetor.config.activation import ActivationResult, activate_org_config
from praetor.config.emergency import (
    EmergencyEntryResult,
    EmergencyNeverContainError,
    add_emergency_never_contain,
    emergency_cannot_authorize_containment,
    evaluate_live_never_contain_for_target,
)
from praetor.config.errors import (
    ActivationError,
    ConfigError,
    ConfigLoadError,
    InternalOnlyConfigOperationError,
    PreflightError,
    SnapshotHashConflictError,
    SnapshotTamperError,
)
from praetor.config.loader import (
    LoadedOrgConfig,
    load_org_config_document,
    load_org_config_source,
)
from praetor.config.preflight import apply_field_defaults, run_preflight
from praetor.config.snapshot import (
    build_org_config_snapshot,
    compute_snapshot_hash,
    verbatim_character_count,
)
from praetor.config.state import (
    fetch_active_org_config,
    fetch_active_snapshot,
    fetch_snapshot_by_hash,
    fetch_verbatim_render_text,
    init_config_schema,
)

__all__ = [
    "ActivationError",
    "ActivationResult",
    "ConfigError",
    "ConfigLoadError",
    "EmergencyEntryResult",
    "EmergencyNeverContainError",
    "InternalOnlyConfigOperationError",
    "LoadedOrgConfig",
    "PreflightError",
    "SnapshotHashConflictError",
    "SnapshotTamperError",
    "activate_org_config",
    "add_emergency_never_contain",
    "apply_field_defaults",
    "build_org_config_snapshot",
    "compute_snapshot_hash",
    "emergency_cannot_authorize_containment",
    "evaluate_live_never_contain_for_target",
    "fetch_active_org_config",
    "fetch_active_snapshot",
    "fetch_snapshot_by_hash",
    "fetch_verbatim_render_text",
    "init_config_schema",
    "load_org_config_document",
    "load_org_config_source",
    "run_preflight",
    "verbatim_character_count",
]
