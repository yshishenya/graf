# Desktop Cabinet Validation Contract

## Automated Validation

Required automated checks:

- desktop cabinet configuration accepts only HTTP(S) base URLs and handles
  missing/invalid configuration as `notConfigured`;
- route policy allows only `/desktop/meetings` and
  `/desktop/meetings/{meeting_id}`;
- route policy blocks share/export/download/delete/capture/local diagnostics
  destinations;
- upload review links are available only when a queue item has server meeting
  identity;
- active recording shell invariants require Stop visibility and focus reach;
- UI/accessibility string scans contain no secrets, signed URLs, raw audio,
  transcript logs, private reference content, or live local paths.

## Manual Or Visual Validation

Required evidence:

- desktop app screenshot at the meetings workspace with native capture/upload
  controls and embedded list route;
- desktop app screenshot at a ready meeting detail;
- desktop app screenshot for a bounded offline/not-configured state;
- comparison note against V8 `V8 03`, `V8 07`, `V8 10`, `V8 11`, `V8 15`, and
  `V8 16` gates;
- clean-room note comparing against Krisp desktop/web IA without committing
  Krisp screenshots or private account content.

## Command Validation

Baseline commands:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|AppControlAccessibility|CaptureControl|DesktopUploadQueue'
swift build --package-path apps/macos -c release --product TwoBrainRecApp
cd apps/server && uv run --extra dev pytest -q tests/contract/test_cabinet_contract.py tests/unit/test_cabinet_web_shell.py
```

If local WebKit visual inspection is available, launch the app and capture
desktop screenshots after starting a local or seeded server route. If launch is
not available in the current runtime, record the blocker and keep automated
route/shell validation as required evidence.

## Evidence Rules

Tracked evidence may include sanitized 2brain screenshots and command output.
Tracked evidence must not include:

- Krisp private screenshots;
- private account names or email addresses;
- transcript content from real meetings;
- raw audio;
- credentials, tokens, signed URLs, passwords, or live filesystem paths.
