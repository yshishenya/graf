# Quickstart: Адаптивная высота таймлайна спикеров

## Prerequisites

- Repository root: `/Users/yshishenya/.codex/worktrees/899d/crisp`
- Project Python environment is available; use `PYTHONPATH=apps/server/src` if
  the shell has not activated the server environment.
- Node.js is available.

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
PYTHONPATH=apps/server/src pytest -q apps/server/tests/unit/test_cabinet_web_shell.py -k 'speaker_timeline'
PYTHONPATH=apps/server/src pytest -q apps/server/tests/contract/test_cabinet_static_assets_contract.py -k 'timeline or resize'
node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
git diff --check
```

Expected result: 1–3 synthetic rows have no useless blank height and no resize
affordance; larger fixtures retain bounded pointer/keyboard resize, viewport
ceiling, one page listener and playback position.

## Synthetic visual matrix

Use Browser and embedded shell fixtures with 1, 2, 3, 4, 12 and 40 speakers at
wide and narrow viewports. Record only counts, dimensions and pass/fail. Do not
save meeting text, audio, credentials or private screenshots in the repository.

## Evidence — implementation closeout

- Status: implementation and focused validation passed.
- Synthetic rows: 1/2/3 use natural height and hide the resize affordance;
  4/12/40 keep bounded pointer/keyboard resize and viewport protection.
- Playback: synthetic resize harness preserved `currentTime` and did not add
  duplicate listeners after a partial update.
- Checks: server unit 12 passed; server contract 7 passed; `node --check` and
  `git diff --check` passed.
- Scope: synthetic metadata only; no meeting text, audio, credentials or
  screenshots were saved.

## Closeout

Run `infra/scripts/ci-local.sh --fast` once after the combined 161/168/169/170
UX slices and record the exact SHA here.

Fast gate evidence: `a219545be3c959576261dcb1edd46b01463bd0d0` — PASS
(`ci-local.sh --fast`).
