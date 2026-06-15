# V8 Krisp Reference Matrix

Date: 2026-06-15
Feature: `030-mvp-experience-design-system`
Reference sources:

- `design/evidence/krisp-full-navigation-audit.md`
- `design/evidence/krisp-v8-window-capture-audit.md`
- `design/evidence/krisp-v10-web-desktop-audit.md`
- `design/evidence/krisp-cleanroom-observation.md`

## Purpose

This matrix turns the Krisp clean-room observation into a screen-by-screen
design gate. It is not a visual copying brief. The goal is to preserve the
Krisp-level product logic and IA quality while keeping 2brain Rec visually,
linguistically, and technically original.

Allowed reference level:

- category patterns;
- information hierarchy;
- state placement;
- surface ownership;
- interaction intent;
- density and scanning behavior.

Forbidden reference level:

- Krisp screenshots, assets, icons, colors, copy, exact proportions, private
  meeting/account content, proprietary model behavior, or exact route naming.

## Reference Principles

| Krisp-observed practice | 2brain Rec design rule | V8 gate |
|---|---|---|
| Meeting list is the first useful workspace, not diagnostics. | Desktop and web open on `Встречи` with current statuses and recent value. | Default app/web frames must show meeting rows, dates, statuses, and next action in the first viewport. |
| Desktop combines embedded cabinet value with compact native/local controls. | Native shell owns capture trust; server/web owns variable meeting UI. | No broad product workflow should be native-only unless it needs OS APIs. |
| Search/filter/sort sit near the meeting list. | Search and filters are list-level controls. | No separate desktop/web filter destination for MVP. |
| Search opens as a contextual layer, not a new product home. | Command search and filters appear over the current meeting workspace and return to the same list. | Search results, filter apply/reset, and upload shortcuts must route back into meeting/detail states, not dead-end screens. |
| Meeting rows are dense and status-rich. | Rows show title, date/time, duration, source/provenance, status, and one next action. | Rows must not become large marketing cards or vague upload receipts. |
| Upload and processing become meeting/list states. | Upload creates/updates a row immediately and progresses through clear statuses. | Upload, validation, processing, and retry must not be top-level navigation. |
| Active recording is a shell/chrome state with one safe stop action. | Recording state appears in menu bar/header/capture strip, not as a standalone route. | Any active-recording frame must show Stop without making recording a separate product page. |
| Detected meeting behavior is a policy-backed prompt. | Ask/auto/manual behavior belongs in settings and is visible in the prompt. | Prompt wording must explain choice and current policy in user language. |
| Meeting detail is the main value surface after processing. | Review includes transcript, playback, notes/actions, provenance, speaker correction, and next actions. | A ready meeting cannot end at "transcript ready"; it must open a useful review workspace. |
| Speaker evidence uses separate speaker lanes. | Speaker assignment is a server-owned review panel with one lane per speaker. | Desktop embeds the same lane model; native code does not own diarization editing. |
| Settings are a list-detail console, not one mixed card. | Desktop settings show launch-critical local behavior; browser owns account/admin/risk. | Settings must be grouped by account/workspace, recording, detection, sources, theme/language, storage, notifications, privacy/deletion, diagnostics/handoff. |
| Risky governance lives in browser context. | Share/export/delete/access use browser-owned policy and confirmation. | Desktop may show entry points, not hide policy or overpromise deletion. |

## V8 Screen Fit Check

