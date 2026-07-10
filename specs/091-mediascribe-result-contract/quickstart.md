# Quickstart: MediaScribe Result Contract

## Focused Validation

Run from `apps/server`:

```sh
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_mediascribe_client_contract.py \
  tests/integration/test_mediascribe_processing_happy_path.py \
  tests/integration/test_processing_failures.py \
  tests/integration/test_meeting_outcomes_generation.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_notes_action_truth_view_models.py
```

Expected outcome:

- Ready/available imports transcript and generates outcomes.
- Ready/unavailable no-speech persists processed-no-transcript metadata and blocks outcomes.
- Failed invalid audio payload is an input-audio business outcome.
- Failed service-origin job keeps service-failure behavior.
- UI copy and artifact download state do not claim transcript availability.

## Migration Check

Run:

```sh
PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_processing_migrations.py tests/integration/test_postgres_migrations.py
```

Expected outcome: migration/model inventory accepts the new nullable failure metadata columns.

## Forbidden Content Scan

Run:

```sh
rg -n \
  -e "(api[_-]?key|access_token|refresh_token|signed_url|object_key|bucket|private_path|raw_transcript|raw_audio)\\s*[:=]\\s*[^,[:space:]}]{4,}" \
  -e "-----BEGIN (RSA|OPENSSH|EC|DSA|PRIVATE) KEY-----" \
  specs/091-mediascribe-result-contract \
  apps/server/src/twobrain_rec_server/mediascribe \
  apps/server/src/twobrain_rec_server/processing \
  apps/server/src/twobrain_rec_server/outcomes \
  apps/server/src/twobrain_rec_server/cabinet \
  apps/server/tests \
  CHANGELOG.md
```

Expected outcome: no live secrets, signed URLs, raw audio, raw transcript text, object keys, or private meeting content.

## Repository Gate

Run before closeout:

```sh
infra/scripts/ci-local.sh
```

Expected outcome: local CI passes. Production deploy is out of scope for this slice.
