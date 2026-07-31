"""Correlation accuracy gate (Task 30).

Measures correlation quality on committed OTRF-style telemetry before judgment
is trusted on real shapes. Verifies fixture manifest checksums, required event
collection, process relationships, account corroboration, ambiguity flags, and
bounded noise overcollection.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from praetor.contracts.evidence import EvidenceFact
from praetor.correlation import correlate_telemetry, load_fixture_events
from praetor.correlation.entities import assemble_process_relationships
from praetor.evidence.provenance import meets_account_corroboration

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
EXPECTED_DIR = EVALS_DIR / "correlation_expected"
DEFAULT_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "fixture_manifest.yaml"


@dataclass(frozen=True)
class ManifestVerificationResult:
    passed: bool
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class CorrelationExpectedScenario:
    scenario_id: str
    description: str
    inputs: dict[str, Any]
    expectations: dict[str, Any]
    raw: dict[str, Any]
    source_path: Path


@dataclass(frozen=True)
class CorrelationGateResult:
    scenario_id: str
    passed: bool
    errors: tuple[str, ...] = ()
    collected_record_ids: tuple[str, ...] = ()
    collected_noise_record_ids: tuple[str, ...] = ()
    noise_overcollection: int = 0


def _parse_anchor_time(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _resolve_repo_path(path_value: str, *, repo_root: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return repo_root / candidate


def _to_manifest_path(fixture_path: str) -> str:
    normalized = fixture_path.replace("\\", "/")
    marker = "tests/fixtures/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        return f"fixtures/{suffix}"
    if normalized.startswith("fixtures/"):
        return normalized
    return normalized


def load_correlation_expected(path: Path) -> CorrelationExpectedScenario:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        msg = f"expected scenario must be a mapping: {path}"
        raise ValueError(msg)
    inputs = raw.get("inputs")
    expectations = raw.get("expectations")
    if not isinstance(inputs, dict) or not isinstance(expectations, dict):
        msg = f"expected scenario missing inputs/expectations: {path}"
        raise ValueError(msg)
    scenario_id = str(raw.get("scenario_id") or path.stem)
    description = str(raw.get("description") or "")
    return CorrelationExpectedScenario(
        scenario_id=scenario_id,
        description=description,
        inputs=inputs,
        expectations=expectations,
        raw=raw,
        source_path=path,
    )


def _manifest_listed_paths(manifest_path: Path) -> set[str]:
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return set()
    entries = data.get("fixtures")
    if not isinstance(entries, list):
        return set()
    paths: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and entry.get("path"):
            paths.add(str(entry["path"]))
    return paths


def _referenced_fixture_paths(inputs: Mapping[str, Any]) -> list[str]:
    paths: list[str] = []
    for key in ("sysmon_fixtures", "security_fixtures", "noise_fixtures"):
        value = inputs.get(key)
        if isinstance(value, list):
            paths.extend(str(item) for item in value)
    return paths


def verify_scenario_fixtures_listed_in_manifest(
    *,
    inputs: Mapping[str, Any],
    manifest_path: Path,
) -> ManifestVerificationResult:
    listed = _manifest_listed_paths(manifest_path)
    errors: list[str] = []
    for fixture_path in _referenced_fixture_paths(inputs):
        manifest_entry = _to_manifest_path(fixture_path)
        if manifest_entry not in listed:
            errors.append(
                f"scenario fixture not listed in fixture manifest: {fixture_path}"
            )
    return ManifestVerificationResult(passed=not errors, errors=tuple(errors))


def verify_fixture_manifest_checksums(
    manifest_path: Path,
    *,
    repo_root: Path = REPO_ROOT,
    fixtures_parent: Path | None = None,
) -> ManifestVerificationResult:
    """Verify every manifest entry matches its declared sha256."""
    if not manifest_path.is_file():
        return ManifestVerificationResult(
            passed=False,
            errors=(f"fixture manifest not found: {manifest_path}",),
        )

    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return ManifestVerificationResult(
            passed=False,
            errors=(f"fixture manifest must be a mapping: {manifest_path}",),
        )
    entries = data.get("fixtures")
    if not isinstance(entries, list) or not entries:
        return ManifestVerificationResult(
            passed=False,
            errors=(f"fixture manifest has no entries: {manifest_path}",),
        )

    base = fixtures_parent
    if base is None:
        base = manifest_path.parent
    errors: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("manifest entry must be a mapping")
            continue
        rel_path = str(entry.get("path") or "")
        expected = str(entry.get("sha256") or "")
        if not rel_path or not expected:
            errors.append("manifest entry missing path or sha256")
            continue
        fixture_path = base.parent / rel_path if rel_path.startswith("fixtures/") else base / rel_path
        if not fixture_path.is_file():
            errors.append(f"manifest fixture missing on disk: {fixture_path}")
            continue
        actual = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        if actual != expected:
            errors.append(
                f"manifest checksum mismatch for {rel_path}: expected {expected}, got {actual}"
            )
    return ManifestVerificationResult(passed=not errors, errors=tuple(errors))


def _load_fixture_events_from_paths(
    paths: Sequence[str],
    *,
    repo_root: Path,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path_value in paths:
        fixture_path = _resolve_repo_path(path_value, repo_root=repo_root)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        events.extend(load_fixture_events(payload))
    return events


def _record_id_from_fact(fact: EvidenceFact) -> str | None:
    try:
        raw = json.loads(fact.raw_source)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    record_id = raw.get("record_id")
    return str(record_id) if record_id is not None else None


def _facts_by_record_id(facts: Sequence[EvidenceFact]) -> dict[str, EvidenceFact]:
    indexed: dict[str, EvidenceFact] = {}
    for fact in facts:
        record_id = _record_id_from_fact(fact)
        if record_id is not None:
            indexed[record_id] = fact
    return indexed


def _noise_record_ids(
    noise_fixture_paths: Sequence[str],
    *,
    repo_root: Path,
) -> set[str]:
    record_ids: set[str] = set()
    for path_value in noise_fixture_paths:
        fixture_path = _resolve_repo_path(path_value, repo_root=repo_root)
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        for event in load_fixture_events(payload):
            record_id = event.get("record_id")
            if record_id is not None:
                record_ids.add(str(record_id))
    return record_ids


def _validate_process_relationships(
    facts: Sequence[EvidenceFact],
    relationships: Sequence[Mapping[str, Any]],
) -> list[str]:
    if not relationships:
        return []
    graph = assemble_process_relationships(facts)
    errors: list[str] = []
    for relationship in relationships:
        parent_guid = str(relationship.get("parent_process_guid") or "")
        child_guid = str(relationship.get("child_process_guid") or "")
        if not parent_guid or not child_guid:
            errors.append("relationship entry missing parent_process_guid or child_process_guid")
            continue
        child = graph.entities.get(child_guid)
        if child is None:
            errors.append(f"missing child process entity for relationship: {child_guid}")
            continue
        if child.parent_process_guid != parent_guid:
            errors.append(
                "process relationship mismatch for "
                f"{child_guid}: parent={child.parent_process_guid}, expected={parent_guid}"
            )
    return errors


def _validate_corroboration_and_provenance(
    facts: Sequence[EvidenceFact],
    expectations: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    if expectations.get("require_account_corroboration"):
        if not meets_account_corroboration(facts):
            errors.append(
                "account corroboration failed: at least one supporting fact required (DEC-065)"
            )
    required_paths = expectations.get("required_provenance_paths")
    if isinstance(required_paths, list) and required_paths:
        actual_paths = {fact.provenance_path for fact in facts}
        for path in required_paths:
            path_str = str(path)
            if path_str not in actual_paths:
                errors.append(f"missing required provenance_path: {path_str}")
    return errors


def _validate_ambiguity_flags(
    facts_by_record_id: Mapping[str, EvidenceFact],
    expectations: Mapping[str, Any],
) -> list[str]:
    required = expectations.get("required_ambiguity_flag_record_ids")
    if not isinstance(required, list) or not required:
        return []
    errors: list[str] = []
    for record_id in required:
        record_key = str(record_id)
        fact = facts_by_record_id.get(record_key)
        if fact is None:
            errors.append(
                f"missing fact for required_ambiguity_flag record_id: {record_key}"
            )
            continue
        if not fact.ambiguity_flag:
            errors.append(f"ambiguity_flag must be true for record_id: {record_key}")
    return errors


def run_correlation_gate(
    expected_path: Path,
    *,
    repo_root: Path = REPO_ROOT,
) -> CorrelationGateResult:
    scenario = load_correlation_expected(expected_path)
    inputs = scenario.inputs
    expectations = scenario.expectations

    manifest_value = str(inputs.get("fixture_manifest") or DEFAULT_MANIFEST)
    manifest_path = _resolve_repo_path(manifest_value, repo_root=repo_root)

    listing_result = verify_scenario_fixtures_listed_in_manifest(
        inputs=inputs,
        manifest_path=manifest_path,
    )
    if not listing_result.passed:
        return CorrelationGateResult(
            scenario_id=scenario.scenario_id,
            passed=False,
            errors=listing_result.errors,
        )

    manifest_result = verify_fixture_manifest_checksums(manifest_path, repo_root=repo_root)
    if not manifest_result.passed:
        return CorrelationGateResult(
            scenario_id=scenario.scenario_id,
            passed=False,
            errors=tuple(
                f"manifest verification failed: {error}" for error in manifest_result.errors
            ),
        )

    anchor_time = _parse_anchor_time(str(inputs.get("anchor_time")))
    window_seconds = int(inputs.get("window_seconds", 300))
    sysmon_paths = list(inputs.get("sysmon_fixtures") or [])
    security_paths = list(inputs.get("security_fixtures") or [])
    noise_paths = list(inputs.get("noise_fixtures") or [])

    sysmon_events = _load_fixture_events_from_paths(sysmon_paths, repo_root=repo_root)
    security_events = _load_fixture_events_from_paths(security_paths, repo_root=repo_root)
    correlation = correlate_telemetry(
        sysmon_events=sysmon_events,
        security_events=security_events,
        anchor_time=anchor_time,
        window_seconds=window_seconds,
    )

    facts = correlation.bundle.facts
    facts_by_record_id = _facts_by_record_id(facts)
    collected_record_ids = tuple(facts_by_record_id.keys())
    collected_set = set(collected_record_ids)
    noise_ids = _noise_record_ids(noise_paths, repo_root=repo_root)
    collected_noise_record_ids = tuple(
        record_id for record_id in collected_record_ids if record_id in noise_ids
    )
    noise_overcollection = len(collected_noise_record_ids)

    errors: list[str] = []
    required_ids = [str(item) for item in expectations.get("required_record_ids") or []]
    for record_id in required_ids:
        if record_id not in collected_set:
            errors.append(f"missing required record_id: {record_id}")

    excluded_ids = [str(item) for item in expectations.get("excluded_record_ids") or []]
    for record_id in excluded_ids:
        if record_id in collected_set:
            errors.append(f"excluded record_id collected: {record_id}")

    min_facts = expectations.get("min_collected_facts")
    max_facts = expectations.get("max_collected_facts")
    fact_count = len(facts)
    if min_facts is not None and fact_count < int(min_facts):
        errors.append(
            f"collected fact count {fact_count} below min_collected_facts {min_facts}"
        )
    if max_facts is not None and fact_count > int(max_facts):
        errors.append(
            f"collected fact count {fact_count} above max_collected_facts {max_facts}"
        )

    max_noise = expectations.get("max_noise_overcollection")
    if max_noise is not None and noise_overcollection > int(max_noise):
        errors.append(
            "noise overcollection record_ids: "
            f"{list(collected_noise_record_ids)} ({noise_overcollection}) "
            f"exceeds max_noise_overcollection {max_noise}"
        )

    relationship_errors = _validate_process_relationships(
        facts,
        list(expectations.get("required_process_relationships") or []),
    )
    errors.extend(relationship_errors)
    errors.extend(_validate_corroboration_and_provenance(facts, expectations))
    errors.extend(_validate_ambiguity_flags(facts_by_record_id, expectations))

    return CorrelationGateResult(
        scenario_id=scenario.scenario_id,
        passed=not errors,
        errors=tuple(errors),
        collected_record_ids=collected_record_ids,
        collected_noise_record_ids=collected_noise_record_ids,
        noise_overcollection=noise_overcollection,
    )


def run_all_default_scenarios(*, repo_root: Path = REPO_ROOT) -> list[CorrelationGateResult]:
    paths = sorted(EXPECTED_DIR.glob("*.yaml"))
    return [run_correlation_gate(path, repo_root=repo_root) for path in paths]


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = [Path(arg) for arg in args] if args else sorted(EXPECTED_DIR.glob("*.yaml"))
    if not paths:
        print("no correlation expected scenarios found", file=sys.stderr)
        return 1

    failed = False
    for path in paths:
        result = run_correlation_gate(path, repo_root=REPO_ROOT)
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.scenario_id}")
        for error in result.errors:
            print(f"  - {error}")
        if not result.passed:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
