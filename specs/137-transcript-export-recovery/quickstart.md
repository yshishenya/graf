# Quickstart: transcript-export-recovery

Run from the repository root.

## Focused validation

```sh
cd apps/server
pytest -q tests/unit/test_outcome_prompts.py \
  tests/integration/test_artifact_egress_policy.py \
  tests/integration/test_transcript_export_egress.py \
  tests/integration/test_meeting_outcomes_generation.py
```

Expected synthetic scenarios:

1. A ready owner meeting with no policy row exposes transcript and accepted
   summary; the same meeting is blocked for a permitted non-owner.
2. An explicit `meeting_override` with `disabled` remains blocked for the owner.
3. A first revision-scoped deterministic baseline becomes current only through
   the trusted import/reconcile flag; a repeated call is idempotent and an
   existing accepted outcome is unchanged.
4. A known segment ID with a wrong provider sequence is stored with the pinned
   sequence; an unknown ID still fails validation.
5. A processed result with `Meeting.status=ingested_pending_processing` remains
   `ready` in the review view model.

## Repository gate

```sh
git diff --check
infra/scripts/ci-local.sh --fast
```

## Последнее validation evidence

- focused server lane: `67 passed`;
- processing/readiness focused lane: `8 passed`;
- `infra/scripts/ci-local.sh --fast`: `859 passed`, lint и Python compile прошли;
- `git diff --check`: passed.

Проверки использовали только синтетические фикстуры и метаданные; transcript,
audio и private meeting content в evidence не попадают.

## Production boundary

Do not run the maintenance command or deploy from this quickstart. After
explicit approval, first use the production dry-run, then a bounded command
such as `python apps/server/scripts/reconcile_initial_outcomes.py
--meeting-id <id> --execute`, and verify only state/count metadata. The
placeholder must be supplied by the operator at runtime; no production ID is
committed here.
