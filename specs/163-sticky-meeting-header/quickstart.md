# Quickstart: Закреплённый верхний блок встречи

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py -k 'detail or tab'
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_recording_workflow_accessibility.py -k 'meeting_review or tab'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

Expected result: one sticky wrapper is present; tabs retain their keyboard and
ARIA contract; synthetic scroll targets are not covered by the header.

## Visual matrix

Use synthetic meeting detail content in browser and embedded modes at wide,
narrow and long-title/action states. Scroll the main container before checking
both tabs. Keep evidence metadata-only.

## Closeout

- Implementation commit: `a8117f0e` (`feat(cabinet): закрепить верхний блок встречи`).
- Focused unit: `21 passed, 54 deselected`.
- Focused accessibility contract: `2 passed, 5 deselected`.
- Regression contract after CSS token update: `22 passed, 53 deselected`.
- `node --check` and `git diff --check`: passed.
- `infra/scripts/ci-local.sh --fast`: passed (`1101 passed`, lint and Python
  compile passed; legacy audio guard passed).
- macOS build: `GRAF_DEV_ORIGIN=http://127.0.0.1:8082 sh
  apps/macos/Scripts/build-dev-app.sh` passed; signed local `GRAF Dev` opened
  the current branch server in embedded mode.
- Metadata-only visual review: wide embedded meeting detail stayed on the
  current branch origin after scrolling a long synthetic transcript; title,
  metadata, actions and both tabs remained visible as one block, with no
  horizontal overflow. Keyboard tab semantics, light theme, reduced motion
  and narrow browser review were also checked; no actionable findings remain.
