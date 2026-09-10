# UI and bridge contract

## Navigation
/settings → /settings/account; /desktop/settings → /desktop/settings/account. Остальные suffix сохраняются: workspace, billing, recording, summaries, integrations/calendar, notifications. Embedded billing сохраняет /billing. Меню/Cmd+, — аккаунт; контекст записи/уведомления — сразу свой раздел. Старые /desktop/settings/meeting-detection и /desktop/settings/notifications/mac остаются совместимыми входами, не вторыми обычными редакторами. Loading не открывает второе окно. Устойчиво недоступный кабинет — один резерв.

## Recording
Существующий grafRecordingSettings version 1 read/set/setAll сохраняется. Полное имя + select/Picker always/ask/never. Mixed placeholder disabled, не записывается. Empty: сообщение/повтор, bulk disabled. Поиск по имени фильтрует только отображение, bulk меняет весь допустимый реестр с явной подписью. Полный registry, без фильтра установленности; подсказка «Поддерживаемые приложения на macOS». Ошибка не меняет подтверждённый выбор.

## Local notifications
Handler grafNotificationSettings: только trusted /desktop/settings/notifications без query/fragment, exact percentEncodedPath, origin/port/scheme, main frame, та же WKWebView, завершённая навигация, активная сессия и совпадающий auth generation.

Request: {version:1, nonce, action}; set добавляет {field,value}. Разрешены reminders/showTitles/sound Bool и offsetMinutes integer 0/1/5. Actions read/set/requestPermission/openSystemSettings/test; точный набор ключей. Нет userID/URL/capture commands/key paths.

Response: {version:1, preferences:{reminders,offsetMinutes,showTitles,sound}, permission, canRequestPermission, canEdit, message?, error?}. Только подтверждённые данные presenter, без личного контента. Новый nonce после подтверждения нового контекста; auth-generation наружу не нужен.

Set накладывает одно поле на текущие preferences. Save сообщает явный успех и сохраняет прежние side effects. Проверки выполняются также внутри presenter.enable/test до побочных действий и публикации message; не только вокруг bridge await. Каждое async-действие перепроверяет поколение/документ перед продолжением и ответом. Auth cookies/owner/workspace change сразу инвалидирует мост; A→B→A не оживляет nonce. Старый JS-response не восстанавливает прежние данные.

Локальная группа disabled на время операции. На ошибке — подтверждённые значения и пояснение. Таймаут 5 секунд: «Не удалось подтвердить изменение. Проверьте текущее значение» и read, без обещания отсутствия записи. Sequence отвергает поздний ответ; фокус сохраняется по field id.

Разрешение/фиксированный System Settings URL/test только по явному клику. Test на сохранённых preferences сообщает передачу системе, не гарантированную доставку. Возврат из macOS обновляет статус. Без owner редактирование disabled; при denied правила редактируются, но статус явно предупреждает о недоставке.

## Server and no-JS
Письма/подсказки: прежний POST с CSRF/version. Автосохранение с JS; обычная кнопка и POST без JS. Version conflict не перезаписывается; предложено загрузить актуальное. Профиль/безопасность/календарь/оплата сохраняют подтверждения и права. Browser не получает локальный bridge.

## Offline reserve
Существующий graf-settings-window только при недоступном кабинете: sidebar recording/notifications, без NSTabViewController/вложенного меню. Подтверждённые правила сохраняются при закрытии. «Все настройки GRAF» повторяет основной маршрут, при успехе закрывает резерв. Локальные правила доступны без сети; новый неизвестный owner не редактирует уведомления до подтверждения контекста.
