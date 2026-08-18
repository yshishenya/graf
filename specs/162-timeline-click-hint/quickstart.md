# Quickstart: Понятная подсказка на таймлайне

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py -k 'speaker_timeline or playback_timeline'
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_recording_workflow_accessibility.py -k 'timeline'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

Expected result: playable render has one concrete action/result hint; track
labels remain keyboard-operable; unavailable render has no misleading hint.

## Evidence — 2026-08-18

- Implementation commit: `0e9c0dba165f496a4ba47782b12977e6b78b42e5`
- Unit render matrix: 5 passed, 70 deselected.
- Accessibility contract: 1 passed.
- JavaScript syntax: `node --check` passed.
- Hygiene: `git diff --check` passed.
- Scope: synthetic metadata only; no audio, transcript text, credentials or
  private screenshots were stored.

## Visual matrix

Review synthetic browser and embedded states at wide and narrow widths, with
long speaker names and reduced-motion preference. Record only pass/fail and
layout observations, not private meeting content.

## Closeout

Record the implementation SHA and focused results here after the feature
commit. The combined fast gate runs at the final UX closeout.
