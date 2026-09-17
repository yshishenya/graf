# Data model: auth error presentation

Новых таблиц, полей и persistent transitions нет. Фича уточняет проекцию уже
существующих данных в одном HTTP-ответе.

## Auth provider snapshot

- Scope: точный `workspace_id` под существующим `WorkspaceAuthContext`.
- Source: `read_auth_providers()` и установленный provider registry.
- Projection: только поддерживаемые и включённые Яндекс ID/VK; VK также даёт
  существующие Mail.ru/Одноклассники authorization hints.
- Disabled/unknown providers не становятся активными.
- При невозможности безопасно прочитать snapshot используется пустое
  fail-closed состояние, а исходная ошибка не скрывается.
- Snapshot не принимается от клиента и не хранится между запросами.

## Auth error presentation

- `workspace_id`: безопасно определённое пространство либо `None`.
- `providers`: фактический snapshot либо пустое fail-closed состояние.
- `next_path`: результат существующей first-party allowlist-нормализации.
- `error`: стабильная публичная причина с прежним HTTP status/headers.
- `invitation_flow` / `mode` / `embedded`: существующая классификация surface.
- `email_value`: необязательный, синтаксически корректный нормализованный email,
  введённый текущим пользователем; выводится только через Jinja autoescape.

## Email authentication attempt

- Pre-delivery rejection не создаёт код, callback state или сессию.
- Delivery failure завершает уже созданный callback по существующим правилам и
  не выдаёт сессию.
- Успешный start и verify flow не меняются.
- Повторное чтение provider snapshot предназначено только для error response и
  не меняет account, identity, audit или rate-limit state.
