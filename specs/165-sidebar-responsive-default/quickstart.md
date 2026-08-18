# Quickstart: Адаптивное стартовое состояние боковой панели

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py -k 'shell or sidebar or rail'
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_cabinet_static_assets_contract.py -k 'rail or sidebar'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

The Node regression harness in
`tests/contract/test_cabinet_static_assets_contract.py` runs synthetic shell
initialization for standalone and embedded modes at 1280, 981, 980, 1121,
1120 and 720 px. It also checks explicit pinned state, two toggle activations,
one listener and manual-state preservation after resize.

## Visual matrix

Use the in-app Browser with synthetic/credential-free cabinet content at
1280×720 and 980×720. Confirm expanded labels on wide browser, compact rail on
narrow browser, truthful tooltip/ARIA state and no horizontal overflow. Repeat
the same matrix in the embedded macOS shell with Computer Use; at 1121 px it
must be expanded, while at 1120 px and below it must expose the compact toggle.
Check light/dark, keyboard focus and reduced-motion states. Keep evidence
metadata-only.

## Repository gate

After implementation and review, run once:

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
infra/scripts/ci-local.sh --fast
```

## Closeout evidence

Record focused test counts, Node syntax result, visual matrix result, fast-lane
result and implementation SHA here. Do not add real meeting text, audio,
credentials or private screenshots.

### Current evidence — 2026-08-18

- Unit shell/sidebar/rail selection: `76 passed`.
- Static contract rail/sidebar selection: `4 passed`, `44 deselected`.
- Node syntax and `git diff --check`: pass.
- `infra/scripts/ci-local.sh --fast`: `1102 passed`; lint and Python compile
  passed; `ci_local_result=pass mode=fast`.
- The Node VM matrix passes all browser/embedded boundaries and manual-state
  checks listed above.
- Browser visual limit: local login rendered successfully, but the synthetic
  `000000` code was rejected, so authenticated meeting-list visual states could
  not be confirmed. Embedded GRAF Dev likewise showed its normal missing-auth
  state. No credentials or meeting content were bypassed or stored.
- Implementation SHA: recorded in the closeout issue comments after the
  implementation commit; do not treat the moving branch as release evidence.
