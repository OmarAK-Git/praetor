# Test fixtures

Fixture data for Praetor tests. Task 1 provides only the manifest stub; scenario and telemetry fixtures are added in later tasks (eval harness, correlation, detection portability).

## Layout

- `fixture_manifest.yaml` — index of fixture entries (stub in Task 1; extended later)

## Usage

Smoke tests load `fixture_manifest.yaml` from this directory. Downstream tasks register paths and checksums in the manifest per `docs/plan.md`.
