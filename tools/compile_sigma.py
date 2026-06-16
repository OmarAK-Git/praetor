"""Compile Praetor Sigma rules to Splunk SPL and savedsearches.conf."""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sigma.backends.splunk import SplunkBackend
from sigma.collection import SigmaCollection
from sigma.correlations import SigmaCorrelationRule
from sigma.exceptions import SigmaError
from sigma.pipelines.splunk import splunk_windows_pipeline
from sigma.rule.rule import SigmaRule

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGMA_DIR = REPO_ROOT / "detections" / "sigma" / "windows"
DEFAULT_SPL_DIR = REPO_ROOT / "detections" / "spl"
DEFAULT_SAVEDSEARCHES = REPO_ROOT / "splunk" / "savedsearches.conf"

ALLOWED_MODIFIERS = frozenset({"contains", "endswith"})


class UnsupportedSigmaFeatureError(ValueError):
    """Raised when a rule uses Sigma features this compiler does not support."""


class SigmaCompileError(RuntimeError):
    """Raised when pySigma fails to compile a supported rule."""


@dataclass(frozen=True)
class CompiledRule:
    rule_id: str
    title: str
    source_stem: str
    spl: str


@dataclass(frozen=True)
class CompileOutputs:
    rules: tuple[CompiledRule, ...]
    savedsearches_conf: str


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _spl_file_name(rule_path: Path) -> str:
    return f"{rule_path.stem}.spl"


def load_sigma_rule_paths(sigma_dir: Path = DEFAULT_SIGMA_DIR) -> list[Path]:
    paths = sorted(sigma_dir.glob("*.yml"))
    if not paths:
        msg = f"no Sigma rules found under {sigma_dir}"
        raise FileNotFoundError(msg)
    return paths


def load_sigma_collection(sigma_dir: Path = DEFAULT_SIGMA_DIR) -> SigmaCollection:
    rules: list[SigmaRule] = []
    errors: list[Any] = []
    for path in load_sigma_rule_paths(sigma_dir):
        collection = SigmaCollection.from_yaml(path.read_text(encoding="utf-8"))
        errors.extend(collection.errors)
        for rule in collection.rules:
            if isinstance(rule, SigmaCorrelationRule):
                raise UnsupportedSigmaFeatureError(
                    f"correlation rules are unsupported (rule id={rule.id}, title={rule.title!r})"
                )
            rules.append(rule)
    if errors:
        raise SigmaCompileError(f"Sigma parse errors: {errors}")
    return SigmaCollection(rules)


def _modifiers_from_field_key(field_key: str) -> list[str]:
    if "|" not in field_key:
        return []
    return field_key.split("|")[1:]


def _iter_selection_field_keys(selection: Any) -> list[str]:
    if isinstance(selection, dict):
        return list(selection.keys())
    if isinstance(selection, list):
        keys: list[str] = []
        for item in selection:
            if isinstance(item, dict):
                keys.extend(item.keys())
        return keys
    return []


def _iter_detection_modifiers(rule: SigmaRule) -> set[str | None]:
    modifiers: set[str | None] = set()
    detection = rule.detection.to_dict()
    for key, value in detection.items():
        if key == "condition":
            continue
        for field_key in _iter_selection_field_keys(value):
            chain = _modifiers_from_field_key(field_key)
            if not chain:
                modifiers.add(None)
            else:
                modifiers.update(chain)
    return modifiers


def validate_rule_supported(rule: SigmaRule | SigmaCorrelationRule) -> None:
    if isinstance(rule, SigmaCorrelationRule):
        raise UnsupportedSigmaFeatureError(
            f"correlation rules are unsupported (rule id={rule.id}, title={rule.title!r})"
        )
    unsupported_modifiers = sorted(
        modifier
        for modifier in _iter_detection_modifiers(rule)
        if modifier is not None and modifier not in ALLOWED_MODIFIERS
    )
    if unsupported_modifiers:
        joined = ", ".join(unsupported_modifiers)
        raise UnsupportedSigmaFeatureError(
            f"unsupported detection modifiers [{joined}] in rule id={rule.id}, title={rule.title!r}; "
            f"allowed modifiers: {sorted(ALLOWED_MODIFIERS)} or none"
        )


def _splunk_backend() -> SplunkBackend:
    return SplunkBackend(processing_pipeline=splunk_windows_pipeline())


