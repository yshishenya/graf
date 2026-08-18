# Quickstart: Выравнивание нижнего playback

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_cabinet_static_assets_contract.py -k 'rail or playback or resize'
PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_cabinet_web_shell.py -k 'playback or cabinet_rail'
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

Synthetic visual matrix: browser 1280/980 and embedded 1121/1120/720, both rail
states, available/preparing/unavailable playback. Record only dimensions and
pass/fail; no private content.

Fast repository validation is shared with the combined UX batch.
