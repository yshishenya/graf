# Figma V8 Clean RU QA Evidence

Date: 2026-06-15
Figma file: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Active page: `030 MVP Experience v8 - Clean RU`
Active page id: `341:2`

## Scope

V8 replaces the v7.4 correction candidate as the current review candidate.
It was created after the stakeholder critique that old v5-v7 screens still had
uneven button sizing, fragmented upload/status flows, underdesigned settings,
overtechnical visible copy, and incomplete web/light-theme coverage.

V8 keeps the clean-room Krisp IA lesson: the product opens on meetings, search
and filters live in the meeting list, upload and processing are row/sheet
states, active recording is a menu-bar/header state, speaker assignment uses
one lane per speaker, and risky access/export/delete actions live in the full
cabinet.

## Current Frame Coverage

| Frame | Purpose | Status |
|---|---|---|
| `V8 00 - Карта MVP-потока и границы` | Product flow and reset rules | PASS |
| `V8 01 - Вход и подключение сервера` | Compact provider sign-in | PASS |
| `V8 02 - Первый запуск и разрешения macOS` | First-open permission guide | PASS |
| `V8 03 - Рабочее пространство встреч` | Desktop default meeting cockpit | PASS |
| `V8 04 - Подсказка найденной встречи` | Inline detected-meeting decision | PASS |
| `V8 05 - Активная запись в меню и окне` | Menu-bar/header recording state | PASS |
| `V8 06 - Загрузка и обработка в списке` | Upload/processing in the list | PASS |
| `V8 07 - Транскрипт и спикеры в приложении` | Embedded transcript and outcomes | PASS |
| `V8 08 - Дорожки назначения спикеров` | One lane per speaker | PASS |
| `V8 09 - Настройки записи и темы` | Settings IA, theme, sources, detection | PASS |
| `V8 10 - Веб-кабинет: встречи и фильтры` | Full web meeting list with inline filters | PASS |
| `V8 11 - Веб-детали встречи и транскрипт` | Full meeting review page | PASS |
| `V8 12 - Поделиться, экспорт, удаление` | Browser-owned governance actions | PASS |
| `V8 13 - Светлая тема: проверка экрана` | Light-theme desktop proof | PASS |
| `V8 14 - Правила интерфейса и QA` | Component sizes and review gates | PASS |
| `V8 15 - Общая загрузка медиа` | Shared desktop/web media upload sheet | PASS |
| `V8 16 - Командный поиск и фильтры` | Contextual search/filter command overlay | PASS |

## Programmatic QA

Final whole-page Figma Plugin API audit across all 17 visible V8 frames:

| Check | Result |
|---|---|
| Frame-bound overflow | `0` in every V8 frame |
| Button heights | only `36px` and `40px` for buttons; `32px` for compact segmented/theme controls |
| Bad button-height nodes | `0` |
| Chip heights | `28px` |
| Bad chip-height nodes | `0` |
| Visible forbidden implementation copy | `0` |
| Placeholder artifact nodes | `0` |
| Desktop speaker lanes | present as separate speaker rows |
| Settings theme coverage | system, dark, light, Russian language |
| Web list search/filter placement | inline on meeting list, no separate filter route |
| Upload/processing placement | list/sheet state, no standalone MVP destination |

Forbidden visible-copy sweep included local/offline auth competition,
implementation labels, route/API/webview terminology, "server online" style
status, irreversible deletion overpromise, and leftover placeholder labels.

Post-copy live recheck before the later overlay follow-up returned:
pre-overlay frame count `15`, `badButtonCount=0`, `badChipCount=0`, `overflowCount=0`,
`placeholderCount=0`, and `forbiddenTextCount=0`.

Post-goal strict re-audit after the user's button/flow/settings critique found
and fixed:

- `V8 10`, `V8 11`, and `V8 12` selected web-nav rows at `34px`; all now use
  the `36px` system height.
- `V8 10` right table columns overlapped between duration/source/status/action;
  source, status chip, and action columns are now separated.
- `V8 07` and `V8 11` playback metadata overlapped between time and source chip;
  the chip columns are now separated.
- `V8 00` still had English review words (`visual guide`, `workspace`,
  `upload`, `prompt`) and an overlapping principle block; copy and spacing are
  now corrected.
- Browser chrome copy used `rec.2brain.local` and English path hints; it now
  uses production-style Russian route hints.

