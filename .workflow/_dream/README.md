# Dream loop — local memory consolidation

An out-of-band system that turns completed `.workflow/<slug>` tasks into a curated
long-term **playbook**. Modeled on the "memory store + past sessions in → a *separate*
output store; input never mutated; you review before adopting" pattern.

It only ever adds files under `.workflow/_dream/` plus one local git hook. It never
touches `src/`, `tests/`, migrations, or config.

## Pipeline

```
commit ──▶ post-commit hook ──▶ queue/            (enqueue {slug, sha}; no synthesis)
                                   │
                consolidate.py ◀───┘  reads playbook.md (read-only) + slug files
                       │              calls Claude headless (tool-less, json-schema)
                       ▼
               proposals/<ts>-<slug>.md            (the OUTPUT store; atomic write)
                       │
            conservation_check.py                  (independent gate; nonzero on violation)
                       │
                  approve.py  (you)  ──▶ playbook.md (atomic promote) + ledger/ + commit
```

## Trust model

The synthesis model is **untrusted**. It runs with `--tools ""` (no repo access) and may
only *suggest* additive entries. `consolidate.py` copies every existing entry **verbatim**
and appends — the model cannot drop or rewrite an entry. `conservation_check.py` then
proves conservation independently. Nothing enters `playbook.md` until **you** run
`approve.py`. The review gate is the mitigation for memory poisoning.

## Conservation invariant (deterministic, enforced in code)

Every existing playbook entry must end up **retained**, **superseded-by** a new entry, or
**merged-into** one — never silently dropped or duplicated. Every new entry carries
provenance (source slug + commit SHA). `conservation_check.py` exits nonzero on any
violation or a missing completion marker.

## Entry format

```
<!-- entry id=GR-0001 source=TASK-034 sha=1d08cfe status=active -->
- **GR-0001** - <insight> _(TASK-034 @1d08cfe)_
```

The HTML marker is the contract; the bullet is for humans. Sections and their ID prefixes:
General Rules `GR`, Architecture Gotchas `AG`, Policy & Edict Rules `PE`, Verified Snippets `VS`.

## Commands

```bash
# enqueue (normally the hook does this)
python .workflow/_dream/bin/enqueue.py --slug TASK-034 --sha <sha>

# synthesize a proposal from the oldest queue entry (default model: opus; $DREAM_MODEL overrides)
python .workflow/_dream/bin/consolidate.py

# validate a proposal against the current playbook (0 = PASS, 1 = violations)
python .workflow/_dream/bin/conservation_check.py --proposal proposals/<ts>-<slug>.md

# promote a reviewed proposal (you run this)
python .workflow/_dream/bin/approve.py --proposal proposals/<ts>-<slug>.md
```

## The hook

`.git/hooks/post-commit` only enqueues. It is loop-safe: it skips commits carrying the
`[dream-promote]` marker and commits that touch only `.workflow/_dream/`. (Note: `git
commit --no-verify` does **not** suppress `post-commit`, so these in-hook guards — not
`--no-verify` — are what actually breaks the loop.) Install/refresh it with
`.workflow/_dream/bin/install-hook.sh`.
