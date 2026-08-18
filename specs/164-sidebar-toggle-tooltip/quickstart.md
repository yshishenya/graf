# Quickstart: Понятный toggle боковой панели

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py -k 'rail or toggle'
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_static_assets_contract.py -k 'rail or profile or static'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

## Visual matrix

Use synthetic credential-free browser and embedded renders at wide and narrow
sizes. Inspect collapsed and expanded states with pointer hover and keyboard
focus, then activate the same control twice without moving the pointer. Repeat
in dark/light themes and reduced-motion mode. Evidence must remain metadata-only.

## Closeout

Implementation SHA: `85e4a6eda0d860cc4525f6b6d871cd860695aebc`.

Focused evidence (2026-08-18):

- `tests/unit/test_cabinet_web_shell.py -k 'rail or toggle'`: 4 passed.
- `tests/contract/test_cabinet_static_assets_contract.py -k 'rail or toggle or shared_shell'`: 4 passed.
- `node --check .../cabinet.js`: PASS.
- `git diff --check`: PASS.
- `infra/scripts/ci-local.sh --fast`: 1101 passed; lint, Python compile and
  legacy-audio guard passed; 2 existing pytest warnings.

Synthetic in-app browser evidence (metadata-only):

- Wide `1280×720`, dark theme: exactly one toggle; collapsed and expanded
  tooltip/action labels matched; pointer activation twice preserved the hit
  target and focus.
- Narrow `390×844`: hover tooltip was fully visible after moving presentation
  outside the rail clipping context; document width stayed exactly `390px`.
- Keyboard Enter activation twice toggled both states and retained focus on the
  toggle. The native `button type="button"` contract remains the Space path;
  the in-app harness did not expose a working Space key alias, so no product
  workaround was added.
- No real account, meeting content, credentials or private screenshots were
  stored in evidence. Feature 165 responsive default state remains out of
  scope.
