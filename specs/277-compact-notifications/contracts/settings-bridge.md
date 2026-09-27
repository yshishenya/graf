# F277 — Локальные настройки

Существующий WKScriptMessageHandlerWithReply на `/desktop/settings/notifications`: сохранить mainframe/source/currentURL/exactorigin/route/nonce/epoch checks. Старый документ не меняет состояние. В regularbrowser локальные настройки недоступны; server inbox/billing не изменять.

Version2 request: version,nonce,action; `read`/`test` без лишних fields; `set` с field/value. Fields: reminders/showTitles/sound/quiet boolean, offsetMinutes0/1/5. Удалить requestPermission/openSystemSettings/permission. Unknown actions/fields отвергать. Version1 не поддерживать параллельно: понятное «Обновите окно настроек», безmutation.

Response: version2, preferences(5fields), canEdit boolean, message string; без permission/canRequestPermission. Ошибкаsave неsuccess. Послеaccountswitch старыйresponse не возвращает прежниеprefs. No tokens/IDs/paths в сообщениях.

UI: напоминания,0/1/5min, названияoff, звукoff, тихийрежимoff, проверка. Пояснение: карточки работают покаGRAFзапущен; quiet отключает необязательные сообщения/звук, не запросначала/индикатор. Нет системногоpermissionUI. Preview настоящий, безhistory/capture; занятыйprompt→понятное сообщение вsettings.

Локальное запасное окно `DesktopNotificationsSettingsView` остаётся работающим при недоступности кабинета: те же предпочтения, подписи, значения по умолчанию и проверочное сообщение. Системный раздел и опрос разрешения удаляются и оттуда. Непроизводимый текущими страницами `/desktop/settings/notifications/mac` и callback его отдельного открытия удаляются; прежний URL получает штатный отказ политики маршрутов. Обычный `/desktop/settings/notifications` не изменяется.
