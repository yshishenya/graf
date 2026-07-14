# US4 Automatic Legacy Backfill Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T063-T072

## Outcome

Legacy playback conversion is now automatic and requires no user or workspace
administrator action. At media-worker startup and every 60 seconds, the
reconciler enumerates workspaces in pages of 50, switches from the narrow global
inventory context to the exact workspace worker context, and inventories
accepted revisions by stable `(created_at, id)` pages of 100.

Every eligible revision receives one durable action before any legacy media job
can run:

- `preserve_valid` for one fully validated canonical artifact with the matching
  accepted-source fingerprint;
- `validate_candidate` for one existing legacy playback candidate;
- `normalize_source` for retained authoritative source, including the case where
  duplicate legacy candidates make candidate selection unsafe;
- `unavailable_source` with terminal `source_missing` or `source_mismatch` when
  neither canonical playback nor usable accepted source exists.

The persisted cursor, counters, action jobs and metadata-only audit receipts are
committed together. A restart resumes after the cursor. A zero-eligible
workspace still reaches a durable completed run. A completed profile run is
reused without duplicate work and reopens only after a later eligible watermark
is proven. A temporary inventory/database interruption records a safe `blocked`
run and the next worker cycle resumes it automatically.

Mutation remains blocked in three places until the whole workspace inventory is
complete: scheduler enumeration, durable lease claim and activity preparation.
Dispatch holds at most 25 IDs and orders new ingest, then due automatic retry,
then legacy backfill. Worker media concurrency remains exactly one.

## Red receipts

The first US4 run failed during collection because the durable inventory and
workspace enumeration functions did not yet exist. After those tests were
implemented, the aggregate admin test still failed with two retained
expectations: the API had no `playback_normalization` aggregate and the admin
view model did not project it. These expectations became green only after the
inventory, scheduler, tenant transition and read-only aggregate paths were
implemented.

No failing expectation was weakened into a button, CLI command, manual repair,
source replacement or unbounded scheduler.

## Green receipt

From `apps/server`:

```text
uv run ruff check .

uv run pytest -q \
  tests/contract/test_playback*.py \
  tests/integration/test_playback_normalization_*.py \
  tests/integration/test_rls_maintenance_context.py \
  tests/integration/test_rls_worker_context.py \
  tests/unit/test_playback_normalization_*.py \
  tests/contract/test_admin_api_contract.py \
  tests/unit/test_admin_audit_view_models.py \
  tests/unit/test_config_validation.py
```

Result:

- Ruff: all checks passed;
- pytest: `188 passed`, `4 skipped`;
- exit code: `0`;
- elapsed time: `26.88s`;
- one pre-existing Starlette/httpx test-client deprecation warning.

The four skipped cases were the environment-gated PostgreSQL cases. They were
not accepted as proof and were rerun against a real disposable PostgreSQL
database below.

The focused US4 inventory, priority, maintenance/worker transition, automatic
blocked recovery and admin aggregate run separately reported `12 passed`.

## Real PostgreSQL and RLS receipt

A unique disposable database was created in the already-running local
PostgreSQL service, migrated to `head`, exercised through both the migration
owner and a restricted RLS probe role, then force-dropped:

```text
RLS_TEST_DATABASE_URL=<disposable-postgresql-url> \
  uv run pytest -q \
    tests/integration/test_playback_normalization_postgres.py \
    tests/integration/test_rls_postgres_policies.py
```

Result:

- `13 passed`, exit code `0`, elapsed time `2.41s`;
- the global inventory function returned only organization/workspace/user/device
  scope IDs, enforced a page cap of 50 and returned no rows under the dispatch
  operation;
- an exact worker context created and completed a zero-eligible run through
  force-RLS;
- inventory/dispatch maintenance contexts remained select-only for normalization
  job/run tables and could not read attempt rows or perform updates;
- request/worker tenant isolation, cross-workspace rejection, one durable lease,
  canonical uniqueness and publication/deletion row locks stayed green;
- disposable database residue after cleanup: `0`.

## Inventory, priority and restart receipts

- A 101-revision workspace committed exactly 100 planned jobs and its cursor on
  the first page. Scheduler enumeration returned zero legacy jobs before the
  boundary. The resumed page added exactly one job, completed inventory and made
  only the first bounded 25 eligible for pickup.
- Pickup excludes future retries and orders one new-ingest job, one due retry and
  then legacy jobs. Calls above page 100, workspace page 50 or dispatch batch 25
  fail closed; enabled configuration requires those exact budgets and media
  concurrency one.
- Preserve, validate, regenerate, duplicate-candidate, missing-source and
  mismatched-source decisions each persisted the expected action. Meeting titles
  remained byte-for-byte unchanged.
- A validated canonical artifact is preserved even when retained source bytes no
  longer exist. Source loss never causes a fabricated replacement.
- Impossible legacy source loss creates one deduplicated metadata-only system
  incident per job/reason. The incident contains only safe hashes, profile and
  reason; it contains no title, filename, object key, media, transcript, summary,
  URL or credential.
- A synthetic inventory failure moved the run to `blocked` with
  `database_unavailable`; the next reconciliation cycle recovered it, inventoried
  the revision and dispatched it without operator or user work.

## Read-only operations visibility

The existing admin metrics GET now exposes only aggregate values:

- run-state counts;
- job-state counts;
- allowlisted safe-reason counts;
- current backlog count;
- oldest backlog age in seconds.

The aggregate contains no meeting/revision/job IDs, titles, local identifiers,
object paths, transcript/summary content or repair actions. The browser metrics
page receives the same aggregate and an ordinary reliability card; no mutation
route or control was added.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-014 | Worker startup and periodic reconciliation automatically create/resume legacy runs and jobs; blocked runs recover with no user/admin action. |
| FR-015 | Every evaluated revision receives a durable planned action and metadata-only audit receipt before the inventory-complete mutation gate opens. |
| FR-016 | Synthetic titles remained unchanged across preserve, validate, normalize, duplicate and unavailable decisions; no title/transcript field is selected for global inventory. |
| FR-017 | Missing and mismatched retained source persist terminal unavailable reasons and do not enter retry or media mutation. |
| FR-033 | Backfill uses only the existing accepted revision fingerprint and authoritative source roles; it creates no source revision, upload session or replacement source artifact. |
| FR-034 | A matching validated canonical playback artifact is preserved even when retained source is unavailable. |
| FR-041 | Valid canonical playback is reused, a unique candidate is validated, duplicate/invalid candidates regenerate from accepted source, and impossible source loss receives terminal truth plus one safe operational incident. |

## Success-criteria receipts

- SC-007: all 101 paged revisions and every decision-matrix revision received a
  planned action before any legacy pickup.
- SC-016: keyset cursor, unique run/job constraints, inventory gate, exact lease
  and bounded deterministic pickup converge concurrent/restarted work on one
  run and one job per revision/profile.
- SC-020: no retry, reprocess, repair, backfill button or operator command is
  needed for supported records.
- SC-021: every tested legacy record either preserved validated playback,
  entered candidate/source conversion, or terminated with an explicit safe
  unavailable reason; no media was fabricated.

## Scope truth

This receipt closes the US4 automatic legacy-backfill checkpoint. The wider
impossible-media matrix and localized user status remain US5; deletion,
retention, full operations/deploy gates and cleanup reports remain US6. Chrome,
production backfill/drain evidence, release and production closeout remain later
feature tasks. No macOS runtime source changed in US4, so no app rebuild or local
installation is required at this checkpoint. Feature 097 and its separate Codex
Security scan were not touched. No implementation commit was created.
