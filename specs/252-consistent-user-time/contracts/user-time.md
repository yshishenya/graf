# Контракт пользовательского времени

- Python: `display_timezone_name()`, `local_datetime(value)`, `format_user_datetime(value, date_only=False, time_only=False, show_zone=False)`; формат ДД.ММ.ГГГГ, ЧЧ:ММ, пусто — «Без даты». Пустой/недействительный пояс явно UTC.
- Browser: `window.GRAFTime.format(value, options)` с dateOnly/timeOnly/showZone, `timezone` и `formatDuration(seconds)`; момент ISO с Z/offset. Без значения не Date(null)=1970.
- Сервер разрешает повтор только GET навигации на точных read-only страницах списка/карточки встреч, настроек, оплаты и административного просмотра; auth/login/callback, invitation consume и произвольные пути не входят. JS читает server-issued разрешение через meta и проверяет cookie read-back; при невозможности прочитать записанную cookie обновления нет. Без сохранённого предпочтения после неуспешного согласования применяется серверный пояс (при отсутствии валидного cookie — UTC) без бесконечного повторения. Сохранённый выбор аккаунта не зависит от cookie устройства.
- Первый HTML GET после смены пояса может безопасно обновиться один раз после записи cookie; POST и встроенные fragment swaps не переотправляются. Если cookies заблокированы, повторного цикла нет, fallback явно обозначен. Следующая навигация применяет смену пояса.
- Сортировка смешанных строк по raw started/updated/duration/title и stable id; фильтры локальных строк учитывают доступные данные, server-only коллекции исключают локальные строки. Локальное время не сериализуется обратно в API.
- Точные сроки содержат дату, время и числовое UTC-смещение на момент события (например UTC+05:00; нулевое — UTC); IANA хранится в настройке. «Сегодня/Завтра» только по тому же локальному дню.

## Настройка аккаунта
`UserIdentity.timezone: str | None`: NULL до выбора, затем валидное IANA. Один select name=timezone, никаких режимов. Существующие POST /settings/account/preferences и /desktop/settings/account/preferences; 303 после успеха, 422 без частичного сохранения при неверном значении.
Метаданные `graf-time-preferred` (пусто либо IANA), `graf-time-user` и `graf-time-session` (UUID authenticated viewer, пусто для anonymous). Сохранённый пояс приоритетнее cookie. Native читает только актуальную доверенную страницу после cookie reconciliation; сбрасывает настройку при auth смене.
Каталог подписей: UTC±HH:MM — русский город/регион, поиск по label/IANA, подсказка текущего времени; текущие offsets в списке, исторические offsets в событии. Save применяет ко всем поверхностям, reset только форме.
