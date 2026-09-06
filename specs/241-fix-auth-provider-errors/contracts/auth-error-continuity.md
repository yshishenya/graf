# Contract: непрерывность auth error screens

## Общая матрица

| Контекст ошибки | Provider actions | Email field | Защищённое состояние |
| --- | --- | --- | --- |
| Workspace, DB и policy доступны | Текущие включённые действия в обычном порядке | Нормализованное значение после успешной проверки | Status, headers, next и flow сохраняются |
| Workspace неизвестен | Пустое состояние, ни один способ не объявляется рабочим | Не отражается | `workspace_required` |
| DB отсутствует | Пустое состояние | Только если маршрут уже безопасно нормализовал значение и rendering доступен | `auth_dependency_unavailable` |
| Policy недоступна | Пустое fail-closed состояние | Нормализованное значение допустимо | Исходная либо policy error остаётся видимой по контракту маршрута |
| Способ выключен policy | Выключенный способ скрыт, остальные включённые сохраняются | Без изменения | `provider_disabled`, HTTP 403 и audit сохраняются |

## Email login и sign-up

- Неверный email не отражается обратно в поле.
- Корректный email после нормализации сохраняется для invitation mismatch,
  rate limit, unavailable identity/workspace и delivery failure.
- `email_start_unavailable` не сообщает, существует ли аккаунт, и не говорит,
  что письмо уже отправлялось.
- `email_delivery_unavailable` явно относится к почтовой доставке.
- Error response не создаёт дополнительный callback state, код, session или
  success audit event.

## Provider start

- Unknown/future provider, rate limit, missing adapter и disabled provider не
  стирают другие фактически включённые способы, если policy читается.
- `db is None` и неизвестный workspace остаются fail closed.
- OAuth callback URL, state/nonce, provider secret custody и safe-next не
  меняются.

## Browser и embedded

- `next` проходит существующую first-party allowlist и не принимается как
  внешний URL.
- `/desktop/...` остаётся embedded surface; действия провайдеров продолжают
  вести на first-party `/login/{provider}/start` с безопасным `next`.
- Активные действия остаются `<a>`; planned entries остаются
  `aria-disabled=true`; alert semantics и доступность формы сохраняются.

## Инварианты

- Forced RLS, CSRF, state/nonce, callback single-use, rate limits,
  verified-email, account ambiguity и merge policy не ослабляются.
- Ordinary login не создаёт, не выбирает, не связывает и не объединяет аккаунт.
- Реальные адреса, коды, токены и account identifiers не попадают в evidence.