| V8 frame | Krisp-derived target | Current fit | Required action |
|---|---|---|---|
| `V8 01 - Вход и подключение сервера` | Compact provider-first entry with no local bypass. | Fits after correction. Provider set is present, `email` is removed from visible Russian copy, and the bottom trust note is start-policy focused. | Keep regression gate: no local bypass and no file-centric first-run promise. |
| `V8 02 - Первый запуск и разрешения macOS` | First-open guided access with visual OS path. | Fits after correction. The simulated macOS title is Russian and the subtitle explains access in plain user language. | Keep regression gate: permission copy must stay user-facing, not implementation-facing. |
| `V8 03 - Рабочее пространство встреч` | Meeting cockpit default with dense rows and inline actions. | Fits after correction. The cockpit now uses readiness language, processing rows use `Расшифровка`, row actions use `Подробнее`, and upload is `Добавить запись` instead of a queue destination. | Keep as baseline for other desktop states; do not reintroduce `Веб-разделы`, vague `Статус` row actions, or queue-first language. |
| `V8 04 - Подсказка найденной встречи` | Inline prompt tied to saved detection policy. | Fits after correction. Prompt remains inline and the policy row now reads as a saved preference preview with `Спрашивать`, `Всегда писать`, and `Вручную`. | Keep regression gate: detected meeting remains a choice/state inside the meeting workspace. |
| `V8 05 - Активная запись в меню и окне` | Recording is chrome/menu-bar/header state, not destination; one visible stop action. | Fits after correction. Recording details are short, the legacy `Видимый индикатор` chip is hidden, the popover button is compact, and the meeting appears in the list after stop. | Keep regression gate: active recording must stay chrome/popover-owned with one clear stop action. |
| `V8 06 - Загрузка и обработка в списке` | Upload/processing are concrete row states. | Fits after correction. Upload uses a meeting-style title, progress is secondary, processing says `Идёт расшифровка`, and action is `Подробнее`. | Keep regression gate: upload and processing remain list states, not separate product destinations. |
| `V8 07 - Транскрипт и спикеры в приложении` | Review is the value surface: transcript, playback, outcomes, speaker action, and visible speaker-lane evidence. | Fits after value-surface and concrete Krisp extraction passes. Transcript, playback, outcomes, speaker entry, named transcript labels, and named bottom player lanes coexist without clipped controls, generic `Спикер 1/2/3` labels, or wrapped speaker-action copy. | Keep regression gate: review cannot end at "transcript ready"; it must open a useful workspace with visible named speaker lanes. |
| `V8 08 - Дорожки назначения спикеров` | One lane per speaker with assignment/save truth. | Fits after value-surface pass and focused stakeholder follow-up. Separate speaker lanes, talk-time evidence, save truth, named speakers, and unresolved speaker lanes are visible; server ownership stays in specs/contracts, not in visible technical copy. | Keep hard gate: desktop hosts the panel but native code does not own diarization editing; user-facing copy says `кабинет`, not `web-кабинет`, `API`, or `с сервера`. |
| `V8 09 - Настройки записи и темы` | List-detail settings with recording/detection/theme/storage/notifications/privacy. | Fits after settings pass. Theme/language, storage, privacy, diagnostics, and browser-only rows are grouped by user intent. | Keep regression gate: settings stay list-detail and Russian-first. |
| `V8 10 - Веб-кабинет: встречи и фильтры` | Dense web meeting list with inline search/filter/sort/upload. | Fits after density/table pass. Date/source/status/action columns no longer collide, row status chips are vertically centered, and upload remains an entry inside the meeting workspace. | Keep regression gate: no separate web upload/status home for MVP. |
| `V8 11 - Веб-детали встречи и транскрипт` | Browser review owns full meeting detail and governance entry. | Fits after detail pass. Transcript, playback, outcomes, speaker correction, and governance entry remain in one review workspace. | Keep regression gate: browser detail remains more complete than embedded desktop. |
| `V8 12 - Поделиться, экспорт, удаление` | Browser-owned risky actions with truthful deletion boundaries. | Fits after governance pass. Export rows do not overlap and deletion truth names outside-control limits. | Keep browser-only. |
| `V8 13 - Светлая тема: проверка экрана` | Theme switch preserves the same meeting cockpit semantics. | Fits after density pass. Light theme keeps the same row/status/action semantics as dark mode. | Keep as regression proof. |
| `V8 14 - Правила интерфейса и QA` | Gates prevent drift back to technical/sparse UI. | Fits after QA-board pass. The Krisp matrix is now represented in the rules surface and row controls now use consistent 40 px/28 px sizing. | Keep Krisp-reference matrix as a handoff gate. |
| `V8 15 - Общая загрузка медиа` | Upload starts from the meeting workspace as a compact sheet, then becomes a row/status. | Added after stakeholder Krisp-IA critique. Desktop and web upload entries now open the same server-owned upload sheet with metadata, validation, and processing handoff; validation uses compact user-facing status copy. | Keep upload as a contextual meeting action; do not create native-only upload logic or a separate upload destination. |
| `V8 16 - Командный поиск и фильтры` | Search/filter is a contextual command layer over the current meeting list. | Added after stakeholder Krisp-IA critique. Search, recent results, filter chips, quick upload, apply/reset, and result open actions are now represented without leaving the list IA. | Keep search/filter overlay lightweight, dense, and returnable to `Встречи`; do not make search a top-level MVP route. |

