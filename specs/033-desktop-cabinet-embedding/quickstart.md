# Quickstart: Desktop Cabinet Embedding

## Prerequisites

- macOS development environment with Swift toolchain.
- Existing feature `016` server cabinet routes available locally or through a
  configured development server.
- No private Krisp screenshots or real meeting content committed to git.

## 1. Focused macOS Tests

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|AppControlAccessibility|CaptureControl|DesktopUploadQueue'
```

Expected:

- desktop cabinet route policy tests pass;
- upload review link tests pass;
- native shell accessibility/control tests pass;
- no test output includes secrets, signed URLs, raw audio, transcript text, or
  live local paths.

## 2. macOS Release Build

```sh
swift build --package-path apps/macos -c release --product TwoBrainRecApp
```

Expected:

- `TwoBrainRecApp` builds without compiler or linker errors.
- No new dependency manager or frontend build step is required.

## 3. Server Cabinet Regression

```sh
cd apps/server
uv run --extra dev pytest -q tests/contract/test_cabinet_contract.py tests/unit/test_cabinet_web_shell.py
```

Expected:

- feature `016` routes still satisfy embedded route expectations;
- desktop route shell remains free of native capture/noise/device controls.

## 4. Local Embedded Route Smoke

Set a development cabinet base URL through the configured desktop environment
or UserDefaults path used by the implementation. Use a seeded development
identity when required.

Open the desktop app and validate:

- meetings workspace opens the embedded meeting list;
- ready detail opens inside the app;
- processing detail shows server processing truth;
- native Record/Stop/upload status remains outside the embedded surface;
- unsupported share/export/delete/download/capture routes are bounded.

Expected screenshots:

- `validation/screenshots/01-desktop-meetings.png`
- `validation/screenshots/02-desktop-ready-detail.png`
- `validation/screenshots/03-desktop-unavailable.png`

## 5. Reference Alignment Review

Compare the implemented app against:

- `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/krisp-reference-matrix.md`
- `specs/030-mvp-experience-design-system/design/reviews/v8-clean-ru-2026-06-15/v8-whole-page-consistency-audit.md`
- feature `016` validation screenshots and evidence.

Expected:

- desktop opens meetings-first, not diagnostics-first;
- upload/processing remain meeting/list states;
- native capture controls remain separate and visible;
- embedded list/detail labels match the web cabinet;
- no Krisp brand/copy/icon leakage;
- no clipped or overlapping primary controls.

## 6. Evidence And Status Update

Record results in:

```text
specs/033-desktop-cabinet-embedding/validation/implementation-evidence.md
```

Update:

- `CHANGELOG.md` `[Unreleased]`;
- `docs/current-product-status.md` so feature `016` is no longer listed as the
  next product slice after 033 implementation.
