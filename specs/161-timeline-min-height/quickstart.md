# Quickstart: Минимальная высота таймлайна спикеров

## Prerequisites

- Repository root: `/Users/yshishenya/.codex/worktrees/899d/crisp`
- Node.js and project Python environment are available.

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
pytest -q apps/server/tests/unit/test_cabinet_web_shell.py -k 'speaker_timeline'
pytest -q apps/server/tests/contract/test_recording_workflow_accessibility.py apps/server/tests/contract/test_cabinet_static_assets_contract.py -k 'timeline or resize'
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

Expected result: all focused tests pass; the three-row fixture has no initial
vertical overflow; larger fixtures retain bounded resize and one resize
listener.

## Evidence — 2026-08-18

- Implementation commit: `09f56e81d078f0f2f50f912d059a902ac809446d`
- Unit: 4 passed, 71 deselected.
- Contract/resize: 3 passed, 49 deselected.
- JavaScript syntax: `node --check` passed.
- Hygiene: `git diff --check` passed.
- Scope: synthetic metadata only; no audio, transcript text, credentials or
  private screenshots were stored.

## Visual matrix

Use synthetic fixtures with 1, 3, 4, 12 and 40 speakers in browser and embedded
render modes. Record only counts, dimensions and pass/fail; do not save meeting
text, audio or private screenshots.

## Closeout

At the final combined UX closeout run `infra/scripts/ci-local.sh --fast` once
and record the exact commit SHA in release evidence.
