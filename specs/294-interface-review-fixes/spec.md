# Feature Specification: Исправления после ревью интерфейса

**Feature Branch**: `294-interface-review-fixes`

**Created**: 2026-11-12

**Status**: Draft

**Input**: Повторное ревью F293 выявило мёртвый код, два высоких дефекта и несколько средних проблем. Нужно аккуратно упростить код, исправить подтверждённые дефекты, протестировать и выпустить новый релиз с выкладкой в production.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Управлять записью предсказуемо (Priority: P1)

Пользователь видит согласованные действия Stop/Pause во всех поверхностях, не теряет запись при отключении микрофона и может восстановить сохранённый выбор микрофона.

**Why this priority**: Ошибки управления записью и микрофоном напрямую влияют на сохранность встречи.

**Independent Test**: Проверить меню, панель, titlebar и меню-бар для состояний active/paused/stopping/degraded; отключить выбранный и системный микрофон; перезапустить приложение с отсутствующим сохранённым устройством.

**Acceptance Scenarios**:

1. **Given** запись активна, **When** пользователь открывает любую поверхность, **Then** доступные действия Stop/Pause одинаковы, а `⌘0` не запускает «Домой».
2. **Given** запись завершается, **When** пользователь смотрит на панель, меню и VoiceOver, **Then** повторная остановка не предлагается как доступная.
3. **Given** сохранённый микрофон отключён, **When** приложение запускается, **Then** выбор сбрасывается на системный микрофон с понятным объяснением.
4. **Given** запись идёт с системным микрофоном, **When** устройство отключается, **Then** сессия переходит в `degraded`, системный звук продолжается и Stop остаётся доступен.

### User Story 2 - Не показывать старые данные (Priority: P1)

Смена аккаунта не оставляет старый `localStorage`, строки записей обновляются при смене часового пояса, а меню-бар не выдаёт ограниченную запись за полноценную.

**Why this priority**: Это приватность и доверие к статусу.

**Independent Test**: Сменить аккаунт с открытым кабинетом и проверить storage; изменить часовой пояс; перевести запись в degraded/failed и проверить меню-бар.

**Acceptance Scenarios**:

1. **Given** старый аккаунт имел `localStorage`, **When** аккаунт меняется, **Then** новая страница загружается только после завершения очистки.
2. **Given** пользователь меняет часовой пояс, **When** список локальных записей уже открыт, **Then** названия и время пересчитываются.
3. **Given** запись ограничена или завершилась ошибкой, **When** пользователь открывает меню-бар, **Then** статус совпадает с панелью.

### User Story 3 - Поддерживать простой код (Priority: P2)

Команда может менять интерфейс без мёртвых моделей, дублирующихся строк и хрупких проверок исходного текста.

**Why this priority**: F293 добавил полезные типы, но часть из них не используется и создаёт второй источник правды.

**Independent Test**: Собрать проект, прогнать тесты; убедиться, что удалённые типы/поля нигде не используются, а поведение не изменилось.

**Acceptance Scenarios**:

1. **Given** presentation-модель содержит состояние, **When** команда ищет его использование, **Then** оно либо используется в production, либо удалено.
2. **Given** два места описывают один пользовательский статус, **When** команда меняет текст, **Then** существует один источник.
3. **Given** изменение затрагивает поведение, **When** запускаются тесты, **Then** есть поведенческая проверка, а не только `source.contains`.

### User Story 4 - Выпустить проверенный релиз (Priority: P1)

Release operator получает новый CalVer-выпуск, нотаризованное приложение, обновление Sparkle и успешную production-выкладку.

**Why this priority**: Исправления должны дойти до пользователя.

**Independent Test**: Пройти PR checks, release-full, нотаризацию, Gatekeeper, Sparkle, deploy и public health.

**Acceptance Scenarios**:

1. **Given** изменения влиты, **When** запускается release-full, **Then** все обязательные проверки проходят на точном SHA.
2. **Given** релиз опубликован, **When** пользователь проверяет обновление, **Then** версия и подпись Sparkle корректны.
3. **Given** production deploy завершён, **When** проверяется public health, **Then** сервис отвечает, а runtime SHA совпадает с релизом.

