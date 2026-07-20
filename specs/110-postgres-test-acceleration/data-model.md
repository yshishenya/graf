# Data Model: PostgreSQL test pipeline

## Test Run

| Field | Meaning | Validation |
|-------|---------|------------|
| `run_token` | Runner-generated identifier for one invocation | lower-case safe database-name suffix; unique per invocation; never user-supplied |
| `worker_count` | Number of fast-lane pytest workers | bounded 1 through 8; canonical default is eight from benchmark evidence |
| `collection_digest` | SHA-256 of sorted collected node IDs | metadata only; used to prove phase union/no omission |
| `phase_result` | `parallel`, `strict`, or `cleanup` result | each phase must succeed before overall pass |
| `timing_summary` | phase wall time and top 20 pytest durations | no URL, credentials, payload or transcript text |

State transitions: `prepared` -> `parallel_complete` -> `strict_complete` ->
`cleanup_complete` -> `pass`; any failure or interrupt transitions through
`cleanup_complete` before a non-pass result is returned.

## Worker Database

| Field | Meaning | Validation |
|-------|---------|------------|
| `database_name` | Generated database for one xdist worker | starts with the generated run prefix and passes the same loopback/disposable guard as the current runner |
| `worker_id` | xdist identity (`master`, `gw0`, …) | converted to safe database-name component only |
| `schema_state` | `migrated_head` after Alembic upgrades the worker once | never shared across worker IDs; includes migration-managed SQL functions and RLS |
| `seed_state` | known organization/workspace/user/device/registry baseline | restored before every fast `client` scenario |

Each worker database belongs to exactly one Test Run. No test may receive a
developer or production URL. The runner's final container cleanup owns removal
even if a worker exits unexpectedly.

## Fast Baseline

The fast baseline is a bounded list of tables derived from server model
metadata plus immutable seed input already used by the test fixture. It is not
a database dump, a production snapshot or a persistent artifact.

State transitions for each client test: `seeded` -> `mutated` -> next test
performs `truncate_and_reseed` -> `seeded`. A failed test follows the same
next reset path, and final cleanup drops the worker database.

## Clean Database

| Field | Meaning | Validation |
|-------|---------|------------|
| `purpose` | `migration`, `rls`, or `empty_schema` | caller must opt into the clean fixture/strict mark |
| `database_name` | isolated disposable database or explicitly reset schema | cannot reuse a fast worker baseline |
| `role_lock` | advisory lock identity for cluster-global role scenarios | held for the strict RLS modules inside the disposable cluster |

Clean databases may change schema or cluster role state as part of their
subject under test. They never run in the generic parallel lane; the enclosing
disposable container prevents state collision with another worktree.

## Worker Execution Context

| Field | Meaning | Validation |
|-------|---------|------------|
| `organization_id`, `workspace_id`, `user_id`, `device_id` | test tenant scope | comes from a seeded job or the shared deterministic test scope |
| `context_kind` | database actor kind | direct normalization worker test must be exactly `worker` |

The context is applied to the SQLAlchemy session before protected worker lookup
or execution. Missing, request or maintenance contexts remain rejected where
the service requires worker authority.
