# Quickstart: Meeting Content Regeneration Lifecycle

This guide is the validation source of truth for Feature 124. It uses synthetic
fixtures and metadata-only evidence. Never use real meeting audio, transcript,
credentials or signed URLs in output.

## Prerequisites

From the repository root:

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
```

Use the server virtual environment and the isolated local PostgreSQL harness
provided by `scripts/run_local_postgres_tests.sh`.

## Scenario matrix

### A. Immutable processing lineage

Run the focused processing/model tests:

```sh
cd apps/server
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/unit/test_processing_store.py \
  tests/integration/test_processing_*.py -q
```

Expected evidence:

- two media revisions produce different workflow/job/result identities;
- same normalized hash is idempotent;
- changed hash creates a new result and never deletes old segments;
- an old callback cannot change the current revision aggregate.

### B. Baseline and manual candidate idempotency

```sh
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/unit/test_outcomes_service.py \
  tests/integration/test_outcome_*.py -q
```

Expected evidence:

- one baseline candidate per full source/template/generator key;
- same-format selector click is a no-op unless explicit refresh intent exists;
- candidate stores provenance and current remains unchanged until accept;
- equivalent active requests deduplicate.

### C. Owner preview and stale accept

```sh
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_cabinet_summary_candidates.py \
  tests/contract/test_cabinet_candidate_preview_contract.py -q
```

Expected evidence:

- owner receives a safe read-only preview with format name;
- shared viewer receives only accepted current content;
- source/current/deletion mismatch returns 409 with no pointer mutation;
- successful accept atomically supersedes the previous current outcome.

### D. Durable dispatch and recovery

```sh
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_generation_dispatch_reconciliation.py \
  tests/unit/test_outcome_generation_workflow.py -q
```

Inject a Temporal start failure after the candidate commit. Expected evidence:
the reconciler retries the same idempotency key or records a bounded terminal
failure; no queued candidate remains indefinitely without a workflow identity or
next action.

### E. Deletion races and retention

```sh
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/integration/test_deletion_generation_races.py \
  tests/unit/test_deletion_service.py -q
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
cd apps/server
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
GRAF_TEST_WORKERS=1 bash ../../scripts/run_local_postgres_tests.sh \
  --focused tests/contract/test_cabinet_static_assets_contract.py \
  tests/contract/test_cabinet_candidate_preview_contract.py -q
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

## Release and production gate

Only after clean Arc/ponytail review, PR checks, migration/backup rehearsal and
explicit approval:

```sh
infra/scripts/cd-remote.sh --dry-run --branch 124-content-regeneration-lifecycle
infra/scripts/cd-remote.sh --execute --branch 124-content-regeneration-lifecycle
```

Then capture health/smoke, rollback readiness, server/app version evidence and
the CalVer tag/release. If live RLS or remote credentials are unavailable, report
the exact blocker and do not claim production readiness.

## Evidence hygiene

- Keep only IDs, hashes, statuses, counts, timestamps and safe problem codes.
- Do not paste transcript text, raw provider JSON, audio paths, tokens,
  credentials, signed URLs or private names into this guide or CI logs.
- Use synthetic fixtures for screenshots/assistive-technology inspection.
