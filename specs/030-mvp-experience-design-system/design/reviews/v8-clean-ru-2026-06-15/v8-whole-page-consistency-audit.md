# V8 Whole-Page Consistency Audit

Date: 2026-06-15
Figma file: <https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr>
Page: `030 MVP Experience v8 - Clean RU`
Page id: `341:2`

## Scope

This audit covers all 17 visible V8 frames, `V8 00` through `V8 16`, after the
Krisp reference matrix pass, remaining value-surface pass, active handoff copy
cleanup, and the post-critique Krisp IA overlay follow-up.

The goal was not to copy Krisp visuals. The goal was to verify that V8 uses the
same category-level product practices:

- meetings are the default workspace;
- upload and processing are meeting/list states, not separate MVP destinations;
- search and filters are contextual command/list overlays, not standalone MVP
  destinations;
- recording trust and one-action stop stay native;
- variable review, status, speaker, settings, and governance surfaces are
  server-owned and can be embedded in desktop;
- speaker assignment is one lane per speaker;
- risky sharing/export/deletion actions stay browser-owned;
- Russian UI copy uses human next actions instead of implementation labels.

## Figma API Result

Whole-page Figma audit result:

| Check | Result |
|---|---|
| Target frames found | `17 / 17` |
| Missing frames | `0` |
| Forbidden visible-copy hits | `0` |
| Stale implementation layer-name hits | `0` for product-copy tokens; structural frame identifiers remain allowed |
| Bad control-height nodes | `0` |
| Text overflow hits | `0` |
| Text overlap hits | `0` |
| Reaction issues | `0` |
| Krisp-derived gate failures | `0` |

Reaction counts by frame:

| Frame | Reactions |
|---|---:|
| `V8 00` | 0 |
| `V8 01` | 5 |
| `V8 02` | 1 |
| `V8 03` | 8 |
| `V8 04` | 6 |
| `V8 05` | 7 |
| `V8 06` | 3 |
| `V8 07` | 7 |
| `V8 08` | 5 |
| `V8 09` | 5 |
| `V8 10` | 5 |
| `V8 11` | 6 |
| `V8 12` | 2 |
| `V8 13` | 7 |
| `V8 14` | 0 |
| `V8 15` | 4 |
| `V8 16` | 10 |

## Gate Coverage

| Frame | Gate result |
|---|---|
| `V8 01 - Вход и подключение сервера` | Provider-first sign-in; no local bypass. |
| `V8 02 - Первый запуск и разрешения macOS` | Russian macOS permission guidance and clear privacy framing. |
| `V8 03 - Рабочее пространство встреч` | Desktop opens on meetings with readiness, rows, statuses, and upload entry. |
| `V8 04 - Подсказка найденной встречи` | Detected meeting is an inline policy-backed choice. |
| `V8 05 - Активная запись в меню и окне` | Active recording remains native chrome with visible `Остановить`. |
| `V8 06 - Загрузка и обработка в списке` | Upload/processing are inline meeting states with `Подробнее`. |
| `V8 07 - Транскрипт и спикеры в приложении` | Transcript review includes playback, outcomes, and speaker entry. |
| `V8 08 - Дорожки назначения спикеров` | Speaker assignment uses separate lanes and server-owned save truth. |
| `V8 09 - Настройки записи и темы` | Settings use list-detail IA with recording, detection, theme, language, storage, privacy, and diagnostics. |
| `V8 10 - Веб-кабинет: встречи и фильтры` | Web meetings list keeps search, filters, upload, status, and row actions in one dense workspace. |
| `V8 11 - Веб-детали встречи и транскрипт` | Web meeting detail supports transcript, playback, outcomes, speaker correction, and governance entry. |
| `V8 12 - Поделиться, экспорт, удаление` | Share/export/delete are browser-owned and use bounded deletion truth. |
| `V8 13 - Светлая тема: проверка экрана` | Light theme preserves the same meeting-cockpit semantics. |
| `V8 14 - Правила интерфейса и QA` | Component rules include the Krisp matrix and no-technical-copy gates. |
| `V8 15 - Общая загрузка медиа` | Shared desktop/web upload sheet keeps upload contextual and routes into inline processing. |
| `V8 16 - Командный поиск и фильтры` | Command search/filter overlay keeps search, filters, recent results, quick upload, and result opening inside the meeting workspace IA. |

