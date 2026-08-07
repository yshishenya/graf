# Implementation Plan: Надёжная очистка production smoke-данных

**Branch**: `codex/smoke-cleanup-fk` | **Date**: 2026-08-07 | **Spec**: [spec.md](spec.md)

## Summary

Smoke cleanup сейчас удаляет revision-связанные строки только по `meeting_id`.
Реальные данные могут сохранять связь через `media_revision_id`, поэтому
удаление media revision получает FK-ошибку и блокирует staged deploy. План
добавляет безопасное удаление зависимостей по обоим путям принадлежности,
сохраняет проверку таблиц/tenant context и добавляет regression coverage для
revision-linked cleanup и идемпотентного повторного запуска.

## Technical Context

**Language/Version**: Python 3.13 runtime, repository supports Python 3.11+

**Primary Dependencies**: SQLAlchemy async engine, PostgreSQL, MinIO, pytest

**Storage**: PostgreSQL rows and MinIO smoke object prefix

**Testing**: pytest unit/integration suites, disposable Postgres fixture,
`infra/scripts/ci-local.sh`

**Risk / Validation Lane**: high-risk-feature; cleanup touches Postgres,
deletion semantics, deployment smoke, rollback and production evidence

**Release Gate**: `cd-remote.sh --dry-run`, then `cd-remote.sh --execute` after
full CI and focused smoke cleanup validation

**Target Platform**: Dockerized production server on `2brain.dev`

**Project Type**: deployment and server maintenance path

**Performance Goals**: cleanup remains bounded by the existing smoke identity
and meeting/revision set; no unbounded global table scan is introduced

**Constraints**: no migration, no FK changes, no user-data deletion outside
the smoke identity, fail closed on true cleanup failure, metadata-only evidence

**Scale/Scope**: one bounded smoke run and its synthetic workspace per deploy

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: selected high-risk lane includes clarify, checklist, tasks, analyze and
  full repository validation.
- PASS: deletion remains truthful and limited to the synthetic smoke identity;
  no product deletion contract changes.
- PASS: deployment keeps backup, restore rehearsal, secret handling, health,
  rollback and metadata-only evidence gates.
- PASS: no schema migration or external egress is introduced.
- PASS: implementation uses existing SQLAlchemy/pytest patterns and adds no
  dependency or architectural abstraction.

## Validation Plan

1. Run the feature quickstart focused unit and integration scenarios, including a
   dependency row linked to a media revision.
2. Run `git diff --check` and the touched smoke cleanup pytest filters.
3. Run `infra/scripts/ci-local.sh` from a clean release worktree.
4. Run `infra/scripts/cd-remote.sh --dry-run --branch master` and inspect the
   pinned SHA/required gates.
5. Run `infra/scripts/cd-remote.sh --execute --branch master`; require backup,
   restore rehearsal, migration, health and smoke cleanup evidence before
   declaring release success.

## Project Structure

### Documentation (this feature)

```text
specs/141-smoke-cleanup-fk/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── infra.md
└── tasks.md
```

### Source Code

```text
apps/server/scripts/cleanup_smoke_artifacts.py
apps/server/tests/unit/test_smoke_cleanup.py
apps/server/tests/integration/test_rls_postgres_policies.py
CHANGELOG.md
```

**Structure Decision**: Keep the existing deployment maintenance script and
its unit/integration tests. The fix is a bounded query predicate/order change;
no new service, migration, dependency or public contract is needed.

## Complexity Tracking

No constitution violations.
