# Quickstart: Честная проверка локального места

## Prerequisites

- macOS 14+
- Swift 6.0.3 toolchain
- clean checkout on `295-capture-storage-gate`
- existing local queue or a synthetic fixture with historical uploaded/terminal_deleted rows

## Local validation

```sh
swift build --package-path apps/macos
apps/macos/Scripts/run-swift-tests.sh
swift run --package-path apps/macos ContractValidation
python3 scripts/validate-changelog-fragments.py
```

## Focused tests

```sh
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.LocalRecordingFootprintTests
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.LocalRecordingFootprintProviderTests
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.RecordingPrerequisiteGateTests
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.MeetingDetectionPolicyTests
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.DesktopCalendarReminderTests
swift test --package-path apps/macos --filter TwoBrainRecSharedTests.CaptureControlTests
```

## Manual scenarios

1. **Historical queue, healthy disk**
   - queue has 1.5+ GB of uploaded/terminal_deleted metadata;
   - actual recordings folder is ~1.1 GB;
   - press Record → recording starts, tray shows Stop and timer.

2. **Warning**
   - actual footprint is between warning and critical;
   - press Record and trigger automatic meeting detection;
   - both start, a non-blocking warning is visible, no error card, no red light.

3. **Critical/full/reserve**
   - actual footprint crosses critical or free disk <= reserve;
   - start is blocked with a clear reason; auto-record is suppressed.

4. **Measurement error**
   - recordings root is unreadable;
   - start fails closed with a storage reason; no false healthy state.

5. **Failed tray**
   - force a start failure;
   - red light is hidden, “Повторить запись” and a safe reason are shown;
   - active recording still shows Stop and timer; `.degraded`/`.stopping` keep the light.

6. **Regression**
   - F284 local playback, local-only mode, deletion/purge, local queue rows and bridge open remain unchanged.

## Release gate

- `governance-fast`, `macos-pr`, `pr-metadata` on exact PR SHA
- `release-full` on frozen candidate
- Developer ID, notarization, staple, Gatekeeper, Sparkle/live appcast
- `cd-remote.sh --dry-run`, production deploy, health, runtime SHA
