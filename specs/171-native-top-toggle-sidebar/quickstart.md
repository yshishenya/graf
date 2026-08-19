# Quickstart: Единый верхний toggle и аккуратный rail

## Focused web checks

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp/apps/server
uv run pytest -q tests/unit/test_cabinet_web_shell.py -k 'rail or sidebar or search'
uv run pytest -q tests/contract/test_cabinet_static_assets_contract.py -k 'rail or sidebar or sidebar_toggle_tooltip or collapsed_sidebar'
node --check src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
cd /Users/yshishenya/.codex/worktrees/899d/crisp
git diff --check
```

The contract harness covers standalone/embedded wide and narrow defaults,
explicit pinned state, two toggles, content click, nav click, focus retention,
one handler and no resize policy.

## Focused native checks

Run the repository's existing macOS test/build command for the two focused test
classes after inspecting the target scheme. The source contract must cover the
top slot, one button per mode, reserved content space, labels/hints and the
unchanged 52px/308px widths.

## Visual matrix

### Web (in-app Browser)

1. At the default wide viewport, Reload and confirm expanded rail, visible logo,
   nav labels, download CTA and profile control.
2. At 900×700, Reload and confirm compact rail, top toggle, no empty header band,
   named nav links and no horizontal overflow.
3. Toggle twice; click the heading and a nav link; confirm manual state is not
   reset by unrelated content interaction.
4. Check hover/focus tooltip, `aria-expanded`, light/dark/high-contrast and
   reduced-motion behavior. Reset the temporary viewport before closeout.

### macOS (Computer Use)

1. Reload `GRAF Dev` with the native inspector collapsed and record the top
   disclosure coordinate.
2. Expand it and confirm the same coordinate, no overlap with title/settings or
   capture controls, and fixed position during content scrolling.
3. Click the same coordinate again without moving the pointer and confirm
   collapse; repeat after keyboard focus.
4. With the native panel collapsed, confirm a normal wide window starts with the
   left rail expanded after Reload; resize/inspect a narrow surface if available.

Evidence is metadata-only: record state, labels, dimensions and test counts;
never store real transcript, audio, credentials or private meeting screenshots.

## Repository gate

After both stories and review are complete, run once:

```sh
cd /Users/yshishenya/.codex/worktrees/899d/crisp
infra/scripts/ci-local.sh --fast
```

## Evidence

Status: PASS — implementation, focused checks and visual review completed on
2026-08-19. Local server was restarted before the final Browser pass so the
asset hash matched the working tree.

### Focused checks

- Web contract rail/sidebar selection: 5 passed; web-shell rail/sidebar/search
  selection: 10 passed; two expected pytest dependency warnings only.
- `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`:
  passed.
- `git diff --check`: passed.
- Native `AppControlAccessibilityTests` +
  `DesktopMeetingShellWebViewBoundaryTests`: 36 passed, 0 failures.

### Browser evidence (in-app Browser)

- `desktop_embedded`, 1280×700: initial state `is-rail-pinned`,
  `aria-expanded=true`, grid `176px + 1104px`; a content click and a move to
  the settings route kept the rail expanded. Navigation links exposed names.
- `desktop_embedded`, 900×700: initial compact state, grid `64px + 836px`,
  workspace header `display:none`, document had no horizontal overflow. The
  toggle stayed at one 40×40 top slot (`x=6`, `y=8`) through open and close.
- The same wide default was confirmed on the standalone browser surface.

### Native evidence (Computer Use)

- `GRAF Dev` collapsed and expanded states expose the same native disclosure
  identifier and top-trailing position; target size is 44 px.
- Labels were truthful in both states: «Показать панель управления» and
  «Скрыть панель управления»; accessibility hints described the corresponding
  action.
- The expanded scroll area started below the header slot; settings and capture
  controls stayed visible and did not overlap. A second activation collapsed the
  panel again without pointer travel.

### Closeout

The temporary Browser viewport override was reset before handoff. The selected
`infra/scripts/ci-local.sh --fast` gate passed with `1103 passed`, legacy audio
guard PASS, server lint PASS, Python compile PASS and isolated-container
cleanup PASS. Implementation commit SHA: `b76c077d`.