## Immediate V8 Correction Queue

- [x] `V8 01`: replace `email` with `почта`; remove file-centric bottom copy.
- [x] `V8 02`: translate the simulated System Settings heading and rewrite the
  subtitle away from "мастер".
- [x] `V8 03`: replace vague cockpit and row language (`Веб-разделы`,
  row-action `Статус`, queue-first upload copy, and `Транскрибация`) with
  `Готовность к записи`, `Подробнее`, `Добавить запись`, and `Расшифровка`.
- [x] `V8 04`: clean the meeting-detection policy row so it reads like a saved
  preference preview, not loose settings fragments.
- [x] `V8 05`: remove `Видимый индикатор`, fix overlap, and make after-stop
  copy about the meeting appearing in the list.
- [x] `V8 06`: make upload rows look like meeting rows first, file/progress
  second; replace vague `Статус` action with `Подробнее`.
- [x] Add missing Krisp IA layers after stakeholder critique: shared media
  upload sheet and contextual command search/filter overlay.
- [x] Re-run Figma API checks for control sizes, clipping, overlap, forbidden
  technical copy, and V8 first-path copy gates.
- [x] Recheck action-row polish against the Krisp IA reference: same-level
  controls use consistent target sizes, compact icon buttons are `40x40`, web
  header actions have real spacing, playback controls are not undersized, and
  recording policy uses concise labels instead of long button copy.
- [x] Recheck concrete Krisp extraction against actual desktop/web reference
  states: add persistent desktop live-control rail, named transcript player
  lanes, server-owned speaker-track proof, compact web filter/date popovers,
  and final `V8 07` player spacing with `stillGeneric=[]`,
  `gapRailDuration=10`, and `gapDurationAction=30`.
- [x] Recheck the stakeholder concern that Krisp UX/IA was underused: remove
  remaining visible technical copy from `V8 03`/`V8 08`, keep server ownership
  as a handoff contract instead of UI text, normalize the `V8 07` speaker
  action at `140x40`, preserve named and unresolved speaker lanes, and remove
  settings queue jargon.

## Post-Correction Result

Targeted Figma API audit on `V8 01` through `V8 06` after the correction queue:

- missing target frames: `0`;
- forbidden Krisp-alignment text hits: `0`;
- bad control heights in the target frames: `0`;
- required first-path copy gates present:
  `Войти по почте`, `Конфиденциальность и безопасность`,
  `Готовность к записи`, `Добавить запись`, `Всегда писать`,
  `После остановки встреча появится в списке.`, `Звонок с клиентом`,
  `Подробнее`, and `Расшифровка`.

Post-Krisp IA follow-up added two frames to close the missing reference
patterns:

- `V8 15 - Общая загрузка медиа`: shared desktop/web upload modal with
  metadata, pre-upload validation, and `Начать загрузку` routing into inline
  processing.
