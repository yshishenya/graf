# Clarifications: Полноценная изолированная Dev-среда GRAF

**Feature**: `229-dev-runtime-full-stack`

**Issue**: [#6276](https://github.com/yshishenya/graf/issues/6276)

**Session**: 2026-09-01

**Status**: Resolved from the issue, F227 evidence and repository baseline; no
user decision is required before planning.

## Decisions

| ID | Decision | Consequence for design and validation |
|---|---|---|
| Q1 | Frontend remains server-rendered on the backend origin. | Do not introduce a second local frontend server or a second origin; smoke checks `/login` through the backend origin. |
| Q2 | Dev gets a dedicated Compose project, volumes, networks, ports and data root. | The old local state is preserved and never reused or deleted implicitly; production boundaries are rejected before any mutation. |
| Q3 | Migration graph mismatch is fail-closed. | Compare observed revision(s) with current graph before API/worker readiness; report a safe fresh namespace; never use `alembic stamp` or edit `alembic_version`. |
| Q4 | There is exactly one installed Dev app. | Use `/Applications/GRAF Dev.app`, bundle ID `pro.2brain.graf.dev`, stable signing/designated requirement and loopback cabinet/upload origins. |
| Q5 | Worker readiness is local, provider calls are not required for smoke. | Start and probe Temporal, processing and media workers with provider integrations disabled by default; any opt-in secrets stay server-side and follow existing gates. |

## Deferred to implementation research

- Exact host ports and Compose project-name derivation must be selected so one
  Dev runtime cannot collide with old local services while preserving the
  loopback-only boundary.
- The adapter must choose whether source SHA is enforced via image tags, image
  labels, runtime metadata endpoint, or a composed combination; the contract
  is exact identity, not a particular mechanism.
- The current repository has both `docker-compose.local.yml` and
  `docker-compose.dev.yml`; the new adapter must make one full-stack file the
  sole active Dev path and document the cutover/rollback boundary.
- A migration preflight must distinguish an empty new database (initialization
  allowed) from an existing incompatible database (blocked), without relying
  on destructive volume reset.

## Clarification quality gate

- No `[NEEDS CLARIFICATION]` markers remain in `spec.md`.
- Scope, isolation, migration safety, app identity and provider boundary are
  explicit and testable.
- Remaining choices are implementation-level research items and do not require
  a product-owner decision before plan review.
