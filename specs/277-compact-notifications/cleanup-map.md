# F277 — Карта удаления

Проверенная база: `f5cca687a`. Инвентаризация Banach, 2026-09-26. Это список требуемых изменений, не заявление о выполнении.

| Область | Удалить | Сохранить или заменить |
|---|---|---|
| DesktopNotificationPresenter | UN delegate, категории, request/trigger, permission state/actions, submit/status/remove injections, системные response handlers | Один собственный scheduler с выбранными 0/1/5 минутами; context/generation и безопасные ссылки |
| PreferencesStore | rollback aliases и двусторонняя запись, future reservations старого планировщика | Полезные prefs и session ownership; существующие incident claims перенести без повторного показа |
| Старое состояние | lastRecordingNotice, RecordingNoticeState, updateRecordingIndicator, записываемое без чтения cardDeadline | Постоянный действующий индикатор записи и вычисление срока события |
| DesktopRecordingNoticePresenter.swift | Весь файл и второй запасной экземпляр карточки | Прямой вызов общей карточки из приложения, короткий текст и срок20s |
| DesktopNotificationCardPresenter | Неиспользуемые screenObserver/buttons, progress%, невыдаваемые actions | Настоящий screen lifecycle observer, optional layout, stable focus и terminal callbacks |
| Защита управления записью (T034) | Единственный перезаписываемый protectedFramesProvider и широкая отметка CaptureControlView в App | Один реестр живых областей с независимым снятием; настоящие CaptureStatusItem, compact indicator/Stop и внутренний titlebar HUD, включая clipping/scroll |
| Bridge/template/cabinet.js | requestPermission/openSystemSettings, permission/canRequestPermission, старые DOM поля | Version2, quiet, контекстная защита, последовательное сохранение |
| cabinet.css | Неиспользуемый селектор `[data-local-notification-permission]` удалённого раздела разрешения | Действующие стили настроек; исходная проверка охватывает также CSS |
| Cabinet navigation | /desktop/settings/notifications/mac, onOpenNotificationSettings через route/webview/workspace/app | Обычная страница notifications; старый URL отклоняется без alias |
| Native settings | Раздел системного разрешения и его refresh | Живой DesktopNotificationsSettingsView для недоступного кабинета, в полном соответствии новым prefs |
| Tests | Контракты старого scheduling/permission, UN-based fixtures вне migration tests, wrapper-only тест | Эквивалентные проверки owner, дедупликации, восстановления prefs, закрытия и actual delivery |
| DesktopControlPanel и потребители | Неотправляемые `DesktopControlAction.settings/localRecordings/permissions`, цепочка `grafOpenLocalRecordingControls` в приложении и `DesktopMeetingShellView`; используемые только старыми тестами `completedRecording/recoveryAction/localIssues`; неиспользуемые для решений `calendarContextEventID/permissionBlocker` в snapshot | Рабочие start/stop/pause/resume и `localRecording(sessionID)`, навигация через `showRecording`, действующие методы открытия настроек и разрешений; локальное вычисление blocker без лишнего поля snapshot |

Нужна только выполняемая очистка pending/delivered сообщений своего bundle. Не удалять весь словарь `.attempts`: он содержит отметки проблем, не только календарные reservations. Минимальный односторонний переход не отправляет уведомления и не поддерживает старый протокол.

Отдельный MeetingDetectionPromptView/Panel уже удалён в базе; отрицательный тест отсутствия остаётся. Встроенный CalendarPromptView, DesktopUploadClient.notificationContext, серверные inbox/billing/email и исторические specs/evidence не являются целью удаления.

Проверить связанные XCTest: DesktopNotificationCardTests, DesktopLocalNotificationDeliveryTests, DesktopNotificationControlTests, ShortRecordingNoticeTests, EmbeddedCabinetNotificationSettingsBridgeTests, AppControlAccessibilityTests, DesktopCabinetRoutePolicyTests; browser fixtures settings-consistency.test.cjs и settings-combobox.test.cjs. Проверка отсутствия старого пути должна охватывать все production consumers, а не только основной presenter.

Дополнительная строка DesktopControlPanel подтверждена независимым чтением и поиском рабочих отправителей 2026-09-26. Одноимённые recoveryAction в диагностике относятся к другим типам и не удаляются. `activeCalendarContextEventId` приложения не является удаляемым полем snapshot. Удаление не затрагивает writer, восстановление записи или обработку аудио; оно входит в T018 как удаление недостижимых потребителей уведомлений. Новые отрицательные проверки выполняются до удаления.

Повторный просмотр 2026-09-27 нашёл оставшийся CSS-селектор старого разрешения.
T018 открыт снова до его удаления и отрицательных проверок. Периметр защиты
дополняется `Shared/Sources` и `Shared/Tests`: рабочие старые Swift-конструкции
запрещаются, но текст отрицательных проверок и необходимые миграционные данные
не считаются реализацией старого канала. Проверка подключения retirement helper
должна отличать выполняемый вызов от одного упоминания в комментарии/объявлении.

Дополнение проверено 2026-09-27: селектор удалён, проверка охватывает оба
Shared-каталога и CSS. Комментарии и литеральный текст Swift-строк не считаются
кодом; выражения интерполяции проверяются. Требуется прямая форма вызова
`DesktopNotificationRetirement.run()`. Это лексическая защита, не доказательство
достижимости ветвей: реальное подключение helper отдельно проверено чтением
presenter. Псевдонимы типов, макросы, условия компиляции и Swift regex literals
не разрешаются этим анализатором. 51 отрицательная/положительная проверка
прошла; T018 снова завершён в пределах карты удаления, не всей приёмки F277.
