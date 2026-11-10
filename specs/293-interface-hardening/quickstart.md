# Quickstart: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## Prerequisites

- Clean checkout of `293-interface-hardening`.
- Swift 6.0.3 toolchain (CI) or current Xcode toolchain for local diagnosis.
- `apps/server/.venv` prepared with `uv sync --frozen --extra dev` if server tests are needed.
- `/Applications/GRAF Dev.app` and `infra/scripts/dev-harness.sh` for manual UI checks.
- Keychain profiles `graf-notary` and Developer ID identities for release only.
- No secrets, raw audio, transcripts or private meeting content in commands or evidence.

## 1. Fast native diagnosis

```sh
swift build --package-path apps/macos
swift test --package-path apps/macos --filter CaptureStatusPresentationTests
swift test --package-path apps/macos --filter AccountSwitchResetTests
swift test --package-path apps/macos --filter AppMenuBuilderTests
```

Expected: build succeeds; focused tests pass; no new compiler warnings in touched files.

## 2. Full native suite

```sh
apps/macos/Scripts/run-swift-tests.sh
```

Expected: all discovered tests pass or explicitly skipped with a published reason; no source-text-only failure caused by moving code.

## 3. Server/cabinet checks (only if CSS/templates changed)

```sh
cd apps/server
.venv/bin/pytest tests/contract/test_cabinet_frontend_foundation_contract.py -q
.venv/bin/pytest tests/browser -q
```

Expected: no dead-class contract failures; browser tests pass.

## 4. Local diagnostic lane

```sh
infra/scripts/ci-local.sh --fast
```

Expected: fast lane completes; any `coverage=partial` is recorded, not claimed as release evidence.

## 5. Manual UI matrix in the single GRAF Dev

```sh
infra/scripts/dev-harness.sh status --json
infra/scripts/dev-harness.sh build --sha "$(git rev-parse HEAD)"
infra/scripts/dev-harness.sh promote --manifest-id <candidate-manifest>
infra/scripts/dev-harness.sh smoke
```

Scenarios:
1. Idle with permissions granted → Start visible, status truthful.
2. Missing microphone permission → onboarding, no recording started.
3. Active recording → Stop in panel, titlebar, menu and `⌘⇧S`.
4. Closed, minimized and full-screen main window → `⌘⇧S` and the application menu stop the recording.
5. Pause/resume → microphone muted/resumed, system audio continues.
6. Stop → saving, local copy, custody status; quit during save either finalizes or preserves a recoverable package.
7. Account switch with open meeting and calendar prompt → old content gone within 1 s; cookies/localStorage from the old account are not readable.
8. Cabinet offline → each settings section explains local availability: «Запись»/«Уведомления» local; «Аккаунт»/«Календарь»/«Биллинг» require the cabinet.
9. Relaunch → window frame, inspector state and microphone preserved.
10. Selected microphone disconnects during recording → degraded state, system audio continues, Stop works; reconnect restores the previous choice after stop unless another microphone was chosen.
11. Increased contrast/reduce motion/VoiceOver → critical actions and status remain usable.
12. Notification card appears during recording → indicator and Stop stay visible and keyboard-reachable.
13. 60-minute recording with 100-item synthetic queue → `os_signpost` control latency ≤100 ms; Instruments Time Profiler shows no `FileManager`, `DiscoverySession`, JSON decode or network wait on the main thread.

## 6. PR checks

```sh
gh pr checks <pr-number> --watch
python3 scripts/validate-pr-checks.py --repository yshishenya/graf --pr <pr-number>
```

Expected: `governance-fast`, `macos-pr`, `pr-metadata` pass on the exact PR SHA/base.

## 7. Release

```sh
GRAF_RELEASE_OPERATOR=<identity> ./scripts/prepare-release.sh 2026.11.10.3
infra/scripts/cd-remote.sh --dry-run
sh apps/macos/Installer/Scripts/release-app-update.sh --version 2026.11.10.3 --phase prepare
# publish commit and tag; server release train runs
sh apps/macos/Installer/Scripts/release-app-update.sh --version 2026.11.10.3 --phase publish --verify-feed 2026.11.10.3
```

Expected: notarization Accepted, stapled, Gatekeeper accepted, Sparkle signature valid, live appcast version matches, GitHub Release published with Russian notes.

## 8. Evidence to keep

- exact source SHA and tag;
- focused/full test output;
- GitHub check URLs and `validate-pr-checks.py` output;
- notary request IDs and Accepted status;
- stapler/Gatekeeper/Sparkle outputs;
- appcast XML and SHA-256;
- known limitations.
