# macOS Regression And App-Impact Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Task**: T098

## Package surface

The repository is SwiftPM-first. `apps/macos/Package.swift` defines two
libraries, the `TwoBrainRecApp` executable and four validation executables, with
one `TwoBrainRecSharedTests` target. No Xcode project/workspace is required for
this focused gate.

The `build-macos-apps:swiftpm-macos` workflow was used: inspect package, build
with SwiftPM, then run the exact quickstart filter.

## Commands and result

```text
swift build --package-path apps/macos
swift test --package-path apps/macos --disable-swift-testing \
  --filter 'CaptureRateAACReviewAudioWriter|SystemAudioRecordingPackage|DesktopUploadClient|DesktopUploadQueue|DesktopCabinetWorkspace|DesktopCabinetUploadLink'
```

Result:

- debug build: passed;
- selected tests: `139 passed`;
- failures: `0`;
- unexpected failures: `0`;
- elapsed test time: `4.156s`;
- exit code: `0`.

The regression proves required microphone/system/manifest roles remain intact,
the optional review descriptor remains AAC-LC/48-kHz/mono, invalid or renamed
optional candidates are dropped without blocking required-source upload,
existing upload sessions remain stable, no repair control appears, and the
desktop still sends media only to GRAF.

## App update decision

The 099 working diff under `apps/macos` contains only these test files:

- `DesktopUploadClientTests.swift`;
- `DesktopUploadQueueTests.swift`;
- `LocalRecordingManifestTests.swift`;
- `SystemAudioRecordingPackageTests.swift`.

There is no runtime, app UI, package product, entitlement, signing, driver or
installer source change. Therefore:

- a validation build was required and passed;
- rebuilding/installing `/Applications/2brain Rec.app` for the user is **not
  required** by feature 099;
- no installed-app replacement was performed.

Browser/embedded playback validation is recorded separately by completed T100
because it exercises the server-owned cabinet surface, not a changed native
binary. Feature 097 was not touched.
