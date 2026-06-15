# Krisp Reference Extraction Pass

Date: 2026-06-15
Feature: `030-mvp-experience-design-system`
Figma page: `030 MVP Experience v8 - Clean RU`

## Why This Pass Exists

The stakeholder challenged whether V8 used enough of the actual Krisp desktop
and web product practice. This pass is the explicit answer: it extracts
clean-room UX/IA patterns from the installed Krisp desktop app and the
`app.krisp.ai` meeting-notes web cabinet, then checks whether the V8 design
uses those patterns in concrete frames.

This is not a visual cloning brief. The allowed reference level is product
structure, information hierarchy, state placement, density, and interaction
intent. The forbidden level remains Krisp assets, exact colors, exact copy,
private account content, private meeting content, route names, or proprietary
visual expression.

## Captured Reference Evidence

Screenshots captured during the reference pass:

- `01-krisp-desktop-meetings-controls.png`: desktop meeting workspace with
  persistent navigation, meeting list, and separate live control rail.
- `02-krisp-detail-notes.png`: meeting detail with notes, action items, tabs,
  and speaker assignment entry.
- `03-krisp-recording-transcript-speaker-lanes.png`: recording/transcript view
  with bottom player and separate speaker lanes.
- `04-krisp-search-command-palette.png`: contextual search overlay with recent
  results and keyboard dismissal.
- `05-krisp-settings-account.png`: account/workspace settings grouping.
- `06-krisp-settings-ai-note-taker.png`: meeting assistant policy settings,
  including auto-start and template-like behavior.
- `07-krisp-settings-privacy-consent.png`: privacy/consent settings and
  meeting-notification controls.
- `08-krisp-action-items-locked.png`: action items as a value surface, with
  plan-gated state represented clearly.
- `09-krisp-web-meeting-notes-list.png`: dense web meeting-notes list.
- `10-krisp-web-filter-menu.png`: compact web filter popover.
- `11-krisp-web-date-filter-popover.png`: anchored date filter popover with
  presets.

## Extracted UX/IA Practices

| Krisp practice observed | 2brain Rec application |
|---|---|
| Desktop opens as a meeting workspace, not diagnostics. | `V8 03` is the default meeting cockpit with rows, readiness, upload, and current statuses. |
| Live controls are persistent but separate from the meeting list. | `V8 03` adds a right-side live recording rail; native shell owns start/stop and source readiness. |
| Meeting detail is the value surface after processing. | `V8 07` shows transcript, playback, summary, actions, and speaker entry in one review screen. |
| Transcript playback includes visible speaker lanes. | `V8 07` bottom player now shows separate named lanes for `Анна`, `Михаил`, and `Клиент`; `V8 08` remains the full assignment workspace. |
| Speaker assignment belongs in the review flow, not only settings. | `V8 07` and `V8 08` both expose speaker correction; the panel is server-owned and embedded in desktop. |
| Search/filter are contextual layers near the list. | `V8 10` uses web list filters and popovers; `V8 16` is the command search/filter overlay. |
| Upload becomes a meeting/status row. | `V8 06` and `V8 15` treat upload as contextual sheet plus lifecycle row, not a top-level product route. |
| Settings are grouped by user policy and ownership. | `V8 09` separates recording policy, detection, sources, theme/language, storage, privacy, diagnostics, and browser-owned settings. |
| Privacy/consent is a policy surface. | Browser-owned cabinet settings remain the source for consent, notification, sharing, and deletion boundaries. |
| Web cabinet is denser and more complete than embedded desktop. | `V8 10`, `V8 11`, and `V8 12` own full meeting list/detail/governance actions; desktop hosts launch-critical slices only. |

## Figma Corrections From This Pass

- `V8 03 - Рабочее пространство встреч`: added a persistent right-side live
  control rail with `Запись сейчас`, readiness, recording policy, source pills,
  and web-cabinet entry. Existing list/readiness/upload blocks were narrowed so
  the rail is a real column, not an overlay.
- `V8 07 - Транскрипт и спикеры в приложении`: added the bottom player with
  separate speaker lanes. Follow-up polish renamed generic speaker labels to
  `Анна`, `Михаил`, and `Клиент`, removed remaining generic `Спикер 1/2/3`
  labels from the visible review screen, shortened the lower speaker action to
  `Спикеры`, and re-spaced rail/duration/action geometry.
- `V8 08 - Дорожки назначения спикеров`: added a multi-lane speaker-track
  proof where each speaker has a separate horizontal track with talk-time
  evidence. The implementation contract remains server-owned, but visible copy
  avoids technical wording such as `web-кабинет` or `с сервера`.
- `V8 10 - Веб-кабинет: встречи и фильтры`: added compact filter and date
  popovers with visible active filter chip.

