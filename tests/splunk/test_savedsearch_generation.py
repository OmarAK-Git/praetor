"""TASK-033: SPL compilation and Splunk saved-search generation."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sigma.collection import SigmaCollection  # noqa: E402
from tools.compile_sigma import (  # noqa: E402
    ALLOWED_MODIFIERS,
    UnsupportedSigmaFeatureError,
    check_outputs,
    compile_outputs,
    load_sigma_collection,
    load_sigma_rule_paths,
    validate_rule_supported,
)
from tools.fixture_events import (  # noqa: E402
    iter_manifest_fixture_events,
    manifest_fixture_count,
)
from tools.spl_match import (  # noqa: E402
    collapse_duplicate_source_terms,
    matching_record_ids,
)
from tools.splunk_conf import parse_savedsearch_queries  # noqa: E402

SIGMA_DIR = REPO_ROOT / "detections" / "sigma" / "windows"
SPL_DIR = REPO_ROOT / "detections" / "spl"
SAVEDSEARCHES = REPO_ROOT / "splunk" / "savedsearches.conf"
PROPS_CONF = REPO_ROOT / "splunk" / "props.conf"
FIXTURE_MANIFEST = REPO_ROOT / "tests" / "fixtures" / "fixture_manifest.yaml"
INGEST_SCRIPT = REPO_ROOT / "tools" / "splunk_ingest_demo.ps1"
COMPILE_SCRIPT = REPO_ROOT / "tools" / "compile_sigma.py"

CORRELATION_RULE_YAML = """
title: Event Count Correlation
id: 22222222-2222-2222-2222-222222222222
status: test
logsource:
  category: process_creation
  product: windows
  service: sysmon
detection:
  selection:
    EventID: 1
  condition: selection
correlation:
  type: event_count
  rules:
    - 22222222-2222-2222-2222-222222222222
  group-by:
    - Computer
  timespan: 5m
  condition:
    gte: 5
"""

SPL_SEMANTIC_EXPECTATIONS: tuple[tuple[str, frozenset[str], frozenset[str]], ...] = (
    (
        "sysmon_powershell_encoded_command.spl",
        frozenset({"1002"}),
        frozenset({"1001"}),
    ),
    (
        "sysmon_cmd_execution.spl",
        frozenset({"1001", "1005", "1006"}),
        frozenset({"1002"}),
    ),
    (
        "security_successful_logon_4624.spl",
        frozenset({"2001"}),
        frozenset({"1001"}),
    ),
    (
        "sysmon_calc_execution.spl",
        frozenset({"9999"}),
        frozenset({"1001", "1002", "1003"}),
    ),
    (
        "sysmon_notepad_execution.spl",
        frozenset({"1003", "1004"}),
        frozenset({"1001"}),
    ),
)


@pytest.fixture(scope="module")
def compiled_outputs():
    return compile_outputs(SIGMA_DIR)


@pytest.fixture(scope="module")
def flattened_manifest_events() -> dict[str, dict]:
    return {
        str(raw["record_id"]): flat
        for _path, raw, flat in iter_manifest_fixture_events()
    }


def test_sigma_rule_files_present_for_compile() -> None:
    paths = load_sigma_rule_paths(SIGMA_DIR)
    assert len(paths) >= 5


def test_compile_outputs_one_spl_per_rule(compiled_outputs) -> None:
    assert len(compiled_outputs.rules) >= 5
    stems = {item.source_stem for item in compiled_outputs.rules}
    assert stems == {path.stem for path in load_sigma_rule_paths(SIGMA_DIR)}


def test_spl_queries_are_deterministic(compiled_outputs) -> None:
    first = compile_outputs(SIGMA_DIR)
    second = compile_outputs(SIGMA_DIR)
    assert first == second


def test_committed_spl_matches_compiler(compiled_outputs) -> None:
    mismatches = check_outputs(compiled_outputs, SPL_DIR, SAVEDSEARCHES)
    assert mismatches == [], f"SPL/savedsearch drift: {mismatches}"


def test_compile_check_cli_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(COMPILE_SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_savedsearches_conf_contains_all_rules(compiled_outputs) -> None:
    text = compiled_outputs.savedsearches_conf
    for rule in compiled_outputs.rules:
        assert f"[{rule.title}]" in text


def test_savedsearches_conf_matches_committed_file(compiled_outputs) -> None:
    committed = SAVEDSEARCHES.read_text(encoding="utf-8").strip()
    assert committed == compiled_outputs.savedsearches_conf.strip()


def test_savedsearch_query_matches_per_rule_spl_after_source_dedup(compiled_outputs) -> None:
    queries = parse_savedsearch_queries(SAVEDSEARCHES.read_text(encoding="utf-8"))
    for rule in compiled_outputs.rules:
        saved_query = queries[rule.title]
        normalized = collapse_duplicate_source_terms(saved_query)
        spl_path = SPL_DIR / f"{rule.source_stem}.spl"
        assert normalized == spl_path.read_text(encoding="utf-8").strip()


def test_committed_spl_semantic_match_and_discrimination(flattened_manifest_events) -> None:
    for spl_name, expected_ids, excluded_ids in SPL_SEMANTIC_EXPECTATIONS:
        spl = (SPL_DIR / spl_name).read_text(encoding="utf-8").strip()
        matched = matching_record_ids(spl, flattened_manifest_events)
        assert matched == set(expected_ids), f"{spl_name}: matched {matched}, expected {expected_ids}"
        for record_id in excluded_ids:
            assert record_id not in matched, f"{spl_name} should exclude record {record_id}"


def test_unsupported_modifier_raises_clear_error() -> None:
    yaml_text = """
