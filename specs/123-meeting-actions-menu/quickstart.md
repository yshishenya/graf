# Quickstart: Понятное меню действий со встречей

## Prerequisites

- Use synthetic meeting fixtures only; do not capture private meeting content.
- Start the existing server test environment described by the repository.
- Exercise both `/meetings/{id}` and `/desktop/meetings/{id}`.

## Focused Automated Checks

```sh
cd apps/server
uv run pytest \
  tests/contract/test_recording_governance_ui_contract.py \
  tests/contract/test_recording_workflow_accessibility.py \
  tests/integration/test_cabinet_meeting_detail.py \
  tests/unit/test_cabinet_web_shell.py
```

Expected: all focused checks pass and no test expects the former large `Ещё`
modal or cockpit content inside the quick menu.

## Scenario 1: Ready owner, all actions

1. Open a synthetic ready meeting with export, audio download and delete allowed.
2. Open `Ещё`.
3. Confirm stable order and copy:
   `Экспортировать…`, `Расшифровка или итоги`, `Скачать аудио…`,
   `Исходная запись`, `Сведения о встрече`, divider,
   `Удалить встречу…`.
4. Confirm no `Файлы`, policy chips, revision, speakers or activity appear in
   the menu.
5. Open each destination and cancel/close without losing page position.

Expected: four concise actions; every destination uses its existing flow.

## Scenario 2: Capability matrix

Exercise synthetic cases for:

| Actor/state | Expected menu |
|---|---|
| Owner, export only | Export, details, permitted delete |
| Owner, audio only | Audio, details, permitted delete |
| Viewer without egress | Details only when details are permitted |
| Processing | Only currently valid actions; no disabled rows |
| Deletion in progress | No export, audio or new delete action |
| No available action | `Ещё` unavailable; no empty menu |

For denied routes, issue direct requests as well.

Expected: presentation is filtered, and server routes independently fail closed.

## Scenario 3: Details separation

1. Open `Ещё`, then `Сведения о встрече`.
2. Confirm files, lifecycle truth, revision, calendar context, speakers and
   activity remain reachable when present.
3. Close by the explicit close control, Escape and backdrop click.

Expected: focus stays in the dialog while open and returns to visible `Ещё`.

## Scenario 4: Keyboard-only menu

1. Tab to `Ещё`.
2. Open with Enter, Space, Down and Up in separate passes.
3. Use Up, Down, Home and End between available items.
4. Activate export and delete with Enter/Space.
5. Close with Escape.

Expected: correct first/last focus, wrap behavior, no hidden-focus target and
focus return to `Ещё` after dismissal.

## Scenario 5: Responsive and assistive states

Check browser and embedded cabinet in:

- dark and light appearance;
- 200% zoom down to 320 CSS px viewport;
- increased contrast and forced colors;
- reduced motion;
- keyboard and VoiceOver.

Expected: no clipping or horizontal scroll in the menu, minimum 40 px targets,
visible focus and complete Russian accessible names.

## Visual QA

Capture the open-menu state at the same viewport as the selected first mock.
Compare hierarchy, anchoring, spacing, helper copy, target size, focus and danger
separation. Record findings in `design-qa.md`; P0/P1/P2 findings block handoff.

## Closeout Gates

```sh
git diff --check
infra/scripts/ci-local.sh
```

Then complete Ponytail review, issue reconciliation and metadata-safe PR evidence.
