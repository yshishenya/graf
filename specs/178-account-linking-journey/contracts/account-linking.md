# Contract: подключение email между двумя подтверждёнными профилями

## GET preview

Routes:

- `/settings/account/merge/{intent_id}`
- `/desktop/settings/account/merge/{intent_id}`

Требует текущую proof-bound survivor session и owned, unexpired intent. Response
показывает только bounded provider labels, workspace/meeting counts, blocker
codes и CSRF-bound actions.

## Confirmable state

Порядок чтения:

1. `Подключить email к текущему профилю` и причина второго шага.
2. Сравнение `Сейчас` → `После подключения` с фактическими способами входа.
3. Сохранность отдельных пространств, встреч и файлов.
4. Отдельное предупреждение о завершении всех сессий.
5. `Подключить email` и `Оставить профили раздельными`.

POST confirm сохраняет существующий contract: CSRF token,
`preview_fingerprint`, intent-bound `idempotency_key`, fresh preflight and one
transaction. Success revokes sessions and redirects to login on the same web or
desktop surface.

До mutation server повторно подтверждает exact initiating session, source
identity и consumed callback state. Email-link intent оставляет
`provider_link_state_id` null. Provider-link-originated intent обязан хранить и
повторно сверять exact `provider_link_state_id`, включая workspace, initiating
user/session, callback state, допустимый terminal status и равенство
`target_provider_identity_id` подтверждённой source identity. Legacy intent без
обязательной session, source identity или callback binding возвращает
`proof_required` без account/data mutation; missing/unusable/mismatched
provider-link или target-identity binding также fail closed без account/data
mutation.

Expired confirm остаётся на recovery surface и не удаляет session cookie.
Completed replay успешен только с тем же idempotency key; другой key получает
safe conflict.

## Cancel state

POST cancel consumes the intent once, performs no account/data mutation and
returns to account settings with copy: `Профили остались раздельными. Email не
подключён к текущему профилю.`

## Blocked state

| Blocker | Explanation | Primary available action |
| --- | --- | --- |
| `billing_conflict` | На втором профиле есть активная оплата | Открыть оплату |
| `calendar_ownership_conflict` | К профилю подключён календарь | Открыть календарь |
| `deletion_state_conflict` | Идёт закрытие/удаление | Вернуться в настройки и повторить позже |
| `workspace_role_conflict` | Роли нельзя объединить автоматически | Получить помощь, если support настроен |
| `meeting_owner_conflict` | Найдена конфликтующая локальная запись | Получить помощь, если support настроен |

При отсутствии configured support экран честно сообщает об этом и оставляет
безопасный возврат; он не обещает созданную заявку.

## Preference merge contract

Каждый optional billing-notification channel (`optional_email_enabled` и
`optional_in_app_enabled`) сохраняется включённым только если он был включён в
обоих профилях. Merge использует logical AND и не может молча включить канал,
который хотя бы один профиль отключил.

## Accessibility and responsive contract

- semantic `h1` then section `h2`; no heading skipped;
- blocker and terminal outcomes use `role=alert/status` appropriately;
- native `<details>` remains keyboard/screen-reader operable;
- wide comparison uses two columns; at 720px and narrower it stacks in DOM
  order without horizontal scrolling;
- buttons have visible focus and never depend on icon/color for meaning;
- embedded links stay under allowed `/desktop/...` routes except the existing
  login handoff.
