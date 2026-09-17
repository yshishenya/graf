# Контракт интерфейса
FR-001/008: .settings-page__content и .calendar-settings__content имеют width:min(780px,100%) и равные горизонтальные поля, текст слева; billing использует свою более широкую разновидность. main padding учитывается в измерениях.
FR-002/004: один main/h1/nav, прежние routes/form actions/input names/CSRF/data hooks. Календарь и дополнительные настройки не теряют действия при 320px. Download только там, где применимо.
FR-003/004: browser+embedded forwarding profile и account_close; failed — error, reauth — warning с безопасным действием, штатные исходы — success. GET ничего не изменяет.
FR-005/006: NSWindow соответствует размеру content; bulk разные значения видимы, но enum содержит только always/ask/never. Сохранение атомарно через прежний store, правила capture не меняются.
FR-007/009: удаления только с поиском потребителей; независимо написанные стили и код, без сторонних ресурсов.
