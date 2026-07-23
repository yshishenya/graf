# Quickstart: Восстановление автозаписи встреч

## Preconditions

- macOS 14+ Apple Silicon development machine or Swift Package test runner.
- Synthetic registry and detector fixtures only; do not use a real meeting,
  transcript, raw audio or credential in evidence.
- Repository root: `/Users/yshishenya/.codex/worktrees/fab3/crisp`.

## 1. Spec and contract checks

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
rg -n "countdown|auto.?start|auto.?record|Всегда писать|Выбрать все|Пропустить" \
  specs/124-restore-automatic-recording \
  apps/macos/RecApp/Sources/MeetingDetection \
  apps/macos/Shared/Sources/MeetingDetection
```

Expected:

- Feature 124 is the active owner of all restored behavior.
- The current source contains `autoRecord`, `autoRecordEligible`, the eight
  second countdown task, checkbox and verified-target list.
- No source path uses the removed routing implementation.
- The prompt task returns on cancellation and checks cancellation again before
  resolving automatic start; one active prompt/output batch cannot create a
  second recording trigger.
- Browser bundles remain outside the native Feature 124 auto-record list; the
  canonical registry keeps browser targets `manual_or_browser_only`.

## 2. Focused policy tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter MeetingDetectionPolicyTests
```

Expected:

- Exact target opt-in returns `.autoRecord(targetID:)`.
- Unchecked target returns `.prompt(targetID:)`.
- Detect-only, unknown, browser/manual-only, blocked permission/storage/policy
  and unavailable one-action Stop never return `.autoRecord`.
- Detector emits `autoRecordEligible` once for a stable opted-in target and
  preserves `promptEligible` for an unchecked target.

## 3. Settings and prompt contract tests

```sh
swift test --package-path apps/macos --disable-swift-testing \
  --filter CaptureControlTests
swift test --package-path apps/macos --disable-swift-testing \
  --filter AppControlAccessibilityTests
```

Expected:

- Settings source contains the common verified native-target list, per-target
  bindings, «Выбрать все», «Снять все» and settings-change notifications.
- Prompt source contains `TimelineView(.periodic`, `countdownSeconds = 8`,
  cancellable `autoStartTask`, checkbox «Всегда писать это приложение»,
  «Записать сейчас», «Пропустить» and the floating `NSPanel`.
- The test suite keeps negative assertions for unknown/blocked/hidden/duplicate
  capture, not for the restored contract itself.
- Prompt disappearance during countdown cannot invoke automatic start, and
  two eligible outputs cannot replace the visible prompt or start a second
  trigger.

## 4. ContractValidation

```sh
swift run --package-path apps/macos ContractValidation
```

Expected: the macOS package and static contracts compile, and no forbidden
routing or secret/evidence regression is reported.

## 5. Repository gate

```sh
infra/scripts/ci-local.sh
```

Expected: local CI passes with no new dependencies, no raw meeting content in
evidence and all focused recording/privacy/accessibility checks green.

## 6. Validation evidence (2026-07-23, post-review)

- Post-review focused policy: 16/16 tests passed.
- Post-review focused capture: 39/39 tests passed, including cancelled
  countdown, prompt disappearance and one-trigger-per-output-batch assertions.
- Post-review focused accessibility: 18/18 tests passed.
- `ContractValidation`: PASS.
- Pre-merge `infra/scripts/ci-local.sh`: PASS — macOS guard/build/all tests
  609/609; server parallel 2191 passed / 1 skipped; strict PostgreSQL/RLS 41
  passed / 1 skipped; lint, Python compile, compose and metadata-only
  deployment scan passed. The production RLS probe was intentionally not part
  of that local run. Release used the documented local-CI bypass for an
  existing host-load-sensitive debug timing assertion. The post-merge rerun
  reproduced only the unrelated SC-017 calendar performance assertion twice
  (`p95=92.78ms` and `201.96ms` versus the `50ms` threshold); neither that test
  nor Feature-124 code was changed. Mandatory remote gates remained enabled.
- Release/deploy receipt: [`v2026.07.23.9`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.9)
  deployed exact SHA `5d5b8428239f9f1439cefc63e11bd1b07e3f4279`; backup,
  restore rehearsal, migration, smoke/cleanup, worker/API/Temporal readiness
  and automatic dispatch passed, with `readiness_verdict=infra_smoke_ready`.
- Production RLS read-only metadata receipt: `production_rls_state_result=pass`,
  `environment=live_production`, `alembic_revision=0033_prompt_opt_maintenance`,
  `covered_table_count=77`, `rls_enabled_and_forced_count=77`,
  `failed_table_names=none`; live and ready health endpoints both returned
  HTTP 200. Candidate `v2026.07.23.8` was stopped fail-closed on the migration
  gate and superseded by `.9`.
- macOS update receipt: [`v2026.07.23.11`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.23.11)
  is published from merge `05d66e582f77a4bfeed66057043e8269077d395a`. Public
  appcast, ZIP and PKG re-fetch passed XML, ZIP-integrity, checksum and Sparkle
  appcast/archive signature checks. The ZIP SHA-256 is
  `8abdb294667f5b696373b50aa3583ea0db0bd22b2b865bbad9c3914a85f789df`, the
  PKG SHA-256 is
  `d8b93e40164347bfb62f71039fae51fd34dbb84c3c473d21c2268b3edaf2f025`, and
  the appcast SHA-256 is
  `1eaac01354991f3eedbf0b73e968cedf1fb1ec3641e25b4899b354b6cb1588e7`.
  The release is owner-only local-Keychain signed, not Developer ID signed or
  notarized; `2026.07.22.6` remains the rollback archive.
- Feature-124 issue mapping was canonical and validated before closeout; all
  24 mapped issues are now closed only after this evidence. A later
  repository-wide canon rerun is blocked by four unrelated, newly opened
  Feature-121 issues (#4320–#4323), which are outside this slice and were not
  modified.
- Ponytail review: no unnecessary abstraction or dependency found; restored
  code reuses the existing policy, registry, prompt and capture path. The
  post-review correction uses the existing task cancellation and output handler;
  no new service or queue was introduced.

## 7. Manual synthetic smoke (when a signed app is available)

1. Open Settings → Встречи → Автозапись.
2. Confirm every verified native registry target is listed.
3. Toggle one target, restart the app, and confirm the toggle persists.
4. For an unchecked synthetic target, observe the floating prompt and its
   eight-second visible countdown.
5. Use «Записать сейчас» and confirm immediate visible capture; repeat and let
   the countdown expire to confirm automatic start.
6. Check «Всегда писать это приложение», stop, and confirm a later same-target
   synthetic event emits auto-record without a prompt.
7. Select «Пропустить» for another target and confirm no recording starts.
8. Close the prompt through detector end/termination/settings shutdown during
   the countdown and confirm no recording starts afterward.
9. Feed two simultaneous synthetic eligible targets and confirm there is no
   second prompt or parallel trigger.
10. Revoke permissions or policy/readiness and confirm the countdown cannot
   start capture and exposes a truthful blocked state.
11. Stop from the local trust surface in one action; do not use network or web
   cabinet state as the stop authority.

## Evidence Rules

Record only metadata such as test names, result, target fixture ID, registry
version, policy reason code and timestamps. Never record meeting names,
transcript text, raw audio, credentials, live local paths or private screenshots.
