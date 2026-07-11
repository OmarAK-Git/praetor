"""TASK-033: SPL compilation and Splunk saved-search generation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sigma.collection import SigmaCollection  # noqa: E402
from tools.compile_sigma import (  # noqa: E402
    ALLOWED_MODIFIERS,
    FIXTURE_DISPATCH_EARLIEST,
    FIXTURE_DISPATCH_LATEST,
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

_SIGMA_RULES_TEST = REPO_ROOT / "tests" / "detections" / "test_sigma_rules.py"
_sigma_spec = importlib.util.spec_from_file_location("test_sigma_rules", _SIGMA_RULES_TEST)
assert _sigma_spec and _sigma_spec.loader
_sigma_rules_mod = importlib.util.module_from_spec(_sigma_spec)
_sigma_spec.loader.exec_module(_sigma_rules_mod)

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


def test_sigma_spl_matcher_sets_equal_per_rule(
    compiled_outputs,
    flattened_manifest_events,
) -> None:
    """Per rule, Sigma matcher set must equal SPL matcher set over manifest fixtures."""
    stem_by_title = {rule.title: rule.source_stem for rule in compiled_outputs.rules}
    divergences: list[str] = []
    for sigma_rule in _sigma_rules_mod._load_sigma_rules():
        stem = stem_by_title.get(sigma_rule.title)
        if stem is None:
            divergences.append(f"{sigma_rule.title}: no compiled SPL stem")
            continue
        sigma_matches: set[str] = set()
        for _path, event in _sigma_rules_mod._iter_manifest_fixture_events():
            fields = _sigma_rules_mod._flatten_fixture_event(event)
            if _sigma_rules_mod._event_matches_rule(sigma_rule, fields):
                sigma_matches.add(str(event["record_id"]))
        spl = (SPL_DIR / f"{stem}.spl").read_text(encoding="utf-8").strip()
        spl_matches = matching_record_ids(spl, flattened_manifest_events)
        if sigma_matches != spl_matches:
            divergences.append(
                f"{sigma_rule.title}: sigma={sorted(sigma_matches)} spl={sorted(spl_matches)}"
            )
    assert divergences == [], f"Sigma↔SPL matcher drift: {divergences}"


def test_savedsearches_use_fixture_stable_dispatch_window() -> None:
    text = SAVEDSEARCHES.read_text(encoding="utf-8")
    assert f"dispatch.earliest_time = {FIXTURE_DISPATCH_EARLIEST}" in text
    assert f"dispatch.latest_time = {FIXTURE_DISPATCH_LATEST}" in text
    assert "-30d" not in text
    assert "dispatch.latest_time = now" not in text


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


def _splunk_login_session_key(mgmt_host: str, username: str, password: str) -> str:
    """Obtain a Splunk session key via ``/services/auth/login``."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    body = urllib.parse.urlencode(
        {"username": username, "password": password}
    ).encode()
    request = urllib.request.Request(
        f"{mgmt_host.rstrip('/')}/services/auth/login",
        data=body,
        method="POST",
    )
    with urllib.request.urlopen(request, context=ctx, timeout=30) as response:
        xml_body = response.read().decode("utf-8")
    root = ET.fromstring(xml_body)
    key = root.findtext(".//{http://www.w3.org/2005/Atom}sessionKey") or root.findtext(
        ".//sessionKey"
    )
    if not key:
        pytest.fail("Splunk login succeeded but returned no sessionKey")
    return key


def _splunk_time_bound(iso_timestamp: str) -> str:
    """Convert fixture ISO timestamps to Splunk ``earliest``/``latest`` form."""
    # Splunk rejects bare ISO-8601 in oneshot earliest/latest; use MM/DD/YYYY:HH:MM:SS.
    date_part, time_part = iso_timestamp.split("T", 1)
    year, month, day = date_part.split("-")
    clock = time_part.split(".")[0]
    if len(clock) == 5:
        clock = f"{clock}:00"
    return f"{month}/{day}/{year}:{clock}"


