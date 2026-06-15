# V8 Deep Current Pass

Date: 2026-06-15
Figma file: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Page: `030 MVP Experience v8 - Clean RU`

## Purpose

This pass responds to the stakeholder concern that previous checks still missed
visible polish issues: different button sizes, flow inconsistencies, technical
copy, underthought settings, and sparse working surfaces.

The pass uses the active V8 Figma page as current evidence, not historical V5
or V7 screenshots.

## Screenshots Captured

Pre-fix current-state screenshots:

- `v8-16-current-search-filter-overlay.png`
- `v8-01-current-sign-in.png`
- `v8-05-current-active-recording.png`
- `v8-06-current-upload-processing-list.png`

Post-fix evidence:

- `v8-16-after-40px-button-fix.png`
- `v8-05-after-stop-wording-fix.png`
- `v8-05-after-stop-cluster-spacing-fix.png`
- `v8-05-after-density-row-fix.png`
- `v8-06-after-media-cta-fix.png`
- `v8-06-after-density-row-fix.png`
- `v8-06-after-density-row-and-height-fix.png`
- `v8-03-final-40px-rhythm.png`
- `v8-11-final-40px-rhythm.png`
- `v8-13-final-40px-rhythm.png`

## Findings Fixed

1. `V8 16 - Командный поиск и фильтры` had five visible buttons at `38px`
   height. They looked close to system controls, but not actually on the
   `40px` button token. Result actions and filter footer actions now use
   `40px`.
2. `V8 05 - Активная запись в меню и окне` used `Стоп` in the menu-bar
   cluster while the product contract and popover used `Остановить`. The top
   action now uses `Остановить`.
3. That wording change created a visual overlap with the `Запись 12:48` chip.
   The menu-bar cluster now has explicit gaps: `8px` between the recording chip
   and stop button, and `16px` before the `Сохраняется` status.
4. `V8 06 - Загрузка и обработка в списке` used `Выбрать файл`, which made
   upload feel file-object-first instead of media/meeting-first. The CTA now
   reads `Выбрать медиа`.
5. `V8 05` and `V8 06` still felt sparse after the earlier mechanical QA.
   `V8 05` now has three recent meeting rows, and `V8 06` now has four
   lifecycle rows. The added rows use realistic synthetic meeting titles and
   `Нужны спикеры` / `Проверить` status-action pairs.
6. The new `V8 06` row initially made the list card too tall. The lifecycle
   list card was reduced to `480px` height after visual QA, leaving `44px`
   bottom padding inside the card.
7. A stricter 2026-06-16 rhythm pass found that the page still mixed `36px`
   sidebar/browser nav rows and one `34px` transcript search field with `40px`
   primary/action controls. All visible nav/action/search controls were
   normalized to the `40px` interaction rhythm.
8. `V8 03 - Рабочее пространство встреч` still had visual text pressure even
   though the API overlap check passed: the readiness copy ran toward the
   primary button, and the first meeting title competed with status/action
   columns. The readiness copy is now shorter, the first meeting title is
   shortened, and status/action columns have stable positions.
9. `V8 11 - Веб-детали встречи и транскрипт` had a `34px` internal search
   field and an odd lower sync chip reading `видно везде`. The search field is
   now `40px`; the lower status now reads `Синхронизировано` and the chip is
   wide enough not to clip.
10. `V8 13 - Светлая тема: проверка экрана` had the clearest visible mixed
    rhythm: a `36px` selected sidebar row near a `40px` icon action. The light
    proof now uses the same `40px` sidebar/action rhythm as the dark desktop
    screens.

## Final Figma Audit

Final all-frame Figma API audit after this pass:

| Check | Result |
|---|---:|
| V8 frames | `17` |
| Missing frames | `0` |
| Text nodes | `691` |
| Controls | `254` |
| Buttons | `96` |
| Chips | `118` |
| Button height distribution | `36px: 1`, `40px: 95` |
| Chip height distribution | `28px: 118` |
| Target-size issues | `0` |
| Same-parent row issues | `0` |
| Technical-copy hits | `0` |
| Required gate failures | `0` |
| `V8 05` meeting rows | `3` |
| `V8 06` lifecycle rows | `4` |
| `V8 06` lifecycle list height | `480px` |
| `V8 06` lifecycle list bottom padding | `44px` |

Additional 2026-06-16 rhythm audit after the stakeholder's repeated
button-size critique:

| Check | Result |
|---|---:|
| V8 frames | `17` |
| True interactive controls | `140` |
| Control height distribution | `40px: 138`, intentional large panels excluded from button QA |
| Low/narrow true controls | `0` |
| Same-parent row issues | `0` |
| Visible technical-copy hits | `0` |
| Overflow hits | `0` |
| Text-overlap hits | `0` |
| Stale `видно везде` status text | `0` |

The raw Figma script still sees two large clickable/panel frames (`48px` and
`354px`) when using broad reaction/name heuristics; those are not button-token
controls and are excluded from the true-control verdict above.

## Remaining Review Note

This pass improves current V8 polish and density, but it does not close final
stakeholder visual approval. Continue to treat V8 as the active review
candidate until approval is explicitly recorded.
