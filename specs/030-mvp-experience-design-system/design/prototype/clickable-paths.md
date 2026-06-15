# Clickable Prototype Paths

## V8 Figma Main Flow

The active visual prototype draft is
`030 MVP Experience v8 - Clean RU` (`341:2`) in
[https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr](https://www.figma.com/design/ylPz3AxOOfVoLJEG4dF9Yr).
The v8 draft page includes 17 visible top-level frames organized as workspaces
and states. The current correction audit found frame-bound overflow `0`, bad
button heights `0`, bad chip heights `0`, visible forbidden implementation
copy `0`, and placeholder artifact nodes `0`.

V8 is currently the visual and clickable handoff source. The V8 page now has
92 valid `ON_CLICK` reactions across 92 nodes, with `issueCount=0`: every
destination is a visible V8 frame, no reaction points to itself, and no
reaction points to a superseded page. Same-frame filters and current-section
sidebar items intentionally remain without fake navigation when the state is
already represented in the frame.

| Path | From | To | Trigger |
|---|---|---|---|
| First launch | `V8 01 - Вход и подключение сервера` | `V8 02 - Первый запуск и разрешения macOS` | Provider or email sign-in |
| Permissions ready | `V8 02 - Первый запуск и разрешения macOS` | `V8 03 - Рабочее пространство встреч` | `Проверить снова` |
| Detected meeting | `V8 03 - Рабочее пространство встреч` | `V8 04 - Подсказка найденной встречи` | detected supported meeting |
| Active recording | `V8 04 - Подсказка найденной встречи` | `V8 05 - Активная запись в меню и окне` | `Записать` |
| Shared upload sheet | `V8 03` / `V8 06` / `V8 10` / `V8 13` | `V8 15 - Общая загрузка медиа` | `Добавить запись` / `Загрузить медиа` |
| Upload and processing | `V8 15 - Общая загрузка медиа` | `V8 06 - Загрузка и обработка в списке` | `Начать загрузку` creates or updates a meeting row |
| Search and filters | `V8 10 - Веб-кабинет: встречи и фильтры` | `V8 16 - Командный поиск и фильтры` | search field or search navigation |
| Open transcript | `V8 06` / `V8 10` | `V8 07 - Транскрипт и спикеры в приложении` / `V8 11 - Веб-детали встречи и транскрипт` | ready row action |
| Speaker mode | `V8 07` / `V8 11` | `V8 08 - Дорожки назначения спикеров` | `Назначить спикеров` / `Уточнить спикеров` |
| Settings | `V8 03` / `V8 10` | `V8 09 - Настройки записи и темы` | `Настройки` |
| Governance actions | `V8 07` / `V8 11` | `V8 12 - Поделиться, экспорт, удаление` | `Поделиться` / `Экспорт` / delete path |
| Light proof | `V8 09` | `V8 13 - Светлая тема: проверка экрана` | theme switch preview |

V8 clickable coverage audit passed for first-run, permissions, desktop manual
recording, shared upload, upload-to-processing, transcript review, speaker mode,
detected-meeting recording, Stop-to-processing, processing-to-review,
review-to-governance, settings-to-web, settings-to-light-proof, web command
search, filter apply/reset, search-result open-to-detail, web list-to-detail,
web detail-to-speakers, web detail-to-governance, governance back-to-detail, and
light proof back into recording/upload.

## Superseded V7.4 Figma Main Flow

The superseded v7.4 page is `030 MVP Experience v7.4 - Superseded by v8`
(`210:2`). It remains clickable evidence only. It includes 16 visible top-level
frames, 13 valid cross-frame `ON_CLICK` reactions, 0 invalid prototype
destinations, `buttonIssueCount=0`, `wrappedButtonTextCount=0`,
`technicalHitCount=0`, `latinHitCount=0`, and `forbiddenNavCount=0`, but v8
supersedes it for final visual review.

## Superseded V7.2 Figma Main Flow

The superseded v7.2 page is `030 MVP Experience v7.2 - Pixel polish RU`
(`158:2`). It remains pixel-polish evidence only. It includes 16 visible
top-level frames, 34 valid cross-frame reactions, 0 invalid prototype
destinations, `buttonIssueCount=0`, `technicalCopyLeaks=0`,
`englishHitCount=0`, and `forbiddenTopLevelNav=0`, but v7.3/v7.4 superseded it
for deeper IA, settings, recording-shell, upload, and governance corrections.

## Superseded V7 Figma Main Flow

The superseded v7 page is `030 MVP Experience v7 - IA rebuilt RU` (`137:2`).
It remains IA coverage evidence only. It includes 19 top-level frames, 16 valid
`ON_CLICK` reactions, no invalid prototype destinations, `overflowCount=0`,
and no forbidden top-level search/upload/processing nav.

## Historical V6 Figma Main Flow

The superseded v6 page is `030 MVP Experience v6 - Krisp-grounded RU`
(`118:2`). It remains mechanical evidence only. It includes 29 top-level
frames, 183 valid `ON_CLICK` reactions, 0 invalid prototype destinations,
`buttonClusterIssues=0`, `technicalCopyHits=0`, and `overflowCount=0`, but it
was rejected for handoff by stakeholder review.

## Historical V5 Figma Main Flow

The superseded v5 page is `030 MVP Experience v5 - Full MVP Flow` (`17:2`).
It remains useful coverage evidence only. Its historical audit found 106 button
frames, 82 button `ON_CLICK` reactions, 130 sidebar/nav `ON_CLICK` reactions, 8
meeting-row/status-pill reactions, 220 total click reactions, and
`appOverflowCount=0`, but the 2026-06-13 re-audit rejected it for visual
handoff because of toolbar, duplicate-control, technical-copy, and
speaker-assignment emphasis blockers.

## Historical V2 Figma Sequential Flow

The historical v2 prototype has 14 `ON_CLICK` reactions: 13 forward transitions
plus one loopback from `V2 System - Components And States` to `V2 Cover -
Product Decision`.

| Step | From | To | Figma reaction |
|---|---|---|---|
| 1 | V2 Cover - Product Decision | V2 Desktop - Ready Cabinet | ON_CLICK navigate |
| 2 | V2 Desktop - Ready Cabinet | V2 Desktop - Active Recording | ON_CLICK navigate |
| 3 | V2 Desktop - Active Recording | V2 Desktop - Upload And Processing | ON_CLICK navigate |
| 4 | V2 Desktop - Upload And Processing | V2 Desktop - Permission Recovery | ON_CLICK navigate |
| 5 | V2 Desktop - Permission Recovery | V2 Tray - Mini Controller | ON_CLICK navigate |
| 6 | V2 Tray - Mini Controller | V2 Web - Meetings List | ON_CLICK navigate |
| 7 | V2 Web - Meetings List | V2 Web - Manual Upload | ON_CLICK navigate |
| 8 | V2 Web - Manual Upload | V2 Web - Processing Status | ON_CLICK navigate |
| 9 | V2 Web - Processing Status | V2 Web - Meeting Review Complete | ON_CLICK navigate |
| 10 | V2 Web - Meeting Review Complete | V2 Web - Degraded Deleted Access | ON_CLICK navigate |
| 11 | V2 Web - Degraded Deleted Access | V2 Settings - Account Workspace Policy | ON_CLICK navigate |
| 12 | V2 Settings - Account Workspace Policy | V2 Matrix - Native Web Route Boundary | ON_CLICK navigate |
| 13 | V2 Matrix - Native Web Route Boundary | V2 System - Components And States | ON_CLICK navigate |
| 14 | V2 System - Components And States | V2 Cover - Product Decision | ON_CLICK loopback |

## Required Path Coverage

1. First-run/sign-in or signed-out local policy state: `V7.4 01`.
2. Desktop idle/ready: `V7.4 03 - Desktop meeting workspace`.
3. Active recording and Stop: `V7.4 04`, `V7.4 10`, `V7.4 11`.
4. Local saved/queued: `V7.4 03`, `V7.4 05`.
5. Permission recovery: `V7.4 02`.
6. Tray/menu state: `V7.4 10 - Menu bar controller`.
7. Upload/current status in app and web: `V7.4 05`.
8. Embedded cabinet entry and browser handoff: `V7.4 03`, `V7.4 07`.
9. Manual upload: `V7.4 05 - Meeting cockpit with upload`.
10. Transcription in progress: `V7.4 05`.
11. Meeting review complete: `V7.4 06 - Review speaker assignment`.
12. Degraded/failure/access/deleted: `V7.4 05`, `V7.4 12`, `V7.4 13`.
13. Settings/account/policy boundary: `V7.4 07 - Settings console`.
14. Route/status/system evidence: `V7.4 00`, `V7.4 09`.
15. Embedded speaker assignment and native Stop proof: `V7.4 06`, `V7.4 11`.
