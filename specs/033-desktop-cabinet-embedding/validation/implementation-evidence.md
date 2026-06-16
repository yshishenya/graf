# Implementation Evidence: Desktop Cabinet Embedding

Feature: `033-desktop-cabinet-embedding`
Date: 2026-06-16

## Status

Implementation validated. User-story checkpoints and final validation gates are complete.

## Checkpoint: Setup And Foundational Models

Status: complete for T001-T009.

Evidence:

- Created the desktop cabinet Swift source area under `apps/macos/RecApp/Sources/Cabinet/`.
- Added configuration, route policy, cabinet state, and native shell invariant tests.
- Verified focused foundational suite with:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet(Configuration|RoutePolicy|Workspace)'
```

Result: 12 tests passed, 0 failures.

## Checkpoint: US1 Desktop Meetings Workspace

Status: complete for T010-T015.

Implemented behavior:

- The desktop app now has a first-class `Встречи` workspace after native capture controls.
- The workspace builds embedded list and detail destinations from the configured cabinet base URL.
- A bounded WebKit wrapper allows the server-owned meeting list/detail routes and applies the route policy to navigation attempts.
- Root app composition keeps native capture controls before the embedded meetings workspace and moves local audio readiness into a separate native section.

Validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetWorkspaceTests|AppControlAccessibilityTests'
```

Result: 10 tests passed, 0 failures.

Privacy note: this evidence records only metadata-safe route/config behavior and test results. It does not include private meeting content, Krisp screenshots, credentials, signed URLs, raw audio, transcript text, or live local filesystem paths.

## Checkpoint: US2 Native Capture Authority

Status: complete for T016-T020.

Implemented behavior:

- Native capture controls remain before the embedded meetings workspace in the root app composition.
- Native capture, upload truth, local audio readiness, and embedded cabinet regions have stable accessibility boundaries.
- The embedded route policy blocks capture, device, permission, local upload, picker, diagnostics, and future governance destinations.
- Blocked capture/device/upload routes use bounded messages and do not claim that local or server actions executed.

Validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetWorkspaceTests|DesktopCabinetRoutePolicyTests|AppControlAccessibilityTests'
```

Result: 16 tests passed, 0 failures.

Privacy note: US2 evidence uses stable route reason values and accessibility identifiers only. It does not include private meeting content, credentials, raw audio, transcript text, or live local filesystem paths.

## Checkpoint: US3 Bounded Unavailable And Auth States

Status: complete for T021-T025.

Implemented behavior:

- Not-configured, loading, offline, timeout, expired-session, denied, not-found, malformed, and blocked-route states have short bounded messages.
- Denied and not-found messages avoid confirming whether a foreign meeting exists.
- State copy is scanned for common secret, signed URL, raw audio, transcript, private reference, and local-path fragments.
- Local recording and upload truth remain modeled as native-shell invariants independent from cabinet availability.

Validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetWorkspaceTests|DesktopCabinetConfigurationTests'
```

Result: 12 tests passed, 0 failures.

Privacy note: unavailable/auth evidence is metadata-only and contains no private account identifiers, meeting transcripts, raw audio, credentials, signed URLs, or live local filesystem paths.

## Checkpoint: US4 Upload-To-Review Continuity

Status: complete for T026-T031.

Implemented behavior:

- Uploaded queue items open an embedded review destination only when server truth contains a meeting identifier.
- Uploaded local-only items do not claim a review exists.
- Queued items with server meeting identity stay processing-only and do not expose a primary review action.
- `CaptureControlView` exposes an `Open review` action only for available review links and routes that action into the desktop cabinet detail route.
- Root app wiring updates the selected embedded cabinet route without changing local retry or stop-retry behavior.

Validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinetUploadLinkTests|CaptureControlTests'
```

Result: 14 tests passed, 0 failures.

Privacy note: upload-to-review evidence uses synthetic meeting IDs and local test paths only inside test fixtures; no private meeting content, raw audio, transcript text, credentials, signed URLs, or live local filesystem paths are recorded here.

## Checkpoint: US5 Clean-Room Copy And IA Alignment

Status: complete for T032-T037.

Implemented behavior:

- Desktop cabinet copy uses product-facing labels such as `Встречи` and `Открыть обзор`.
- Automated UI copy checks reject visible Krisp, WebView, API, route, email, and local path fragments in the desktop cabinet labels under test.
- The implementation follows the V8/Krisp IA gate at category level: meetings-first workspace, native capture authority outside embedded content, upload-to-review as a meeting continuity path, and browser/server ownership for variable review/governance surfaces.
- The implementation does not commit Krisp private screenshots, Krisp assets, Krisp copy, private account names, private email addresses, or real transcript content.

Reference notes:

- `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/krisp-reference-matrix.md` defines Krisp as an IA/category reference only, with exact visuals, copy, assets, colors, proportions, private content, and route naming forbidden.
- `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/v8-whole-page-consistency-audit.md` records the V8 gates used here: meetings default, upload/processing as meeting states, recording trust native, server-owned variable review, and no technical copy.
- `specs/016-meeting-dashboard-review/validation/implementation-evidence.md` records the server-owned desktop embedded routes and sanitized screenshots that this macOS shell embeds.

Validation:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'AppControlAccessibilityTests'
```

Result: 6 tests passed, 0 failures.

Screenshot evidence:

- `validation/screenshots/01-desktop-meetings.png`
  - macOS desktop shell with native `Record System Audio`, idle recording
    truth, input meters, and embedded meetings list.
  - Captured from a synthetic local cabinet fixture with no private account
    identifiers, no real meeting content, no transcript text, no raw audio, no
    signed URLs, and no Krisp assets.
- `validation/screenshots/02-desktop-ready-detail.png`
  - macOS desktop shell with native capture controls still outside the embedded
    surface and a ready meeting detail visible inside the cabinet region.
  - Captured from a synthetic ready-detail fixture so the visual evidence proves
    embedded detail rendering without relying on unstable coordinate clicking in
    the automated window-capture environment.
- `validation/screenshots/03-desktop-unavailable.png`
  - macOS desktop shell with native recording controls still available and the
    bounded `Кабинет встреч недоступен` state visible when cabinet configuration
    is absent.

Visual/reference comparison:

- V8 `03`, `07`, `10`, `11`, `15`, and `16` category gates are represented:
  meetings-first workspace, dense list/detail states, upload/review continuity,
  contextual list actions, server-owned review content, and native capture
  authority outside the embedded surface.
- Krisp is used only as a clean-room IA reference. The implementation does not
  copy Krisp visuals, color treatment, icons, product copy, private screenshots,
  private account content, or exact route naming.
- Feature `016` remains the server/web owner of list and detail review
  surfaces. Feature `033` embeds those route classes inside the macOS shell
  instead of rebuilding the review UI natively.
- Risky governance and egress actions remain out of scope: share, export,
  download, retention, deletion, access policy, and public links still require
  later browser-owned feature slices.

Rendering note:

- A SwiftUI/AppKit composition issue was found during screenshot validation:
  the WebKit host could load successfully while the embedded surface captured as
  blank when the AppKit view was masked and launched as a raw SwiftPM
  executable. The implementation now avoids masking the `WKWebView` layer and
  uses an explicit AppKit container for the hosted web view.

## Final Validation

Status: complete for T038-T042.

Validation commands:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|AppControlAccessibility|CaptureControl|DesktopUploadQueue'
swift build --package-path apps/macos -c release --product TwoBrainRecApp
cd apps/server && uv run --extra dev pytest -q tests/contract/test_cabinet_contract.py tests/unit/test_cabinet_web_shell.py
infra/scripts/ci-local.sh
```

Results:

- Focused macOS suite: 42 tests passed, 0 failures.
- macOS release build: `TwoBrainRecApp` built successfully.
- Server cabinet regression: 8 tests passed, 0 failures.
- Canonical local CI: `ci_local_result=pass` with 360 server tests passed,
  4 skipped, server lint passed, Python compile passed, production compose
  config rendered, and deployment evidence scan passed.
- Feature evidence text scan: no private account identifiers, email addresses,
  bearer/token values, signed URL signatures, live local paths, or raw audio
  filenames found under `specs/033-desktop-cabinet-embedding/validation/`.
- Screenshot payload scan: no private account identifiers, email addresses,
  bearer/token values, signed URL signatures, live local paths, or raw audio
  filenames found in committed PNG evidence.
- GitHub issue sync: issues `#801`-`#842` are closed after validation comments
  were added in Russian; open issue query for label `feature:033` returned an
  empty list.
