# Quickstart: Canonical Speaker Turns

## Prerequisites

- Repository checkout with the server development environment installed.
- No production credentials, raw meeting audio, or real transcript text in
  fixtures or logs.

## Focused validation

From `apps/server`:

```sh
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_transcript_turn_contract.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
uv run ruff check src/twobrain_rec_server/api/schemas.py \
  src/twobrain_rec_server/cabinet/view_models.py \
  src/twobrain_rec_server/cabinet/rendering.py \
  tests/contract/test_transcript_turn_contract.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected focused outcomes:

- Same-speaker rows with pairwise gaps at or below one second form one derived
  turn with first-start/last-end timing and ordered text.
- A gap above one second, speaker change, source-role change, processing-result
  boundary, unknown mapping, or malformed interval prevents an unsafe merge.
- Raw `segments` remain present and unchanged; rebuilding from the same fixture
  produces the same `speaker_turns`.
- The server-rendered review uses turns for readable rows and preserves seek
  timing without provider credentials or external identifiers.

## Repository gate

After focused checks pass, run the required high-risk server gate from the
repository root:

```sh
infra/scripts/ci-local.sh
```

Do not run production deploy or backfill in this feature slice. Production
proof, if requested later, must use metadata-only smoke evidence and an
explicit release/deploy approval.
