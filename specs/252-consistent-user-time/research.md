# Исследование

## Подтверждённые причины
- `queries._apply_sort`: started_at без fallback, тогда как manual upload показывает created_at.
- `cabinet.js renderLocalRecordingRows`: безусловный prepend вне сортировки и фильтров.
- `view_models._localized_datetime`: смещение записи; календарь использует профиль/браузер, billing МСК, shared/settings UTC.
- SQL `_meeting_visible_row_search_expression` отдельно повторяет старое форматирование; нужен тот же текущий IANA-пояс.
- Нативный `DesktopMeetingShellView` использует createdAt очереди, bridge уже recordingStartedAt.

## Решения
Decision: ДД.ММ.ГГГГ, ЧЧ:ММ и пояс устройства. Rationale: однозначный год, одинаковые строки во всех разделах. Alternatives: относительные даты или локаль ОС приводят к дополнительным форматам; на первом этапе использовалось только устройство; уточнение FR-012–015 добавляет явный сохранённый выбор аккаунта.
Decision: изолированный request-local display context и проверенная IANA-cookie. Rationale: уже много серверных форматтеров; не протаскивать новый параметр через весь сервисный код и не локализовать данные в БД. UTC fallback явно подписан. Cookie не влияет на расчёты, auth и сроки.
Decision: переиспользовать существующие SQL expression и сортировки, добавить числовые DOM-ключи; не создавать новый frontend framework.

## Инвентаризация поверхностей
Список/карточка/генерируемый заголовок; календарь будущих/предыдущих встреч и кандидатов; shared/invitations/сроки доступа; журнал активности; account devices/sessions/closure; billing history/trial/subscription/reset; referrals/fair-use; admin HTML. Все переходят на display formatter. Динамические calendar/retry/invitation/local rows используют browser helper.
Нативные local rows/calendar tray/custody deadlines переходят на единые локальные форматы. Capture manifest/имена директорий/queue scheduling/telemetry/ISO JSON остаются машинными. Длительность унифицируется без часового пояса. Письма и exports без контекста устройства сохраняют явно названный исходный пояс.

## Krisp: живое наблюдение 2026-09-06

Проверены нативный Krisp, список My Meetings, меню сортировки и переход в карточку через публичный интерфейс. В списке название/длительность слева, дата/время справа; меню разделяет Date/Duration/Last modified и Newest/Oldest. Карточка повторяет момент из списка. Английское представление использует Month day и AM/PM; автоматически сохранённое название может содержать отличающееся время. Для GRAF сохраняем компактную строку и повторяемость между поверхностями, но используем российский формат ДД.ММ.ГГГГ, ЧЧ:ММ. Чужие исходники, assets, внутренние API и частное содержимое не копировались, screenshots в git отсутствуют.


## Детали после проверки
- При blocked cookies или невозможности согласовать пояс через разрешённый GET браузер сохраняет серверный пояс, чтобы поиск, заголовок и дата не расходились. UTC подписан явно.
- Shared/invitation HTML имеет отдельные display-поля; исходный JSON occurred_at сохранён. Автоматическая дата из shared-заголовка убрана, пользовательский текст сохранён.
- Native bridge передаёт префикс только подтверждённого автоматически созданного названия: браузер форматирует его дату в том же поясе, что строку, даже при UTC fallback.
- Разрешение повторного GET включает проверенные страницы invoice/status и calendar settings; checkout return, refresh, share consumption и POST исключены.
- Источник manual upload в SQL учитывает только accepted+immutable ревизии, как отображение; pending replacement не меняет дату.

## Настройка пояса — уточнение в Feature 252
Решение: одно поле, nullable существующая timezone, без режима. Старое ограничение находится в 0053_account_preferences.py; сохранение — settings._save_account_preferences. Auth уже читает UserIdentity, поэтому отдельный запрос для display context не нужен.
Русские названия: stdlib ZoneInfo и Intl проверяют IANA/смещения, но не дают полного словаря русских городов; Babel/CLDR заменяет ручную таблицу переводов. Каталог включает канонические зоны с сохранением валидных aliases при отображении текущего выбора.
Native research audit_native_dates: доверенный WKWebView + существующая синхронизация cookies; пользователь/сессия приходят из серверного viewer context. Не вводим /me handshake или долговременный глобальный кеш чужого пояса. Холодный offline запуск использует устройство до подтверждения аккаунта; временный offline в текущем процессе сохраняет выбранный пояс.
