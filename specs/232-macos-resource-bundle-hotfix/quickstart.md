# Quickstart: Безопасный запуск macOS после обновления

## 1. Focused resolver tests

```sh
cd apps/macos
swift test --filter MeetingTargetRegistryTests
```

Expected: packaged-layout resolution and missing-resource cases pass without a
Swift trap; existing registry cache/bundle tests remain green.

## 2. Smoke self-test

```sh
apps/macos/Installer/Scripts/test-packaged-app-launch.sh
```

Expected: living child passes, immediate exit fails, and an unrelated process
remains alive.

## 3. Production-like package

Build the universal public candidate with the existing Developer ID release
path. Before any appcast mutation:

```sh
apps/macos/Scripts/validate-packaged-app-launch.sh /absolute/path/GRAF.app 5 arm64
apps/macos/Scripts/validate-packaged-app-launch.sh /absolute/path/GRAF.app 5 x86_64
file /absolute/path/GRAF.app/Contents/MacOS/GRAF
```

Expected: resource bundle and baseline JSON exist under `Contents/Resources`,
the binary contains arm64 and x86_64, and the exact candidate process survives
five seconds. Repeat ten times for SC-001. Run the x86_64 slice with Rosetta
when available; otherwise record that hardware gate as blocked, not passed.

Copy the candidate to a temporary location, remove only the copied baseline
resource and launch it. Expected: no startup crash; meeting detection is
truthfully unavailable or resolves from the existing cache/remote path.

## 4. Repository gates

```sh
infra/scripts/ci-local.sh --fast
infra/scripts/cd-remote.sh --dry-run --branch master
```

After merge and release metadata preparation, freeze the exact clean candidate
and run exactly one candidate-bound `infra/scripts/ci-local.sh --full` as
described in `docs/agent-guidance/release-and-validation.md`.

## 5. Public release gates

- Confirm app and PKG Developer ID signatures, Apple Accepted notarization,
  staples and Gatekeeper acceptance.
- Validate manual install over `v2026.09.02.1`.
- Validate Sparkle update from the confirmed previous healthy public version.
- Re-download public ZIP/PKG/checksum/release notes and verify version, bytes,
  SHA-256, signature, UUID and startup against the exact release SHA.
- Publish `graf-appcast.xml` last, then re-download and validate it.
