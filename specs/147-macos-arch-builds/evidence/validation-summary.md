# Feature 147 Validation Summary

Дата: 2026-08-12

## Пройдено

- `17 passed` — focused server tests for the public download page and static
  asset contract.
- `3 passed` — `swift test --package-path apps/macos --filter PlatformSupportTests`.
- Universal installer build completed for
  `arm64-apple-macosx14.5` and `x86_64-apple-macosx14.5`.
- `lipo -archs` reported `x86_64 arm64` for the app and staged app.
- `validate-system-audio-capture-pivot.sh --installer-app-only` passed.
- Installer components contain only `graf-desktop-app.pkg`; no driver package or
  distribution reference was found.

## Открытые блокеры

- `swift run --package-path apps/macos ContractValidation` currently stops on a
  pre-existing app-start-path invariant failure: `App start path must expose
  blocker clearing, preparing state, and permission prompts`.
- `bash infra/scripts/ci-local.sh` reached `1253 passed, 4 skipped`, then failed
  two pre-existing RLS inventory assertions because the current dirty tree adds
  `playback_normalization_attempts`, `playback_normalization_jobs`, and
  `playback_backfill_runs` without matching inventory fixtures/migration maps.

These blockers are outside the universal installer slice. T021 and T022 remain
open until the repository owner resolves them and reruns the complete gates.
