# Quickstart: Одна колонка настроек без legacy gutter

> **Superseded in part by Feature 174:** fallback assertions below are
> historical Feature 173 evidence. The inner navigation macro and
> `settings_mode` were removed after a complete production caller trace.

## Focused checks

```sh
cd /Users/yshishenya/.codex/worktrees/173-settings-single-column/crisp/apps/server
uv run pytest -q tests/contract/test_settings_ui_contract.py -k 'navigation or layout or settings'
uv run pytest -q tests/unit/test_cabinet_web_shell.py -k 'settings or sidebar'
cd /Users/yshishenya/.codex/worktrees/173-settings-single-column/crisp
git diff --check
```

After changing shared navigation expectations, run the focused PostgreSQL-backed
matrix from the repository root:

```sh
apps/server/scripts/run_local_postgres_tests.sh \
  tests/contract/test_settings_ui_contract.py \
  tests/unit/test_cabinet_web_shell.py \
  tests/integration/test_settings_ia_flow.py \
  tests/integration/test_cabinet_meeting_list.py \
  -k 'settings or sidebar or cabinet_settings_calendar_anchor'
```

Current expectation after Feature 174: one outer navigation, no inner legacy
macro or reserved column, and unchanged route/fragment boundaries.

## Visual matrix

### In-app Browser

1. Open `/settings` at 1280×720 and record sidebar/main/settings/content bounds.
2. Require content to start after standard main padding with no 220px+32px
   legacy offset; one navigation landmark only.
3. Visit recording, summaries, account, calendar and billing pages.
4. Repeat at a narrow viewport; require no overflow, overlap or clipped focus.
5. Keyboard through sidebar and content; confirm reading/focus order.

### GRAF Dev

1. Restart/reload the installed app from the final worktree server.
2. Open overview and one nested settings form.
3. Confirm native chrome, outer rail and content do not overlap in expanded and
   compact rail states.

Evidence is metadata-only. Screenshots remain outside the repository and must
not contain private meeting content or credentials.

## Repository gate

Run `infra/scripts/ci-local.sh --fast` once after focused, visual and review
passes. Full CI belongs to the later exact-SHA release candidate.

## Validation evidence — 2026-08-19

### Automated checks

- Focused settings/shell/integration matrix: `34 passed, 97 deselected`, two
  known dependency warnings, isolated PostgreSQL removed after the run.
- Earlier focused contract pass before the integration review: `21 passed`.
- Earlier focused shell pass before the integration review: `8 passed`.
- Fast repository lane: `1103 passed`, server lint PASS, Python compile PASS,
  legacy audio architecture guard PASS. macOS Swift validation was intentionally
  skipped by the fast lane; full CI remains reserved for the exact-SHA release
  candidate.
- `git diff --check`: PASS.
- Final Spec Kit analyze: 11 buildable requirements/criteria mapped to 7 tasks,
  100% coverage, no ambiguity, duplication, constitution or blocking findings.

### In-app Browser

| Surface | Viewport | Result |
|---|---:|---|
| Settings overview | 1280×720 | Sidebar `176px`; main starts at `x=176`; content starts at `x≈217` after standard padding instead of the previous `x≈469`; one `1022px` grid column, `0px` gap, one navigation landmark, no legacy navigation. |
| Recording, account, calendar, billing | 1280×720 | Every content wrapper starts at `x≈217`; one active page link and one navigation landmark; no legacy navigation. |
| Settings overview | 800×720 | Compact rail `64px`; content starts at `x≈90`; no horizontal overflow or overlap. |
| Embedded settings | 1100×720 | Compact rail `64px`; content starts at `x≈92`; one navigation landmark; no horizontal overflow or legacy navigation. |

Accepted screenshots were inspected and kept outside the repository. The saved
set includes the measured before state, wide web after state, narrow web after
state and embedded after state; no private meeting content was captured.

### GRAF Dev

- Installed `GRAF Dev` was pointed at the Feature 173 server on loopback `8081`
  and opened `/desktop/settings` through the real native shell.
- Compact and manually expanded rail states were both inspected at normal and
  zoomed window sizes. Cards begin after the standard content padding, native
  chrome and the right capture controls remain unobstructed, and the AX tree
  exposes one cabinet navigation with one active settings link.
- Wide-window default expansion remains owned by the already validated Feature
  171 train in PR #5363; this independent slice did not duplicate its state
  logic and only verified that either rail width composes correctly with the
  new single-column settings layout.

### Review closeout

- Correctness/root-cause: PASS after replacing stale integration assertions
  that required `data-settings-nav`, a duplicate inner landmark and two active
  links.
- Historical fallback contract: superseded by Feature 174 after the caller
  trace proved that no production surface depended on it.
- Product Design/accessibility: PASS for visible hierarchy, standard content
  origin, responsive reflow, single landmark and native/web non-overlap. Full
  WCAG conformance was not inferred from screenshots.
- Ponytail: Lean already. The implementation remains one macro guard and one
  existing settings-mode CSS override; no JavaScript, new state, breakpoint,
  dependency or per-page caller edits were added.

### Integration metadata

- Validated implementation commit: `af559060`.
- Pull request: `#5371`.
- Tasks T001–T007 were synchronized to issues `#5364`–`#5370` with validation
  comments. Issues remain open until the PR is merged; PR #5371 carries the
  closing references.