## Handoff Cleanup

After the whole-page audit, active implementation-facing docs were also cleaned
so development cannot drift back to the old UI:

- `design/system/components.md`: native capture buttons use `Начать запись` and
  `Остановить`; upload queue rows use human meeting titles and `Подробнее`.
- `design/system/localization-matrix.md`: Russian state labels use
  `Идёт запись`, `Идёт расшифровка`, and speaker terminology.
- `design/status-state-matrix.md`: row actions no longer use vague `Статус`;
  speaker statuses use `спикеры`.
- `design/screens/*`: tray, upload, processing, permission recovery, and web
  meeting-list actions are Russian-first and match V8.
- `design/mvp-experience-blueprint.md`: visible action labels and embedded/web
  copy were aligned with V8 and the server-owned cabinet split.

## Stricter Follow-Up Pass

The next pass rechecked V8 against the live Krisp desktop reference and Figma
metadata, not just visible text:

- `computer-use` read-only Krisp state confirmed the reference IA: desktop is a
  full meeting workspace with left navigation, meeting list, upcoming meetings,
  search/filter/action controls, and a separate audio-control rail. 2brain keeps
  the workspace density and meeting-list-first IA, but does not copy Krisp's
  audio/noise rail.
- `V8 09` settings was corrected from a vague `Доступ` category to
  `Конфиденциальность`, and the text node was resized to keep it one line.
- `V8 10` web upload action was corrected from `Загрузить файл` to
  `Загрузить медиа`, with the button widened to avoid clipping.
- Figma layer names and any exact visible leaks were cleaned for:
  `client-call.mp4`, `Транскрибация`, `Button / Статус`, and
  desktop/light `Загрузить файл` button names.
- The final strict audit checked both visible text and layer names before the
  overlay follow-up and returned: pre-overlay frame count `15`,
  `buttonLike=77`, `reactionNodes=67`,
  `badControlHeights=0`, `visibleStaleHits=0`,
  `textOverflow=0`, `textOverlaps=0`, and `gateFailures=0`.
- Visual screenshots were reviewed after the fixes:
  `/tmp/2brain-v8-09-settings-current.png`,
  `/tmp/2brain-v8-10-web-list-current.png`, and
  `/tmp/2brain-v8-13-light-current.png`.

## Krisp IA Follow-Up

The stakeholder correctly challenged that V8 still used too little of Krisp's
actual UX/IA depth. The follow-up added the two missing list-level practices
without copying Krisp visuals:

- `V8 15 - Общая загрузка медиа`: desktop `Добавить запись`, web
  `Загрузить медиа`, light-theme upload, and processing-frame upload entries now
  open one shared server-owned upload sheet with metadata and validation.
- `V8 16 - Командный поиск и фильтры`: the web meetings search field and
  search nav open a contextual command/filter overlay over `Встречи`; results
  open the meeting detail, filters apply/reset to the list, and quick upload
  opens `V8 15`.
- Upload start routes from `V8 15` to `V8 06`; cancel/close returns to `V8 10`.
- Final focused Figma API audit after the post-stakeholder Krisp IA polish
  returned `frameCount=17`, `expectedFrameCount=17`,
  `totalTextNodes=683`, `totalVisibleTextOutsideQA=647`,
  `totalButtonLike=240`, `totalReactionNodes=92`, `staleNames=[]`,
  `forbiddenVisibleText=[]`, `suspectButtons=[]`, and `gateFailures=0`.
- The same pass confirmed the key coordinates and sizes: V8 10 web shell at
  `x=140`, `y=96`; V8 05 popover stop button at `220x40`; V8 10 row chips at
  `28px` high; V8 14 example icon button at `40x40`; V8 15 validation text
  `Аудиофайл готов. После загрузки встреча появится в списке.`; and V8 16
  `Esc` is a `Key / Esc` token, not a clickable button.