title: Unsupported Modifier Rule
id: 11111111-1111-1111-1111-111111111111
logsource:
  category: process_creation
  product: windows
  service: sysmon
detection:
  selection:
    Image|startswith: 'C:\\\\Windows\\\\'
  condition: selection
"""
    rule = SigmaCollection.from_yaml(yaml_text).rules[0]
    with pytest.raises(UnsupportedSigmaFeatureError, match="unsupported detection modifiers \\[startswith\\]"):
        validate_rule_supported(rule)


def test_unsupported_list_form_modifier_raises_clear_error() -> None:
    yaml_text = """
title: List Form Unsupported
id: 11111111-1111-1111-1111-111111111112
logsource:
  category: process_creation
  product: windows
  service: sysmon
detection:
  selection:
    - Image|startswith: 'C:\\\\Windows\\\\'
  condition: selection
"""
    rule = SigmaCollection.from_yaml(yaml_text).rules[0]
    with pytest.raises(UnsupportedSigmaFeatureError, match="unsupported detection modifiers \\[startswith\\]"):
        validate_rule_supported(rule)


def test_unsupported_chained_modifier_raises_clear_error() -> None:
    yaml_text = """
title: Chained Unsupported
id: 11111111-1111-1111-1111-111111111113
logsource:
  category: process_creation
  product: windows
  service: sysmon
detection:
  selection:
    CommandLine|contains|all: ['-enc', 'hidden']
  condition: selection
