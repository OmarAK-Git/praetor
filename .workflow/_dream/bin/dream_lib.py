"""Shared primitives for the Praetor local "dream loop".

This module is intentionally stdlib-only and fully typed (passes ``mypy --strict``).
It lives OUTSIDE the repo's configured mypy packages (praetor/consumer_sdk/evals),
so the project's ``mypy src evals consumer_sdk`` invocation never touches it.

Core ideas it encodes:
  * The playbook is a sectioned markdown doc. Every durable item is an *entry*
    delimited by a machine-readable HTML marker:

        <!-- entry id=GR-0001 source=TASK-034 sha=1d08cfe status=active -->
        - **GR-0001** - ...insight... _(TASK-034 @1d08cfe)_

  * The marker is the contract. Human-visible bullets are for reading; the
    conservation checker only trusts markers.
  * Proposals are produced by *copying every existing entry verbatim* and only
    appending new ones / flipping markers to ``status=superseded``. The model can
    never silently drop an entry; the checker independently proves it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Layout / constants
# --------------------------------------------------------------------------- #

SECTIONS: list[tuple[str, str]] = [
    ("General Rules", "GR"),
    ("Architecture Gotchas", "AG"),
    ("Policy & Edict Rules", "PE"),
    ("Verified Snippets", "VS"),
]
SECTION_TITLES: list[str] = [title for title, _ in SECTIONS]
SECTION_PREFIX: dict[str, str] = {title: prefix for title, prefix in SECTIONS}

SLUG_FILES: tuple[str, ...] = (
    "state.json",
    "plan.md",
    "final-report.md",
    "verification.md",
    "traceability.md",
    "review.md",
)

# Highest-signal subset for cheap bulk backfill: the distilled outcome, the
# proven checks, and the human review notes. Drops plan/traceability/state.
LEAN_SLUG_FILES: tuple[str, ...] = (
    "final-report.md",
    "verification.md",
    "review.md",
)

# Completion marker stamped as the LAST line of every finished proposal. A
# proposal lacking it is treated as partial/untrusted and is never approvable.
COMPLETION_PREFIX = "<!-- dream:proposal-complete"

# Rendered under any section that has no entries; also recognized on parse so it
# never survives a round-trip as stray "intro" text.
EMPTY_PLACEHOLDER = "_No entries yet._"

MARKER_RE = re.compile(r"^<!--\s*entry\s+(?P<attrs>.*?)\s*-->\s*$")
SECTION_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
ATTR_RE = re.compile(r"([A-Za-z][\w-]*)=(\S+)")

REQUIRED_ATTRS: tuple[str, ...] = ("id", "source", "sha", "status")


# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #


def repo_root() -> Path:
    """Repository root via git, with a structural fallback."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.SubprocessError, OSError):
        # .../.workflow/_dream/bin/dream_lib.py -> repo root is parents[3]
        return Path(__file__).resolve().parents[3]


def dream_dir() -> Path:
    return repo_root() / ".workflow" / "_dream"


def playbook_path() -> Path:
    return dream_dir() / "playbook.md"


def queue_dir() -> Path:
    return dream_dir() / "queue"


def proposals_dir() -> Path:
    return dream_dir() / "proposals"


def approved_dir() -> Path:
    return proposals_dir() / "approved"


def ledger_dir() -> Path:
    return dream_dir() / "ledger"


def prompts_dir() -> Path:
    return dream_dir() / "prompts"


def digest_path() -> Path:
    return dream_dir() / "playbook.digest.md"


def now_stamp() -> str:
    """UTC timestamp safe for filenames, e.g. 20260628T143501Z."""
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------- #
# Entry model
# --------------------------------------------------------------------------- #


@dataclass
class Entry:
    id: str
    source: str
    sha: str
    status: str  # "active" | "superseded"
    section: str = ""
    text: str = ""
    superseded_by: str | None = None
    merged_into: str | None = None
    scopes: list[str] = field(default_factory=list)  # subsystem tags for differential loading (AG/PE only; comma-sep in marker)

    @property
    def prefix(self) -> str:
        return self.id.split("-", 1)[0]

    @property
    def number(self) -> int:
        try:
            return int(self.id.split("-", 1)[1])
        except (IndexError, ValueError):
            return -1


