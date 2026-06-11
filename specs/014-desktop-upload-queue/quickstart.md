# Quickstart: Desktop Upload Queue And Resilient Upload Behavior

## Prerequisites

- macOS 14+ on Apple Silicon.
- Feature directory: `specs/014-desktop-upload-queue`.
- Production ingest base URL: `https://rec.2brain.pro`.
- Smoke identity:
  `org=00000000-0000-0000-0000-000000014001`,
  `workspace=00000000-0000-0000-0000-000000014002`,
  `user=00000000-0000-0000-0000-000000014003`,
  `device=00000000-0000-0000-0000-000000014004`.
- Bearer auth must come from ignored local environment only:
  `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN`; never paste the value into evidence.
- Production live smoke requires a raw Rec `AuthSession` token with a matching
  database hash and trusted device binding. The Docker
  `twobrain_smoke_credential` secret is not accepted as this bearer token by
  the public Rec API.
- The bearer token and `X-Organization-Id` / `X-Workspace-Id` / `X-User-Id` /
  `X-Device-Id` headers must come from the same seeded smoke session; do not
  mix sample identity values with a different session token.
- Full provider login/session/device-token handling is intentionally out of
  scope here and tracked as `specs/028-provider-auth-session`.
- Existing local recording package with `manifest.json`, `mic.wav`, and
  `incoming.wav`, or a controlled recording created through the app.
- Optional owner-controlled ingest server URL configured for live upload smoke.

## 1. Static Spec And Contract Checks

```sh
rg -n "NEEDS CLARIFICATION|027-desktop-upload-resilience" \
  AGENTS.md \
  specs/014-desktop-upload-queue/spec.md \
  specs/014-desktop-upload-queue/plan.md \
  specs/014-desktop-upload-queue/research.md \
  specs/014-desktop-upload-queue/data-model.md \
  specs/014-desktop-upload-queue/tasks.md \
  specs/014-desktop-upload-queue/contracts

rg -n "MediaScribe|signedUrl|signed_url|token|credential|password|rawAudio|transcriptText|meetingContent" \
  specs/014-desktop-upload-queue apps/macos/Shared/Sources apps/macos/RecApp/Sources \
  --glob '!specs/014-desktop-upload-queue/quickstart.md' \
  --glob '!specs/014-desktop-upload-queue/contracts/desktop-upload-queue-contract.md' \
  --glob '!specs/014-desktop-upload-queue/evidence/test-results.md'
```

Expected:

- no unresolved clarification markers;
- no stale active feature references;
- forbidden-content matches are policy wording or redaction lists only.

## 2. Build And Test

```sh
cd apps/macos
swift build
swift test
swift run ContractValidation
```

Expected:

- build succeeds;
- upload queue unit tests pass;
- contract validation includes desktop queue redaction/contract checks.

## 3. Production Smoke Environment

Create an ignored local env file such as `.env.014-production-smoke.local`:

```sh
TWO_BRAIN_REC_UPLOAD_BASE_URL=https://rec.2brain.pro
TWO_BRAIN_REC_CLIENT_VERSION=smoke-014
TWO_BRAIN_REC_ORGANIZATION_ID=00000000-0000-0000-0000-000000014001
TWO_BRAIN_REC_WORKSPACE_ID=00000000-0000-0000-0000-000000014002
TWO_BRAIN_REC_USER_ID=00000000-0000-0000-0000-000000014003
TWO_BRAIN_REC_DEVICE_ID=00000000-0000-0000-0000-000000014004
TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN=<set locally only>
```

Expected:

- the env file remains ignored by git;
- bearer value is not copied into docs, diagnostics, logs, or queue JSON;
- desktop requests include identity headers and `Authorization: Bearer ...`.
- this env-only bridge remains internal-smoke-only until
  `028-provider-auth-session` replaces it for user-facing production.

## 4. Local Queue Discovery

Run or create one local recording, stop it, then relaunch the app.

Expected:

- local package remains present;
- queue item appears within 30 seconds;
- queue ID preserves package identity;
- upload status is non-terminal unless server accepted/finalized it.

Metadata evidence path:

```text
specs/014-desktop-upload-queue/evidence/test-results.md
```

## 5. Offline Retry Scenario

Start with no server URL or with network unavailable, then let the app discover
a valid package.

Expected:

- item state becomes `retrying` or `blocked` with `failureCategory=network`;
- local artifacts remain present;
- next retry time is visible in queue metadata;
- UI explains that data is still local and upload is delayed.

## 6. Resume Scenario

Use a controlled server or mocked client that accepts one track/part and reports
missing ranges for the rest.

Expected:

- retry continues only missing ranges;
- accepted bytes are preserved;
- repeated retry does not create duplicate terminal success;
- `uploaded` appears only after finalize server truth.

## 7. Security And Diagnostics

Export or inspect metadata-only diagnostics for a queue item with retry history.

Expected:

- queue state, failure category, retry mode, accepted byte counts, and server
  truth metadata are present;
- raw audio, transcripts, meeting content, tokens, credentials, signed URLs,
  MediaScribe credentials, and absolute local paths are absent.

## 8. UI Gate

Inspect the existing recording control UI with:

- no queue items;
- queued item;
- uploading item with progress;
- retrying item;
- blocked/manual-only item;
- uploaded item.

Expected:

- active recording status and Stop control remain primary while recording;
- queue status is compact, readable, and accessible;
- each non-terminal problematic state has one clear next-action label.