Final strict Figma Plugin API re-audit result:
`frames=15`, `controls=112`, `badControls=0`, `chips=98`,
`badChips=0`, `forbiddenText=0`, `englishText=0`, `textOverlap=0`,
`overflow=0`, `reactions=65`, `invalidReactions=0`, `selfReactions=0`,
and `supersededReactions=0`.

Post-`computer-use` Krisp live pass correction:

- The visual screenshot pass found that several V8 desktop native sidebars still
  exposed `Загрузка` as a top-level navigation item even though upload is now a
  meeting-list sheet/status, not a standalone MVP destination.
- Figma text nodes in `V8 03`, `V8 04`, `V8 05`, `V8 06`, `V8 07`, `V8 08`,
  `V8 09`, and `V8 13` were corrected from top-level sidebar `Загрузка` to
  `Обзор`.
- Inline upload/status chips in `V8 06` were restored to `Загрузка` because
  those labels are status/filter states, not navigation.
- The settings subnav item was changed from `Загрузка` to `Хранилище` to
  represent storage/local queue settings without implying a separate upload
  section.

Targeted post-correction Figma API audit result before the later overlay
follow-up: pre-overlay frame count `15`, `buttonLike=72`, `badControls=0`, `chips=98`,
`badChips=0`, `sidebarUploadLeakCount=0`, `nativeSidebarOverviewCount=7`,
`settingsStorageCount=1`, `inlineUploadStatusCount=2`, `overflowCount=0`,
and `targetTextOverlapCount=0`.

Post-contract and density polish:

- The implementation-facing route/status/screen specs were synchronized with
  V8 so implementation cannot reintroduce separate desktop `Загрузка` or
  `Обработка` navigation.
- Figma layer names for corrected sidebar labels were renamed from stale
  `Загрузка` names to `Обзор`, so metadata and visual text now agree.
- `V8 03 - Рабочее пространство встреч` and
  `V8 13 - Светлая тема: проверка экрана` each gained one additional realistic
  meeting row to reduce the empty list area and make the meeting workspace read
  more like a dense operational surface.
- A clipped dark status chip introduced by that density pass was corrected from
  the long label to the compact Russian status label `Расшифровка`.

Targeted density post-polish audit result:
`badNavUploadCount=0`, `staleLayerNamesCount=0`, `badControlsCount=0`, and
`overflowCount=0` for both `V8 03` and `V8 13`; each now has four visible
meeting rows. Reviewed PNGs:
`/tmp/2brain-figma-v8-current-check/v8-03-density-polish-fixed.png` and
`/tmp/2brain-figma-v8-current-check/v8-13-density-polish.png`.

Settings and web table/detail polish:

- `V8 09 - Настройки записи и темы` wording was tightened in the right
  rail: `Полный кабинет`, `Правила сейчас`, `Системная`, and `Тёмная`.
- The `V8 09` theme row was re-spaced after the `Системная` chip was widened;
  the chip overlap count is now `0`.
- `V8 10 - Веб-кабинет: встречи и фильтры` had clipped row-action buttons and
  then a status/action overlap. The source/status/action columns were
  reflowed so row actions are inside the clipped row bounds and no longer
  collide with status chips.
- `V8 11 - Веб-детали встречи и транскрипт` playback source chip was changed from clipped
  long copy to `2 дорожки`.

Targeted V8 09/10/11 post-polish audit result:
`forbiddenCount=0`, `badControlsCount=0`, `overflowCount=0`, and
`clippedByParentCount=0` on all three frames. Reviewed PNGs:
`/tmp/2brain-figma-v8-next-pass/v8-09-settings-after-fixed2.png`,
`/tmp/2brain-figma-v8-next-pass/v8-10-web-list-after-fixed.png`, and
`/tmp/2brain-figma-v8-next-pass/v8-11-web-detail-after.png`.

Remaining value-surface deep pass:

- A dedicated screen-by-screen pass was added:
  `v8-remaining-screens-deep-pass.md`.
- The first audit of `V8 07` through `V8 14` found product and layout issues in
  the remaining value surfaces: `rec.2brain.dev` browser hints, `client-call.mp4`
  as a primary meeting title, a vague row action `Статус`, web-list table
  overlaps, playback source overlap, export row button overlap, weak deletion
  boundary wording, and QA-board ownership overlap.
- Figma corrections changed web browser hints to `Кабинет / ...`, changed file
  rows to human meeting titles, changed vague actions to `Подробнее`, separated
  overlapping table/playback/export elements, added explicit outside-control
  deletion truth, and added the Krisp matrix to the QA rules screen.