- `V8 16 - Командный поиск и фильтры`: command search, recent/results,
  status/source/date filters, quick upload, apply/reset, and result open actions
  over the web meetings list.
- Initial Figma API audit after this follow-up returned `frameCount=17` and
  `reactionNodeCount=92`; the stricter post-stakeholder polish below supersedes
  that intermediate metric set.

Post-stakeholder Krisp IA review then tightened the same follow-up instead of
leaving it at the broad IA level:

- V8 frame layer names were renamed to Russian handoff terms so Figma metadata,
  visible frame titles, and implementation docs now agree.
- `V8 05` active-recording popover was corrected after a coordinate regression:
  the `Остановить` action is back inside the popover at `220x40`.
- `V8 10` browser cabinet shell was restored to `x=140`, `y=96`, and web-list
  status chips were centered at `28px` high.
- `V8 15` and `V8 16` no longer show explanatory implementation copy such as
  "filters work here"; they show real list counts and upload validation state.
- `V8 15` validation chip was shortened to `Готово` after visual QA caught a
  two-line wrap.
- Final focused Figma API audit returned `frameCount=17`,
  `expectedFrameCount=17`, `totalTextNodes=683`,
  `totalVisibleTextOutsideQA=647`, `totalButtonLike=240`,
  `totalReactionNodes=92`, `staleNames=[]`, `forbiddenVisibleText=[]`,
  `suspectButtons=[]`, and `gateFailures=0`.
- The final standards/action-row pass then checked the same V8 page with
  same-parent row grouping and returned `frameCount=17`,
  `missingFrameNames=[]`, `controls=216`, `buttons=94`, `chips=116`,
  `stepMarkers=5`, `reactionNodes=92`, `targetSizeIssues=[]`,
  `buttonRowIssues=[]`, `technicalCopyHits=[]`, `staleNames=[]`,
  `missingSettingsConcepts=[]`, `missingFlowWords=[]`, and `gateFailures=0`.
  It also fixed `V8 09` to the launch labels `Спрашивать`, `Всегда писать`,
  and `Вручную`.

Latest focused Krisp IA follow-up after the stakeholder challenged whether
enough actual Krisp UX/IA had been used:

- `V8 03` visible cabinet copy now avoids `с сервера`.
- `V8 07` lower speaker action is `140x40`, and the `Спикеры` label is inside
  the button bounds.
- `V8 08` hides the technical sync banner and obsolete lower panels, while
  preserving named speaker lanes plus `Не назначен 1` / `Не назначен 2`.
- `V8 09` settings summary no longer uses queue jargon.
- Focused Figma API validation returned `badCopy=[]`,
  `genericSpeakers=[]`, `v07Action40px=true`,
  `v07LabelInsideAction=true`, and `v08NamedLanes=true`.
- 2026-06-16 explicit reference-use recheck accepts the stakeholder concern
  that Krisp UX/IA must be represented as product gates, not broad
  inspiration. The recheck maps the desktop reference to meetings-first
  workspace, separated live controls, contextual search/filter, review value
  surface, speaker correction, and policy-grouped settings; it maps the web
  reference to dense list/detail, filters/date popovers, upload as meeting
  action, status continuity, full transcript review, and browser-owned
  governance. Figma validation returned `missingSettingsConcepts=[]`,
  `technicalSettingsText=[]`, all Krisp IA coverage booleans `true`,
  `invalidDestinations=[]`, and active clickable graph `98`.

## Completion Rule

A V8 screen can be marked `Krisp-aligned` only when both are true:

- it follows the allowed Krisp category pattern above; and
- it remains clean-room: no copied visual expression, copy, private content, or
  exact layout.

Mechanical Figma checks are necessary but not sufficient. A screen with correct
button heights can still fail this matrix if the product object, state
placement, or settings ownership feels unlike the Krisp IA lesson.