@dataclass
class Section:
    title: str
    prefix: str
    intro: str = ""
    entries: list[Entry] = field(default_factory=list)


@dataclass
class Playbook:
    preamble: str
    sections: list[Section]

    def all_entries(self) -> list[Entry]:
        return [e for s in self.sections for e in s.entries]

    def section(self, title: str) -> Section:
        for s in self.sections:
            if s.title == title:
                return s
        raise KeyError(f"unknown section: {title!r}")


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def parse_attrs(raw: str) -> dict[str, str]:
    return {k: v for k, v in ATTR_RE.findall(raw)}


def _entry_from_attrs(attrs: dict[str, str], section: str, text: str) -> Entry:
    missing = [k for k in REQUIRED_ATTRS if not attrs.get(k)]
    if missing:
        raise ValueError(
            f"entry marker missing required attr(s) {missing}: {attrs!r}"
        )
    return Entry(
        id=attrs["id"],
        source=attrs["source"],
        sha=attrs["sha"],
        status=attrs["status"],
        section=section,
        text=text,
        superseded_by=attrs.get("superseded-by"),
        merged_into=attrs.get("merged-into"),
        scopes=[s.strip() for s in attrs["scope"].split(",") if s.strip()]
        if attrs.get("scope")
        else [],
    )


def parse_markers(text: str) -> list[Entry]:
    """Flat, section-agnostic scan of every entry marker.

    Used by the conservation checker: it trusts ONLY the markers, never the
    surrounding prose. Raises ValueError on a malformed marker.
    """
    entries: list[Entry] = []
    for line in text.splitlines():
        m = MARKER_RE.match(line)
        if not m:
            continue
        entries.append(_entry_from_attrs(parse_attrs(m.group("attrs")), "", ""))
    return entries


def _parse_section_body(body: list[str], title: str) -> tuple[str, list[Entry]]:
    first: int | None = None
    for j, line in enumerate(body):
        if MARKER_RE.match(line):
            first = j
            break
    if first is None:
        intro_only = "\n".join(body).strip()
        return ("" if intro_only == EMPTY_PLACEHOLDER else intro_only), []

    intro = "\n".join(body[:first]).strip()
    if intro == EMPTY_PLACEHOLDER:
        intro = ""
    entries: list[Entry] = []
    j = first
    while j < len(body):
        m = MARKER_RE.match(body[j])
        if not m:
            j += 1
            continue
        k = j + 1
        text_lines: list[str] = []
        while k < len(body) and not MARKER_RE.match(body[k]):
            text_lines.append(body[k])
            k += 1
        text = "\n".join(text_lines).strip()
        entries.append(_entry_from_attrs(parse_attrs(m.group("attrs")), title, text))
        j = k
    return intro, entries


def parse_playbook(text: str) -> Playbook:
    """Structured parse preserving section order and verbatim entry bodies."""
    lines = text.splitlines()
    i = 0
    preamble: list[str] = []
    while i < len(lines) and not SECTION_RE.match(lines[i]):
        preamble.append(lines[i])
        i += 1

    parsed: dict[str, Section] = {}
    while i < len(lines):
        m = SECTION_RE.match(lines[i])
        assert m is not None
        title = m.group("title").strip()
        i += 1
        body: list[str] = []
        while i < len(lines) and not SECTION_RE.match(lines[i]):
            body.append(lines[i])
            i += 1
        intro, entries = _parse_section_body(body, title)
        prefix = SECTION_PREFIX.get(title, "")
        parsed[title] = Section(
            title=title, prefix=prefix, intro=intro, entries=entries
        )

    # Always present the canonical sections in canonical order; keep any extra
    # (unknown) sections after them so nothing a human added is lost.
    sections: list[Section] = []
    for title, prefix in SECTIONS:
        sections.append(parsed.pop(title, Section(title=title, prefix=prefix)))
    sections.extend(parsed.values())
    return Playbook(preamble="\n".join(preamble).rstrip(), sections=sections)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def render_entry(e: Entry) -> str:
    attrs = f"id={e.id} source={e.source} sha={e.sha} status={e.status}"
    if e.superseded_by:
        attrs += f" superseded-by={e.superseded_by}"
    if e.merged_into:
        attrs += f" merged-into={e.merged_into}"
    if e.scopes:
        attrs += f" scope={','.join(e.scopes)}"
    body = e.text if e.text else f"- **{e.id}** _(no text)_"
    return f"<!-- entry {attrs} -->\n{body}"