def compile_outputs(sigma_dir: Path = DEFAULT_SIGMA_DIR) -> CompileOutputs:
    collection = load_sigma_collection(sigma_dir)
    backend = _splunk_backend()
    compiled: list[CompiledRule] = []

    rule_paths = load_sigma_rule_paths(sigma_dir)
    path_by_id = {}
    for path in rule_paths:
        single = SigmaCollection.from_yaml(path.read_text(encoding="utf-8"))
        for rule in single.rules:
            validate_rule_supported(rule)
            path_by_id[str(rule.id)] = path

    for rule in sorted(collection.rules, key=lambda item: (item.title or "", str(item.id))):
        validate_rule_supported(rule)
        queries = backend.convert(
            SigmaCollection([rule]),
            output_format="default",
        )
        if backend.errors:
            raise SigmaCompileError(
                f"backend errors compiling rule id={rule.id}, title={rule.title!r}: {backend.errors}"
            )
        if not queries or not isinstance(queries[0], str) or not queries[0].strip():
            raise SigmaCompileError(
                f"empty SPL generated for rule id={rule.id}, title={rule.title!r}"
            )
        source_path = path_by_id.get(str(rule.id))
        if source_path is None:
            raise SigmaCompileError(f"no source file for rule id={rule.id}")
        compiled.append(
            CompiledRule(
                rule_id=str(rule.id),
                title=rule.title or str(rule.id),
                source_stem=source_path.stem,
                spl=queries[0].strip(),
            )
        )

    try:
        savedsearches_conf = backend.convert(collection, output_format="savedsearches")
    except SigmaError as exc:
        raise SigmaCompileError(f"failed to generate savedsearches.conf: {exc}") from exc
    if not isinstance(savedsearches_conf, str) or not savedsearches_conf.strip():
        raise SigmaCompileError("savedsearches.conf generation returned empty output")
    if backend.errors:
        raise SigmaCompileError(f"backend errors generating savedsearches.conf: {backend.errors}")

    return CompileOutputs(
        rules=tuple(compiled),
        savedsearches_conf=_normalize_newlines(savedsearches_conf).strip() + "\n",
    )


def write_outputs(
    outputs: CompileOutputs,
    spl_dir: Path = DEFAULT_SPL_DIR,
    savedsearches_path: Path = DEFAULT_SAVEDSEARCHES,
) -> None:
    spl_dir.mkdir(parents=True, exist_ok=True)
    savedsearches_path.parent.mkdir(parents=True, exist_ok=True)

    for path in spl_dir.glob("*.spl"):
        path.unlink()

    for compiled in outputs.rules:
        spl_path = spl_dir / f"{compiled.source_stem}.spl"
        spl_path.write_text(compiled.spl + "\n", encoding="utf-8", newline="\n")

    savedsearches_path.write_text(outputs.savedsearches_conf, encoding="utf-8", newline="\n")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def check_outputs(
    outputs: CompileOutputs,
    spl_dir: Path = DEFAULT_SPL_DIR,
    savedsearches_path: Path = DEFAULT_SAVEDSEARCHES,
) -> list[str]:
    mismatches: list[str] = []
    for compiled in outputs.rules:
        spl_path = spl_dir / f"{compiled.source_stem}.spl"
        expected = (compiled.spl + "\n").encode("utf-8")
        if not spl_path.is_file():
            mismatches.append(f"missing committed SPL file: {spl_path.relative_to(REPO_ROOT)}")
            continue
        actual = spl_path.read_bytes()
        if actual != expected:
            mismatches.append(
                f"SPL drift for {spl_path.name}: committed hash {_file_sha256(spl_path)}, "
                f"compiler hash {hashlib.sha256(expected).hexdigest()}"
            )
    if not savedsearches_path.is_file():
        mismatches.append(
            f"missing committed savedsearches.conf: {savedsearches_path.relative_to(REPO_ROOT)}"
        )
    else:
        committed = _normalize_newlines(savedsearches_path.read_text(encoding="utf-8")).strip()
        if committed != outputs.savedsearches_conf.strip():
            mismatches.append("savedsearches.conf drift vs compiler output")
    return mismatches


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Verify committed SPL and savedsearches.conf match compiler output",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="Write compiler output to detections/spl/ and splunk/savedsearches.conf",
    )
    parser.add_argument(
        "--sigma-dir",
        type=Path,
        default=DEFAULT_SIGMA_DIR,
        help="Directory containing Sigma YAML rules",
    )
    parser.add_argument(
        "--spl-dir",
        type=Path,
        default=DEFAULT_SPL_DIR,
        help="Directory for plain SPL output files",
    )
    parser.add_argument(
        "--savedsearches",
        type=Path,
        default=DEFAULT_SAVEDSEARCHES,
        help="Path for savedsearches.conf output",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    outputs = compile_outputs(args.sigma_dir)
    if args.write:
        write_outputs(outputs, args.spl_dir, args.savedsearches)
        return 0
    mismatches = check_outputs(outputs, args.spl_dir, args.savedsearches)
    if mismatches:
        for mismatch in mismatches:
            print(mismatch, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
