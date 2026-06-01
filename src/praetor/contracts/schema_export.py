"""Deterministic JSON Schema artifact export (generated files are not authoritative)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from praetor.contracts.alert import AlertEnvelope
from praetor.contracts.containment import ContainmentDirective
from praetor.contracts.edict import DecisionEdict
from praetor.contracts.evidence import EvidenceBundle
from praetor.contracts.feed import RevocationFeedRecord
from praetor.contracts.governance import AnalystAnnotation
from praetor.contracts.health import SystemHealthAlert
from praetor.contracts.identity import CanonicalAccountIdentity
from praetor.contracts.judgment import ModelJudgment
from praetor.contracts.ledger import (
    DirectiveRevocationRecord,
    EmergencyNeverContainRecord,
    NeverContainSnapshotRecord,
)
from praetor.contracts.org_config import OrgConfigSnapshot
from praetor.contracts.policy import PolicyGateResult

SCHEMA_EXPORTS: list[tuple[type[BaseModel], str]] = [
    (AlertEnvelope, "alert_envelope.json"),
    (EvidenceBundle, "evidence_bundle.json"),
    (OrgConfigSnapshot, "org_config_snapshot.json"),
    (ModelJudgment, "model_judgment.json"),
    (PolicyGateResult, "policy_gate_result.json"),
    (DecisionEdict, "decision_edict.json"),
    (ContainmentDirective, "containment_directive.json"),
    (DirectiveRevocationRecord, "directive_revocation_record.json"),
    (NeverContainSnapshotRecord, "never_contain_snapshot_record.json"),
    (EmergencyNeverContainRecord, "emergency_never_contain_record.json"),
    (RevocationFeedRecord, "revocation_feed_record.json"),
    (SystemHealthAlert, "system_health_alert.json"),
    (AnalystAnnotation, "analyst_annotation.json"),
    (CanonicalAccountIdentity, "canonical_account_identity.json"),
]


def canonical_schema_bytes(schema: dict[str, Any]) -> bytes:
    """Stable JSON encoding for schema artifacts."""
    text = json.dumps(schema, sort_keys=True, indent=2, ensure_ascii=True)
    return (text + "\n").encode("utf-8")


def export_schemas(output_dir: Path | None = None) -> list[Path]:
    """Write all contract JSON Schemas; returns paths written."""
    root = output_dir or Path(__file__).resolve().parents[3] / "schemas"
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model, filename in SCHEMA_EXPORTS:
        path = root / filename
        schema = model.model_json_schema(mode="serialization")
        path.write_bytes(canonical_schema_bytes(schema))
        written.append(path)
    return written


def main() -> None:
    paths = export_schemas()
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
