# US1 First-Party Playback Receipt

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

**Tasks**: T021-T037

## Outcome

The first-party accepted-source path now creates one durable normalization job,
uses a verified optional playback candidate before deterministic microphone and
system fallback, publishes one fully validated canonical M4A, and exposes that
artifact independently from transcript or summary processing. The user performs
no conversion, retry, reprocess, or backfill action.

Playback list, detail, browser, embedded cabinet, download and Range routes all
derive from the same durable job/canonical-artifact truth. A candidate, source,
attempt, temporary output, weak legacy row, mismatched ready pointer, or invalid
validation bundle cannot become playback egress.

## Red receipt

The new playback-status contract was run before its implementation:

```text
uv run pytest tests/contract/test_playback_status_contract.py -q
```

Result: `4 failed, 1 passed`. The failures were the intended missing durable
state fields, transcript-independent availability, safe terminal projection and
accepted-revision reconciliation state. The already-green test proved an
unvalidated candidate was not streamed.

## Green receipt

From `apps/server`:

```text
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_playback_normalization_contract.py \
  tests/contract/test_playback_status_contract.py \
  tests/contract/test_playback_normalization_no_secret_egress.py \
  tests/contract/test_ingest_openapi_contract.py \
  tests/contract/test_openapi_contract_drift.py \
  tests/integration/test_playback_normalization_finalize.py \
  tests/integration/test_playback_normalization_workflow.py \
  tests/integration/test_playback_normalization_idempotency.py \
  tests/integration/test_finalize_processing_autostart.py \
  tests/integration/test_manual_media_upload.py \
  tests/integration/test_ingest_happy_path.py \
  tests/integration/test_cabinet_playback_route.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_cabinet_meeting_list.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/contract/test_cabinet_contract.py \
  tests/contract/test_cabinet_no_secret_content_egress.py \
  tests/unit/test_manifest_validation.py \
  tests/integration/test_finalize_integrity.py \
  tests/unit/test_playback_normalization_bmff.py \
  tests/unit/test_playback_normalization_profile.py \
  tests/unit/test_playback_normalization_selection.py \
  tests/unit/test_playback_normalization_worker.py \
  tests/unit/test_playback_normalization_workflow_identity.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_artifact_egress_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Result:

- `267 passed`;
- one pre-existing Starlette/httpx test-client deprecation warning;
- exit code `0`;
- elapsed time `103.22s`.

The workflow suite includes a real local FFmpeg/FFprobe run that generates a
dual-source M4A, re-probes and fully decodes it, verifies AAC-LC 48 kHz mono,
fast-start non-fragmented BMFF, bounded size, duration and digest, and cleans its
temporary directory.

Focused legacy cabinet/playback compatibility also reported `98 passed`, and
the exact runtime-versus-committed OpenAPI projection reported `4 passed`.

## Requirement receipts

| Requirement | Receipt |
|---|---|
| FR-001 | Publication creates one profile-v1 `playback` artifact and points the ready job to it. |
| FR-002 | Playback and audio download select only that matching ready canonical pointer; Range reads the stored object without conversion. |
| FR-003 | Manual accepted media enters the same durable queued job in finalize; the full supported-format conversion matrix remains owned by US2/T038-T046 and is not claimed complete here. |
| FR-004 | First-party finalize with absent, valid or invalid optional candidate reaches validated playback through candidate-first/fallback workflow tests. |
| FR-005 | Preparing/available/unavailable/deleting/deleted playback states compose independently with processing, ready and failed transcript states; no dead audio element is rendered. |
| FR-006 | Missing, empty, oversized, weakly validated, mismatched, wrong-codec and non-canonical rows fail the readiness gate. |
| FR-007 | Duplicate workflow/publication and losing publisher tests converge to one canonical artifact and clean the losing object. |
| FR-038 | Candidate byte-copy and container-layout remux decisions are validated; the complete manual M4A reuse matrix remains owned by US2/T040/T046. |
| FR-042 | Job persistence is in the accepted-source transaction; dispatch observes the committed job and remains independent from MediaScribe enablement/result state. |

## Success-criteria receipts

- SC-001: every green first-party scenario ends with one full-validated canonical
  artifact before `can_play=true`.
- SC-003: playback-route tests prove no probe, mix, remux or transcode occurs in
  the request path.
- SC-004 and SC-005: duplicate finalize/workflow/publication converge on the
  existing meeting, revision, job and canonical artifact.
- SC-011: `200` and bounded single-range `206` responses stream via
  `iter_object`; full-object reads are rejected by the test double.
- SC-013 and SC-014: attempt source selection uses the accepted revision's
  retained artifacts and introduces no competing ingest path.
- SC-015: candidate, source, attempt and invalid canonical rows are never
  exposed.
- SC-019: preparing/available playback is proven independently with transcript
  processing, ready and failed states.
- SC-020: the first-party supported-source path needs no user or workspace-admin
  repair control.
- SC-022: normalization scheduling precedes and does not wait for transcript or
  summary completion.

## Scope truth

This receipt closes the US1 first-party checkpoint. It does not claim the US2
full manual format matrix, automatic retry cycles, legacy backfill, deletion
races, production worker/deploy readiness, real Chrome evidence, or release
closeout. Those remain explicit later tasks. Feature 097 and its separate
security scan were not touched. No implementation commit was created.