- Reviewed screenshots:
  `v8-05-active-recording-after-krisp-ia-pass.png`,
  `v8-10-web-meetings-after-krisp-ia-pass.png`,
  `v8-14-qa-rules-after-krisp-ia-pass.png`,
  `v8-15-upload-sheet-after-chip-fix.png`, and
  `v8-16-search-filter-overlay-after-krisp-ia-pass.png`.

## Standards And Action-Row Follow-Up

The next diagnostic pass checked the V8 page for the exact defects that make an
otherwise correct IA feel rough: mixed same-row button sizes, small icon
targets, clipped playback controls, vague settings policies, and technical
handoff wording leaking into visible copy.

Corrections applied:

- `V8 07` and `V8 11` playback controls now meet the minimum `56x40` compact
  button contract.
- `V8 03`, `V8 04`, `V8 07`, `V8 11`, and `V8 13` icon/action rows use
  consistent `40px` same-row controls.
- `V8 10`, `V8 15`, and `V8 16` web header actions use at least `8px` spacing.
- `V8 09` recording behavior uses the launch labels `Спрашивать`,
  `Всегда писать`, and `Вручную`.
- `V8 14` checklist number markers are metadata-only `Step marker` nodes, not
  interactive chips.

Final same-parent Figma API audit result:
`frameCount=17`, `missingFrameNames=[]`, `controls=216`, `buttons=94`,
`chips=116`, `stepMarkers=5`, `reactionNodes=92`,
`targetSizeIssues=[]`, `buttonRowIssues=[]`, `technicalCopyHits=[]`,
`staleNames=[]`, `missingSettingsConcepts=[]`, `missingFlowWords=[]`, and
`gateFailures=0`.

2026-06-16 explicit Krisp reference-use recheck supersedes only the clickable
count, not the visual/layout findings above: after adding missing reactions for
the V8 03 live rail and V8 09 sound-check action, the active prototype graph is
`reactionNodes=98`, `totalReactions=98`, `invalidDestinationCount=0`,
`selfLinkCount=0`, and `supersededDestinationCount=0`.

Reviewed screenshots:
`v8-07-transcript-after-krisp-action-row-fix.png`,
`v8-09-settings-after-recording-policy-fix.png`,
`v8-11-web-detail-after-krisp-action-row-fix.png`, and
`v8-14-qa-rules-after-step-marker-fix.png`.

## Deep Current-State Pass

A follow-up current-state pass was saved at `deep-current-pass/audit.md`.
It specifically looked for issues that prior mechanical gates could miss:
near-token button heights, menu-bar copy inconsistencies, upload wording,
cloned-row stale labels, and sparse working areas.

Corrections applied:

- `V8 16` result and filter footer actions were normalized from `38px` to
  `40px`.
- `V8 05` menu-bar action changed from `Стоп` to `Остановить`.
- `V8 05` active menu-bar cluster was re-spaced to avoid overlap:
  `Запись 12:48` -> `8px` gap -> `Остановить` -> `16px` gap ->
  `Сохраняется`.
- `V8 06` upload action changed from `Выбрать файл` to `Выбрать медиа`.
- `V8 05` gained a third recent meeting row.
- `V8 06` gained a fourth lifecycle row, then the lifecycle card was resized
  to `480px` so the new row leaves `44px` bottom padding.

Final audit result after this pass:
`frameCount=17`, `missingFrames=[]`, `textNodes=691`, `controls=254`,
`buttons=96`, `chips=118`, `buttonHeightDistribution={36:1,40:95}`,
`chipHeightDistribution={28:118}`, `targetSizeIssueCount=0`,
`rowIssueCount=0`, `technicalCopyHitCount=0`, and
`requiredGateFailures=0`.

## Remaining Limit

This audit proves mechanical consistency and clean-room Krisp IA alignment for
the V8 candidate. It does not replace stakeholder visual approval. V8 remains
the active review candidate until visual approval is explicitly recorded.
