# Implementation Plan: Полноценная изолированная Dev-среда GRAF

**Branch**: `codex/229-dev-runtime-full-stack` | **Date**: 2026-09-01 | **Spec**: [spec.md](spec.md)

**Umbrella issue**: [#6276](https://github.com/yshishenya/graf/issues/6276)

**Base SHA**: `836cbba8f1c53695dd9e06a21f58bf74365286ef` (F227)

**Dependency gate**: remote merge/release claims remain blocked until F227 PR
[#6275](https://github.com/yshishenya/graf/pull/6275) is merged and its exact
SHA is revalidated. Local implementation may proceed from the recorded F227
base, but must not claim the dependency is merged.

## Summary

Заменить неполный live adapter, который запускает только `start-local.sh` с
`processing_enabled=false`, на один GRAF-specific adapter для
`infra/docker-compose.dev.yml`. Adapter собирает и запускает весь server/runtime
stack в отдельном namespace, проверяет migration graph до readiness, привязывает
образы и Dev app к одному exact SHA и атомарно публикует один active manifest и
`/Applications/GRAF Dev.app`.

Generic manifest/lock/receipt contracts F227 и reusable
`graf-development-harness` остаются общими; Compose, worker readiness, signing
и data boundaries остаются в GRAF.

## Risk / Validation Lane

`high-risk-feature`: изменяются Docker/Temporal/Postgres/MinIO/migrations,
локальный backend/worker runtime, подписанное macOS-приложение, state isolation,
promotion и rollback. Обязательный путь:
`specify → clarify → plan → checklist → tasks → analyze → taskstoissues →
implement → converge → quickstart → fast validation`; production deploy не входит.

## Technical Context

**Language/Version**: Python 3.13 runtime; POSIX `sh`; Swift 6.0, macOS 14+;
Docker Compose v2.

**Primary Dependencies**: existing FastAPI/uv backend, Alembic, PostgreSQL 17,
MinIO, Temporal `1.27.2`, existing SwiftPM app and signing scripts. No new
dependency is required by the design.

**Storage**: dedicated Dev PostgreSQL/Temporal schemas, MinIO Dev volumes and
metadata-only harness state under the machine-local GRAF Dev state root.

**Testing**: existing Python governance/server integration tests, Compose config
validation, shell checks, Swift tests, deterministic fixtures and one real macOS
live smoke on a clean Dev state.

**Risk / Validation Lane**: `high-risk-feature`; requires infra/security
checklists, clarification evidence, analyze with zero unresolved critical/high
findings, focused contract tests, clean-state live smoke and exact-SHA fast CI.

**Release Gate**: `no deploy`; no production `cd-remote.sh` execution. Product
release remains a later release-train operation.

**Target Platform**: developer macOS workstation with Docker Desktop, `uv`,
Swift 6/macOS 14+, local Developer signing identity and loopback networking.

**Project Type**: self-hosted backend + server-rendered web app + native macOS
desktop app + local Docker runtime.

**Performance Goals**: promotion uses bounded health-check/process timeouts and
must not leave duplicate apps, volumes or server processes; idempotent
re-promotion is safe.

**Constraints**: loopback-only origins; production app/data/credentials never
reachable; no `docker compose down -v`, `alembic stamp` or direct
`alembic_version` edits; one active manifest and one installed Dev app; no raw
audio/transcript/secrets in evidence.

**Scale/Scope**: one developer Mac, one active Dev runtime, one app install and
one live candidate at a time; multiple worktrees may build metadata candidates,
but live promotion is serialized by the shared Dev lock.

## Constitution Check — before Phase 0

- **Principle I**: no capture path is changed; the runtime only enables the
  existing processing stack and preserves native app identity.
- **Principle III**: external AI/MediaScribe calls are disabled by default;
  secrets stay server-side and outside app/evidence. No new egress is created.
- **Principle V**: Dev signing stays separate from public Developer ID release;
  no update-feed or notarization rule is weakened.
- **Principle VI**: this is high-risk infrastructure work and follows the full
  Spec Kit path with reviewer-owned checklists and exact-SHA evidence.
- **Principle IV**: no meeting lifecycle/deletion semantics change; reset is
  limited to explicitly confirmed Dev state.

**Gate**: PASS for planning. Implementation remains blocked until reviewer-owned
infra/security checklists and `$speckit-analyze` have no critical/high findings.

## Phase 0 — Research and decisions

Detailed decisions are in [research.md](research.md) and clarifications in
[clarifications.md](clarifications.md). Before implementation:

1. Make `docker-compose.dev.yml` the only full-stack live adapter input; retain
   `docker-compose.local.yml` as a separate historical/local path until cutover.
2. Derive a fixed validated Compose project/volume/network namespace for the one
   Dev runtime. Host bindings are loopback-only and do not reuse old state.
3. Pass the requested SHA into image/app metadata and verify it for every running
   service before pointer commit. The checkout must be clean and at that SHA.
4. Run migration preflight against the isolated DB before API/workers readiness.
   Empty new state may initialize; unknown/multiple/mismatched revision blocks.
5. Keep provider calls opt-in and secret-free by default; readiness proves local
   worker/task-queue capability, not external provider success.

## Phase 1 — Design

### Runtime flow

```text
clean checkout + exact SHA
          ↓
manifest/build (SHA + namespace + migration graph)
          ↓
compose config/build (labels and image identity)
          ↓
isolated Postgres/MinIO/Temporal
          ↓
migration preflight/init (fail closed on mismatch)
          ↓
API + processing/media/maintenance workers
          ↓
signed GRAF Dev.app staged separately
          ↓
lock + app/runtime swap + full smoke
          ↓
atomic active-manifest pointer
```

### Component changes and ownership

| Component | Planned ownership | Expected path |
|---|---|---|
| Compose namespace and full-stack graph | GRAF-specific | `infra/docker-compose.dev.yml` |
| Live lifecycle and identity checks | GRAF adapter | `scripts/dev-harness.py`, `infra/scripts/dev-harness.sh` only if needed |
| Startup/migration preflight | GRAF runtime adapter | `infra/scripts/start-dev-runtime.sh`, `infra/scripts/dev-migration-preflight.py` |
| Service SHA/readiness metadata | server/runtime contract | `infra/server/Dockerfile`, existing health/readiness modules where needed |
| App build/install | existing native scripts | `apps/macos/Scripts/build-dev-app.sh`, `apps/macos/Scripts/install-dev-app.sh` |
| Contract/failure tests | governance/infra | `tests/governance/test_dev_runtime.py`, `tests/governance/test_dev_migration_preflight.py` |
| Operator docs | scoped guidance | `infra/dev/README.md`, `docs/agent-guidance/local-development.md` |

### Data and state model

See [data-model.md](data-model.md). No application schema migration is
introduced merely for the adapter. An incompatible database is a blocker, not a
repair target.

### Interface contracts

See [contracts/dev-runtime.v1.md](contracts/dev-runtime.v1.md). Existing
`infra/dev/manifest.schema.json` remains the generic manifest baseline; the
contract adds GRAF-specific obligations for Compose services, readiness and
promotion transaction without weakening it.

### Constitution Check — after Phase 1 design

- Full-stack enablement is bounded to development and does not alter capture,
  privacy or auth semantics.
- Isolation and fail-closed migration behavior preserve data and secret
  boundaries; no destructive repair is designed.
- One app identity and existing signing checks remain unchanged; production
  updater metadata is rejected.
- Existing scripts/dependencies are reused first; only the minimum adapter and
  preflight code is added (Ponytail full mode).

**Gate**: PASS with reviewer validation still required for security and infra
checklists. Any path that mutates production, old local state or app identity is
an automatic design failure.

## Validation Plan

1. `python3 scripts/check_spec_kit_governance.py` and active-pointer validation.
2. Contract tests for SHA equality, namespace isolation, migration outcomes,
   readiness coverage, app identity and transaction failure paths.
3. Static Compose config and shell/Python compile checks without provider secrets.
4. Fixtures proving malformed, stale and unowned inputs fail closed.
5. On a disposable clean Dev state, run `build --live → promote --live →
   smoke --live`; capture metadata-only evidence and verify production app/data
   fingerprints before and after.
6. Inject failures at staging, install, runtime-start and smoke stages; prove the
   previous candidate remains active and rollback returns to smoke PASS.
7. Run `infra/scripts/ci-local.sh --fast` on the exact implementation SHA.
   Full CI is a later release-train gate, not a feature-development gate.

## Requirement and success-criteria traceability

| Requirement | Tasks | Evidence gate |
|---|---|---|
| FR-001–FR-004 | T005–T006, T010–T018, T022–T025 | Compose graph, namespace, SHA and egress tests |
| FR-005–FR-006 | T007, T015, T020–T023 | migration preflight and forbidden-repair tests |
| FR-007 | T006, T018, T030 | app identity and atomic install tests |
| FR-008–FR-010 | T026–T032 | promotion transaction and rollback tests |
| FR-011 | T012, T017, T038–T039 | named live smoke checks |
| FR-012 | T006, T025, T035 | metadata-only evidence governance |
| FR-013 | T026–T032, T035 | idempotency, lock and stale-parent tests |
| FR-014 | T021, T023–T025, T035, T040 | production/legacy boundary and closeout gates |
| SC-001 | T010–T018, T038–T039 | full-stack clean-state smoke |
| SC-002–SC-003 | T006–T008, T011, T015, T019–T021 | exact SHA and mismatch fixtures |
| SC-004–SC-006 | T026–T032 | repeated promotion, ownership and rollback tests |
| SC-007 | T003–T004, T006, T035 | metadata-only evidence scan |

## Project Structure

### Documentation (this feature)

The feature directory contains `spec.md`, `clarifications.md`, `plan.md`,
`research.md`, `data-model.md`, `quickstart.md`, `contracts/dev-runtime.v1.md`,
the reviewer-owned infra/security checklists and `tasks.md`.

### Source Code (repository root)

Implement the adapter in existing `scripts/dev-harness.py` and
`infra/docker-compose.dev.yml`, with a minimal startup/preflight helper under
`infra/scripts/` if reuse is insufficient. Extend existing native build/install
scripts only for exact-SHA and origin inputs. Add contract/negative tests under
`tests/governance/fixtures/feature_229/` and `tests/governance/`.

**Structure Decision**: reuse the generic harness and native app scripts;
isolate GRAF-specific runtime behavior in `infra/` and existing
`scripts/dev-harness.py`. Do not introduce a second frontend server or
per-worktree installed app.

## Complexity Tracking

No constitution violation is proposed. New adapter/preflight files are needed
only because the existing local adapter cannot represent the required full
stack; reuse of existing Compose, readiness and signing helpers is mandatory.

## Legacy Impact

Classification: `retain-with-exception`

The old processing-disabled `start-local.sh`-only live adapter is retained only
as a non-active, bounded exception until T038–T039 pass and operator cutover.
Feature 228 owns its later removal. No new caller, compatibility fallback,
duplicate app, per-worktree live runtime or shared old volume may be added.

owner: `dev-runtime`

expiry: 2026-10-31

removal trigger: full-stack adapter reaches clean-state smoke PASS and rollback
evidence; then Feature 228 retirement review

retirement task: Feature 228 issue #6238, task T000; this feature only changes the active adapter

risk: retaining the old path can produce a misleading green result if an agent
uses it instead of the full-stack adapter

validation: active-path guard, exact-SHA identity, isolation, migration mismatch,
smoke and failure-injection rollback tests

reason: keep the incomplete path available only for controlled rollback and
diagnosis while the full-stack adapter is validated; do not add new use of it.