- Post-fix Figma API audit across `V8 07` through `V8 14` returned
  `missingFrames=0`, `badControls=[]`, `textOverlap=[]`, and
  `forbiddenHits=[]`. Screen-specific gates passed for transcript review,
  speaker lanes, settings, web list, web detail, share/export/delete, light
  theme proof, and component QA rules.

Krisp reference recheck:

- The stakeholder challenged whether V8 uses enough product practice from the
  Krisp desktop/web IA reference, beyond broad meeting-cockpit principles.
- A dedicated clean-room reference matrix was added:
  `krisp-reference-matrix.md`.
- Mechanical V8 QA remains useful, but it is no longer sufficient for final
  handoff. The Krisp-alignment queue was applied to `V8 01`, `V8 02`,
  `V8 03`, `V8 04`, `V8 05`, and `V8 06`, covering provider/login wording,
  guided permissions copy, desktop meeting-cockpit language, detected-meeting
  policy row clarity, active-recording chrome/popover copy and overlap, and
  upload rows behaving like meeting rows rather than file receipts.
- Figma corrections made after this recheck:
  - `V8 01`: `Войти по email` became `Войти по почте`; bottom trust copy now
    says recording does not start without explicit user start.
  - `V8 02`: simulated System Settings copy uses
    `Конфиденциальность и безопасность` and plain permission wording.
  - `V8 03`: `Веб-разделы` became `Готовность к записи`; processing rows now
    use `Расшифровка`; vague row-action `Статус` became `Подробнее`; the
    upload rail says `Добавить запись` instead of `Очередь загрузки пустая`.
  - `V8 04`: policy preview uses `Спрашивать`, `Всегда писать`, and `Вручную`.
  - `V8 05`: legacy `Видимый индикатор` copy is hidden; active-recording copy
    stays short and the popover says the meeting appears in the list after
    stop.
  - `V8 06`: uploaded media is represented as `Звонок с клиентом`, progress is
    secondary, and processing action is `Подробнее`.
- Targeted Figma API re-audit across `V8 01` through `V8 06` returned
  `missingFrames=0`, `forbiddenHits=0`, `badControls=[]`, with the required
  first-path copy gates present.

Whole-page Krisp IA consistency audit:

- A dedicated whole-page audit was added:
  `v8-whole-page-consistency-audit.md`.
- It covers `V8 00` through `V8 14` after the Krisp reference matrix pass,
  remaining value-surface pass, and active handoff copy cleanup.
- Whole-page Figma API result before the later overlay follow-up:
  pre-overlay frame count `15`, `missingFrames=0`,
  `forbiddenHits=0`, `badControls=0`, `textOverlapHits=0`,
  `reactionIssues=0`, and `gateFailures=0`.
- The same pass verified the Krisp-derived product gates: meeting workspace
  default, inline upload/processing, native active recording with
  `Остановить`, speaker lanes, list-detail settings, dense web list/detail,
  browser-owned governance, light-theme parity, and component QA rules.
- Active implementation-facing handoff docs were cleaned after the audit so
  development cannot reintroduce old UI copy such as vague `Статус` row
  actions, English `Stop`/`Start` labels, `Транскрибация`, or filename-first
  upload rows.

Stricter follow-up audit:

- A read-only `computer-use` pass against the installed Krisp desktop app
  reconfirmed the clean-room reference IA: desktop is a full meeting workspace
  with left navigation, dense meeting list, upcoming meetings, search/filter
  controls, and a separate audio-control rail. V8 uses the workspace/list IA
  but does not copy Krisp's audio/noise product rail.
- Figma fixes after this pass:
  - `V8 09`: settings category `Доступ` became `Конфиденциальность`, with the
    text node resized to stay on one line.
  - `V8 10`: primary web upload action `Загрузить файл` became
    `Загрузить медиа`, and the button was widened.
  - `V8 03`, `V8 06`, and `V8 13`: desktop/light upload actions changed from
    `Загрузить файл` to `Добавить запись`.
  - stale layer names for `client-call.mp4`, `Транскрибация`, and
    `Button / Статус` were renamed to the current V8 product language.
- Final strict Figma API audit checked visible text and implementation-relevant
  layer names before the overlay follow-up: pre-overlay frame count `15`,
  `buttonLike=77`, `reactionNodes=67`,
  `badControlHeights=0`, `visibleStaleHits=0`, `textOverflow=0`,
  `textOverlaps=0`, and `gateFailures=0`.