"""
    rule = SigmaCollection.from_yaml(yaml_text).rules[0]
    with pytest.raises(
        UnsupportedSigmaFeatureError,
        match="unsupported detection modifiers \\[all\\]",
    ):
        validate_rule_supported(rule)


def test_correlation_rule_rejected_by_validate_rule_supported() -> None:
    rule = SigmaCollection.from_yaml(CORRELATION_RULE_YAML).rules[0]
    with pytest.raises(
        UnsupportedSigmaFeatureError,
        match=r"correlation rules are unsupported \(rule id=22222222-2222-2222-2222-222222222222, title='Event Count Correlation'\)",
    ):
        validate_rule_supported(rule)


def test_correlation_rule_rejected_by_load_sigma_collection(tmp_path: Path) -> None:
    sigma_dir = tmp_path / "windows"
    sigma_dir.mkdir()
    (sigma_dir / "correlation.yml").write_text(CORRELATION_RULE_YAML, encoding="utf-8")
    with pytest.raises(
        UnsupportedSigmaFeatureError,
        match=r"correlation rules are unsupported \(rule id=22222222-2222-2222-2222-222222222222, title='Event Count Correlation'\)",
    ):
        load_sigma_collection(sigma_dir)


def test_allowed_modifiers_cover_task32_rules() -> None:
    for path in load_sigma_rule_paths(SIGMA_DIR):
        collection = SigmaCollection.from_yaml(path.read_text(encoding="utf-8"))
        for rule in collection.rules:
            validate_rule_supported(rule)


def test_fixture_manifest_checksums_python_mirror() -> None:
    manifest = yaml.safe_load(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
    for entry in manifest["fixtures"]:
        rel = entry["path"].removeprefix("fixtures/")
        fixture_path = REPO_ROOT / "tests" / "fixtures" / rel
        assert fixture_path.is_file(), f"missing fixture: {fixture_path}"
        digest = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"checksum drift for {entry['path']}"


def test_ingest_script_validate_only() -> None:
    if sys.platform != "win32":
        pytest.skip("PowerShell ingest script validation is Windows-only in CI")
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INGEST_SCRIPT),
            "-ValidateOnly",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    assert "ValidateOnly complete" in result.stdout


def test_ingest_script_validates_manifest_fixture_count() -> None:
    if sys.platform != "win32":
        pytest.skip("PowerShell ingest script validation is Windows-only in CI")
    expected = manifest_fixture_count()
    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INGEST_SCRIPT),
            "-ValidateOnly",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    match = re.search(r"Validated (\d+) fixture\(s\)", result.stdout)
    assert match is not None, result.stdout
    assert int(match.group(1)) == expected


def test_ingest_script_fails_on_checksum_tamper(tmp_path) -> None:
    if sys.platform != "win32":
        pytest.skip("PowerShell ingest script validation is Windows-only in CI")

    repo_copy = tmp_path / "repo"
    repo_copy.mkdir()
    for rel_dir in ("tests/fixtures/sysmon", "tests/fixtures/security", "tools"):
        (repo_copy / rel_dir).mkdir(parents=True)
    for rel in (
        "tests/fixtures/fixture_manifest.yaml",
        "tests/fixtures/sysmon/process_chain.json",
        "tools/splunk_ingest_demo.ps1",
        "tools/fixture_events.py",
    ):
        target = repo_copy / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO_ROOT / rel).read_bytes())

    tampered = repo_copy / "tests/fixtures/sysmon/process_chain.json"
    payload = json.loads(tampered.read_text(encoding="utf-8"))
    payload["events"][0]["record_id"] = "tampered"
    tampered.write_text(json.dumps(payload), encoding="utf-8")

    result = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo_copy / "tools/splunk_ingest_demo.ps1"),
            "-ValidateOnly",
            "-RepoRoot",
            str(repo_copy),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "checksum mismatch" in (result.stderr + result.stdout).lower()


def test_props_conf_parses_as_splunk_stanzas() -> None:
    stanzas: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in PROPS_CONF.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
            stanzas[current] = {}
            continue
        if current is None:
            continue
        key, value = stripped.split("=", 1)
        stanzas[current][key.strip()] = value.strip()
    assert "praetor_fixture_json" in stanzas
    assert stanzas["praetor_fixture_json"]["INDEXED_EXTRACTIONS"] == "JSON"
    assert "source::WinEventLog:Microsoft-Windows-Sysmon/Operational" in stanzas


@pytest.mark.integration
def test_splunk_demo_manual_procedure_only() -> None:
    """Splunk demo reproducibility is manual per splunk/README.md — not CI-gated."""
    import os

    if not os.environ.get("PRAETOR_SPLUNK_HEC_HOST") or not os.environ.get(
        "PRAETOR_SPLUNK_HEC_TOKEN"
    ):
        pytest.skip(
            "Optional: set PRAETOR_SPLUNK_HEC_HOST and PRAETOR_SPLUNK_HEC_TOKEN "
            "before running the manual splunk/README.md demo"
        )
    if not (Path("/opt/splunk").exists() or Path("C:/Program Files/Splunk").exists()):
        pytest.skip("Splunk installation not present on this host")


def test_allowed_modifiers_documented() -> None:
    assert "contains" in ALLOWED_MODIFIERS
    assert "endswith" in ALLOWED_MODIFIERS