def render_playbook(pb: Playbook) -> str:
    out: list[str] = []
    if pb.preamble.strip():
        out.append(pb.preamble.rstrip())
        out.append("")
    for sec in pb.sections:
        out.append(f"## {sec.title}")
        out.append("")
        if sec.intro.strip():
            out.append(sec.intro.rstrip())
            out.append("")
        if not sec.entries:
            out.append(EMPTY_PLACEHOLDER)
            out.append("")
            continue
        for e in sec.entries:
            out.append(render_entry(e))
            out.append("")
    return "\n".join(out).rstrip() + "\n"


_DIGEST_PREFIX_RE = re.compile(r"^-\s*\*\*[\w-]+\*\*\s*-?\s*")
_DIGEST_SUFFIX_RE = re.compile(r"\s*_\([^)]*\)_\s*$")


def _digest_text(text: str) -> str:
    one = " ".join(text.split())
    one = _DIGEST_PREFIX_RE.sub("", one)
    return _DIGEST_SUFFIX_RE.sub("", one).strip()


def playbook_digest(pb: Playbook) -> str:
    """Compact, marker-free view of the playbook for prompt context.

    Far fewer tokens than the full marked-up doc (drops HTML markers and
    provenance), while keeping IDs so the model can still target supersedes.
    AG/PE entries include their scope tag in brackets for differential loading.
    """
    lines: list[str] = []
    for sec in pb.sections:
        lines.append(f"[{sec.title}]")
        if not sec.entries:
            lines.append("  (none)")
            continue
        for e in sec.entries:
            scope_tag = f" [{','.join(e.scopes)}]" if e.scopes else ""
            lines.append(f"  {e.id} ({e.status}){scope_tag}: {_digest_text(e.text)}")
    return "\n".join(lines)


def render_digest_text(pb: Playbook) -> str:
    """Full body of the standalone digest file agents read at startup.

    A short header plus the compact, marker-free ``playbook_digest`` view. The
    digest is a DERIVED artifact: ``playbook.md`` remains the source of truth and
    the drill-down reference (full text, provenance, superseded history).

    Loading tiers:
      - GR + VS: always load — universal rules and verified commands (~2k tokens).
      - AG + PE: load only the scopes relevant to the current task. Each AG/PE
        entry shows its scope tag in brackets, e.g. [policy-gate], [sqlite].
        Scopes: auth, contracts, correlation, directive, evals, feed, hashing,
        ledger, metrics, outbox, policy-gate, sigma, sqlite, stamp, startup.
    """
    n_total = len(pb.all_entries())
    n_active = sum(1 for e in pb.all_entries() if e.status == "active")
    header = (
        "# Praetor Dream Playbook - digest\n"
        "\n"
        "Compact, auto-generated view of `playbook.md` for cheap startup context.\n"
        "DO NOT EDIT: regenerated by `approve.py` and `bin/render_digest.py`.\n"
        "Full text, provenance, and superseded history live in `playbook.md`.\n"
        f"{n_active} active / {n_total} total entries.\n"
        "\n"
        "Loading tiers: GR+VS always; AG+PE load only matching scope(s) for the task.\n"
        "Entries may carry multiple comma-separated scopes (e.g. policy-gate,ledger);\n"
        "union the scopes your task touches — cross-subsystem entries appear in both.\n"
        "Scopes: auth, contracts, correlation, directive, evals, feed, hashing,\n"
        "        ledger, metrics, outbox, policy-gate, sigma, sqlite, stamp, startup.\n"
    )
    return header + "\n" + playbook_digest(pb) + "\n"


# --------------------------------------------------------------------------- #
# ID allocation
# --------------------------------------------------------------------------- #


def max_number(pb: Playbook, prefix: str) -> int:
    nums = [e.number for e in pb.all_entries() if e.prefix == prefix]
    return max(nums, default=0)


# --------------------------------------------------------------------------- #
# Atomic IO
# --------------------------------------------------------------------------- #


