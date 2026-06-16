"""Parse savedsearches.conf search lines for portability tests."""

from __future__ import annotations


def parse_savedsearch_queries(conf_text: str) -> dict[str, str]:
    """Return mapping of stanza name -> search query string."""
    queries: dict[str, str] = {}
    stanza: str | None = None
    for line in conf_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            stanza = stripped[1:-1]
            continue
        if stanza is None:
            continue
        if stripped.startswith("search = "):
            queries[stanza] = stripped.removeprefix("search = ")
    return queries