- Post-Krisp IA overlay follow-up added `V8 15` shared upload sheet and `V8 16`
  command search/filter overlay. A stricter follow-up then renamed all V8 frame
  layers to Russian handoff names, restored the active-recording popover stop
  button after a coordinate regression, restored the V8 web shell to `x=140`,
  `y=96`, centered web status chips at `28px`, removed remaining
  implementation-facing filter/upload explanatory copy, and shortened the
  upload validation chip to `Готово` after screenshot QA found a two-line wrap.
- Final focused Figma API audit after this polish returned `frameCount=17`,
  `expectedFrameCount=17`, `totalTextNodes=683`,
  `totalVisibleTextOutsideQA=647`, `totalButtonLike=240`,
  `totalReactionNodes=92`, `staleNames=[]`, `forbiddenVisibleText=[]`,
  `suspectButtons=[]`, and `gateFailures=0`.
- Reviewed PNGs are saved in this review folder:
  `v8-05-active-recording-after-krisp-ia-pass.png`,
  `v8-10-web-meetings-after-krisp-ia-pass.png`,
  `v8-14-qa-rules-after-krisp-ia-pass.png`,
  `v8-15-upload-sheet-after-chip-fix.png`, and
  `v8-16-search-filter-overlay-after-krisp-ia-pass.png`.

Standards and Krisp action-row diagnostic pass:

- The stakeholder challenged whether V8 used enough concrete Krisp UX/IA
  practice. The follow-up pass rechecked V8 against the clean-room Krisp
  principles, Apple platform control expectations, WCAG 2.2 target/focus/
  contrast requirements, and NN/g status-visibility / recognition-over-recall
  heuristics.
- Real Figma issues found and fixed: three remaining `36x36` icon buttons were
  normalized to `40x40`; two playback controls were widened from `54x40` to
  `56x40`; web header action spacing was changed from `4px` to `8px`; the web
  detail header no longer overlaps `Экспорт` with the kebab menu; and V8 QA
  number markers were renamed from `Chip / N` to `Step marker / N`.
- `V8 09` recording policy now uses the short Russian labels
  `Спрашивать`, `Всегда писать`, and `Вручную`, with explanatory copy outside
  the chips.
- The visible QA copy was tightened to avoid implementation vocabulary while
  preserving the rule that users should not see internal service details.
- Final stricter same-parent Figma API audit result:
  `frameCount=17`, `missingFrameNames=[]`, `textNodes=683`, `controls=216`,
  `buttons=94`, `chips=116`, `stepMarkers=5`, `reactionNodes=92`,
  `targetSizeIssues=[]`, `buttonRowIssues=[]`, `technicalCopyHits=[]`,
  `staleNames=[]`, `missingSettingsConcepts=[]`, `missingFlowWords=[]`, and
  `gateFailures=0`.
- Reviewed PNGs from this pass are saved in this review folder:
  `v8-07-transcript-after-krisp-action-row-fix.png`,
  `v8-09-settings-after-recording-policy-fix.png`,
  `v8-11-web-detail-after-krisp-action-row-fix.png`, and
  `v8-14-qa-rules-after-step-marker-fix.png`.

Deep current-state polish pass:

- A stricter current-state pass was added under `deep-current-pass/` after the
  stakeholder asked for another screen-by-screen check of button sizes, flow
  consistency, technical wording, settings, and empty working space.
- The pass fixed five `38px` buttons in `V8 16`, aligned the active-recording
  menu-bar action to `Остановить`, repaired the resulting top-cluster spacing
  to `8px` / `16px`, changed `V8 06` upload CTA from `Выбрать файл` to
  `Выбрать медиа`, and added realistic density rows to `V8 05` and `V8 06`.
- Final all-frame audit after this pass returned `frameCount=17`,
  `missingFrames=[]`, `textNodes=691`, `controls=254`, `buttons=96`,
  `chips=118`, `buttonHeightDistribution={36:1,40:95}`,
  `chipHeightDistribution={28:118}`, `targetSizeIssueCount=0`,
  `rowIssueCount=0`, `technicalCopyHitCount=0`,
  `requiredGateFailures=0`, `V8 05` meeting rows `3`, `V8 06` lifecycle rows
  `4`, and `V8 06` lifecycle list bottom padding `44px`.
