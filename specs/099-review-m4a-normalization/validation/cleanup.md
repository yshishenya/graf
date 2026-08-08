# Feature 099 Deletion Race And Cleanup Receipt

**Date**: 2026-07-14
**Task**: T101

## Command

```sh
cd apps/server
GRAF_TEST_REC_DIR=<authorized-test-rec> PYTHONPATH=src \
  uv run --extra dev pytest -q \
  tests/integration/test_playback_normalization_deletion.py \
  tests/integration/test_meeting_deletion_workflow.py::test_manual_deletion_purges_server_audio_objects_and_upload_temps \
  tests/integration/test_retention_policy_execution.py::test_retention_deletion_cancels_active_normalization_without_user_action \
  tests/integration/test_playback_normalization_test_rec_e2e.py
```

Result: `9 passed, 1 warning in 12.53s`.

The warning is the existing Starlette `TestClient` deprecation notice and does
not affect lifecycle or residue assertions.

## Post-review response-loss regression

The original cooperative upload/deletion test was extended after independent
review exposed the harder case where MinIO can finish an accepted `PUT` after
the worker process loses its database connection. The final behavior is:

- a deleted `local_preparing` or `cleanup_pending` attempt whose immutable
  object is absent records `already_missing_pending_recheck`;
- `cleaned_at` remains null, so the attempt stays in the bounded round-robin
  cleanup selector without a TTL;
- an empty reconciliation does not falsely close the tombstone;
- whenever the late object appears, the next reconciliation deletes it and
  records the truthful `deleted` result;
- an exact response-loss harness converged with `cleanup_count=1` and no late
  object residue;
- the same proof with a synthetic 365-day delay converged without user or
  administrator action.

Focused post-fix results:

- deletion plus audit regression: `28 passed`;
- deletion/retention/retry/restart/deploy neighborhood: `69 passed`;
- disposable PostgreSQL 17 normalization/RLS suite: `19 passed`;
- direct RLS probe: `pass`;
- temporary runtime-role residue: `0`.

## Deletion-race truth

- Deletion won from `queued`, `running`, `publishing` and `retry_wait` states.
- A local worker paused after source preparation, deletion completed, then the
  worker resumed. It was denied publication and returned the durable deferred
  result. A process-loss variant also proved that an object arriving after the
  deletion transaction is removed by the durable no-TTL tombstone.
- Every affected job ended `cancelled` with `meeting_deleting`.
- Every created attempt ended `purged`; lease ownership was cleared.
- Candidate, canonical and attempt temp objects were accounted separately.
- No validated canonical artifact appeared after deletion.
- Candidate/canonical object deletion was deduplicated when an attempt and
  published artifact referenced the same object.
- Retention-triggered deletion cancelled active normalization without any user
  repair or retry action.
- Deletion reports remained metadata-only and exposed no object key.

## Residue truth

- Per-job normalization work directories: empty.
- Isolated fake object stores after local `test-rec` E2E: `0` objects.
- Authorized source SHA-256 before/after: unchanged for all selected sources.
- Local UI app process: stopped.
- Local UI listener on port `8099`: absent.
- Feature UI runtime and isolated-home temp prefixes: `0` paths.
- Generated local UI `.app`, installer stage, package, state and HTML files:
  removed.
- `git status` contains no generated `.build` or `graf-099` artifact.
- `git diff --check`: pass.

## Final current-master UI deletion and cleanup

The post-review candidate repeated deletion through the real Chrome cabinet
using only synthetic records. One tab submitted the ordinary confirmation
while another tab continuously polled the preparing detail. The polling tab
changed to `Запись больше недоступна`, contained no audio element or range
input, and remained terminal after a deliberately scheduled late publication
attempt. The detail route returned `404` and the Chrome warning/error log was
empty.

After that run:

- the harness, reverse proxy and disposable QA app were stopped;
- ports `8099`, `8100` and `55499` were clear;
- the derived app, installer stage, package, isolated home, state file,
  feature-owned saved state and harness runtime directories were removed;
- feature-owned pytest temp sessions from the focused PostgreSQL and cabinet
  runs were removed;
- no feature container, volume or image remained;
- the installed `/Applications/GRAF.app` process remained separate and
  running;
- no file was staged, committed, pushed, released or deployed.

An independent final read-only recheck reproduced feature temp paths `0`,
listeners `0`, derived processes `0` and Docker feature residue `0`. The only
matching application process was the separate installed GRAF app; at that
read-back it was version `2026.07.14.11` and remained outside the feature-099
test lifecycle.

This is feature-local lifecycle acceptance. It does not complete or alter the
separately deferred feature 097 security scan.
