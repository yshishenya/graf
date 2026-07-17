# Validation Receipt

**Lane**: high-risk capture, storage, external-processing, deletion and
installed-app UX. All results below are local and content-free.

## 2026-07-17

- Focused macOS v5 group after integrating `v2026.07.17.6`: `213` tests
  passed, `0` failures.
- Focused server v5 and release-integration group: `117` tests passed,
  `11` expected skips, `0` failures; one pre-existing Starlette TestClient
  deprecation warning.
- `swift run --package-path apps/macos ContractValidation`: passed.
- Shell syntax for the modified v5 validators and manual-gate script: passed.
- v5 metadata validator self-tests and manual-gate self-test: passed.
- `PYTHONPATH=src uv run --extra dev ruff check .`: passed.
- `docker compose -f infra/docker-compose.yml config`: passed.
- `git diff --check`: passed.
- `infra/scripts/ci-local.sh`: passed after the stale deleted-view test path
  and ingest-validation ordering regression were corrected and the
  `v2026.07.17.6` integration was merged; the macOS full suite reported `561`
  tests, `0` failures, and the server full suite reported `1781` passed, `28`
  skipped, with the same pre-existing TestClient warning.

The installed-app hardware, exact-baseline rollback and release/deploy gates are
intentionally still open and are documented in `hardware-acceptance.md`.