### Edge Cases

- Микрофон отключён во время записи, затем снова подключён.
- Сохранённый микрофон отсутствует, системный микрофон тоже недоступен.
- Смена аккаунта происходит во время загрузки кабинета.
- Часовой пояс меняется во время активной записи.
- Запись в состоянии stopping, degraded или failed.
- Окно сохранено на отключённом мониторе или с размером меньше минимума.
- Release-full падает после публикации тега; тег и релиз не должны остаться частично опубликованными.


## Canonical capture state matrix

| State | Panel | Titlebar / menu bar | Application menu Stop | VoiceOver |
|---|---|---|---|---|
| idle/detecting | Start enabled if permissions allow | «Готово к записи» | disabled | «Активной записи нет» |
| starting | Start blocked, Stop available | «Начинаем запись…» | enabled | Stop available |
| active | Stop and Pause mic available | «Идет запись» | enabled | Stop and Pause available |
| paused | Stop and Resume mic available | «Идет запись · микрофон выключен» | enabled | Stop and Resume available |
| degraded | Stop available; recovery guidance | «Запись с ограничением» | enabled | Stop available; limitation announced |
| stopping | Stop hidden/disabled; no repeat action | «Сохраняем запись…» | disabled | «Запись завершается», repeat Stop unavailable |
| stopped/finalized | No Stop/Pause; local custody shown | «Запись остановлена» | disabled | «Активной записи нет» |
| failed | No Stop/Pause; recovery guidance | «Нужна помощь» | disabled | failure announced; no Stop announced |

`.failed` never renders as success or “Готово к записи”. `.degraded` never renders as full success.

## Settings sections and terminology

The five sections are exactly: «Аккаунт», «Запись», «Уведомления», «Календарь», «Биллинг». «Запись» and «Уведомления» are local; the other three require the cabinet. The fallback sidebar lists all five. «Все настройки GRAF» opens the account/general cabinet settings route, not the currently selected local section.

## Local custody text source

The single source covers exactly the reachable local-custody states `active`, `saved`, `degraded`, `blocked`, `failed`. Queue-only states such as uploading, expired, deleting, corrupted or terminal are not claimed by this source and are not added without a production consumer.

## Microphone lifecycle terminology

- **Saved microphone**: the device ID persisted in `InterfacePreferences`.
- **System default**: the current macOS default input device when no saved device is available.
- **Temporary disconnect**: the device disappears while recording; the session becomes `degraded`, the saved preference is kept, system audio continues.
- **Permanent absence at launch**: the saved device is not available when the app starts; the preference is cleared and the system default is used.
- On reconnect, the saved preference is restored only if the user has not chosen another microphone in the meantime.
- A saved preference is cleared only for a confirmed unavailable device, not for a transient read failure.

## Requirements *(mandatory)*

