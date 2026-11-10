# Research: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## Decision 1: Типизированное представление записи

**Decision**: Ввести value-типы `CaptureStatusPresentation`, `RecordingBlockerPresentation` и `LocalRecordingPresentation`. View получает готовые `title`, `detail`, `systemImage`, `tone`, `isActionable` и не разбирает текст.

**Rationale**: Сейчас `CaptureControlView` определяет поведение через `localizedCaseInsensitiveContains` по русским и английским подстрокам. Любое изменение копирайта меняет логику. Типы делают состояния проверяемыми и позволяют менять текст без риска.

**Alternatives considered**:
- Оставить строки и добавить enum рядом — два источника правды, рассинхронизация.
- Полный редизайн модели `CaptureSession` — слишком рискованно для релиза.

## Decision 2: Единый источник статусов и текстов

**Decision**: Один `CaptureStatusCopy`/`RecordingStatusPresentation` используют панель записи, `CaptureStatusItem`, titlebar HUD, меню-бар и локальные строки. Для сохранности — один `DesktopUploadCustodyCopy`-совместимый слой. Для разрешений — один `PermissionPresentation`.

**Rationale**: Сейчас один и тот же статус описан в 3–4 местах, а тексты расходятся (`Идет`/`Идёт`, «загрузка»/«отправка», `Mute`/«Выключить микрофон»). Это видимая несогласованность и источник ошибок.

**Alternatives considered**:
- Оставить дубли и синхронизировать вручную — уже привело к расхождениям.
- Полная локализация через `Localizable.strings` — шире задачи и не нужна для русского продукта.

## Decision 3: Сброс контекста при смене аккаунта

**Decision**: Выделить `AccountSwitchResetPolicy` и вызывать единый сброс: маршрут кабинета → список встреч, календарный prompt и pending/failed состояние → nil, локальный плеер → close, выбранная запись → nil, web bridges → invalidate, web view → session boundary/reload. Сброс выполняется синхронно до асинхронного обновления данных.

**Rationale**: Сейчас `ContentView` сбрасывает очередь и плеер, но не маршрут и календарный prompt. Старое название встречи может остаться на экране после смены аккаунта. Это приватность и доверие.

**Alternatives considered**:
- Полагаться на ответ сервера/redirect — окно утечки и мигание старого контента.
- Полный перезапуск окна — дороже и теряет позицию.

## Decision 4: Глобальная остановка записи

**Decision**: Добавить пункт меню приложения «Остановить запись» с сочетанием `⌘⇧S`, действием в `AppLifecycleDelegate` и валидацией по `DesktopControlModel.snapshot.active`/transition. Пункт доступен, пока запись активна или завершается. Меню-бар сохраняет свой пункт.

**Rationale**: При закрытом окне сейчас остановка доступна только через открытие меню-бара — это два действия. Конституция требует одношаговый Stop. `⌘⇧S` не конфликтует с `⇧⌘R` (запись) и `⌘0` (масштаб).

**Alternatives considered**:
- Глобальный hotkey через Carbon/event tap — лишние разрешения и сложность.
- Только меню-бар — не удовлетворяет одношаговому пути.
- `Esc` — конфликтует с диалогами и web view.

## Decision 5: Меню и сочетания клавиш

**Decision**: Меню приложения и View-меню переводятся на русский. `Zoom In` остаётся одним пунктом с `⌘=`, `⌘+` остаётся альтернативой на уровне системы только если AppKit поддерживает; второй видимый пункт удаляется. `⌘0` остаётся за «Actual Size»; «Домой» получает `⌘⇧H`. Меню масштаба называется «Масштаб кабинета».

**Rationale**: Сейчас два видимых «Zoom In», `⌘0` конфликтует с «Домой», а английские пункты смешаны с русским интерфейсом. Это прямые видимые дефекты.

**Alternatives considered**:
- Оставить английские пункты — противоречит языковой политике.
- Убрать все shortcuts — ухудшает клавиатурную доступность.

## Decision 6: Производительность пути отрисовки

**Decision**:
- Список микрофонов кэшируется в `MicrophoneCaptureService` и обновляется по `AVCaptureDevice.wasConnected/wasDisconnected` и `onAppear`; `ContentView` не вызывает DiscoverySession в body.
- `EmbeddedCabinetLocalRecordingRow.rows` вычисляется при изменении `uploadQueueItems` вне body; файловые проверки выполняются в detached task, результат кладётся в `@State`.
- `UserTime` использует ограниченный кэш `DateFormatter` по формату и часовому поясу (NSLock, максимум 8 записей).
- `loadItems`/`applyRetentionExpiry` вызываются в detached task; MainActor получает только результат.
- `AppLog` пишет через serial queue, кэширует ISO8601 formatter, не делает `createDirectory`/`attributesOfItem` на каждую строку.
- 30-секундные циклы не запускают сетевую работу, пока приложение неактивно (по `NSApplication.didBecomeActive`/`didResignActive`), кроме уже существующих точечных обновлений.

