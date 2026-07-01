# Runtime Flows

## Flow 1: Capture To Local Package

Plain-language goal: the desktop app captures a meeting locally and creates a
custody-ready recording package.

Evidence paths:

- `apps/macos/RecApp/Sources/Capture/`
- `apps/macos/RecApp/Sources/Upload/`
- `apps/macos/Shared/Sources/Models/`
- `docs/adr/001-local-trust-shell-and-server-dashboard.md`
- `docs/adr/002-system-audio-first-mvp-pivot.md`

Steps:

1. User starts capture from the native macOS app.
2. Native capture state is owned by `CaptureSessionController` and capture
   services.
3. Microphone and system audio capture feed local writing paths.
4. `LocalRecordingWriter` and related manifest/package services finalize local
   files and metadata.
5. Active capture remains locally visible, manual stop remains available, and
   one-action stop stays part of the product gate.

State touched:

- Local recording package.
- Local manifest.
- Capture session state.
- Diagnostic metadata when requested.

Trust boundaries:

- Native app owns capture-critical truth.
- Server cabinet does not own active capture controls.
- Virtual driver work is parked outside MVP acceptance.

Validation before refactor:

- Swift package tests around capture/session state.
- Local recording package contract validation.
- Manual or scripted capture proof for capture-critical edits.

## Flow 2: Local Package To Upload/Ingest

Plain-language goal: the desktop app uploads a completed local recording to the
self-hosted server without handing third-party credentials to the desktop.

Evidence paths:

- `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- `apps/server/src/twobrain_rec_server/api/ingest.py`
- `apps/server/src/twobrain_rec_server/ingest/`
- `apps/server/src/twobrain_rec_server/storage/`

Steps:

1. Desktop queue scans or receives a completed recording package.
2. Desktop upload client creates or resumes an upload session.
3. Server ingest routes validate ownership/session context.
4. Audio/package parts are stored through server-owned storage paths.
5. Server finalizes ingest state and makes the recording available for
   processing.

State touched:

- Desktop upload queue and custody projection.
- Server DB rows for meeting/upload state.
- Object storage entries in MinIO.

Trust boundaries:

- Desktop authenticates to the self-hosted server.
- Server owns object storage credentials.
- Upload custody and local purge acknowledgement must remain explicit.

Validation before refactor:

- Desktop upload queue tests.
- Server ingest API tests.
- Storage contract checks.
- No-secret evidence scan when diagnostics or support flows are touched.

## Flow 3: Ingest To Processing And MediaScribe

Plain-language goal: the server processes accepted recordings and sends only
server-owned requests to MediaScribe.

Evidence paths:

- `apps/server/src/twobrain_rec_server/processing/`
- `apps/server/src/twobrain_rec_server/workflows/`
- `apps/server/src/twobrain_rec_server/mediascribe/`
- `docs/integrations/mediascribe-dual-track-api.md`

Steps:

1. Finalized ingest state becomes eligible for processing.
2. Processing pickup/submit code schedules or coordinates worker work.
3. Temporal worker paths execute processing flow.
4. Server-only MediaScribe integration submits dual-track requests.
5. Processing results are stored for cabinet/review.

State touched:

- Processing DB state.
- Temporal worker state.
- Object storage inputs/outputs.
- MediaScribe request/response metadata.

Trust boundaries:

- Desktop never stores MediaScribe credentials.
- Server and worker own third-party integration.
- Langfuse traces must remain metadata-only by default.

Validation before refactor:

- Processing and workflow tests.
- MediaScribe contract tests or mocked integration checks.
- Metadata-only trace review for Langfuse-adjacent changes.

## Flow 4: Cabinet Review And Desktop WebView

Plain-language goal: users review processed meetings through cabinet surfaces
while the native desktop app keeps capture trust local.

Evidence paths:

- `apps/server/src/twobrain_rec_server/cabinet/`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/macos/RecApp/Sources/Cabinet/`
- `docs/adr/001-local-trust-shell-and-server-dashboard.md`

Steps:

1. Server `main.py` mounts cabinet routes/static assets.
2. Cabinet queries build view models and rendering context.
3. Server-rendered cabinet pages and APIs expose meeting review/download/export
   behavior.