- The 2026-06-16 rhythm follow-up tightened the same pass after another
  button-size review. Sidebar/browser nav rows, the desktop cabinet action,
  the upload-sheet close action, and the web-detail transcript search field now
  use the `40px` interaction rhythm. `V8 03` readiness copy and first-row
  columns were shortened/repositioned to avoid visual pressure, `V8 11`
  replaces `видно везде` with a non-clipped `Синхронизировано` status chip,
  and `V8 13` light proof now matches dark-screen sidebar/action sizing.
- Final focused Figma API validation for this rhythm pass returned
  `frameCount=17`, `totalControls=140`,
  `controlHeightDistribution={40:138}` for true interactive controls,
  `lowControlCount=0`, `forbiddenCount=0`, `visibleEverywhereCount=0`,
  `overflowCount=0`, and `textOverlapCount=0`.
- Evidence and notes: `deep-current-pass/audit.md`.

Concrete Krisp extraction response:

- After the stakeholder challenged whether V8 used enough of the real Krisp
  desktop/web UX and IA, a dedicated reference extraction pass was added under
  `krisp-reference-pass/`.
- The pass captured 11 Krisp reference states: desktop meeting controls,
  meeting detail notes, transcript speaker lanes, search command palette,
  account settings, AI note-taker policy, privacy/consent settings,
  action-items gating, web meeting-notes list, web filter menu, and web date
  filter popover.
- The extracted clean-room practices are now explicit gates: desktop meeting
  cockpit first, persistent native live-control rail, contextual search/filter,
  upload as row/status, server-owned speaker assignment, separate speaker
  lanes, list-detail settings, browser-owned governance, and dense web cabinet
  list/detail.
- Figma fixes from this pass added the `V8 03` right-side live control rail,
  the `V8 07` bottom player with named speaker lanes, the `V8 08` server-source
  speaker-track proof, and the `V8 10` compact filter/date popovers.
- Visual QA then found and fixed a remaining `V8 07` rough edge: generic
  `Спикер 1/2/3` labels and a wrapped lower speaker action. The review screen
  now uses `Анна`, `Михаил`, and `Клиент`, the compact player action is
  `Спикеры`, and the player rail/duration/action spacing has explicit gaps.
- Final targeted Figma API validation for this pass returned missing frames
  `0`, required gate text present in `V8 03`, `V8 07`, `V8 08`, and `V8 10`,
  key overlap areas `0`, `V8 07` `stillGeneric=[]`, `gapRailDuration=10`, and
  `gapDurationAction=30`.
- Stakeholder follow-up converted this from "Krisp-inspired" to
  "Krisp IA extracted": `V8 03` no longer exposes server copy, `V8 07` has a
  stable `140x40` speaker action with the label inside its bounds, `V8 08`
  hides the technical sync banner and obsolete lower panels while keeping
  named lanes plus unresolved lanes, and `V8 09` removes queue jargon from the
  settings summary. Focused Figma validation returned `badCopy=[]`,
  `genericSpeakers=[]`, `v07Action40px=true`, `v07LabelInsideAction=true`,
  and `v08NamedLanes=true`.
- The 2026-06-16 reference-use recheck accepts the stakeholder concern that
  the Krisp practices must be more explicit. V8 now treats the observed Krisp
  desktop and web IA as concrete product gates: meetings-first workspace,
  separated live-control rail, contextual search/filter, upload as row/sheet
  state, review as the main value surface, speaker correction in the review
  flow, list-detail settings, dense web cabinet list/detail, and
  browser-owned governance. Figma validation returned
  `missingSettingsConcepts=[]`, `technicalSettingsText=[]`,
  `krispIaCoverage` all `true`, and `invalidDestinations=[]`.
- The same pass fixed missing clickable-product affordances: `V8 03`
  `Начать запись`, `Загрузить медиа`, and `Открыть кабинет` now route to
  active recording, shared upload, and web cabinet respectively; `V8 09`
  `Проверить звук` routes back to the meeting workspace. This keeps the
  prototype aligned with Krisp's flow logic instead of behaving like a static
  visual board. The current reaction graph now has `98` valid `ON_CLICK`
  reactions across `98` nodes, with invalid destinations `0`, self-links `0`,
  and superseded-page destinations `0`.
- The next settings-focused polish pass corrected `V8 09` after visual review:
  the selected settings section is now `Основное`, top actions are equal
  `124x40`, right-rail actions are grouped at `138x40`, `Проверить звук` no
  longer floats at the bottom of an empty rail, `биллинг` was replaced with
  `оплата`, and the stale source layer name is `Chip / Система`. Focused
  Figma validation returned `technicalHits=[]`, `missingRequired=[]`,
  `badButtonSizes=[]`, `labelOverflowCount=0`, and `textOverlapCount=0`.
