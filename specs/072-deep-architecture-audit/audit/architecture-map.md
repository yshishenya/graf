# Architecture Map

## Evidence Baseline

072 was anchored from a clean worktree based on fresh `origin/master`.
Architecture evidence was collected from repository files, not from production
state. This stage does not modify product/runtime code.

Static inventory:

- Server Python: 154 files under `apps/server/src/twobrain_rec_server`, about
  35,646 lines.
- macOS Swift: 213 files under `apps/macos`, about 53,152 lines.
- Shell scripts: 54 scripts across the repository.
- Runtime/deploy surfaces: `infra/docker-compose.yml`,
  `infra/docker-compose.dev.yml`, `infra/server/Dockerfile`, and
  `infra/scripts/`.
- Product baseline surfaces: `docs/prd-voice-layer-final.md`,
  `docs/current-product-status.md`, `docs/adr/`, `docs/integrations/`, and
  existing `specs/`.

## Server Surface

The server is organized around FastAPI routers, domain services, storage,
processing, and worker workflows.

Key entrypoint:

- `apps/server/src/twobrain_rec_server/main.py` builds the FastAPI app, configures
  logging, database engine, storage, static mounts, and routers.
- `infra/server/Dockerfile` launches
  `uvicorn twobrain_rec_server.main:create_app --factory --host 0.0.0.0 --port 8080`.

Main areas:

- `api/`: public and desktop-facing API routers for auth, ingest, cabinet,
  admin, calendar, processing, support, and deletion-related operations.
- `auth/`: auth callbacks, dependencies, session/device behavior, and provider
  integration.
- `cabinet/`: server-rendered cabinet web surface, view models, rendering,
  queries, egress/download/export helpers, templates, and static assets.
- `ingest/`: desktop upload session, object storage custody, and ingest state.
- `processing/`, `workflows/`, `mediascribe/`: processing dispatch, Temporal
  worker paths, and server-only MediaScribe integration.
- `deletion/`: deletion, retention, and local purge behavior.
- `support/`: support incident redaction and server-owned support reporting.
- `storage/`, `db/`, `domain/`: persistence and shared domain boundaries.

Healthy signals:

- MediaScribe is server-side by design; desktop credentials are not part of the
  desktop app contract.
- Cabinet presentation is separated from capture-critical native controls by
  product docs and ADRs.
- Deployment has explicit local CI, migration, backup, restore, and smoke
  scripts rather than hidden manual steps.

Pain signals:

- `cabinet/web.py` is a large presentation/router hub and mixes many cabinet
  responsibilities.
- `readiness/matrix.py`, `cabinet/view_models.py`, `cabinet/rendering.py`, and
  `cabinet/egress.py` are large enough to make focused review difficult.
- Auth/session/device and deletion paths are safety-sensitive and should not be
  casually split without dedicated evidence.

## macOS Surface

The macOS app is a Swift Package with shared models, app core, executable app,
tools, and tests.

Package targets:

- `CShmHelpers`: C helper target under `Shared/CShmHelpers`.
- `TwoBrainRecShared`: shared models and utilities.
- `TwoBrainRecAppCore`: app services under `RecApp/Sources`.
- `TwoBrainRecApp`: executable app under `RecApp/App`.
- Validation tools: `ContractValidation`, `LeakageValidation`,
  `MeetingMuteTruthRuntimeProof`, and `WebRTCAEC3Validation`.
- `TwoBrainRecSharedTests`: XCTest target with fixtures.

Main areas:

- `RecApp/Sources/Capture/`: capture session state, system audio, microphone,
  route engine, local recording writer, and capture controls.
- `RecApp/Sources/Upload/`: desktop upload queue, client, custody projection,
  local purge acknowledgement, and support incident interactions.
- `RecApp/Sources/Cabinet/`: desktop cabinet shell, route policy, embedded
  WebView behavior, and native trust shell.
- `RecApp/Sources/Diagnostics/`: metadata-only diagnostic bundle assembly.
- `Shared/Sources/Models/`: shared contracts and local recording/upload models.
- `AudioDriver/`: parked advanced-routing driver surface, not required for MVP
  recording acceptance.

Healthy signals:

- Capture-critical work is native and visible locally.
- Shared contracts are centralized in Swift package targets.
- The future audio driver is parked as advanced-routing work rather than MVP
  acceptance scope.

Pain signals:

- `TwoBrainRecApp.swift`, `DesktopUploadQueueService.swift`,
  `DesktopUploadClient.swift`, `DesktopUploadCustodyProjection.swift`,
  `LocalRecordingWriter.swift`, `DiagnosticBundleService.swift`, and several
  capture views/services are large safety-sensitive hotspots.
- Some large tests are useful evidence but can become hard to maintain if they
  mix fixture construction, assertions, and scenario setup.

## Infra, Scripts, And Runtime Surface

Production and local runtime surfaces live under `infra/` and app-specific
script directories.

Key scripts:

- `infra/scripts/ci-local.sh`: canonical local CI gate.
- `infra/scripts/cd-remote.sh`: release/deploy gate with dry-run and execute
  paths.
- `infra/scripts/run-production-smoke.sh`: production smoke helper.
- `infra/scripts/backup-rec-stack.sh` and
  `infra/scripts/rehearse-rec-restore.sh`: backup/restore safety gates.
- `apps/macos/Scripts/validate-system-audio-capture-pivot.sh`: large capture
  validation script.

Runtime services:

- Production Compose: `rec-api`, `rec-processing-worker`, `rec-temporal`,
  `rec-migrate`, `rec-postgres`, `rec-minio`, and `rec-minio-init`.
- Development Compose mirrors the API, worker, migration, Postgres, MinIO, and
  Temporal surfaces.

Healthy signals:

- Release/deploy has scripted validation rather than only prose.
- Runtime secrets are modeled as Compose secrets rather than committed values.
- Deploy script runs local CI and remote safety checks before execute.

Pain signals:

- Capture validation shell scripts are large and deserve helper extraction only
  after preserving capture evidence.
- Deploy scripts encode operational contracts and should be treated as risky
  unless a release/deploy slice owns the change.

## Docs And Specs Surface

Important product and governance documents:

- `docs/prd-voice-layer-final.md`: product baseline until superseded by a
  feature spec.
- `docs/current-product-status.md`: current accepted implementation status.
- `docs/adr/001-local-trust-shell-and-server-dashboard.md`: native trust shell
  and server dashboard split.
- `docs/adr/002-system-audio-first-mvp-pivot.md`: system-audio-first MVP and
  parked virtual driver scope.
- `docs/integrations/mediascribe-dual-track-api.md`: server-owned MediaScribe
  integration contract.
- `docs/agent-guidance/`: Spec Kit, product, tracker, release, and worktree
  guidance.

Healthy signals:

- Product trust boundaries are documented and can be used as refactor gates.
- Current status and ADRs explain why some apparently extra surfaces are
  intentional.

Pain signals:

- Older specs and baseline docs may contain stale pre-merge expectations.
  Reconciliation should be a product-truth docs slice, not an incidental cleanup
  inside a code refactor.

