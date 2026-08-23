# UX Checklist: Windows desktop-приложение GRAF

**Purpose**: Проверить требования к parity с macOS, нативному indicator/Stop,
permissions, automatic recording, accessibility, localization и degraded copy.
**Created**: 2026-08-23
**Feature**: [spec.md](../spec.md), [windows-desktop-contract.md](../contracts/windows-desktop-contract.md)

## Product parity и ownership

- [ ] CHK001 Parity matrix перечисляет каждое macOS recording state/action, permission state, custody state и cabinet route, а для Windows указывает same meaning и допустимое native convention difference. [Completeness, Spec §FR-002, §SC-002]
- [ ] CHK002 Web cabinet reuse явно отделён от native-only capture controls, чтобы Windows не получил вторую meeting-list/detail/settings UI. [Consistency, Spec §FR-003]
- [ ] CHK003 Copy для shared-loopback scope прямо сообщает, что записывается общий микс выбранного render endpoint, а не только звук одного приложения. [Truthfulness, Spec §Context and goal]
- [ ] CHK004 Состояния idle/ready/checking/starting/recording/paused/degraded/stopping/finalizing/saved/queued/uploaded/blocked/failed имеют короткие русские названия и recovery action. [Clarity, Contract §Session transitions]

## Indicator и управление

- [ ] CHK005 При active capture persistent native strip содержит state, source scope и one-action Stop вне зависимости от WebView, focus, minimize или network. [Completeness, Spec §FR-015]
- [ ] CHK006 Tray/background surface сохраняет читаемый state и Stop, а repeated Stop не создаёт вторую finalizer или двусмысленное состояние. [Recovery, Contract §Indicator and accessibility]
- [ ] CHK007 Native indicator является источником capture truth и не может быть скрыт/удалён изменением DOM или сообщением WebView. [Ownership, Contract §Indicator and accessibility]
- [ ] CHK008 Pause/Resume copy объясняет privacy semantics, включая отсутствие raw microphone fallback и сохранение timeline/reference. [Clarity, Contract §Session transitions]
- [ ] CHK009 Permission denial, endpoint missing, clock failure, protected audio, disk full и WebView unavailable имеют разные понятные причины, а не общий «что-то пошло не так». [Coverage, Spec §Edge Cases]

## Automatic recording

- [ ] CHK010 Prompt содержит восьмисекундный countdown и однозначные действия «Записать сейчас», «Пропустить» и «Всегда писать это приложение». [Completeness, Spec §FR-016]
- [ ] CHK011 Settings показывают target identity evidence, scope, текущий opt-in и обратимый способ выключить правило. [Clarity, Spec §FR-016]
- [ ] CHK012 Unknown process name, ordinary media playback, missing permission, missing endpoint и timeout не дают silent automatic start. [Safety, Spec §FR-016, §SC-007]
- [ ] CHK013 Automatic start использует тот же indicator, Stop, readiness gate и degraded semantics, что и manual Record. [Consistency, Spec §FR-016]

## Accessibility, localization и layout

- [ ] CHK014 Keyboard-only flow имеет видимый focus для Record/Pause/Resume/Stop, permission recovery, tray action и prompt choices. [Accessibility, Spec §SC-009]
- [ ] CHK015 Screen reader получает accessible name/description и state announcement для indicator, Stop, degraded reason и upload/custody state. [Accessibility, Contract §Indicator and accessibility]
- [ ] CHK016 High Contrast, 200% DPI, narrow window, reduced motion и system theme сохраняют читаемость, target size, focus и отсутствие горизонтального overflow. [Coverage, Spec §SC-009]
- [ ] CHK017 Active/paused/degraded/failed различаются текстом, icon/shape или accessible state, а не только цветом. [Clarity, Spec §SC-009]
- [ ] CHK018 Русские тексты native shell согласованы с macOS/web copy, не раскрывают технические секреты и не обещают невозможную process isolation. [Localization, Spec §FR-002, §FR-021]
- [ ] CHK019 Offline, auth-expired, runtime-missing и upload-pending состояния не маскируются под нормальную встречу и предлагают действие в текущем контексте. [Truthfulness, Spec §US1–US3]
- [ ] CHK020 Brand-distance review охватывает native strip, tray, onboarding, permissions, settings, prompt, degraded/error states и визуальную границу с серверным кабинетом. [Design gate, Constitution §Clean-room UX]
- [ ] CHK021 Quit/close/relaunch during capture объясняет, что будет с локальным пакетом, и не оставляет пользователя без Stop или без custody status. [Recovery, Spec §Edge Cases]
- [ ] CHK022 UI не требует WebView route для критического Stop, permission recovery или локальной сохранности записи. [Ownership, Spec §FR-004, §FR-015]
