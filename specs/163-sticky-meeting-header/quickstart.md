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

Record the implementation SHA and focused results here after the commit.
