# Quickstart: Interactive Playback Timeline

## Prerequisites

- Server development environment installed.
- Synthetic fixture data only; no real audio, transcript, participant names, credentials, or private screenshots in evidence.

## Focused validation

From `apps/server`:

```sh
bash scripts/run_local_postgres_tests.sh \
  tests/contract/test_cabinet_playback_contract.py \
  tests/contract/test_transcript_turn_contract.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/integration/test_speaker_names.py \
  tests/integration/test_rls_meeting_content_policies.py \
  tests/integration/test_postgres_migrations.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py

uv run ruff check \
  src/twobrain_rec_server/api/schemas.py \
  src/twobrain_rec_server/cabinet \
  src/twobrain_rec_server/db/models \
  src/twobrain_rec_server/deletion/service.py \
  tests/contract/test_cabinet_playback_contract.py \
  tests/contract/test_transcript_turn_contract.py \
  tests/integration/test_speaker_names.py \
  tests/integration/test_rls_meeting_content_policies.py \
  tests/integration/test_postgres_migrations.py \
  tests/unit/test_cabinet_view_models.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected focused outcomes:

- Main progress and speaker lanes share one measurable inner start/end and equivalent pointer positions differ by at most 0.25 seconds.
- Lane pointer seeks work on speech and gap areas; skip and transcript timestamp controls use the same bounded path.
- Single, overlapping, silence, pause, end, and seek samples produce the expected active lane/current-turn states.
- Deliberate seeks center the matching transcript turn without moving focus; reduced motion disables animation.
- Creator/owner/admin can set, replace, clear, and reload a speaker name; view-only, cross-workspace, invalid-CSRF, invalid-name, and unknown-speaker requests fail closed.
- Audit contains actor/action/key only, and meeting deletion removes the override row.
- Browser and desktop-embedded detail share the same behavior and authorization.

## In-app browser and design QA

Use a synthetic meeting-detail fixture with retained playback and at least three speaker lanes:

1. Compare 0%, 25%, 50%, 75%, and 100% positions across the main progress row and every lane.
2. Seek through a speaker segment and a silence gap; verify audio time, aligned playheads, active lanes, and centered transcript.
3. Exercise range keyboard controls and visible focus; repeat with reduced motion.
4. Rename, reload, and clear one speaker; verify transcript, timeline, and speaker summary stay consistent.
5. Check browser console, browser cabinet width, and desktop-embedded width.
6. Record the source-vs-implementation review in repository-root `design-qa.md`; resolve all P0-P2 findings and set `final result: passed`.

## Repository gate

From the repository root:

```sh
git diff --check
infra/scripts/ci-local.sh
```

No deploy or production data mutation is part of this feature lane.
