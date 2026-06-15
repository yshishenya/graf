# Screen Inventory

## Current V8 Screen Families

Current active Figma page: `030 MVP Experience v8 - Clean RU`, page id `341:2`.
V8 is the active review candidate after the v7.4 correction pass and the
follow-up stakeholder critique found remaining visual density, settings,
button consistency, web-cabinet, light-theme, and technical-copy issues. It is
not final implementation handoff until stakeholder visual acceptance is
recorded.

| Family / frame | Surface | Launch role |
|---|---|---|
| V8 00 - Карта MVP-потока и границы | prototype overview | required |
| V8 01 - Вход и подключение сервера | native_desktop + web | required |
| V8 02 - Первый запуск и разрешения macOS | native_desktop | required |
| V8 03 - Рабочее пространство встреч | native_desktop + embedded | required |
| V8 04 - Подсказка найденной встречи | native_desktop + embedded | required |
| V8 05 - Активная запись в меню и окне | native_desktop | required |
| V8 06 - Загрузка и обработка в списке | native_desktop + embedded | required |
| V8 07 - Транскрипт и спикеры в приложении | embedded_cabinet | required |
| V8 08 - Дорожки назначения спикеров | embedded_cabinet | required |
| V8 09 - Настройки записи и темы | native_desktop + embedded + browser handoff | required |
| V8 10 - Веб-кабинет: встречи и фильтры | browser_cabinet | required |
| V8 11 - Веб-детали встречи и транскрипт | browser_cabinet | required |
| V8 12 - Поделиться, экспорт, удаление | browser_cabinet | required browser-owned handoff |
| V8 13 - Светлая тема: проверка экрана | system/product proof | required |
| V8 14 - Правила интерфейса и QA | system | required |
| V8 15 - Общая загрузка медиа | browser_cabinet + embedded_cabinet | required contextual layer |
| V8 16 - Командный поиск и фильтры | browser_cabinet + embedded_cabinet | required contextual layer |

V8 consolidates the launch MVP into one owner value loop: record in the app or
upload a user-owned media file, see the same current status in app and web,
open the completed transcript, correct speakers by lane, read outcomes, and
share/export/delete from the browser-owned cabinet. Search, filters, upload,
and processing stay on the meeting list. The shared upload sheet and
search/filter overlay are contextual layers over `Встречи`, not top-level
destinations. Active recording stays in the menu-bar/header trust shell rather
than becoming a standalone destination.
Settings cover recording policy, supported meeting detection apps, audio
sources, theme/language, upload, access, notifications, diagnostics, and
browser handoff.

Implementation-facing screen specs for the active V8 families:

- `design/screens/desktop-home-ready.md`
- `design/screens/web-meetings-list.md`
- `design/screens/settings-recording-theme.md`
- `design/screens/web-meeting-review-complete.md`
- `design/screens/web-meeting-review-exceptions.md`
- `design/screens/web-manual-upload.md`
- `design/screens/web-processing-status.md`
- `design/screens/desktop-active-recording.md`
- `design/screens/desktop-tray-status.md`
- `design/screens/desktop-permission-recovery.md`
- `design/screens/desktop-account-status.md`

## Superseded V7.4 Screen Families

Figma page: `030 MVP Experience v7.4 - Superseded by v8`, original page id
`210:2`. V7.4 corrected the v7.3 IA direction but is now superseded by v8
because the web list/detail/governance, settings, light proof, and final
component QA rules needed a cleaner Russian handoff pass.

| Family / frame | Surface | Launch role |
|---|---|---|
| V7.4 00 - IA and value loop | prototype overview | required |
| V7.4 01 - First launch auth | native_desktop + web | required |
| V7.4 02 - Guided permissions | native_desktop | required |
| V7.4 03 - Desktop meeting workspace | native_desktop + embedded | required |
| V7.4 04 - Detected meeting prompt state | native_desktop + embedded | required |
| V7.4 05 - Meeting cockpit with upload | browser_cabinet + embedded | required |
| V7.4 06 - Review speaker assignment | browser_cabinet + embedded | required |
| V7.4 07 - Settings console | browser_cabinet + desktop account | required |
| V7.4 08A - Light meeting cockpit | system/product proof | required |
| V7.4 08B - Light review speakers | system/product proof | required |
| V7.4 08C - Light settings console | system/product proof | required |
| V7.4 09 - QA gates | system | required |
| V7.4 10 - Menu bar controller | native_desktop | required |
| V7.4 11 - Active recording over cabinet | native_desktop + embedded | required |
| V7.4 12 - Share export delete | browser_cabinet | required browser-owned handoff |
| V7.4 13 - Light critical states | system/product proof | required |

