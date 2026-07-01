# Dependency Graphs

## Python Server Graph

Scope:

- `apps/server/src/twobrain_rec_server/**/*.py`
- `apps/server/pyproject.toml`
- `infra/server/Dockerfile`
- server tests where they explain runtime-only dependencies

High-level internal flow:

```text
main.py
├── api/*
├── admin/web.py
├── cabinet/web.py
├── health/*
└── shared app setup: config, db, storage, logging

api/*
├── auth/*
├── cabinet/*
├── deletion/*
├── domain/*
├── ingest/*
├── processing/*
└── support/*

ingest/*
├── auth/config/db/domain
├── processing
└── storage

processing/* and workflows/*
├── db/domain/storage
├── mediascribe
└── Temporal worker/client paths

cabinet/*
├── auth/calendar/db/deletion/domain/outcomes
├── templates/static rendering
└── egress/export/download helpers
```

External import roots observed most often:

- `sqlalchemy`: persistence and migration-adjacent ORM work.
- `fastapi`, `starlette`, `jinja2`: API and server-rendered cabinet/admin
  surfaces.
- `pydantic`, `pydantic_settings`: request/config contracts.
- `temporalio`: worker/runtime processing.
- `httpx`: third-party or internal HTTP clients.
- `cryptography`: security-sensitive auth or token handling.

Runtime-only dependency interpretation:

- `asyncpg`: keep intentionally for SQLAlchemy Postgres URLs even when not
  directly imported.
- `uvicorn[standard]`: keep intentionally because the production Dockerfile
  launches Uvicorn.
- `python-multipart`: keep intentionally for FastAPI form/file parsing.
- `aiosqlite`: keep intentionally for test database URLs.
- `ruff`: keep intentionally for local CI and linting.

Risk interpretation:

- Server boundaries are mostly recognizable by package area.
- Cabinet is a dependency hub and should be split by behavior-preserving PRs,
  not by a global framework rewrite.
- Auth/session/device, deletion, processing, MediaScribe, and storage paths are
  risky because small signature changes can alter trust boundaries.

Limitations:

- Static imports do not prove runtime route coverage.
- Framework dependencies may be indirect.
- Dynamic worker registration and HTTP route behavior need focused tests before
  refactor.

## Swift macOS Graph

Scope:

- `apps/macos/Package.swift`
- `apps/macos/RecApp/**`
- `apps/macos/Shared/**`
- `apps/macos/AudioDriver/**`
- `apps/macos/Scripts/**`

Package target graph:

```text
CShmHelpers
└── TwoBrainRecShared
    ├── TwoBrainRecAppCore
    │   ├── TwoBrainRecApp
    │   ├── ContractValidation
    │   ├── LeakageValidation
    │   ├── MeetingMuteTruthRuntimeProof
    │   └── WebRTCAEC3Validation
    └── TwoBrainRecSharedTests
```

Common Swift imports:

- `Foundation`: broad model/service base.
- `TwoBrainRecShared`: shared local recording, upload, and contract models.
- `TwoBrainRecAppCore`: app service layer imported by app/tests/tools.
- `XCTest`: test target.
- `SwiftUI`, `AppKit`, `WebKit`: app UI, native shell, embedded cabinet.
- `AVFoundation`, `AudioToolbox`, `CoreAudio`, `ScreenCaptureKit`: capture and
  audio surfaces.

Risk interpretation:

- Capture and upload flows have clear target boundaries, but several files are
  large because they combine lifecycle, state, validation, and UI glue.
- `AudioDriver/` is parked advanced-routing code. It is not MVP acceptance
  scope, but it is not delete-now without a separate driver cleanup spec.
- WebView route policy is a security/product boundary between server cabinet
  and native trust shell.

Limitations:

- Swift imports do not show callback timing, app lifecycle ordering, or audio
  runtime behavior.
- Capture refactors require runtime or focused Swift validation, not just static
  graph review.

## Shell And Infra Graph

Scope:

- `infra/scripts/*.sh`
- `apps/macos/Scripts/*.sh`
- root helper scripts
- Docker and Compose files

Key shell entrypoint graph:

```text
infra/scripts/cd-remote.sh
├── infra/scripts/ci-local.sh
│   └── infra/scripts/scan-deployment-evidence.sh
├── infra/scripts/backup-rec-stack.sh
├── infra/scripts/rehearse-rec-restore.sh
├── infra/scripts/run-production-smoke.sh
│   ├── infra/scripts/validate-production-config.sh
│   └── infra/scripts/verify-rec-migration.sh
└── remote compose/deploy/smoke checks

apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh
├── apps/macos/Scripts/sample-system-audio-cpu-gate.sh
└── apps/macos/Scripts/validate-system-audio-capture-pivot.sh
    └── apps/macos/Scripts/build-local-installer.sh
```

Risk interpretation:

- `ci-local.sh` is the canonical local gate and should not be weakened by
  architecture cleanup.
- `cd-remote.sh` is a release/deploy contract and requires release-lane
  validation for behavior changes.
- Large capture scripts are split-soon candidates only if extraction preserves
  the same evidence and command behavior.

Limitations:

- Shell call graphs from text search do not prove every branch.
- Runtime shell behavior depends on environment, remote host, and secrets that
  are intentionally not captured in 072 evidence.

## Docker Runtime Graph

Scope:

- `infra/docker-compose.yml`
- `infra/docker-compose.dev.yml`
- `infra/server/Dockerfile`

Production services:

- `rec-api`: FastAPI server container.
- `rec-processing-worker`: background processing worker.
- `rec-temporal`: Temporal service dependency.
- `rec-migrate`: migration runner.
- `rec-postgres`: Postgres data store.
- `rec-minio`: object storage.
- `rec-minio-init`: MinIO bootstrap/init helper.

Runtime dependency interpretation:

- API and worker share the Python server package but run different commands.
- Postgres, MinIO, and Temporal are core runtime dependencies, not optional
  cleanup targets.
- Compose secrets are runtime configuration contracts; 072 records only their
  roles, not secret values.

Limitations:

- Compose syntax does not prove remote host state.
- 072 intentionally does not perform production smoke or deploy.

