# Implementation Plan: Ponytail Refactor Audit

**Branch**: `codex/071-ponytail-refactor` | **Date**: 2026-06-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/071-ponytail-refactor/spec.md`

## Summary

Run a repo-wide Ponytail audit and apply only proven, minimal cleanup batches. The work starts by preserving the already validated small server cleanup as Batch A, then audits dependencies, Python server code, macOS Swift/C/C++ code, JavaScript, shell scripts, and infra references before making further changes. Each batch must remain independently reviewable and pass focused validation plus the appropriate repository gate.

## Technical Context

**Language/Version**: Python 3.13+ server project with Ruff target `py312`; Swift Package targeting macOS 14; JavaScript static/runtime checks with Node; Bash shell scripts; C/C++ macOS audio driver code.

**Primary Dependencies**: Existing FastAPI/Starlette, Jinja2, SQLAlchemy async, Alembic, Pydantic, MinIO SDK, Temporal, cryptography, httpx, pytest, pytest-asyncio, Ruff, Swift Package Manager, AVFoundation/CoreAudio/ScreenCaptureKit-era native macOS surfaces, Docker Compose images and services.

**Storage**: Postgres, MinIO, local macOS recording files/manifests, and repository documentation/evidence files are only audited for cleanup boundaries; this slice must not change storage schemas or retention semantics.

**Testing**: `uv run --extra dev pytest`, `ruff`, `python3 -m compileall`, `infra/scripts/ci-local.sh`, `swift test --package-path apps/macos`, `node --check`, `bash -n`, and focused tests named per batch.

**Risk / Validation Lane**: significant/high-risk cleanup. The audit may touch auth, admin, cabinet, privacy, deletion, diagnostics, upload, storage, deployment, and macOS capture-adjacent code. Clarify, checklist, tasks, analyze, and full validation are required before implementation continues beyond Batch A.

**Release Gate**: no deploy. Production release or smoke is out of scope unless a later release/deploy slice explicitly requests it.

**Target Platform**: 2brain Rec server, browser cabinet, macOS desktop app, macOS audio-driver proof code, and Docker Compose development/production surfaces.

**Project Type**: Multi-surface product repository with Python web service, macOS Swift package, native audio-driver proof code, shell/infra automation, and Spec Kit documentation.

**Performance Goals**: Cleanup batches must not add runtime overhead, new network requests, new dependencies, or extra startup/runtime work. Any performance-related removal must be behavior-preserving and validated by existing gates.

**Constraints**: No new dependencies, no speculative abstractions, no product behavior change, no deletion of safety tests without replacement evidence, no auth/privacy/deletion/capture/deploy shortcut, no cabinet API/service split mixed with presentation cleanup.

**Scale/Scope**: Repository code audit covers 647 code/script/test files and 120820 lines at kickoff, plus declared dependencies in `apps/server/pyproject.toml`, `apps/server/uv.lock`, `apps/macos/Package.swift`, Docker Compose files, and shell scripts. Historical specs/evidence/assets are read-only unless independently proven obsolete.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first MVP integrity: Pass with constraint. macOS capture and audio-driver code may be audited, but behavior-changing capture cleanup requires focused Swift/capture validation and must not alter active capture visibility, one-action stop, track truth, or permission behavior.
- Visible consent and user control: Pass with constraint. Refactors must preserve active capture indicator, manual start/stop availability, and local stop path.
- Data boundary and secret discipline: Pass with constraint. Dependency/script cleanup must not expose secrets, weaken secret-file handling, broaden egress, or log private meeting content.
- Deletion truth and lifecycle accounting: Pass with constraint. Cleanup must not remove lifecycle accounting, retention/deletion reports, external dependency limits, or truthful deletion copy.
- Spec-driven delivery with testable gates: Pass. This plan selects the stricter lane, requires checklist/analyze before implementation, and keeps batches independently testable.
- Product/platform constraints: Pass. No platform support expansion, no new runtime architecture, no production deploy.

Post-design re-check: Pass. The design keeps cleanup as evidence-first batches and rejects broad rewrites, new dependencies, and mixed high-risk refactors.

## Validation Plan

- Batch-local validation:
  - Run caller/reference searches before changing a candidate.
  - Run focused tests for every touched domain.
  - Run language syntax/lint checks for touched languages.
- Server repository gate:
  - `cd apps/server && PYTHONPATH=src uv run --extra dev ruff check src tests`
  - `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q`
  - `infra/scripts/ci-local.sh`
- macOS repository gate:
  - `cd apps/macos && swift test`
- Script/static gate:
  - `find apps/server/src apps/server/tests apps/macos infra scripts -type f -name '*.js' -print0 | xargs -0 -n1 node --check`
  - `find apps/macos infra scripts .specify/scripts -type f -name '*.sh' -print0 | xargs -0 -n1 bash -n`
- Closeout:
  - `git diff --check`
  - final retained-candidate note
  - selected risk/validation lane and evidence in final response/PR

## Project Structure

### Documentation (this feature)

```text
specs/071-ponytail-refactor/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── audit-batch-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── infra.md
│   ├── audio-capture.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml
├── uv.lock
├── src/twobrain_rec_server/
└── tests/

apps/macos/
├── Package.swift
├── RecApp/
├── Shared/
└── AudioDriver/

infra/
├── docker-compose.yml
├── docker-compose.dev.yml
└── scripts/

scripts/
└── prepare-release.sh
```

**Structure Decision**: Use existing repository structure only. Cleanup may delete or simplify proven unused code, but must not introduce new packages, module layers, frameworks, or migration paths.

## Complexity Tracking

No constitution violations or complexity exceptions.