V7.4 keeps the model from equal screens to product workspaces plus states.
Search, filters, upload, and processing are integrated into the meeting
workspace rather than primary navigation destinations. Active recording is a
native header/menu-bar state rather than a full destination. Speaker assignment
is available inside the desktop app as an embedded server-owned review route,
with one separate lane per speaker.

## Superseded V7.3 Screen Set

Figma page: `030 MVP Experience v7.3 - Screen-by-screen polish RU`, page id
`177:2`. V7.3 preserved many v7.2 improvements but failed the deeper
screen-by-screen critique because active recording, queue/upload, settings,
speaker assignment, and governance still read as separate or under-designed
surfaces rather than a cohesive meeting cockpit.

## Superseded V7.2 Screen Set

Figma page: `030 MVP Experience v7.2 - Pixel polish RU`, page id `158:2`.
V7.2 remains useful evidence for the pixel-polish step, but it is superseded by
v7.4 for implementation-facing review.

## Superseded V7 Screen Set

Figma page: `030 MVP Experience v7 - IA rebuilt RU`, page id `137:2`. V7
introduced the correct IA direction but was superseded by v7.1 because
first-run composition, light proof, menu-bar invariants, active embedded review,
and governance actions needed another critic fix-pass. V7.1 was then
superseded by v7.2 for pixel polish and prototype-link repair.

| Family / frame | Surface | Historical role |
|---|---|---|
| V7 00-V7 04 | overview + entry/onboarding | coverage evidence |
| V7 05-V7 08 | desktop workspace and recording shell | coverage evidence |
| V7 09-V7 11 | web cockpit, upload, lifecycle rows | coverage evidence |
| V7 12-V7 14 | review, speaker assignment, governance | coverage evidence |
| V7 15-V7 18 | settings, detection policy, theme, QA | coverage evidence |

## Superseded V6 Screen Set

Figma page: `030 MVP Experience v6 - Krisp-grounded RU`, page id `118:2`.
V6 is mechanically cleaner than v5, but it was rejected by stakeholder
product/design review and remains coverage evidence only. The v6 page has 183
valid `ON_CLICK` reactions and no invalid prototype destinations.

| Screen | Surface | Launch role |
|---|---|---|
| V6 00 Acceptance map and blockers | prototype overview | required |
| V6 01 Auth sign-in and local policy | native_desktop + web | required |
| V6 02 Account session expired | native_desktop + web | required |
| V6 03 Desktop ready with embedded meetings | native_desktop + embedded | required |
| V6 04 Desktop active recording | native_desktop + embedded | required |
| V6 05 Desktop saved and uploading | native_desktop | required |
| V6 06 Desktop upload retry | native_desktop | required |
| V6 07 macOS permission recovery | native_desktop | required |
| V6 08 Menu bar ready | native_desktop | required |
| V6 09 Menu bar recording | native_desktop | required |
| V6 10 Web meetings list | browser_cabinet | required |
| V6 11 Search and filters | browser_cabinet | required |
| V6 12 Manual media upload | browser_cabinet + embedded | required |
| V6 13 Upload validation errors | browser_cabinet + embedded | required |
| V6 14 Processing status | browser_cabinet + embedded | required |
| V6 15 Degraded processing | browser_cabinet + embedded | required |
| V6 16 Review transcript and playback | browser_cabinet + embedded | required |
| V6 17 Notes decisions and actions | browser_cabinet | required |
| V6 18 Speaker assignment lanes | browser_cabinet + embedded | required |
| V6 19 Speaker conflict and save failure | browser_cabinet + embedded | required |
| V6 20 Meeting scoped AI drawer | browser_cabinet | conditional/deferred by backend scope |
| V6 21 Share access browser modal | browser_cabinet | required browser-owned handoff |
| V6 22 Export and download menu | browser_cabinet | required browser-owned handoff |
| V6 23 Delete and retention truth | browser_cabinet | required |
| V6 24 Account and settings | browser_cabinet + desktop account | required |
| V6 25 Browser only handoff | native_desktop + browser | required |
| V6 26 Empty offline signed out states | desktop + browser | required |
| V6 27 Tokens and components | system | required |
| V6 28 Native web route matrix | contract board | required |

## Historical V5 Screen Set

