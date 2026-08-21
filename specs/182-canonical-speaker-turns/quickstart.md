# Quickstart: Canonical Provider Speaker Turns

## Preconditions

- Work from branch `182-canonical-speaker-turns` at production baseline
  `c72e190d2de14c054fe6ebc04733021240d7f03e`.
- Use synthetic text and UUIDs only.
- Do not contact or deploy MediaScribe.

## Focused validation

```sh
cd apps/server
uv run pytest -q \
  tests/unit/test_canonical_speaker_turns.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_transcript_exports.py \
  tests/unit/test_mediascribe_result_import.py \
  tests/contract/test_recording_workflow_export_contract.py \
  tests/contract/test_transcript_export_no_secret_egress.py
```

Run PostgreSQL-backed parity and rename tests with the repository test helper:

```sh
apps/server/scripts/run_local_postgres_tests.sh \
  tests/integration/test_speaker_names.py \
  tests/integration/test_transcript_export_egress.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/integration/test_mediascribe_processing_happy_path.py
```

## Required synthetic assertions

1. One ASR row over two and three provider turns preserves every provider row.
2. A hypothetical winner below 50 percent is never confirmed.
3. A 40 ms unknown does not create a confirmed participant.
4. Three full-text duplicates degrade and emit ASR text once.
5. Stable one-, two-, and eleven-label inputs are deterministic.
6. Normal recording and manual upload produce equivalent models.
7. API, timeline, Markdown, CSV, XLSX, JSON, SRT, VTT, and outcomes have the
   same ordered canonical tuples and degraded state.
8. Saved names stay on the same provider identity after display renumbering.
9. Presentation rounding does not mutate canonical boundaries.
10. Diagnostics contain every allowed field and no forbidden content.

## Repository gate

```sh
infra/scripts/ci-local.sh --fast
```

## Closeout checks

```sh
git diff --check
git status --short
git diff --name-only
```

Review changed files for private content and verify there are no MediaScribe
external service/config/deploy changes. Stop without commit or deploy.
