# Research: Полноценная изолированная Dev-среда GRAF

**Scope**: planning-only research for issue #6276; no runtime mutation was
performed.

## R1 — Source of truth for the full stack

**Decision**: use `infra/docker-compose.dev.yml` as the only live adapter input
for the complete Dev stack. Keep `infra/docker-compose.local.yml` separate until
the new path is proven and explicitly cut over.

**Rationale**: the Dev compose already declares API, migration, Postgres,
MinIO, Temporal, processing worker, maintenance worker and media worker. The
current `start-local.sh` starts only local Postgres/MinIO and a host API with
`TWOBRAIN_PROCESSING_ENABLED=false`, so it cannot prove the worker path.

**Alternatives rejected**: adding more flags to `start-local.sh` would keep two
different service graphs and make it easy to test a partial runtime by mistake;
starting each service manually would violate the one-command smoke contract.

## R2 — Namespace and data isolation

**Decision**: derive one explicit Compose project name and explicit volume,
network, port and state-root names for the single machine-local Dev runtime.
Bind host ports to loopback only. Never reuse or delete old local volumes as
part of promotion.

**Rationale**: Compose's implicit project name and volume names are not a
sufficient boundary when several worktrees exist. An explicit namespace makes
production-looking paths and accidental cross-worktree state detectable.

**Alternatives rejected**: `docker compose down -v` or a global reset would be
destructive and could remove user data; per-worktree live stacks would conflict
with the requirement for one installed app and one active runtime.

## R3 — Exact SHA binding

**Decision**: use the requested full SHA as the candidate identity, pass it into
container image tags/labels and app metadata, and verify all running services and
the installed app before updating the active pointer.

**Rationale**: manifest-only metadata does not prove that a container was built
from the requested checkout. A combined image/runtime/app check prevents mixed
SHA testing after parallel worktree changes.

**Alternatives rejected**: mutable `latest` tags, branch names or timestamps do
not identify the code under test and cannot prove reproducibility.

## R4 — Migration safety

**Decision**: run a read-only preflight against the isolated database before API
or worker readiness. Empty new state may initialize through the normal migration
command. Unknown, missing, divergent or multiple heads block with a safe fresh
namespace instruction.

**Rationale**: the F227 live blocker showed a stored revision absent from the
current graph. Guessing or stamping it would hide drift and can corrupt state.

**Alternatives rejected**: `alembic stamp`, direct `alembic_version` edits and
`down -v` are explicitly forbidden by repository safety rules.

## R5 — Worker/provider boundary

**Decision**: process and readiness-test Temporal, processing and media workers
locally, but keep external MediaScribe/LiteLLM/Langfuse calls disabled by default
for the smoke. Provider use remains a separate explicit opt-in with server-side
secrets.

**Rationale**: local smoke must prove the runtime graph without exporting meeting
content or requiring credentials; worker readiness and provider success are
different contracts.

**Alternatives rejected**: embedding credentials in the app or making a public
provider call a prerequisite for every local promotion would violate the
constitution and slow inner-loop validation.

## R6 — Atomic lifecycle

**Decision**: reuse F227's shared Dev lock, manifest parent chain, app snapshot,
runtime ownership record and compensation logic; add Compose stop/start and
service identity checks inside the transaction before pointer commit.

**Rationale**: an app swap without runtime rollback, or a runtime swap without
the app, creates a mixed candidate. The active pointer must be the final commit
point.

**Alternatives rejected**: changing the pointer first and repairing failed
services later leaves smoke and rollback ambiguous.

## Known risks to resolve in implementation

- Existing Dev Compose host port mappings are not yet proven collision-free with
  local services; choose and validate an explicit loopback port map.
- Compose currently has no uniform source-SHA label contract for every service;
  implement and test the minimum metadata needed to verify it.
- Migration preflight must distinguish a genuinely empty database from an
  incompatible non-empty database without deleting either.
- The adapter must stop only its own Compose project and owned host process; a
  stale runtime record or unknown container must fail closed.
- A clean-state live smoke must prove that `/Applications/GRAF.app` and
  production data are untouched; local tests alone cannot establish that.
