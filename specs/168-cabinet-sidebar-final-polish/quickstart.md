# Quickstart: Финальная геометрия боковой панели

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_cabinet_web_shell.py -k 'cabinet_rail or sidebar'
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_cabinet_static_assets_contract.py -k 'rail or sidebar_toggle'
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

## Visual matrix

Use synthetic browser and embedded shell states: browser 1280/980, embedded
1121/1120/720, expanded and collapsed. Check first paint, toggle focus/tooltip,
bottom playback inline start and horizontal overflow. Record dimensions and
pass/fail only.

## Evidence

Status: pending implementation. No private meeting content, audio or
credentials may be saved.

Closeout fast lane is shared with Features 161, 169 and 170.
