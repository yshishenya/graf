# Quickstart: Видимый прогресс загрузки записи

Run commands from the repository root.

## Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/128-upload-progress-visibility \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected: JSON points to Feature 128 after `tasks.md` is generated.

## Focused projection and UI contract

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter CaptureControlTests
```

Expected: upload custody tests pass for active, queued, retrying, finalizing,
uploaded and accessibility-safe states. The source contract must confirm that
the existing local row consumes the bounded progress value and has no manual
retry/stop controls.

## Build and repository validation

```sh
swift build --package-path apps/macos
git diff --check
infra/scripts/ci-local.sh
```

Expected: native build and canonical local CI pass. The no-deploy runner may
report its documented production-RLS probe boundary as blocked because no live
production database is supplied; this feature does not claim production proof.

## Validation evidence (2026-07-25)

- Focused XCTest: `CaptureControlTests`, `41/41` passed.
- Native build: `swift build --package-path apps/macos`, PASS.
- `git diff --check` and metadata-only forbidden-content scan, PASS.
- `infra/scripts/ci-local.sh`, PASS: macOS `639/639`, server `2420 passed / 1
  skipped`, strict PostgreSQL `41 passed / 1 skipped`, lint, compile, Compose
  and deployment evidence scan passed.
- `rls_validation_result=blocked` is an expected no-deploy boundary: live
  production probe was not attempted because no production database was
  supplied.

## Manual synthetic review

Using metadata-only fixtures, inspect the existing local list for 0%, 25%, 75%
and 100% accepted-byte snapshots. Confirm:

1. active upload is understandable without opening the inspector;
2. 100% accepted bytes still says that finalization/checking continues;
3. queued/retrying/blocked rows show no stale progress;
4. VoiceOver reads the state and percentage;
5. no audio, transcript, private title, path, credential or server identifier is
   present in output or evidence.

## Release boundary

No `cd-remote.sh` command is part of this slice. Installed-app and production
owner-journey evidence remain separate gates from Feature 052.
