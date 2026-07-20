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

## 2026-07-18 — stop-drain closeout rerun

- The focused macOS quickstart group after the stop-drain change passed `219`
  tests with `0` failures. `SystemAudioCaptureServiceTests` includes the
  source-level assertion for draining the serial callback queue before
  `stopCapture`.
- The focused server quickstart group passed `97` tests with `0` failures;
  Ruff reported `All checks passed!`. The only test warning remains the
  pre-existing Starlette TestClient deprecation warning.
- `swift run --package-path apps/macos ContractValidation` passed;
  `sh apps/macos/Scripts/validate-recording-artifact-format.sh` passed its
  `98` selected tests and reported `no-legacy-audio-driver: PASS`;
  `bash -n apps/macos/Scripts/validate-recording-artifact-format.sh` and
  `docker compose -f infra/docker-compose.yml config` passed.
- The canonical `infra/scripts/ci-local.sh` gate passed after the code change:
  macOS `567` tests passed with `0` failures, server `1781` passed with `28`
  expected skips and `0` failures, and the deployment evidence scan passed.
  Its RLS production probe was correctly blocked because no disposable
  PostgreSQL database was supplied; this remains local validation only.
- `git diff --check` passed. No raw audio, transcript, secret, private path or
  provider payload was added. Exact pre-v5 baseline rollback remains the only
  open Feature 106 acceptance gate (T064); no release or deployment claim is
  made.

## 2026-07-20 — master v2026.07.20.1 integration closeout

- `origin/master` was merged into the feature branch without conflicts. The
  active feature pointer in `AGENTS.md` remains
  `specs/106-mixed-wav-recording/plan.md`; the master release/bootstrap,
  cabinet, support and server updates are included.
- Post-merge focused macOS recording/upload/UI group passed `252` tests with
  `0` failures. The full macOS suite in `infra/scripts/ci-local.sh` passed
  `573` tests with `0` failures.
- The focused v5 server group passed `97` tests with `0` failures against the
  disposable PostgreSQL runner. The full PostgreSQL runner collected `1872`
  tests and the canonical `infra/scripts/ci-local.sh` completed with
  `ci_local_result=pass`; Ruff, Python compile, RLS hardening validation and
  deployment evidence scan also passed.
- `ContractValidation`, the recording artifact validator (`97` selected
  tests, `no-legacy-audio-driver: PASS`), both modified shell syntax checks,
  production Compose config and `git diff --check` passed after the merge.
- No raw audio, transcript, secret, private path or provider payload was added.
  The old-baseline rehearsal is now a deferred contingency and is not a current
  v5 acceptance gate; no release, deployment or user-data mutation is claimed
  here.
