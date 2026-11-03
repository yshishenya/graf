# F292 — договор интерфейсов

## Owner API

Существующий `/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/link` GET/POST сохраняется. POST добавляет content_scope=summary_only|full_meeting (default summary_only); template_key остаётся совместимым. Повторный POST существующей ссылки возвращает её без изменения scope/expiry/token/version. Ответ добавляет content_scope. Изменение `/link/scope` POST требует grant_id/expected_version/content_scope/template_key; update/expiry/rotate/delete остаются и сравнивают версию. Все изменения требуют собственного owner membership, tenant/CSRF и meeting fence. 409 → обновить состояние, не повторять расширение молча. Старый create_scoped_share_grant отказывает при попытке изменить современную link строку без версии. Публичные capabilities только view, summary-only без audio/transcript. Адресные роли и workspace grants используют существующий API access-sharing, не новую систему отправки.

## Public API

`GET /api/v1/cabinet/public-shares/{token}?workspace_id={UUID}` сохраняет narrow summary JSON для summary_only; full_meeting выдаёт отдельную явную проекцию. Accept text/html → общий reader. Resolver проверяет settings/public-abuse gate, workspace/token hash/status/expiry, meeting fence/deletion, повторно grant. Ошибка безопасная 404. Защитные заголовки на всех статусах: private/no-store, no-referrer, noindex/nofollow/noarchive. Нет приватных полей в HTML/JSON.

`GET .../{token}/playback?workspace_id=...` требует full_meeting и повторной проверки каждого запроса. Только серверный аудиопоток, single Range, 206/416; буфер <=4MiB; без Range полный 200, при Range полный запрошенный диапазон 206. Ошибка аудио не притворяется успешным audio. Read proof не даёт download/export/comment/edit. Copy text локально только видимое разрешённое содержимое. Owner export переиспользует capability endpoints.

## Продолжение

`GET .../{token}/continue?workspace_id=...&action=sign-in|sign-up` проверяет ссылку и ставит зашифрованный короткий cookie; redirect во вход/регистрацию с next=/shared-meeting/continue. `GET /shared-meeting/continue` проверяет/поглощает cookie и восстанавливает только канонический локальный адрес. Нет token в URL входа, нет identity/membership mutation.

## Native

`grafrec[-dev]://shared-meeting?v=1&workspace_id=<UUID>&share_token=<URL-safe token>&tab=outcomes|recording&position_ms=<integer>` для публичного ресурса. Для адресного ресурса вместо share_token — meeting_id, оба одновременно запрещены. Строго одна копия каждого разрешённого поля; версия1; position_ms=0..86400000. Только configured origin, own app session. Внешний URI никогда не даёт полномочий. Route policy допускает только точный путь общей страницы и ограниченное состояние просмотра. Cookie/сеансы/произвольный next/url запрещены. Dev принимает grafrec-dev, production grafrec; атрибуция следует той же конфигурации.

## UX contract и матрица

Владелец: Share справа → панель <=480px, Share/Export → приглашение → owner/access list → audience → scope → copy. Никакой публикации при открытии. У неподдерживаемых прав понятная причина. Сужение/расширение — отдельное подтверждённое действие; copy стабильно. Срок 7/30/90, expiry/rotate/revoke отдельно. F286 email/auto-send чётко «Отправить только итоги».

Получатель: первый диалог GRAF со свободным просмотром, постоянная шапка, колонка <=720px, название/дата/длительность, «Итоги»/«Расшифровка», Copy, локальный поиск, говорящие/время, нижний player ±15/speed/seek. Вкладка/время отражаются в безопасном fragment и сохраняются при переходе. Только итоги не содержит скрытого аудио/реплик. Нет итогов — ясное пустое состояние; нет расшифровки/аудио — отдельные причины. Гость/внешний вошедший/адресный/owner имеют явные права. Закрытая ссылка — обращение к отправителю/вход/своя встреча без раскрытия названия.

320/390/1440px и light/dark; padding16/24, text16/line1.6, heading24. Visible focus, корректные tablist/aria-live/dialog/labels, Escape/возврат фокуса, keyboard seek, reduced-motion. Без JS документ и обычные ссылки видны. Промо не перекрывает текст/player; имя/аватар владельца не публикуются без отдельного основания, приглашение нейтральное «С вами поделились встречей» (privacy deviation). Собственные GRAF tokens/icons, без assets Krisp.

Сравнение не заявляется 1:1 для ненаблюденных состояний: мобильная/светлая версия Krisp, завершение регистрации, установка/первый native запуск; они всё равно входят в собственную приёмку GRAF.


## Атомарная общая аудитория и версия записи

GET/POST `/api/v1/cabinet/meetings/{id}/sharing/general-access`: audience=invite_only|workspace|link, content_scope=summary_only|full_meeting, expected_fingerprint (64 hex SHA256 канонического набора active link/workspace grants: id/publication_version/scope/audience/expiry). Под meeting fence сравнивается fingerprint. invite_only отзывает все общие grants, workspace отзывает link, link отзывает workspace. User grants/invitations не меняются. Создание link с явно выбранным составом; существующий link не расширяется этим POST, scope меняется только отдельной версионной командой. Ответ state/fingerprint/link/scope/workspace grant. Ошибка stale409. Срок/ротация текущей link общие с F286.

Полная projection добавляет media_version=первые24 hex SHA256 принятой media_revision UUID + effective result UUID (либо absent), без раскрытия этих UUID. Playback требует media_version query; не совпадает — 409 до заголовков/выдачи. Fragment: #outcomes | #recording | #recording?position_ms=N; N integer 0..86400000; никакой другой query/fragment. Native intent допускает те же фиксированные tab и положение; переход при новой версии записи не обязан воспроизводить старый материал: сервер требует актуальное media_version и пользователь обновляет страницу.

Native intent и canonical public URL допускают дополнительный `media_version` строго24 lowercase hex; он нужен при переносе position_ms. Сервер сравнивает его с актуальным до применения позиции. При несовпадении показывает «Запись обновилась» и требует явного обновления; старая позиция автоматически не применяется. Пустой fragment означает исходную вкладку, некорректный fragment не выполняет seek. Cookie продолжения сохраняет только проверенные tab/position/media_version.