4. Desktop WebView route policy controls which cabinet routes may appear in the
   native shell.
5. Native shell keeps capture controls and local trust signals outside server
   authority.

State touched:

- Cabinet read models.
- Meeting review state.
- Desktop cabinet route decisions.
- Access/download/export state.

Trust boundaries:

- Server owns post-meeting cabinet/review.
- Native shell owns active capture and local status.
- Route policy is a security and product boundary.

Validation before refactor:

- Cabinet route/template tests.
- Desktop route policy tests.
- Screenshot or UI smoke where route layout changes.
- CSRF/session checks for form or auth-adjacent changes.

## Flow 5: Deletion, Export, And Local Purge

Plain-language goal: users can export or delete data with truthful limits and
explicit custody across server and desktop state.

Evidence paths:

- `apps/server/src/twobrain_rec_server/deletion/`
- `apps/server/src/twobrain_rec_server/cabinet/egress.py`
- `apps/server/src/twobrain_rec_server/api/cabinet.py`
- `apps/macos/RecApp/Sources/Upload/`
- `docs/agent-guidance/product-gates.md`

Steps:

1. User requests export, download, or deletion through cabinet/API.
2. Server verifies session/device/account authority.
3. Egress helpers package allowed output, or deletion service marks and removes
   server-owned data.
4. Local purge tasks flow to desktop where applicable.
5. Desktop acknowledges local purge state.

State touched:

- Server deletion/retention rows.
- Object storage.
- Export/download packages.
- Desktop local purge queue and acknowledgement.

Trust boundaries:

- Deletion copy must not promise universal erasure outside `2brain Rec`
  control.
- Local purge is a desktop/server custody boundary.
- Export must not leak unauthorized content.

Validation before refactor:

- Deletion/retention tests.
- Cabinet egress tests.
- Desktop local purge acknowledgement tests.
- Product copy review for deletion language.

## Flow 6: Support And Diagnostics

Plain-language goal: users/operators can collect support evidence without
leaking private meeting content or secrets.

Evidence paths:

- `apps/macos/RecApp/Sources/Diagnostics/`
- `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- `apps/server/src/twobrain_rec_server/api/support_incidents.py`
- `apps/server/src/twobrain_rec_server/support/`

Steps:

1. Desktop creates diagnostic/custody evidence from local metadata.
2. Redaction rules remove secrets and private content.
3. Desktop or server submits support incident metadata.
4. Server support paths store/report the incident through server-owned
   credentials.

State touched:

- Diagnostic bundle metadata.
- Upload custody projection.
- Support incident rows or external issue payloads.

Trust boundaries:

- No raw audio, transcript text, tokens, signed URLs, or credentials in support
  evidence.
- Server owns external support integration credentials.

Validation before refactor:

- Diagnostic redaction tests.
- Support incident payload tests.
- Secret/evidence scan.

## Flow 7: Release And Deploy

Plain-language goal: operators release safely with local validation, backup,
restore rehearsal, deployment, and smoke proof.

Evidence paths:

- `infra/scripts/ci-local.sh`
- `infra/scripts/cd-remote.sh`
- `infra/scripts/run-production-smoke.sh`
- `infra/scripts/backup-rec-stack.sh`
- `infra/scripts/rehearse-rec-restore.sh`
- `infra/docker-compose.yml`
- `infra/server/Dockerfile`

Steps:

1. Local CI validates tests, lint, compile checks, RLS, compose config, and
   evidence scan.
2. Deploy dry-run shows the release path without changing production.
3. Execute deploy requires clean/synced state, pinned commit, backup, restore
   rehearsal, remote compose checks, migration, deployment, and smoke.
4. Public health or smoke endpoint evidence confirms deployment.

State touched:

- Git branch/commit state.
- Remote deployment directory.
- Backup artifacts.
- Compose services, Postgres, MinIO, Temporal.

Trust boundaries:

- Production secrets stay outside repo evidence.
- Deploy behavior is not changed by 072.

Validation before refactor:

- `infra/scripts/ci-local.sh`.
- `infra/scripts/cd-remote.sh --dry-run` for deploy-script changes.
- `infra/scripts/cd-remote.sh --execute` only when a release request authorizes
  production deployment.

