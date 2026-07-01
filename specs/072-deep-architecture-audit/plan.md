# Implementation Plan: Deep Architecture Audit

**Branch**: `codex/072-deep-architecture-audit` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/072-deep-architecture-audit/spec.md`

**Lane**: Significant architecture / high-risk read-only audit.

## Summary

Feature 072 creates an evidence-backed architecture audit for the whole
`2brain Rec` product before any refactor or cleanup work. The first stage is
read-only for product/runtime code: it may add Spec Kit and audit documents
only, may not remove files, may not change behavior, and may not deploy.

The audit maps the current server, macOS app, infrastructure, scripts, specs,
docs, dependencies, and release/deploy path from a clean worktree based on fresh
`origin/master`. It records dependency graphs, runtime flows, boundary risks,
and a small-PR refactor roadmap. Ponytail governs the shape of future work:
reuse existing tools and boundaries, avoid new dependencies and large rewrites,
but keep the high-risk validation lane intact.

## Technical Context

**Language/Version**: Python 3.13 server runtime; Swift Package Manager macOS
app with Swift tools version 6.0 and macOS 14 minimum; Bash shell scripts;
Docker Compose runtime; Markdown Spec Kit artifacts.

**Primary Dependencies**: FastAPI, SQLAlchemy asyncio, Alembic, Pydantic,
Temporal Python SDK, MinIO client, Jinja2, HTTPX, Uvicorn, asyncpg,
python-multipart; Swift Foundation, SwiftUI, AppKit, AVFoundation, CoreAudio,
AudioToolbox, WebKit, ScreenCaptureKit; Docker Compose, Postgres, MinIO,
Temporal.

**Storage**: Postgres, MinIO, Temporal state, local macOS recording packages,
local desktop upload queue/custody state. Feature 072 itself writes only
Markdown audit artifacts under `specs/072-deep-architecture-audit/`.

**Testing**: Read-only audit validation uses existing local commands and static
inspection: `rg`, Python AST import inventory, Swift Package target inspection,
shell/Docker entrypoint inspection, Spec Kit prerequisite/analyze checks, and
Markdown placeholder checks. Future refactor batches must use their own focused
pytest/XCTest/script/CI gates listed in the roadmap.

**Risk / Validation Lane**: Significant architecture / high-risk read-only
audit. The scope touches capture, privacy, deletion, auth/session/device,
MediaScribe, Langfuse, MinIO/Postgres/Temporal, desktop WebView/cabinet, infra,
and release paths, so the full Spec Kit planning sequence is required even
though this stage does not change runtime code.

**Release Gate**: No deploy for 072. Production dry-run/execute is explicitly
out of scope until a later release or refactor slice asks for it.

**Target Platform**: Linux containerized backend and workers; macOS desktop app;
self-hosted deployment infrastructure.

**Project Type**: Self-hosted web/API service plus native macOS desktop
application plus repository-managed infrastructure/scripts/docs.

**Performance Goals**: No runtime performance changes. Audit tooling must be
repeatable with local repository tools and fast enough for review in one PR.
Future refactors must preserve existing capture, upload, processing, cabinet,
and deploy gates.

**Constraints**: No code deletion; no behavior rewrites; no dependency removal;
no production deploy; no secrets, raw audio, transcript text, signed URLs, or
private meeting content in evidence; no 071 release mixing; no new audit
dependencies unless existing tools cannot produce required evidence.

**Scale/Scope**: Repository-wide audit. Current evidence inventory covers 154
server Python files, 213 macOS Swift files, 54 shell scripts, Docker/Compose
runtime definitions, specs, docs, and release/deploy scripts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS.

- Spec-driven delivery: PASS. 072 has its own numbered Spec Kit slice and does
  not reuse 071 as implementation scope.
- Product truth and clean-room boundaries: PASS. Audit records current product
  evidence and does not copy third-party design or change UX.
- Capture and privacy safety: PASS. First-stage output is metadata-only docs;
  no audio, transcript, credential, or user content evidence is collected.
- Desktop/server trust boundary: PASS. Native capture authority and server
  cabinet authority are audited as boundaries, not changed.
- Deletion and retention truth: PASS. Deletion copy or behavior changes are
  classified as risky / needs spec.
- Release discipline: PASS. No production deploy, release tag, or 071 release
  mixing is part of 072.
- Ponytail form: PASS. Use the smallest audit artifacts and existing tools;
  classify future work into focused PRs instead of a rewrite.

**After Phase 1 design**: PASS. Contracts and quickstart define evidence
formats and validation without adding runtime code, dependencies, or deploy
actions.

## Validation Plan

- Run Spec Kit prerequisite checks for the feature directory before tasks and
  analyze.
- Run Markdown placeholder checks for unresolved template tokens.
- Review audit docs against the required surfaces: server, macOS, infra,
  scripts, specs, docs, dependencies, release/deploy path, runtime flows, and
  trust boundaries.
- Run `$speckit-analyze` consistency review after `tasks.md` exists.
- Do not run production deploy for 072.
- Do not run full runtime CI for this planning-only stage unless a later
  refactor PR changes code. The roadmap names the required focused validation
  gates for those future batches.

## Project Structure

### Documentation (this feature)

```text
specs/072-deep-architecture-audit/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── audit/               # Evidence map and roadmap for this read-only audit
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml
├── src/twobrain_rec_server/
│   ├── api/
│   ├── auth/
│   ├── cabinet/
│   ├── deletion/
│   ├── domain/
│   ├── ingest/
│   ├── mediascribe/
│   ├── processing/
│   ├── storage/
│   ├── support/
│   └── workflows/
└── tests/

apps/macos/
├── Package.swift
├── AudioDriver/
├── RecApp/
├── Shared/
└── Scripts/

infra/
├── docker-compose.yml
├── docker-compose.dev.yml
├── server/Dockerfile
└── scripts/

docs/
├── agent-guidance/
├── adr/
├── integrations/
├── prd-voice-layer-final.md
└── current-product-status.md

specs/
└── 072-deep-architecture-audit/
```

**Structure Decision**: [Document the selected structure and reference the real
**Structure Decision**: 072 does not create a new runtime module. All new work
stays under `specs/072-deep-architecture-audit/` and updates the Spec Kit agent
context marker only. Product code, app code, infra scripts, and release files
are read-only inputs for this stage.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