- **FR-001**: `⌘0` ДОЛЖЕН однозначно сбрасывать масштаб кабинета; «Домой» ДОЛЖЕН иметь другой shortcut или не иметь его.
- **FR-002**: Доступность Stop/Pause ДОЛЖНА определяться одним предикатом для панели, titlebar, меню и accessibility.
- **FR-003**: При `.stopping` повторный Stop НЕ ДОЛЖЕН предлагаться как доступное действие; при `.failed` Stop/Pause не показываются и не озвучиваются как доступные.
- **FR-003a**: VoiceOver ДОЛЖЕН озвучивать скрытые/недоступные действия как недоступные, а не как доступные.
- **FR-004**: Сохранённый микрофон, которого больше нет, ДОЛЖЕН сбрасываться с fallback на системный и понятным объяснением.
- **FR-005**: Отключение системного микрофона во время записи ДОЛЖНО переводить сессию в `degraded`, не останавливая системный звук.
- **FR-006**: Очистка `localStorage`/`sessionStorage` при смене аккаунта ДОЛЖНА завершаться до перезагрузки кабинета и уведомления.
- **FR-007**: Строки локальных записей ДОЛЖНЫ пересчитываться при изменении часового пояса.
- **FR-008**: Меню-бар ДОЛЖЕН различать recording, degraded и failed.
- **FR-009**: «Все настройки GRAF» ДОЛЖНЫ открывать общий экран настроек, а не текущий локальный раздел.
- **FR-010**: В фолбэке настроек ДОЛЖНЫ быть доступны все пять разделов, включая недоступные локально.
- **FR-011**: Сохранённый frame окна ДОЛЖЕН соответствовать минимальному размеру и пересекаться с видимой областью экрана.
- **FR-012**: Неиспользуемые presentation-состояния, поля и policy-константы ДОЛЖНЫ быть удалены, а не «достроены» без потребителя.
- **FR-013**: Пользовательские статусы сохранности ДОЛЖНЫ иметь один источник текста.
- **FR-014**: Обновление списка микрофонов НЕ ДОЛЖНО выполнять discovery синхронно на MainActor.
- **FR-015**: Разрешение микрофона, полученное после запуска, ДОЛЖНО обновлять доступный список устройств.
- **FR-016**: Логи ДОЛЖНЫ сбрасываться при штатном завершении приложения.
- **FR-017**: Поведенческие изменения ДОЛЖНЫ покрываться тестами; хрупкие source-text проверки не должны быть единственным доказательством.
- **FR-018**: Новый выпуск ДОЛЖЕН использовать CalVer, Developer ID, нотаризацию, stapling, Gatekeeper, Sparkle и production deploy с проверкой public health.
- **FR-019**: Изменения НЕ ДОЛЖНЫ ослаблять гейты записи, приватности, удаления, диагностики и доступа к аккаунту.
- **FR-020**: Мёртвый код ДОЛЖЕН удаляться только после подтверждения отсутствия production-потребителей; тесты и публичное поведение не должны ломаться.

### Key Entities

- **Capture status**: состояние записи, доступные действия и accessibility-описание.
- **Microphone selection**: сохранённый выбор, фактическое устройство, fallback и degraded.
- **Account switch**: очистка storage, сброс маршрута и данных, порядок уведомления/перезагрузки.
- **Interface preferences**: frame окна, панель, микрофон.
- **Release evidence**: версия, SHA, проверки, нотаризация, appcast, deploy.

## Success Criteria *(mandatory)*

- **SC-001**: Нет конфликтующих shortcut-ов между навигацией кабинета и меню масштаба; это проверяется тестом.
- **SC-002**: Stop/Pause отображаются и озвучиваются одинаково; при `.stopping` повторный Stop недоступен.
- **SC-003**: Сохранённый отсутствующий микрофон сбрасывается; отключение системного микрофона даёт `degraded`.
- **SC-004**: Перезагрузка кабинета происходит после очистки storage; это подтверждено кодом и тестом/контрактом.
- **SC-005**: Меню-бар различает recording/degraded/failed; строки записей обновляются при смене часового пояса.
- **SC-006**: Количество неиспользуемых presentation-полей/состояний — 0; дублирующий источник текста сохранности — 0.
- **SC-007**: Все обязательные проверки, release-full, нотаризация, Gatekeeper, Sparkle и production health — PASS.
- **SC-008**: Полный набор тестов не уменьшается по покрытию поведения; новые тесты проверяют исправленные сценарии.

## Legacy Impact

Classification: `untouched`

- Удалённое audio routing не возвращается.
- `LocalBufferService`, analytics scaffold и существующие контракты сохраняются.
- Формат очереди, локальные записи, bundle ID и разрешения не меняются.
- Публичный macOS-выпуск остаётся Developer ID-only.

## Assumptions

- Продукт остаётся русскоязычным.
- Полный Dynamic Type/локализация не входят в этот срез.
- 60-минутный аппаратный performance gate остаётся отдельным ограничением.
- Новый выпуск — CalVer `v2026.11.12.1` (или следующий свободный).
- Production deploy выполняется только после release-full и подтверждённого решения.
