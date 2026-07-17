# Validation Receipt

**Lane**: high-risk capture, storage, external-processing, deletion and
installed-app UX. All results below are local and content-free.

## 2026-07-17

- Post-review regression: a v5 package now fails closed when either required
  capture origin produces no frames. The timeline does not publish a
  microphone-only or system-audio-only package; `RecordingAudioTimelineTests`
  and `SystemAudioRecordingPackageTests` cover both forms of the failure.
- Focused macOS v5 group after that regression: `215` tests passed, `0`
  failures.
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
  and ingest-validation ordering regression were corrected, the
  `v2026.07.17.6` integration was merged, and the required-input regression
  was added; the macOS full suite reported `563` tests, `0` failures, and the
  server full suite reported `1781` passed, `28` skipped, with the same
  pre-existing TestClient warning. Its RLS production probe remained correctly
  blocked because this local lane has no disposable PostgreSQL test database;
  it is not represented as deployed proof.
- GitHub reconciliation: every `[X]` task has its matching Feature 106 issue
  closed with a Russian metadata-only validation comment. The only open Feature
  106 execution issues are `T049`, `T063` and `T064`; `T066` is marked
  complete and its closure is recorded with this checkpoint. The
  `validate_issue_canon.py` check passed for all `211` Spec Kit issues.

The installed-app hardware, exact-baseline rollback and release/deploy gates are
intentionally still open and are documented in `hardware-acceptance.md`.
