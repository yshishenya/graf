# Implementation Plan: Desktop Upload Custody Architecture

**Branch**: `codex/086-desktop-upload-custody-architecture` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/086-desktop-upload-custody-architecture/spec.md`

**Lane**: Significant architecture / high-risk read-only audit.

## Summary

Feature 086 maps the desktop upload custody flow before any refactor. It uses
the 085 architecture priority refresh to move away from low-value cabinet
micro-splits and toward the product-trust node where local recording packages,
desktop queue state, server ingest, custody projection, local purge, support
evidence, and review readiness meet.

Stage one is documentation only. It creates a focused responsibility map,
contracts, data model, quickstart validation guide, findings, and small-PR
roadmap. It does not change Swift, Python, schemas, dependencies, migrations,
release files, or production state.

## Technical Context

**Language/Version**: Swift Package Manager macOS app with Swift tools version
6.0 and macOS 14 minimum; Python 3.13 FastAPI server; Markdown Spec Kit
artifacts.

**Primary Dependencies**: Swift Foundation, SwiftUI/AppKit surfaces used by the
desktop app; FastAPI/Pydantic server contracts; existing repository scripts and
shell tools for evidence collection. No new dependency is added by this slice.

**Storage**: Local desktop recording packages and upload queue document; server
Postgres records for meetings/upload sessions/local purge/support incidents;
MinIO temporary/final media objects. 086 writes only Markdown under `specs/`.

**Testing**: Stage-one validation is artifact validation and static evidence
review. Future refactor batches must run `swift test --package-path apps/macos`,
focused desktop upload queue/custody/local purge/support tests, server ingest
contract checks, support redaction checks, and `infra/scripts/ci-local.sh` when
server code changes.

**Risk / Validation Lane**: Significant architecture / high-risk read-only
audit. The scope touches upload custody, deletion/local purge, support evidence,
desktop/server trust boundaries, and ingest contracts.

**Release Gate**: No deploy. Production dry-run/execute is out of scope.

**Target Platform**: macOS desktop app and Linux containerized backend.

**Project Type**: Native macOS desktop app plus self-hosted web/API service.

**Performance Goals**: No runtime performance change in stage one. Future PRs
must preserve upload retry behavior, missing-range retry, queue responsiveness,
and local purge acknowledgement behavior.

**Constraints**: No code change; no dependency change; no deletion; no
migration; no deploy; no private meeting content, raw audio, transcript text,
tokens, signed URLs, or private local paths in evidence.

**Scale/Scope**: Focused architecture slice over `apps/macos/RecApp/Sources/Upload/`,
upload/custody tests, server ingest/local purge/support routes, and supporting
contract docs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS.

- Capture-first MVP integrity: PASS. 086 starts after local recording package
  completion and does not change capture behavior.
- Visible consent and user control: PASS. No active-capture UI or stop-path
  behavior changes.
- Data boundary and secret discipline: PASS. Evidence is metadata-only and
  desktop does not gain MediaScribe or server secrets.
- Deletion truth and lifecycle accounting: PASS. Local purge is mapped as a
  deletion lifecycle boundary; wording/behavior changes are deferred.
- Spec-driven delivery: PASS. The slice has a numbered Spec Kit directory,
  clarify outcome, plan, checklist, tasks, and analyze validation.
- Ponytail form: PASS. Existing tools only; no new dependencies; no code
  movement without evidence; future batches must reduce real custody risk.

**After Phase 1 design**: PASS. Contracts and quickstart preserve read-only
scope and define validation gates before implementation.

## Validation Plan

- Run Spec Kit prerequisite checks for the 086 feature directory.
- Run placeholder scans for unresolved template tokens in 086 artifacts.
- Review audit docs against required flow stages: local package, queue,
  upload/ingest, custody projection, local purge, support incident, and cabinet
  review readiness.
- Run `$speckit-analyze` consistency review after `tasks.md` exists.
- Do not run production deploy.
- Do not run full runtime CI for the docs-only stage; list those commands as
  future implementation gates.

## Project Structure

### Documentation (this feature)

```text
specs/086-desktop-upload-custody-architecture/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── audit/
└── tasks.md
```

### Source Code (repository root, read-only input)

```text
apps/macos/RecApp/Sources/Upload/
apps/macos/RecApp/Sources/Cabinet/
apps/macos/Shared/Tests/
apps/server/src/twobrain_rec_server/api/
apps/server/src/twobrain_rec_server/ingest/
apps/server/src/twobrain_rec_server/deletion/
apps/server/src/twobrain_rec_server/support/
apps/server/tests/
```

**Structure Decision**: 086 creates no runtime module. All new work stays under
`specs/086-desktop-upload-custody-architecture/` plus the managed `AGENTS.md`
Spec Kit pointer.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
