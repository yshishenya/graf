# Quickstart: Meeting Content Regeneration Lifecycle

This guide is the validation source of truth for Feature 124. It uses synthetic
fixtures and metadata-only evidence. Never use real meeting audio, transcript,
credentials or signed URLs in output.

## Prerequisites

From the repository root:

```sh
SPECIFY_FEATURE_DIRECTORY=specs/124-content-regeneration-lifecycle \
  .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Use the server virtual environment and the isolated local PostgreSQL harness
provided by `scripts/run_local_postgres_tests.sh`.

## Scenario matrix

### A. Immutable processing lineage

Run the focused processing/model tests:

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/unit/test_processing_fences.py \
  tests/integration/test_processing_result_idempotency.py \
  tests/integration/test_processing_pickup.py \
  tests/integration/test_processing_worker_restart.py -q
```

Expected evidence:

- two media revisions produce different workflow/job/result identities;
- same normalized hash is idempotent;
- changed hash creates a new result and never deletes old segments;
- an old callback cannot change the current revision aggregate.

### B. Baseline and manual candidate idempotency

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/unit/test_summary_candidate_revisions.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_outcome_generation_dispatch.py -q
```

Expected evidence:

- one baseline candidate per full source/template/generator key;
- same-format selector click is a no-op unless explicit refresh intent exists;
- candidate stores provenance and current remains unchanged until accept;
- equivalent active requests deduplicate.

### C. Owner preview and stale accept

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_cabinet_meeting_outcomes.py \
  tests/integration/test_transcript_export_egress.py \
  tests/contract/test_summary_template_ui_contract.py -q
```

Expected evidence:

- owner receives a safe read-only preview with format name;
- shared viewer receives only accepted current content;
- source/current/deletion mismatch returns 409 with no pointer mutation;
- successful accept atomically supersedes the previous current outcome.

### D. Durable dispatch and recovery

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_outcome_generation_dispatch.py \
  tests/integration/test_processing_worker_restart.py \
  tests/integration/test_outcome_generation_workflow.py -q
```

Inject a Temporal start failure after the candidate commit. Expected evidence:
the reconciler retries the same idempotency key or records a bounded terminal
failure; no queued candidate remains indefinitely without a workflow identity or
next action.

### E. Deletion races and retention

```sh
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_recording_workflow_deletion_races.py \
  tests/integration/test_meeting_outcomes_deletion.py \
  tests/integration/test_local_purge_coordination.py \
  tests/integration/test_retention_policy_execution.py -q
```

Expected evidence:

- deletion epoch blocks late import/generation/accept;
- no transcript/outcome content reappears after tombstone;
- completed GenerationCall/Langfuse/Temporal content is explicitly reported as
  retained operator-controlled observability, while GRAF-controlled meeting
  copies are purged through their artifact states;
- object-store deletion journal converges through retry and does not claim
  universal erasure outside GRAF control.

### F. Cabinet UX and accessibility contracts

```sh
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh \
  --focused tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_summary_template_ui_contract.py \
  tests/integration/test_cabinet_meeting_outcomes.py -q
