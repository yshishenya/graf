# Quickstart: Real Playback Availability

## Goal

Validate that processed real recordings show in-page review playback by default
without enabling artifact download, and that the playback experience works in
web and macOS embedded review like a proper transcript-linked review player.

## Prerequisites

- Work from branch `048-real-playback-availability`.
- Evidence must be metadata-only.
- Browser runtime validation must use synthetic or content-safe fixture text.

## Spec Kit Prerequisites

```sh
SPECIFY_FEATURE_DIRECTORY=specs/048-real-playback-availability \
  bash .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Expected outcome:

- feature directory resolves to `specs/048-real-playback-availability`;
- `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`,
  `quickstart.md`, and `tasks.md` are available.

## Focused Server Validation

Run focused playback tests:

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_cabinet_playback_contract.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/unit/test_playback_audio.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/unit/test_artifact_egress_audit.py
```

Expected outcomes:

- owner ready review playback is available without `audio_download="allowed"`;
- audio download/export controls remain policy-disabled when policy is disabled;
- playback route supports safe range responses;
- denied states fail closed;
- web and embedded HTML include the bottom review player only when playback is
  available;
- no direct storage URL, signed URL, object key, credential, raw audio, or
  private transcript text appears in responses or evidence.

## Browser Runtime Validation

Use a synthetic fixture rendered by the real server-side meeting detail
renderer.

Required checks:

- web desktop ready page has one playback audio element and bottom player;
- embedded desktop ready page has the same playback state;
- mobile-width ready page has no horizontal overflow;
- unavailable pages have no playable audio element;
- clicking at least three timestamp controls updates audio current time to the
  matching safe segment start;
- speaker timeline lanes are visible when diarization is available.

Evidence to record:

- viewport class;
- playback element count;
- seek target count;
- observed seek seconds;
- horizontal overflow count;
- unavailable-state audio element count;
- pass/fail result.

## macOS Embedded Review Validation

Run focused macOS cabinet tests if embedded routing or shell state changes:

```sh
swift test --package-path apps/macos --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --filter DesktopCabinetConfigurationTests
```

If no macOS code changes, record why the server-owned `/desktop/meetings/{id}`
route is the shared embedded surface and validate that route through server and
browser checks.

## Full Local Gates

Run the repository gate before closeout:

```sh
infra/scripts/ci-local.sh
```

If release or production proof is requested, follow
`docs/agent-guidance/release-and-validation.md`:

```sh
infra/scripts/cd-remote.sh --dry-run
```

## Forbidden Content Scan

Scan 048 evidence and docs before closeout:

```sh
find specs/048-real-playback-availability -type f ! -name quickstart.md -print0 \
  | xargs -0 rg -n '(/Users/|/private/|/var/folders|BEGIN (RSA|OPENSSH|PRIVATE) KEY|sk-(proj|live|test|svcacct)-[A-Za-z0-9_-]+|Bearer [A-Za-z0-9._-]+|https?://[^ ]*X-Amz-Signature|signed_url=|signedUrl=|storage_object_key|transcript_text|transcriptText|raw_audio|rawAudio)' || true
```

Expected outcome:

- no matches.
