# Tasks: F291 eMudhra security

Input: spec.md, plan.md, research.md, data-model.md, quickstart.md. Lane: high-risk-product then release-deploy. Legacy Impact: untouched.

## Phase 1: Setup

- [X] T001 Record advisory, source/runtime inventory and ownership in `specs/291-emudhra-security/research.md`; preserve foreign changes.
- [X] T002 Complete reviewer checklist/tasks review, analyze and GitHub issue sync in `specs/291-emudhra-security/` before implementation.

## Phase 2: User Story 1 — HTTPS trust (P1)

Independent test: resolved locks, governance test, image package checks and ordinary/compromised HTTPS controls.

- [X] T003 [US1] Add certifi security floor in `apps/server/pyproject.toml`, targeted upgrade `apps/server/uv.lock` and reproducibly export `apps/server/constraints.txt`; review every dependency delta (FR-001).
- [X] T004 [US1] Update Node22 pins in `.github/workflows/governance-fast.yml` and `.github/workflows/release-full.yml`, synchronize `tests/governance/test_governance_workflow.py` and run it (FR-002).
- [ ] T005 [US1] Update the system CA package through `infra/server/Dockerfile`, verify runtime/media image paths and bounded HTTPS checks from `quickstart.md` (FR-003/004).

## Phase 3: User Story 2 — Verified release (P1)

Independent test: exact-SHA PR/CI/release decision and production receipt; no claims from a draft release.

- [ ] T006 [US2] Add `changes/unreleased/F291.yaml`, run focused checks and convergence, open draft PR and require exact governance-fast/macos-pr/pr-metadata evidence before reviewed merge (FR-005/006).
- [ ] T007 [US2] Verify current release owner/range and backup permission/restore applicability; prepare candidate/train/full CI/decision and CD dry-run under existing `infra/scripts/` processes, keeping execute blocked on missing authority/evidence (FR-005/007/008).
- [ ] T008 [US2] Execute authorized guarded server release only after gates; record image/package/TLS/health/smoke and repeated worker readiness plus rollback outcome in `docs/deployments/2brain-rec/` metadata-only receipt, preserving published macOS assets (FR-004/005/006/008; SC-001/002/003).

## Dependencies and implementation strategy

T001 → T002 → T003/T004/T005 → T006 → T007 → T008. T003/T004 touch independent files but one coordinated implementation process owns them; no parallel implementation. MVP source correction is US1; production completion requires US2. Any added finding becomes an append-only task via convergence. No new financial, SMTP, analytics, CA-policy or backup-infrastructure actions.

Tracking: #7734 owns T001–T008. Analyze 2026-10-23: critical0/high0, FR001–008 covered; independent requirements/tasks review PASS8/8. Implementation release gates remain open.
