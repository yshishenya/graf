# Quickstart: Цельная геометрия compact rail

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
uv run pytest -q tests/contract/test_cabinet_static_assets_contract.py -k 'rail or collapsed_sidebar'
uv run pytest -q tests/unit/test_cabinet_web_shell.py -k 'rail or sidebar'
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

Expected: the contract requires one complete final collapsed geometry owner,
rejects the old 52×36 active item pattern and preserves existing state/markup
contracts.

## Visual matrix

### Web with the in-app Browser

1. Open a safe synthetic/empty cabinet surface at a viewport wider than 1120px.
2. Collapse manually and inspect computed bounds: rail 64px; toggle, selected
   nav item and profile 40×40px; their centers and icon centers at `x=32±1px`.
3. Hover and keyboard-focus each action. Confirm active/hover/focus backgrounds
   share bounds and focus is not clipped.
4. Resize/reload below 981px and repeat. Confirm the same geometry and no empty
   workspace-header slot or horizontal overflow.
5. Expand and confirm current 176px layout, texts and profile menu are unchanged.

### macOS with Computer Use

1. Build/relaunch the installed `GRAF Dev` from the final working tree.
2. Confirm titlebar/traffic lights do not overlap web controls and the top toggle
   sits below the native safe area.
3. Collapse/expand twice without moving the pointer. Confirm the toggle remains
   in its top slot and no nav/profile element overlaps another.
4. Check profile bottom inset and menu opening in compact and expanded states.

Evidence is metadata-only. Do not store real meeting text, names, email,
screenshots, audio, credentials or signed URLs in the repository.

## Review and repository gate

- Correctness/root-cause review: no remaining competing compact dimensions.
- UX/accessibility review: one axis, one state geometry, visible focus.
- Ponytail review: deletion/narrowing over another override; no new abstraction.
- Run `infra/scripts/ci-local.sh --fast` once after focused and visual checks.

## Evidence

Status: PASS — focused, visual and repository fast validation completed on
2026-08-19.

### Focused checks

- Contract selection: 5 passed, 46 deselected; two existing dependency warnings.
- Web-shell selection: 9 passed, 68 deselected; the same two existing warnings.
- `git diff --check`: PASS.

### In-app Browser

- 1280×700 wide manual compact and 900×700 responsive compact both measured a
  64px rail. Toggle, selected nav item and profile were 40×40px; control/icon
  centers were `x=31.5–32px`, within the 1px contract.
- Workspace header computed `display:none`; horizontal overflow delta was 0.
- Expanded toggle measured `x=12,y=8`; collapsed measured `x=11.5,y=8`. The
  half-pixel difference is the 1px divider and leaves the pointer in the same
  target for the second click.
- Keyboard focus exposed a 2px visible outline with 2px offset. Temporary
  viewport overrides were reset after validation.

### GRAF Dev / Computer Use

- A clean process restart loaded the final CSS from the 127.0.0.1:8081 stand.
- Compact rail showed centered toggle/navigation/profile with no titlebar,
  content or native-panel overlap; the profile remained present in the
  accessibility tree and at the bottom of the rail.
- The compact profile menu opened with «Настройки» and «Выйти» and closed by
  Escape.
- Two clicks at the unchanged left-toggle coordinate `(31,49)` expanded and
  collapsed the web sidebar. Two clicks at `(1014,49)` did the same for the
  top-fixed native inspector toggle.
- No screenshots or private meeting content were written to the repository.

### Repository fast gate

- `infra/scripts/ci-local.sh --fast`: PASS.
- 1103 server tests passed with two existing dependency warnings.
- Legacy audio architecture guard, server lint and Python compile: PASS.
- Isolated Postgres test container cleanup: PASS.
