# Quickstart: Meeting Playback Timestamp Seek

## Prerequisites

- Work from branch `046-meeting-playback-timestamp-seek`.
- Confirm active feature:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/046-meeting-playback-timestamp-seek \
  .specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

## Focused Server Validation

Run contract, integration, and unit tests that cover playback review state,
policy blocking, no-secret/no-content egress, and web shell rendering:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/contract/test_cabinet_playback_contract.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected outcome:

- authorized retained-audio meeting exposes playback;
- dual-track retained-audio meeting exposes a combined review stream or a safe
  unavailable state, never an unlabeled single-track substitute;
- blocked states do not expose playable audio;
- transcript timestamp controls seek to segment starts in rendered/runtime
  checks;
- no storage URL, object key, signed URL, credential, private path, or private
  content appears in status/evidence payloads.

## Browser Runtime Validation

Run a local browser/runtime check for:

- web meeting detail desktop viewport;
- desktop embedded route viewport;
- mobile-width viewport;
- play/pause control presence;
- timestamp seek activation for at least three segments;
- unavailable-state rendering for deleted, processing, failed, no-audio, and
  policy-disabled meetings;
- no horizontal overflow or text overlap.

Record only metadata-safe evidence in
`specs/046-meeting-playback-timestamp-seek/evidence/validation-log.md`.

## macOS Embedded Review Check

If the desktop bridge changes, run the focused macOS tests that cover embedded
cabinet routing and review URL policy:

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DesktopCabinet
```

Expected outcome:

- desktop embedded review opens the same meeting review state as the web
  cabinet;
- no native capture controls are duplicated inside embedded web review;
- playback availability and unavailable reasons match the server review state.

## Full Gate

Before PR readiness:

```sh
infra/scripts/ci-local.sh
infra/scripts/cd-remote.sh --dry-run
```

Do not run production deploy without explicit release approval.

## Evidence Safety Scan

Before committing evidence:

```sh
find specs/046-meeting-playback-timestamp-seek -type f ! -name quickstart.md -print0 |
  xargs -0 rg -n '(/Users/|/private/|/var/folders|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-(proj|live|test|svcacct)-[A-Za-z0-9_-]+|Bearer [A-Za-z0-9._-]+|https?://[^ ]*X-Amz-Signature|signed_url=|signedUrl=|storage_object_key|transcript_text|transcriptText|raw_audio|rawAudio)' || true
```

Expected outcome: no forbidden committed evidence.