| Screen | Surface | Repo spec | Figma frame | Launch role |
|---|---|---|---|---|
| V5 00 cover | prototype overview | `design/mvp-experience-blueprint.md` | `V5 00 - Full flow cover and acceptance map` | required |
| Auth and workspace connection | native_desktop + web | `design/screens/desktop-account-status.md` | `V5 01`, `V5 02` | required |
| Desktop permissions | native_desktop | `design/screens/desktop-permission-recovery.md` | `V5 03 - macOS permissions onboarding` | required |
| Desktop home ready | native_desktop + embedded | `design/screens/desktop-home-ready.md` | `V5 04 - Desktop ready cabinet` | required |
| Desktop active recording | native_desktop | `design/screens/desktop-active-recording.md` | `V5 05 - Desktop active recording` | required |
| Desktop tray status | native_desktop | `design/screens/desktop-tray-status.md` | `V5 06 - Menu bar controller` | required |
| Desktop upload queue and embedded upload | native_desktop + embedded | `design/screens/desktop-upload-queue.md`, `design/screens/desktop-embedded-cabinet-entry.md` | `V5 07`, `V5 08` | required |
| Web cabinet IA and meetings | browser_cabinet | `design/screens/web-cabinet-ia.md`, `design/screens/web-meetings-list.md` | `V5 09`, `V5 10` | required |
| Web manual upload | browser_cabinet | `design/screens/web-manual-upload.md` | `V5 11`, `V5 12` | required |
| Web processing status | browser_cabinet | `design/screens/web-processing-status.md` | `V5 13`, `V5 14` | required |
| Web review complete | browser_cabinet + embedded_desktop | `design/screens/web-meeting-review-complete.md` | `V5 15`, `V5 16`, `V5 17`, `V5 18`, `V5 19`, `V5 34` | required |
| Share/export/delete lifecycle | browser_cabinet | `design/screens/web-meeting-review-complete.md`, `design/screens/web-meeting-review-exceptions.md` | `V5 20`, `V5 21`, `V5 22` | required |
| Account settings and browser-only handoff | native_desktop + browser | `design/screens/desktop-account-status.md`, `design/route-visibility-matrix.md` | `V5 23`, `V5 24` | required |
| Empty states and light-theme proof | browser_cabinet + desktop | `design/status-state-matrix.md`, `design/system/tokens.md` | `V5 25`, `V5 26`, `V5 27`, `V5 28`, `V5 29` | required |
| System/components/status | contract board | `design/system/`, `design/status-state-matrix.md`, `design/route-visibility-matrix.md` | `V5 30`, `V5 31`, `V5 32`, `V5 33` | required |

## Historical V3 Supporting State/Detail Boards

These boards were created in the superseded v3 file and remain useful as
requirement coverage notes. They are not the accepted visual direction.
Production implementation review should use the active V8 clean Russian screen
families plus the repo screen specs as source of truth for detailed states
after stakeholder visual approval is recorded.

| Board | Surface | Source artifacts | Launch role |
|---|---|---|---|
| `RU Dark Detail 14 — Состояния доступа в приложении` | native_desktop | desktop account/status specs, status matrix | required |
| `RU Dark Detail 15 — Обзор встречи внутри приложения` | embedded_cabinet | embedded cabinet spec, review specs | required |
| `RU Dark Detail 16 — Ошибка загрузки в приложении` | native_desktop | upload queue spec, status matrix | required |
| `RU Dark Detail 17 — Поиск по встречам и транскриптам` | browser_cabinet | web IA, Krisp audit lessons, component inventory | required |
| `RU Dark Detail 18 — Фильтры и сортировка кабинета` | browser_cabinet | web meetings list spec, route matrix | required |
| `RU Dark Detail 19 — Варианты строки встречи` | browser_cabinet | web meetings list spec, status matrix, provenance | required |
| `RU Dark Detail 20 — Доступ к встрече` | browser_cabinet | route matrix, meeting review spec | required as browser-only marker |
| `RU Dark Detail 21 — Экспорт и скачивание` | browser_cabinet | route matrix, meeting review spec | required as browser-only marker |
| `RU Dark Detail 22 — Удаление и восстановление правды` | browser_cabinet | deletion/access requirements, lifecycle truth | required |
| `RU Dark Detail 23 — Панель ИИ по встрече` | browser_cabinet | meeting review spec, route matrix | required |
| `RU Dark Detail 24 — Теги, активность и задачи` | browser_cabinet | web IA, action items scope, route matrix | required |
| `RU Dark Detail 25 — Пустые состояния кабинета` | browser_cabinet | web meetings/upload/review specs | required |
| `RU Dark Detail 26 — Только браузер` | native_desktop + browser | route visibility matrix | required |
| `RU Dark Detail 27 — Сессии и безопасность аккаунта` | browser_cabinet | auth/account status specs | required |
| `RU Dark Detail 28 — Ошибки загрузки медиафайла` | web + embedded | manual upload spec, status matrix | required |
| `RU Dark Detail 29 — Сбой обработки на сервере` | browser_cabinet | processing status spec, 015 dependency | required |
| `RU Dark Detail 30 — Словарь русского интерфейса` | system | localization matrix, terminology | required |
| `RU Dark Detail 31 — Доступность и фокус` | system | accessibility requirements, components | required |