**Rationale**: 5 Гц обновление уровней вызывает полный рендер `ContentView`; файловые проверки и DiscoverySession в body превращают это в постоянную нагрузку. Кэш и вынос I/O устраняют риск.

**Alternatives considered**:
- Снизить частоту уровней — ухудшает обратную связь.
- Оставить и оптимизировать позже — релиз с известным дефектом.

## Decision 7: Тестируемость и перенос app-shell

**Decision**: Перенести `ContentView`, `AppLifecycleDelegate`, `AppLog`, `MeetingDetectionPrompt`, `AppContentRoot` и `AppMenuBuilder` в `RecApp/Sources/AppShell` (target `TwoBrainRecAppCore`). В `RecApp/App/TwoBrainRecApp.swift` остаётся только `@main` и вызов `AppMenuBuilder.install`. Добавить `@testable import TwoBrainRecAppCore` тесты для меню, сброса аккаунта, статусов и презентационных политик.

**Rationale**: Сейчас 3 773 строки координации недоступны тестам; 437 source-text assertions проверяют наличие строк, а не поведение. Перенос — единственный способ проверять меню и сброс без запуска приложения.

**Alternatives considered**:
- Оставить в executable и тестировать через UI-автоматизацию — дорого, медленно, не покрывает детали.
- Создать отдельный тестовый executable — дублирование кода.

## Decision 8: Поведенческие тесты вместо source-text

**Decision**: Для затронутых поверхностей добавить тесты, которые создают модель/меню/политику и проверяют результат. Source-text assertions, которые проверяют только наличие строк, удалить или заменить. Для визуальных состояний использовать `NSHostingView`/`NSView` + accessibility tree и snapshot-проверки там, где это устойчиво.

**Rationale**: Source-text тесты ломаются при перемещении кода и не доказывают поведение. Новые тесты должны пережить рефакторинг.

**Alternatives considered**:
- Оставить все старые тесты и добавить новые — двойная стоимость и ложные падения.
- Полностью удалить accessibility-тесты — потеря доказательств.

## Decision 9: Контракт дизайн-токенов

**Decision**: Добавить тест, который читает `:root` и `html[data-theme="light"]` из `cabinet.css`, сравнивает ключевые CSS-переменные с `DesktopDesignTokens` и падает при расхождении. Не генерировать Swift из CSS в этой фиче.

**Rationale**: Палитра уже синхронизируется вручную; комментарий «values match» не является проверкой. Контрактный тест ловит дрейф без нового toolchain.

**Alternatives considered**:
- Генерация кода — новый шаг сборки и риск для релиза.
- Оставить ручную синхронизацию — уже было причиной расхождений.

## Decision 10: Веб-CSS без нового toolchain

**Decision**: Удалить только подтверждённо неиспользуемые классы из `cabinet.css`, проверив шаблоны, JS и Python-рендеринг. Не добавлять Vite/PostCSS. Для динамических `speaker-color-N` и классов, собираемых из строк, оставить исключения. Добавить контрактный тест на отсутствие выбранных мёртвых классов.

**Rationale**: Контракт `test_cabinet_frontend_foundation_contract.py` запрещает отдельный frontend-toolchain. Точечная уборка безопаснее.

**Alternatives considered**:
- Минификация/bundling — нарушает контракт.
- Массовое удаление по正则 — риск сломать динамические классы.

## Decision 11: Доступность

**Decision**: В рамках фичи:
- заменить фиксированные размеры ключевых панелей на `@ScaledMetric`/адаптивные ограничения там, где это не ломает утверждённую плотность;
- добавить `accessibilitySortPriority` для панели записи;
- учитывать `accessibilityReduceMotion` в `EqualizerBars`;
- расширить `colorSchemeContrast` на критические состояния в настройках и онбординге;
- добавить проверки accessibility tree для меню и ключевых кнопок.
Полная поддержка Dynamic Type для всех 582 строк — вне фичи; ключевые поверхности должны не обрезать текст при увеличенном системном размере.

**Rationale**: Нельзя переписать весь визуальный язык в релизе, но критические действия и состояния должны быть доступны.

**Alternatives considered**:
- Полный перевод всех шрифтов на semantic styles — большой визуальный риск.
- Оставить только source-text проверки — не доказательство.

## Decision 12: Релиз

**Decision**: Использовать существующий release train: `prepare-release.sh 2026.11.10.3` после merge, затем `release-app-update.sh --phase prepare/publish`, Developer ID identities из Keychain, профиль `graf-notary`, проверка feed `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml`. Публикация только после `release-full` и `cd-remote.sh --dry-run`.

**Rationale**: Это единственный разрешённый public macOS path; credentials и notary profile уже доступны.

**Alternatives considered**:
- Локальная/ad-hoc сборка — запрещена конституцией.
- Ручная замена appcast — запрещена.
