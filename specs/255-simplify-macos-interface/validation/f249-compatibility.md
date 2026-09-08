# F255 и F249: проверка перед merge, 2026-09-08

## Проверенные ревизии

- F255 / PR #6766: `a163c539f131db5fe20a28623ea35ebbf33941e1`.
- F249 / PR #6707: `5bb12c4b564c70b1ff1437631b5bb27269103e66`.
- origin/master: `7ff2c5c77ec007aac09cd86cded0579cd1a0443c`.
- Ветки обновлены через fetch. Обе PR открыты; F249 не включена в F255.
- `git merge-tree --write-tree HEAD origin/master`: exit 0, конфликтов нет.
- `git merge-tree --write-tree HEAD origin/codex/249-notification-control-design`: exit 1, 15 конфликтующих файлов. Команда не меняет рабочее дерево и ветки.

## Порядок объединения

Сначала F255 на проверенном master. Затем F249 переносится поверх фактически полученного master с ручным разрешением перечисленных пересечений и повторной совместной приёмкой. Текущий F249 нельзя автоматически объединять с выбором целого файла одной стороны. Готовность F255 к отдельному merge не означает готовности объединённого выпуска F249/F255.

Владелец подтвердил 2026-09-08: «меню верхней панели полностью оставим из 255». Это обязательное решение при разрешении конфликта CalendarTray, а не предложение рецензента.

Приоритет интерфейса — последние решения владельца в F255: прежняя навигация и профиль, hover-подменю с проходимым зазором, компактная матовая оболочка, NSMenu, монохромный знак GRAF с красным центром 9 pt, Mute микрофона, общие настройки и штатный Quit. F249 сохраняет владение уведомлениями, их доставкой и историей; её продуктовые функции нельзя удалить выбором версии F255.

## Разрешение пересечений

| Область / конфликтующие файлы | Что сохранить при переносе F249 |
|---|---|
| `CalendarTray.swift` | NSMenu, template-вектор, красный центр, Mute/Unmute, общие настройки/Quit и run-loop fix F255. Из F249 перенести `onProjection`, `onAuthInvalidated`, немедленную очистку при смене сессии и связь с `DesktopNotificationPresenter`. Уведомление календаря открывает действующее `showMenu`, не удалённый `showPopover`. Не возвращать CalendarTrayView, CalendarTrayState и большую панель ради старого API. |
| `TwoBrainRecApp.swift` | Команды и состояние меню F255; snapshot/синхронизацию уведомлений, DesktopRecordingWidget, вкладку локальных уведомлений, исправления cleanup при скрытии окна и stop-session F249. Существующая семантика mic-only сохраняется; в новых текстах F249 использовать принятые Mute/Включить микрофон. |
| `DesktopMeetingShellView.swift` | Геометрию и темы F255, удаление мёртвой queue-панели обеих веток; новый вход `.grafOpenLocalRecordingControls` F249 не потерять. |
| `CaptureControlViewCore.swift`, `CaptureStatusItem.swift`, `SystemAudioCaptureCoreModels.swift` | Подписи и mic/mic.slash F255; полезные переносы длинного текста и необходимые nonisolated-декларации F249. Проверить видимый Stop в узкой панели. |
| `MeetingDetectionSettingsView.swift` | Общие для веток 28 pt, radius 6, отсутствие app.dashed; контраст выбранного правила F255 и размер для контейнера вкладок F249. |
| `cabinet.css`, `cabinet.js` | Hover, проход через padding, сохранение темы без перехода, мягкие границы F255. Сохранить inbox/history/recovery, responsive и доступность уведомлений F249. Не заменять целиком общие CSS/JS. |
| `AppControlAccessibilityTests.swift`, `CabinetSidebarRuntimeTests.swift`, `CaptureControlV5Tests.swift`, `CaptureIndicatorTests.swift`, `SystemAudioLocalizationTests.swift`, `test_cabinet_static_assets_contract.py` | Совместить смысловые проверки обеих фич с финальными подписями/геометрией. Не удалять тесты уведомлений или boundary ради компиляции. |

## Пересечения без текстового конфликта

- Новый `DesktopNotificationControlTests.swift` F249 вызывает удалённый `CalendarTrayController.panelSize`; даже после выбора файла F255 сборка без адаптации теста не пройдёт. Убрать проверку отменённой popover-геометрии, сохранить проверки модели и доставки уведомлений.
- `sections.html` и `web_routes/settings.py` объединяются автоматически, но требуют проверки account preferences/CSRF, текущего маршрута и notification preferences.
- F249 меняет серверные модели, RLS, producer/worker и добавляет миграции 0086/0088. Это не часть F255 и не доказано тестами интерфейса. Dev promotion объединённой ветки должен пройти её schema-transition gates; нельзя откатывать локальную БД схемой F255.
- F249 меняет dev-harness и переход от GRAF Local к единому GRAF Dev. Сохранить её identity/schema/restore guards и общие проверки F255, отвязанные от закрытой F229.

## Обязательная совместная проверка после переноса F249

1. Сборка Swift; DesktopNotificationControl, DesktopCalendarReminder, CabinetSidebarRuntime, AppControlAccessibility, CaptureControlV5, CaptureIndicator, SystemAudioLocalization, DesktopMeetingShellWebViewBoundary.
2. Серверные notification inbox/routes/preferences, миграции/RLS, кабинетные формы/тема/профиль, dev-harness/schema-transition.
3. Официальный Dev на едином SHA: Start → Mute → Unmute → Stop; скрытие главного окна не останавливает capture; Stop/Quit работают; внешнее закрытие меню; обе темы и Reduce Motion.
4. Реальные уведомления/переходы, смена аккаунта без старых событий, настройки уведомлений, сохранение записей/истории и восстановление доставки.
5. Новые exact-SHA governance-fast и установленная приёмка. Release-full только для frozen объединённого кандидата.

Эта проверка выявляет и описывает конфликты; пробная совместная сборка или совместная установленная приёмка не заявляются. Чужая ветка F249 не изменена.
