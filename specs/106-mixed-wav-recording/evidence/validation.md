# Validation Receipt

**Lane**: high-risk capture, storage, external-processing, deletion and
installed-app UX. All results below are local and content-free.

## 2026-07-17

- Post-review regression: a v5 package now fails closed when either required
  capture origin produces no frames. The timeline does not publish a
  microphone-only or system-audio-only package; `RecordingAudioTimelineTests`
  and `SystemAudioRecordingPackageTests` cover both forms of the failure.
- Focused macOS v5 group after the native desktop-upload sequence proof and
  parallel-version contract correction: `216` tests passed, `0` failures.
- The current quickstart server v5 group passed: `97` tests, `0` failures;
  one pre-existing Starlette TestClient deprecation warning.
- Focused server v5 and release-integration group: `117` tests passed,
  `11` expected skips, `0` failures; one pre-existing Starlette TestClient
  deprecation warning.
- `swift run --package-path apps/macos ContractValidation`: passed.
- Shell syntax for the modified v5 validators and manual-gate script: passed.
- v5 metadata validator self-tests and manual-gate self-test: passed.
- `PYTHONPATH=src uv run --extra dev ruff check .`: passed.
- `docker compose -f infra/docker-compose.yml config`: passed.
- `git diff --check`: passed.
- `infra/scripts/ci-local.sh`: passed again after the native desktop-upload
  sequence proof and parallel-version contract correction; the macOS full
  suite reported `564` tests, `0` failures, and the server full suite reported
  `1781` passed, `28` skipped, with the same pre-existing TestClient warning.
  Its RLS production probe remained correctly blocked because this local lane
  has no disposable PostgreSQL test database; it is not represented as
  deployed proof.
- Convergence check for T067: native `CMSampleBuffer` PTS are now retained as
  source-domain timestamps and only admitted after a bounded, stable callback
  observation against the CoreMedia host clock. Missing or unstable mappings
  fail closed before frames are written. The merge with `v2026.07.17.9`
  preserved that guard; the focused macOS group reported `235` tests, `0`
  failures, the v5 server group reported `97` tests, `0` failures, and the
  refreshed full local gate reported `567` macOS tests, `0` failures and
  `1781` server tests passed with `28` expected skips. The pre-existing
  TestClient deprecation warning remains non-feature evidence.
- GitHub reconciliation: every `[X]` task has its matching Feature 106 issue
  closed with a Russian metadata-only validation comment. The only open Feature
  106 execution issues are `T063` and `T064`; `T066` is marked
  complete and its closure is recorded with this checkpoint. The
  `validate_issue_canon.py` check passed for all `210` Spec Kit issues after
  the completed task issues were closed.

The installed-app hardware, exact-baseline rollback and release/deploy gates are
intentionally still open and are documented in `hardware-acceptance.md`.

## 2026-07-18

- Focused macOS v5/capture/upload/UI group: `219` tests passed, `0` failures.
- Focused server ingest/processing/deletion/playback group: `97` passed,
  `0` failures, with the same pre-existing Starlette TestClient deprecation
  warning.
- `bash -n` for the recording validator and local installer script, production
  Compose config, and server Ruff check: all passed.
- `infra/scripts/ci-local.sh`: passed; full macOS suite `567` passed,
  `0` failures; full server suite `1781` passed, `28` expected skips, `0`
  failures; one pre-existing TestClient warning. The RLS production probe was
  correctly blocked because no disposable PostgreSQL test database was
  provided, so it is not presented as deployment evidence.
- No raw audio, transcript, secret or private provider payload was added to
  this repository or to the validation receipt.