def atomic_write(path: Path, data: str) -> None:
    """Write ``data`` to ``path`` atomically: temp -> fsync -> os.replace.

    A crash mid-write leaves only a dotfile temp (``.tmp-*``), never a file that
    looks like a finished, approvable artifact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".tmp-{os.getpid()}-{path.name}"
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, data.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(path))
    _fsync_dir(path.parent)


def _fsync_dir(directory: Path) -> None:
    # Best effort; directory fsync is not supported on Windows and will raise.
    try:
        fd = os.open(str(directory), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_stale_temps(directory: Path) -> None:
    if not directory.exists():
        return
    for p in directory.glob(".tmp-*"):
        try:
            p.unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------- #
# Slug / git helpers
# --------------------------------------------------------------------------- #


def slug_dir(slug: str) -> Path:
    return repo_root() / ".workflow" / slug


def slug_status(slug: str) -> str | None:
    state = slug_dir(slug) / "state.json"
    if not state.exists():
        return None
    try:
        data: dict[str, Any] = json.loads(state.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = data.get("status")
    return value if isinstance(value, str) else None


def read_slug_bundle(
    slug: str, per_file_cap: int = 16000, lean: bool = False
) -> str:
    """Concatenate a slug's reliably-present files into one delimited blob.

    ``lean=True`` sends only the highest-signal subset (final report, verification
    ledger, review) to cut tokens on bulk backfill.
    """
    d = slug_dir(slug)
    if not d.exists():
        raise FileNotFoundError(f"slug dir not found: {d}")
    parts: list[str] = []
    for name in LEAN_SLUG_FILES if lean else SLUG_FILES:
        fp = d / name
        if not fp.exists():
            continue
        content = fp.read_text(encoding="utf-8")
        if len(content) > per_file_cap:
            content = content[:per_file_cap] + "\n...[truncated]...\n"
        parts.append(f"===== {slug}/{name} =====\n{content.rstrip()}\n")
    if not parts:
        raise FileNotFoundError(f"no readable slug files under {d}")
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Claude headless synthesis
# --------------------------------------------------------------------------- #


def claude_executable() -> str:
    exe = shutil.which("claude")
    if exe is None:
        raise RuntimeError("`claude` CLI not found on PATH")
    return exe


def run_claude_json(
    *,
    system_prompt: str,
    user_prompt: str,
    schema_json: str,
    model: str,
    timeout: int = 300,
) -> tuple[dict[str, Any], float]:
    """Run a sandboxed, tool-less headless synthesis; return (parsed JSON, cost_usd).

    Flags are all verified against ``claude --help``:
      -p / --print, --output-format json, --json-schema, --tools "" (disable all
      tools => no repo access), --no-session-persistence, --model, --system-prompt.
    """
    cmd = [
        claude_executable(),
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
        "--tools",
        "",
        "--no-session-persistence",
        "--model",
        model,
        "--system-prompt",
        system_prompt,
    ]
    proc = subprocess.run(
        cmd,
        input=user_prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude exited {proc.returncode}: {proc.stderr.strip()[:500]}"
        )
    envelope: dict[str, Any] = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude reported error: {envelope.get('subtype')}")
    result = envelope.get("result")
    if isinstance(result, str):
        data: dict[str, Any] = json.loads(result)
    elif isinstance(result, dict):
        data = result
    else:
        raise RuntimeError(f"unexpected result type: {type(result).__name__}")
    cost_raw = envelope.get("total_cost_usd", 0.0)
    cost = float(cost_raw) if isinstance(cost_raw, (int, float)) else 0.0
    return data, cost


# --------------------------------------------------------------------------- #
# Synthesis: schema, prompt, code-assembled conservation
# --------------------------------------------------------------------------- #

# json-schema the model output is validated against. It may only ADD entries (and
# optionally point at existing IDs it supersedes) - never rewrite the playbook.
OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "section": {"type": "string", "enum": SECTION_TITLES},
                    "text": {"type": "string"},
                    "scope": {"type": "string"},  # subsystem tag, required for AG/PE
                    "supersedes": {"type": "array", "items": {"type": "string"}},
                    "rationale": {"type": "string"},
                },
                "required": ["section", "text"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["candidates"],
}


def build_synthesis_prompt(
    slug: str,
    sha: str,
    playbook_text: str,
    bundle: str,
    existing_ids: list[str] | None = None,
) -> str:
    if existing_ids is None:
        existing_ids = [e.id for e in parse_markers(playbook_text)]
    return (
        f"You are consolidating completed Praetor task `{slug}` (commit {sha}) "
        f"into a long-term engineering playbook.\n\n"
        f"## Current playbook (READ-ONLY context, for dedup and supersede "
        f"decisions)\n\n"
        f"Existing entry IDs you may reference in `supersedes`: "
        f"{existing_ids or '(none yet)'}\n\n"
        f"```markdown\n{playbook_text.strip()}\n```\n\n"
        f"## Completed task source files\n\n"
        f"{bundle}\n\n"
        f"## Your job\n\n"
        "Emit ONLY durable, reusable insights as additive `candidates`. Each "
        "candidate is one entry: pick the best-fitting `section`, write a crisp "
        "one- or two-sentence `text` (do NOT include an ID or provenance - those "
        "are stamped automatically). For AG and PE candidates, also set `scope` to "
        "the subsystem(s) this entry applies to — comma-separated from: auth, "
        "contracts, correlation, directive, evals, feed, hashing, ledger, metrics, "
        "outbox, policy-gate, sigma, sqlite, stamp, startup. Use multiple scopes "
        "when an entry is genuinely cross-subsystem (e.g. 'policy-gate,ledger' for "
        "an entry about wiring ledger appends inside the gate transaction). "
        "Use `supersedes` only to point at an existing "
        "entry ID that your new entry replaces. Skip one-off debugging noise, "
        "restating the obvious, or anything not reusable on a future task. Prefer "
        "fewer, higher-signal entries. If nothing is worth keeping, return an empty "
        "`candidates` array."
    )


def apply_candidates(
    pb: Playbook, slug: str, sha: str, candidates: list[dict[str, Any]]
) -> tuple[list[str], list[str], list[str]]:
    """Fold model `candidates` into `pb` in place (conservation by construction).

    Existing entries are never removed - only appended to, or flipped to
    status=superseded. Returns (added_ids, superseded_ids, warnings).
    """
    short = sha[:7]
    warnings: list[str] = []
    added_ids: list[str] = []
    superseded_ids: list[str] = []

    by_id: dict[str, Entry] = {e.id: e for e in pb.all_entries()}
    counters: dict[str, int] = {
        prefix: max_number(pb, prefix) for _, prefix in SECTIONS
    }

    for cand in candidates:
        section = cand.get("section", "")
        text = str(cand.get("text", "")).strip()
        if section not in SECTION_PREFIX or not text:
            warnings.append(f"skipped malformed candidate: {cand!r}")
            continue
        prefix = SECTION_PREFIX[section]
        counters[prefix] += 1
        new_id = f"{prefix}-{counters[prefix]:04d}"
        raw_scope = str(cand.get("scope", "")).strip()
        scopes = [s.strip() for s in raw_scope.split(",") if s.strip()] if raw_scope else []
        bullet = f"- **{new_id}** - {text} _({slug} @{short})_"
        entry = Entry(
            id=new_id,
            source=slug,
            sha=short,
            status="active",
            section=section,
            text=bullet,
            scopes=scopes,
        )
        pb.section(section).entries.append(entry)
        by_id[new_id] = entry
        added_ids.append(new_id)

        for target in cand.get("supersedes", []) or []:
            old = by_id.get(target)
            if old is None:
                warnings.append(f"{new_id}: supersedes unknown id {target!r} (ignored)")
                continue
            if old.status == "superseded":
                warnings.append(f"{new_id}: {target} already superseded (ignored)")
                continue
            old.status = "superseded"
            old.superseded_by = new_id
            if "_(superseded by" not in old.text:
                old.text = f"{old.text}  _(superseded by {new_id})_"
            superseded_ids.append(target)

    return added_ids, superseded_ids, warnings


def completion_marker(**fields: object) -> str:
    """Render the trailing proposal-complete marker line from key=value fields."""
    attrs = " ".join(f"{k}={v}" for k, v in fields.items())
    return f"{COMPLETION_PREFIX} {attrs} -->"