```

Expected evidence:

- current accepted content remains visible while candidate changes;
- ready status names the format;
- stale conflict includes `Обновить`;
- polling pauses while hidden and ends at a finite bound;
- keyboard/VoiceOver labels and focus return remain intact for browser and
  embedded cabinet surfaces.

## Required repository gate

After all focused scenarios pass:

```sh
infra/scripts/ci-local.sh
```

Record the exact result, test counts and warnings in this file. A green focused
suite does not waive the full repository gate.

## Implementation evidence (2026-07-24)

- Revision-scoped reprocess API: `POST
  /api/v1/meetings/{meeting_id}/media-revisions/upload-sessions`; the same
  idempotency key returns the same pending revision/session, while an accepted
  immutable revision cannot be rewritten.
- Migrations `0032`–`0039` apply the lineage, purge journal, candidate expiry,
  reconciliation, generator-provenance, isolated candidate-outcome and
  MediaScribe submission-claim schema changes. Migration `0037` also binds legacy NULL source hashes to the
  immutable processing-result identity without fabricating generator config;
  its downgrade is intentionally guarded until candidate rows and generator
  duplicates are archived/deduplicated. Migration `0032` restores the legacy
  meeting-wide uniqueness constraints on downgrade and blocks if revision
  history contains duplicate groups that cannot fit the old schema. Migration
  `0039` marks pre-revision workflow/job rows with `legacy:<run-id>`; the
  reconciler relinks only one fully attested revision and blocks ambiguous
  rows. Legacy rows may poll an already-submitted provider job, but never
  submit a newer revision under a NULL lineage identity.
- Focused PostgreSQL coverage for reprocess, cabinet outcomes, generation,
  deletion, dispatch, result idempotency, source-fence regression, malformed
  provider responses, bounded runtime retries, deployment rollback discovery
  and view models is green: **103 passed, 2 warnings**. The focused
  candidate/outcome/export/template/static regression set is **122 passed, 2
  warnings**; the Temporal/observability correction set is **14 passed, 2
  warnings**.
- Source-fence unit regression: **3 passed, 2 warnings** in 4.22s. A changed
  source result rejects accept without mutating the current pointer and marks
  the attempt stale.
- Static checks passed after the final source/provenance changes: Ruff,
  Python compileall, JavaScript syntax check and `git diff --check`.
- Automatic baseline policy is deliberately fixed to built-in `graf-auto-v1`
  plus a stable configuration hash. Personal/workspace template changes are
  explicit actions and never silently rewrite accepted content.
- Request-time candidate dedupe deliberately does not call Langfuse: active
  attempts keep their identity while the worker pins a verified prompt/model
  snapshot before egress. A deployment therefore never mutates or re-keys an
  active attempt; `Обновить итоги` uses a unique explicit refresh intent when
  the owner wants a new snapshot.
- Deterministic baseline generator exceptions are terminal rather than
  repeatedly retried on every reopen; an operator/manual re-run creates a new
  lineage after the defect or prerequisite is fixed.
- Expired candidates are durable terminal lineage: the outcome set and every
  linked nonterminal generation attempt are marked `expired` with bounded
  failure metadata before the replacement candidate is created.
- Adversarial correction loop: the first full server run exposed seven
  contract/race regressions. Follow-up Arc review found and closed transport
  polling/mutation recovery, expired-preview exposure, result-version
  ordering, stale source reads and Temporal child-start finalization. The
  production-baseline merge then exposed listener registration order in the
  cabinet; `initCabinet()` now registers meeting-list fencing before share
  listeners. Each correction was followed by a focused test and the full CI
  was rerun from a clean isolated database.

- Final repository gate (`infra/scripts/ci-local.sh`, 2026-07-24): **PASS**.
  macOS legacy guard/build/tests/contract validation passed; Swift tests were
  **625 passed**. The final isolated server collection was **2,458** tests
  with digest `4884c64dd789e021944b1b88eaf23db32c1891b67bb886d52fdabeb8fe7b7edb`;
  the final server result was **2,415 passed, 1 skipped, 11 warnings** in
  352.29s, and the strict lane remained **41 passed, 1 skipped, 2 warnings**.
  Warnings are limited to pytest assert-rewrite, Starlette/httpx deprecation
  and the known SQLAlchemy table-cycle warning.
- The rollback-expiry regression added in commit `9d7d3125` passed in the
  focused PostgreSQL deletion/upload/local-purge set: **36 passed, 2 warnings**.
  It reproduces a failed first purge item rolling back the session and proves
  the next meeting is reloaded from scalar identifiers rather than implicitly
  refreshing an expired ORM object.
- Final evidence scans: deployment evidence scan **PASS (7 files)**;
  production Compose config **PASS**; deployment/test shell syntax **PASS**;
  disposable RLS verifier regression **1 passed, 2 warnings**; metadata-only
  no-secret cabinet/admin contract suite **26 passed, 2 warnings**. Running
  the standalone RLS verifier without a configured database correctly reports
  `postgres_test_database_required`; live production RLS remains uninspected
  and is a release gate, not a claim of production readiness.
- Ponytail review: **Lean already. Ship.** No removable dependency,
  speculative abstraction or standard-library replacement was found without
  weakening lifecycle fences or evidence; net simplification opportunity is
  **0 lines**.
- Arc review correction loop: the production-baseline pass found and closed a
  release P1 where the merge had dropped the Feature 124 changelog entry;
  `CHANGELOG.md` was restored in commit `bad87292`. Final repeat review is
  required on the release candidate before deploy.
- Migration correction loop: Arc found that the content migrations could
  replace the production maintenance helper without `prompt_optimization`;
  `0035` and `0039` now preserve that operation. The merge revision remains a
  minimal no-op because Alembic traverses the sibling content branch itself.
  The production-head migration test now asserts the resulting schema and
  final helper SQL; the focused migration/RLS set passed **18 tests, 2
  warnings**.
- Rollback correction loop: when legacy lineage markers prevent downgrading
  `0039`, the runtime now keeps the safe `0040` schema, closes automatic
  dispatch and starts the compatibility runtime; it never starts the old
  checkout against an unknown merge-head schema. The guard is covered by the
  deployment-readiness fixture and the focused rollback set is green.
- Maintenance correction loop: the first post-deploy Arc pass found a live
  `MissingGreenlet` in the deletion reconciler after a session rollback. The
  reconciler, manual request and retry branches now cache immutable IDs and
  reacquire meetings after rollback; the regression test and full CI passed on
  `9d7d3125`.

The focused harness had one transient PostgreSQL startup failure during an
earlier retry; the final isolated runs above passed and removed their test
containers.

- The first production execute against the pre-merge Feature 124 branch
  stopped safely at the migration gate because production was already at
  `0037_auth_rate_limit_buckets`, which that branch did not contain. Runtime
  rollback was attempted and the remote checkout returned to its previous
  SHA; no schema change was applied. The integrated candidate adds
  `0040_merge_content_regen_share` and a regression proving an existing
  Feature 125 head upgrades to it. A new dry-run must be recorded after the
  recovery branch is updated to the integrated commit.
- Integrated release dry-run (`infra/scripts/cd-remote.sh --dry-run --branch
  codex/124-content-regeneration-lifecycle-recovery`, 2026-07-24): **PASS**
  against runtime candidate `9d7d3125`. The dry-run emitted the complete
  clean-worktree, pinned-SHA, backup, restore, migration-head,
  runtime-readiness, smoke, dispatch, rollback, health and post-deploy
  reconciliation step plan. Execute remains gated on the production evidence
  below.

## Release and production gate

Only after clean adversarial/Ponytail review, PR checks, migration/backup
rehearsal and explicit approval:

```sh
infra/scripts/cd-remote.sh --dry-run --branch codex/124-content-regeneration-lifecycle-recovery
infra/scripts/cd-remote.sh --execute --branch codex/124-content-regeneration-lifecycle-recovery
```

Then capture health/smoke, rollback readiness, server/app version evidence and
the CalVer tag/release. If live RLS or remote credentials are unavailable, report
the exact blocker and do not claim production readiness.

## Evidence hygiene

- Keep only IDs, hashes, statuses, counts, timestamps and safe problem codes.
- Do not paste transcript text, raw provider JSON, audio paths, tokens,
  credentials, signed URLs or private names into this guide or CI logs.
- Use synthetic fixtures for screenshots/assistive-technology inspection.
