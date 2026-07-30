# Reverse Spec + Debt Ledger Extraction

**Tier:** T2  
**Goal:** Produce `AS_BUILT.md` (reverse spec of the system that exists) and `DEBT_LEDGER.md` (recoverable MVP-era traces) via structured probes, not open-ended discovery.  
**Status:** complete  
**Updated:** 2026-07-18

## Extraction checklist (fixed probes)

### AS_BUILT probes
1. Module inventory from `src/praetor/**` — done
2. Public interfaces / contracts — done
3. Data flows — done
4. Invariants claimed vs enforced — done (25 rows)
5. Error-handling posture — done
6. Test coverage map — done

### DEBT_LEDGER probes
1. TODO/FIXME/HACK comments — done (none classic)
2. Git log debt language — done
3. Hardcoded constants — done
4. Swallowed exceptions — done
5. Single-implementation abstractions — done
6. High-complexity functions — done
7. Untested paths — done
8. Pinned dependencies — done (no lockfile)

## Deliverables
- `AS_BUILT.md` (repo root) — written
- `DEBT_LEDGER.md` (repo root) — written

## Verification
- Structured probes via explore subagents + local greps on Protocols, Outcome Matrix finishers, schemas, pyproject
- Shell git-log recheck was flaky in harness; git signals taken from explore agent probe (hashes cited in ledger)
