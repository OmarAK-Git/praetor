"""TASK-032: Sigma rule repository validation and fixture matching."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from sigma.backends.test.backend import TextQueryTestBackend
from sigma.collection import SigmaCollection
from sigma.exceptions import SigmaRuleLocation
from sigma.rule.rule import SigmaRule
from sigma.validation import SigmaValidator
from sigma.validators.base import SigmaValidationIssueSeverity
from sigma.validators.core import validators as core_validators

REPO_ROOT = Path(__file__).resolve().parents[2]
DETECTIONS = REPO_ROOT / "detections"
SIGMA_DIR = DETECTIONS / "sigma" / "windows"
ATTACK_MAPPING = DETECTIONS / "attack_mapping.yaml"
FIXTURES = REPO_ROOT / "tests" / "fixtures"

ATTACK_TECHNIQUE_TAG = re.compile(r"^attack\.t[\d.]+$", re.IGNORECASE)
ATTACK_TACTIC_TAG = re.compile(r"^attack\.[a-z-]+$", re.IGNORECASE)
VALIDATOR_EXCLUSIONS = frozenset(
    {
        "-specific_instead_of_generic_logsource",
    }
)

# _event_matches_rule evaluates detection selections only (field/modifier match).
# Logsource constraints are NOT enforced — compile smoke tests cover rule structure.
DISCRIMINATION_CASES: tuple[tuple[str, str, bool], ...] = (
    ("Suspicious PowerShell Encoded Command", "1001", False),
    ("Suspicious PowerShell Encoded Command", "1002", True),
    ("Windows Command Shell Execution", "2001", False),
    ("Windows Command Shell Execution", "1001", True),
    ("Successful Security Logon (4624)", "1001", False),
    ("Successful Security Logon (4624)", "2001", True),
)


def _load_sigma_rules() -> list[SigmaRule]:
    rules: list[SigmaRule] = []
    for path in sorted(SIGMA_DIR.glob("*.yml")):
        collection = SigmaCollection.from_yaml(
            path.read_text(encoding="utf-8"),
            source=SigmaRuleLocation(path=path),
        )
        assert collection.errors == [], f"collection errors in {path.name}: {collection.errors}"
        rules.extend(collection.rules)
    return rules


def _load_attack_mapping() -> dict[str, Any]:
    payload = yaml.safe_load(ATTACK_MAPPING.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _flatten_fixture_event(event: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in ("EventID", "Channel", "Computer", "@timestamp", "record_id"):
        if key in event:
            fields[key] = event[key]
    event_data = event.get("EventData")
    if isinstance(event_data, dict):
        fields.update(event_data)
    if "EventID" in fields:
        try:
            fields["EventID"] = int(fields["EventID"])
        except (TypeError, ValueError):
            pass
    return fields


def _coerce_equal(actual: Any, expected: Any) -> bool:
    if actual == expected:
        return True
    try:
        return int(actual) == int(expected)
    except (TypeError, ValueError):
        return str(actual).casefold() == str(expected).casefold()


def _endswith_match(actual: str, expected: str) -> bool:
    suffix = expected.replace("\\\\", "\\")
    return actual.casefold().endswith(suffix.casefold())


def _selection_matches(selection: dict[str, Any], fields: dict[str, Any]) -> bool:
    for key, expected in selection.items():
        if "|" in key:
            field, modifier = key.split("|", 1)
        else:
            field, modifier = key, None
        if field not in fields:
            return False
        actual = fields[field]
        if modifier == "contains":
            if str(expected).casefold() not in str(actual).casefold():
                return False
        elif modifier == "endswith":
            if not _endswith_match(str(actual), str(expected)):
                return False
        elif modifier is None:
            if not _coerce_equal(actual, expected):
                return False
        else:
            pytest.fail(f"unsupported sigma modifier in test rules: {modifier}")
    return True


def _event_matches_rule(rule: SigmaRule, fields: dict[str, Any]) -> bool:
    detection = rule.detection.to_dict()
    condition = detection.pop("condition", None)
    if condition is None:
        return False
    selections = {
        name: _selection_matches(spec, fields)
        for name, spec in detection.items()
        if isinstance(spec, dict)
    }
    if condition == "selection" or condition == list(selections.keys())[0]:
        return any(selections.values())
    if isinstance(condition, str) and condition in selections:
        return selections[condition]
    return False


def _iter_manifest_fixture_events() -> list[tuple[str, dict[str, Any]]]:
    manifest = yaml.safe_load((FIXTURES / "fixture_manifest.yaml").read_text(encoding="utf-8"))
    events: list[tuple[str, dict[str, Any]]] = []
    for entry in manifest["fixtures"]:
        rel_path = entry["path"].removeprefix("fixtures/")
        fixture_path = FIXTURES / rel_path
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        for event in payload.get("events", []):
            events.append((rel_path, event))
    return events


def _fixture_event_by_record_id(record_id: str) -> dict[str, Any]:
    for _path, event in _iter_manifest_fixture_events():
        if str(event.get("record_id")) == record_id:
            return event
    pytest.fail(f"no committed fixture event with record_id={record_id!r}")


def _rule_by_title(rules: list[SigmaRule], title: str) -> SigmaRule:
    matches = [rule for rule in rules if rule.title == title]
    assert len(matches) == 1, f"expected one rule titled {title!r}, found {len(matches)}"
    return matches[0]


def _attack_technique_from_tag(tag: str) -> str:
    match = ATTACK_TECHNIQUE_TAG.match(tag)
    assert match, f"not an attack technique tag: {tag!r}"
    suffix = tag.split(".", 1)[1]
    return f"T{suffix[1:].upper()}" if suffix.lower().startswith("t") else f"T{suffix.upper()}"


def _attack_tactic_from_tag(tag: str) -> str:
    assert tag.lower().startswith("attack."), tag
    tactic = tag.split(".", 1)[1]
    assert not tactic.lower().startswith("t"), tag
    return tactic


def _mapping_entry_for_rule(
    attack_mapping: dict[str, Any],
    rule: SigmaRule,
) -> dict[str, Any]:
    rule_id = str(rule.id)
    for entry in attack_mapping["rules"]:
        if entry["id"] == rule_id:
            return entry
    pytest.fail(f"attack_mapping.yaml missing entry for rule id {rule_id}")


@pytest.fixture(scope="module")
def sigma_rules() -> list[SigmaRule]:
    return _load_sigma_rules()


@pytest.fixture(scope="module")
def attack_mapping() -> dict[str, Any]:
    return _load_attack_mapping()


def test_sigma_rule_files_exist() -> None:
    rule_files = sorted(SIGMA_DIR.glob("*.yml"))
    assert rule_files, "expected at least one sigma rule under detections/sigma/windows/"
    assert ATTACK_MAPPING.is_file()


def test_sigma_rules_parse_without_errors(sigma_rules: list[SigmaRule]) -> None:
    assert len(sigma_rules) >= 5
    for rule in sigma_rules:
        assert rule.errors == [], f"{rule.title} parse errors: {rule.errors}"


def test_sigma_rules_validate_without_blocking_issues(sigma_rules: list[SigmaRule]) -> None:
    """Gate HIGH/MEDIUM pySigma issues; stylistic logsource validator excluded."""
    validator = SigmaValidator.from_dict(
        {"validators": ["all", *VALIDATOR_EXCLUSIONS]},
        core_validators,
    )
    issues = validator.validate_rules(iter(sigma_rules))
    blocking = [
        issue
        for issue in issues
        if issue.severity
        in {SigmaValidationIssueSeverity.HIGH, SigmaValidationIssueSeverity.MEDIUM}
    ]
    assert blocking == [], f"blocking validation issues: {blocking}"


def test_sigma_rules_compile_via_textquery_backend(sigma_rules: list[SigmaRule]) -> None:
    backend = TextQueryTestBackend()
    for rule in sigma_rules:
        queries = backend.convert_rule(rule, output_format="default")
        assert queries, f"{rule.title} produced no textquery output"
        assert all(isinstance(query, str) and query.strip() for query in queries)


def test_sigma_rules_have_attack_tags(sigma_rules: list[SigmaRule]) -> None:
    for rule in sigma_rules:
        technique_tags = [str(tag) for tag in rule.tags if ATTACK_TECHNIQUE_TAG.match(str(tag))]
        assert technique_tags, f"{rule.title} missing attack.t* tag"


def test_attack_mapping_covers_every_rule_file(
    sigma_rules: list[SigmaRule],
    attack_mapping: dict[str, Any],
) -> None:
    mapped_ids = {entry["id"] for entry in attack_mapping["rules"]}
    mapped_files = {entry["file"] for entry in attack_mapping["rules"]}
    for rule in sigma_rules:
        assert str(rule.id) in mapped_ids, f"missing attack mapping for rule id {rule.id}"
    for path in sorted(SIGMA_DIR.glob("*.yml")):
        rel = f"sigma/windows/{path.name}"
        assert rel in mapped_files, f"missing attack mapping file entry for {rel}"


def test_attack_mapping_entries_have_techniques(attack_mapping: dict[str, Any]) -> None:
    for entry in attack_mapping["rules"]:
        techniques = entry.get("techniques") or []
        assert techniques, f"mapping for {entry['id']} missing techniques"
        for technique in techniques:
            assert re.match(r"^T\d", technique), f"invalid technique id {technique!r}"


def test_attack_tags_match_mapping(
    sigma_rules: list[SigmaRule],
    attack_mapping: dict[str, Any],
) -> None:
    for rule in sigma_rules:
        entry = _mapping_entry_for_rule(attack_mapping, rule)
        tag_techniques = sorted(
            _attack_technique_from_tag(str(tag))
            for tag in rule.tags
            if ATTACK_TECHNIQUE_TAG.match(str(tag))
        )
        tag_tactics = sorted(
            _attack_tactic_from_tag(str(tag))
            for tag in rule.tags
            if ATTACK_TACTIC_TAG.match(str(tag)) and not str(tag).lower().startswith("attack.t")
        )
        assert tag_techniques == sorted(entry["techniques"]), (
            f"{rule.title} technique tag drift: tags={tag_techniques} mapping={entry['techniques']}"
        )
        assert tag_tactics == sorted(entry["tactics"]), (
            f"{rule.title} tactic tag drift: tags={tag_tactics} mapping={entry['tactics']}"
        )


def test_manifest_covers_committed_telemetry_fixtures() -> None:
    manifest = yaml.safe_load((FIXTURES / "fixture_manifest.yaml").read_text(encoding="utf-8"))
    manifest_paths = {entry["path"] for entry in manifest["fixtures"]}
    for directory in ("sysmon", "security"):
        for path in sorted((FIXTURES / directory).glob("*.json")):
            expected = f"fixtures/{directory}/{path.name}"
            assert expected in manifest_paths, (
                f"{expected} missing from fixture_manifest.yaml; "
                "add manifest entry before relying on gate coverage"
            )


def test_each_fixture_event_matches_at_least_one_rule(
    sigma_rules: list[SigmaRule],
) -> None:
    unmatched: list[str] = []
    for fixture_path, event in _iter_manifest_fixture_events():
        fields = _flatten_fixture_event(event)
        record_id = event.get("record_id", "?")
        if not any(_event_matches_rule(rule, fields) for rule in sigma_rules):
            unmatched.append(f"{fixture_path} record_id={record_id}")
    assert unmatched == [], f"fixture events unmatched by any sigma rule: {unmatched}"


@pytest.mark.parametrize(("rule_title", "record_id", "expected_match"), DISCRIMINATION_CASES)
def test_sigma_rule_discrimination(
    sigma_rules: list[SigmaRule],
    rule_title: str,
    record_id: str,
    expected_match: bool,
) -> None:
    rule = _rule_by_title(sigma_rules, rule_title)
    fields = _flatten_fixture_event(_fixture_event_by_record_id(record_id))
    assert _event_matches_rule(rule, fields) is expected_match, (
        f"{rule_title} vs record {record_id}: expected match={expected_match}"
    )


def test_4624_rule_does_not_match_sysmon_process_creation(
    sigma_rules: list[SigmaRule],
) -> None:
    rule = _rule_by_title(sigma_rules, "Successful Security Logon (4624)")
    sysmon_events = [
        fields
        for path, event in _iter_manifest_fixture_events()
        if path.startswith("sysmon/")
        and (fields := _flatten_fixture_event(event))["EventID"] == 1
    ]
    assert sysmon_events, "expected sysmon EventID=1 fixture events"
    assert not any(_event_matches_rule(rule, fields) for fields in sysmon_events)


def test_contains_modifier_is_case_insensitive(sigma_rules: list[SigmaRule]) -> None:
    rule = _rule_by_title(sigma_rules, "Suspicious PowerShell Encoded Command")
    fields = _flatten_fixture_event(_fixture_event_by_record_id("1002"))
    fields["CommandLine"] = fields["CommandLine"].replace("-enc", "-ENC")
    assert _event_matches_rule(rule, fields)