@pytest.mark.integration
def test_splunk_demo_integration_with_hec_env() -> None:
    """Live Splunk Free demo: ingest fixtures via HEC and verify SPL match sets."""
    hec_host = os.environ.get("PRAETOR_SPLUNK_HEC_HOST")
    hec_token = os.environ.get("PRAETOR_SPLUNK_HEC_TOKEN")
    if not hec_host or not hec_token:
        pytest.skip(
            "Set PRAETOR_SPLUNK_HEC_HOST and PRAETOR_SPLUNK_HEC_TOKEN "
            "to run the live Splunk demo integration test"
        )
    if sys.platform != "win32":
        pytest.skip("PowerShell ingest script requires Windows")

    index = os.environ.get("PRAETOR_SPLUNK_HEC_INDEX", "main")
    mgmt_host = os.environ.get("PRAETOR_SPLUNK_MGMT_HOST")
    if not mgmt_host:
        # Management port is TLS by default even when HEC is plain HTTP.
        mgmt_host = hec_host.replace(":8088", ":8089")
        if mgmt_host.startswith("http://"):
            mgmt_host = "https://" + mgmt_host[len("http://") :]
    mgmt_token = os.environ.get("PRAETOR_SPLUNK_MGMT_TOKEN")
    if not mgmt_token:
        user = os.environ.get("PRAETOR_SPLUNK_USER")
        password = os.environ.get("PRAETOR_SPLUNK_PASSWORD")
        if user and password:
            mgmt_token = _splunk_login_session_key(mgmt_host, user, password)
        else:
            mgmt_token = hec_token

    ingest = subprocess.run(
        [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INGEST_SCRIPT),
            "-SplunkHost",
            hec_host,
            "-HecToken",
            hec_token,
            "-Index",
            index,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ingest.returncode == 0, ingest.stderr or ingest.stdout
    assert "Ingested" in ingest.stdout

    time.sleep(3)

    def _run_oneshot_search(search: str) -> set[str]:
        form = urllib.parse.urlencode(
            {
                "search": search,
                "output_mode": "json",
                "exec_mode": "oneshot",
            }
        ).encode()
        url = f"{mgmt_host.rstrip('/')}/services/search/jobs/export"
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        last_error: str | None = None
        # Session keys from /services/auth/login use ``Splunk <key>``.
        for auth_header in (
            f"Splunk {mgmt_token}",
            f"Bearer {mgmt_token}",
        ):
            request = urllib.request.Request(
                url,
                data=form,
                method="POST",
                headers={"Authorization": auth_header},
            )
            try:
                with urllib.request.urlopen(request, context=ctx, timeout=120) as response:
                    body = response.read().decode("utf-8")
            except urllib.error.HTTPError as exc:
                err_body = exc.read().decode("utf-8", errors="replace")[:300]
                last_error = (
                    f"{auth_header.split()[0]} auth failed: HTTP {exc.code}; {err_body}"
                )
                continue
            except urllib.error.URLError as exc:
                pytest.fail(f"Splunk management API unreachable at {mgmt_host}: {exc}")
            record_ids: set[str] = set()
            for line in body.splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                result = row.get("result", row)
                rid = result.get("record_id")
                if rid is not None:
                    record_ids.add(str(rid))
            return record_ids
        pytest.fail(
            f"Splunk search auth failed at {mgmt_host}; {last_error}. "
            "Set PRAETOR_SPLUNK_MGMT_TOKEN or PRAETOR_SPLUNK_USER/"
            "PRAETOR_SPLUNK_PASSWORD if the HEC token cannot query the "
            "management API."
        )

    time_bounds = (
        f"earliest={_splunk_time_bound(FIXTURE_DISPATCH_EARLIEST)} "
        f"latest={_splunk_time_bound(FIXTURE_DISPATCH_LATEST)}"
    )
    for spl_name, expected_ids, _excluded in SPL_SEMANTIC_EXPECTATIONS:
        spl = (SPL_DIR / spl_name).read_text(encoding="utf-8").strip()
        search = (
            f"search index={index} {time_bounds} {spl} "
            "| dedup record_id | table record_id"
        )
        matched = _run_oneshot_search(search)
        assert matched == set(expected_ids), (
            f"{spl_name}: live Splunk matched {matched}, expected {expected_ids}"
        )


def test_allowed_modifiers_documented() -> None:
    assert "contains" in ALLOWED_MODIFIERS
    assert "endswith" in ALLOWED_MODIFIERS