- Evidence and notes:
  `krisp-reference-pass/audit.md`;
  final reviewed PNG:
  `krisp-reference-pass/v8-07-transcript-player-speaker-names-fixed.png`;
  speaker-lane cleanup PNG:
  `krisp-reference-pass/v8-08-speaker-lanes-cleaned.png`.

## Clickable QA

V8 clickable prototype pass:

| Check | Result |
|---|---|
| `ON_CLICK` reactions | 98 |
| Nodes with reactions | 98 |
| Invalid destination count | 0 |
| Self-destination count | 0 |
| Superseded-page destination count | 0 |
| Required owner-value-loop coverage | PASS |

Covered transitions include first-run, permissions, desktop manual recording,
shared media upload sheet, upload-to-processing, transcript review, speaker
assignment, detected-meeting recording, Stop-to-processing, settings-to-web,
settings-to-light-theme, command search/filter overlay, filter apply/reset,
search result open-to-detail, web list-to-detail, web detail-to-speakers, web
detail-to-governance, and governance back-to-detail.

## Screenshot QA

Local screenshots reviewed during the V8 pass:

- `/tmp/2brain-figma-v8-qa/v8-01-signin-fixed.png`
- `/tmp/2brain-figma-v8-qa/v8-03-workspace-final.png`
- `/tmp/2brain-figma-v8-qa/v8-04-prompt-final.png`
- `/tmp/2brain-figma-v8-qa/v8-05-active-recording-final.png`
- `/tmp/2brain-figma-v8-qa/v8-06-upload-processing.png`
- `/tmp/2brain-figma-v8-qa/v8-07-transcript-fixed.png`
- `/tmp/2brain-figma-v8-qa/v8-08-speakers-fixed.png`
- `/tmp/2brain-figma-v8-qa/v8-09-settings-final-v3.png`
- `/tmp/2brain-figma-v8-qa/v8-10-web-list-final-2.png`
- `/tmp/2brain-figma-v8-qa/v8-11-web-detail.png`
- `/tmp/2brain-figma-v8-qa/v8-12-share-export-delete-v2.png`
- `/tmp/2brain-figma-v8-qa/v8-13-light-proof.png`
- `/tmp/2brain-figma-v8-qa/v8-14-rules.png`
- `/tmp/2brain-figma-v8-live-check/v8-05-live-fixed-2.png`
- `/tmp/2brain-figma-v8-post-computer-use/v8-09-settings-storage-fixed.png`
- `/tmp/2brain-figma-v8-post-computer-use/v8-06-upload-status-restored.png`
- `/tmp/2brain-v8-09-settings-current.png`
- `/tmp/2brain-v8-10-web-list-current.png`
- `/tmp/2brain-v8-13-light-current.png`
- `v8-09-settings-after-ia-rail-polish.png`
- `v8-15-upload-sheet-after-chip-fix.png`
- `v8-16-search-filter-overlay-after-krisp-ia-pass.png`

Screenshot review found and fixed:

- clipped `Назначить спикеров` and source chips in the transcript review;
- header/status chip clipping in speaker assignment;
- settings policy chips that looked visually cramped despite passing bounds;
- settings row text width overflows;
- sparse settings right rail with an isolated lower action and uneven top
  action widths;
- stale web/server wording in review and speaker status copy;
- placeholder web screens `10-14`;
- web list right-rail/action-column overlap;
- web detail bottom and action button crowding;
- share/export/delete warning overlap;
- QA board examples that contained the same implementation words they were
  meant to forbid;
- English visible frame titles on the primary `00-09` review frames.
- a post-handoff live check found visible `Stop`, `Локально`, and related
  technical wording in five V8 text nodes; all five were rewritten and the same
  Figma text sweep returned `hitCount=0`.
- a post-`computer-use` live-reference pass found stale top-level desktop
  sidebar `Загрузка` labels; top-level labels now use `Обзор`, while inline
  lifecycle chips still use `Загрузка` and settings uses `Хранилище`.

## Current Limits

V8 is a review candidate, not production UI. It still needs stakeholder visual
approval before implementation handoff is final. The current pass validates
layout, IA, screen coverage, Russian copy, dark/light proof, and clean-room
reference distance, but does not implement production app/web code.