## Programmatic Validation

Targeted Figma API recheck after corrections:

- missing target frames: `0`;
- `V8 03` required gates present: `Готовность к записи`, `Начать запись`,
  `Добавить запись`, `Открыть кабинет`, `Спрашивать перед встречей`;
- `V8 07` required gates present: `Плеер и дорожки спикеров`,
  `Назначить спикеров`, `Анна`, `Михаил`, `Клиент`;
- `V8 08` required gates present: `Каждый спикер — отдельная дорожка`,
  named lanes for `Анна`, `Михаил`, `Клиент`, plus unresolved lanes
  `Не назначен 1` and `Не назначен 2`;
- `V8 10` required gates present: `Избранные`, `Дата`, `Содержит`,
  `Компания`, `Теги`, `Сегодня`, `Свой период`, `Содержит: демо`;
- key overlap checks returned `area=0` for live rail vs readiness/upload,
  transcript player vs transcript heading, contains chip vs search, and filter
  menu vs date popover;
- final `V8 07` speaker-player polish returned `stillGeneric=[]`,
  `gapRailDuration=10`, and `gapDurationAction=30`.

Focused stakeholder follow-up after the question "is enough Krisp UX/IA
actually used?" tightened the extraction from broad inspiration into explicit
product rules:

- `V8 03` no longer exposes technical server copy; the meeting workspace says
  the cabinet updates statuses, speakers, and access in user language.
- `V8 07` lower player action is a stable `140x40` control labeled `Спикеры`;
  the label is inside the button bounds.
- `V8 08` removed the visible technical sync banner, hides obsolete lower
  panels, and keeps separate named speaker lanes plus two unresolved lanes.
- `V8 09` removes queue jargon from the settings summary and keeps policy,
  theme, language, and pending-recording state in product language.
- Focused Figma API validation returned `badCopy=[]`,
  `genericSpeakers=[]`, `v07Action={w:140,h:40}`,
  `v07LabelInsideAction=true`, and `v08NamedLanes=true`.

2026-06-16 stakeholder concern recheck:

- The current critique is accepted: Krisp must be used as an explicit UX/IA
  reference system, not as vague inspiration. V8 is therefore judged by the
  product practices above before visual polish metrics are considered.
- The desktop application reference contributes these concrete gates:
  meeting workspace first, persistent but separated live recording controls,
  contextual search/filter, meeting detail as value surface, speaker correction
  inside the review flow, and settings grouped by user policy.
- The web cabinet reference contributes these concrete gates: dense meeting
  list/table, inline filters and date popovers, upload as a meeting action,
  status visibility across list/detail, full transcript review, browser-owned
  share/export/delete, and account/privacy settings outside the native shell.
- Rechecked V8 against those gates by Figma API. The settings IA has
  `missingSettingsConcepts=[]` and `technicalSettingsText=[]`; web/list/detail
  coverage gates for product center, quick filters, upload path, status
  continuity, and speaker assignment returned `true`.
- Fixed a prototype gap that made the design feel less like a real product:
  the `V8 03` live rail actions now route to active recording, shared media
  upload, and web cabinet; `V8 09` `Проверить звук` routes back to the
  meeting workspace. Validation returned valid reactions for all four actions
  and `invalidDestinations=[]`. The active clickable graph now has `98`
  valid `ON_CLICK` reactions across `98` nodes, with `selfLinkCount=0` and
  `supersededDestinationCount=0`.
- Settings follow-up: `V8 09` is now the implementation baseline for settings,
  not just a proof that settings exist. The selected section is `Основное`, the
  right rail groups cabinet and sound-check actions near the relevant copy,
  save/cancel use equal `124x40` actions, cabinet/sound-check use equal
  `138x40` actions, and `биллинг` was replaced with the user-facing word
  `оплата`. Focused validation returned no technical hits, no missing settings
  requirements, no bad button sizes, no label overflow, and no text overlap.

Final reviewed 2brain screenshot from this pass:

- `v8-07-transcript-player-speaker-names-fixed.png`.

## Handoff Rule

Future implementation and design edits must not reduce this to a visual theme
reference. The mandatory Krisp-derived product rules are:

- desktop and web start from meeting value, not diagnostics;
- upload/search/processing stay contextual to the meeting workspace;
- native shell owns capture trust, visible recording state, and one-action stop;
- variable meeting UI, speaker assignment, policies, and governance come from
  the server/web cabinet;
- each speaker lane is a separate horizontal track with a visible label and
  talk-time evidence;
- implementation ownership must stay in specs and contracts; visible UI must
  use user language such as `кабинет`, not `backend`, `API`, `web-кабинет`, or
  `с сервера`;
- mechanical button-size QA is not sufficient unless these IA gates still pass.
