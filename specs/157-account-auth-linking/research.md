# Research: связка способов входа и merge аккаунтов

## Decision 1: использовать существующую модель identity

- Canonical account в текущем продукте — строка `user_identities`; отдельную
  параллельную таблицу аккаунтов в v1 не вводим.
- OAuth identity — существующая `external_identities`, которая уже уникальна по
  `(provider, provider_subject)`.
- Email-code остаётся passwordless и проходит через существующий
  `auth_callback_states`/`auth_email_flow.py`.
- Для уже поддержанного link flow переиспользуем
  `WorkspaceProviderLinkState`, `provider_links.py` и существующие browser/
  desktop settings routes.

Это минимизирует число trust boundaries и не создаёт второго механизма
авторизации.

## Decision 2: отдельный merge intent для cross-account recovery

Обычный link intent менять владельца другой identity не может. Для конфликта
нужен отдельный короткоживущий `AccountMergeIntent` с двумя подтверждениями,
preview fingerprint, выбранным survivor и одноразовым confirm. Состояние
merge не следует кодировать в OAuth callback state: callback доказывает
провайдера, а merge требует ещё email proof и явного согласия с политикой.

## Decision 3: данные сохраняются, но workspace не объединяются

Встречи и их связанные строки остаются в исходных workspace и сохраняют
стабильные ID. Переносится только ownership/reference пользователя там, где
это безопасно и не меняет authorization boundary. Дедупликация по названию,
времени, содержимому или похожести запрещена: одинаковые встречи могут быть
разными записями.

Workspaces, роли, billing, календарные credentials и deletion/closure state
не угадываются. Ролевой, billing- или deletion-конфликт останавливает merge;
активные секреты не копируются. Это сохраняет существующие RLS и tenant
границы.

## Decision 4: fail closed для ambiguous email

`_resolve_email_login_user` уже умеет обнаруживать неоднозначность, но login
start должен переводить это состояние в локализованный recovery response, а
не в 500. Ни start, ни verify не выдают сессию до успешного разрешения.

## Decision 5: атомарность и повторный запуск

Preflight читает обе стороны и возвращает безопасный preview без content.
Confirm блокирует survivor/source/identity rows в детерминированном порядке,
повторно проверяет preflight fingerprint и применяет изменения в одной DB
transaction. Успешный результат идемпотентен; отмена, ошибка, expired intent и
replay не меняют данные. Source user не удаляется физически, а становится
архивным redirect для аудита и предотвращения повторного входа.

## Existing patterns reused

- CSRF: `cabinet/web_routes/*`, `require_web_csrf`.
- OAuth state/nonce and single-use callback: `auth/sessions.py` and
  `auth/callbacks.py`.
- Metadata-only auth audit: `auth/audit.py`.
- Recovery-safe unlink guard: `auth/provider_links.py`.
- Browser/embedded parity: existing `/settings/...` and
  `/desktop/settings/...` route pairs plus settings contract tests.

## Alternatives rejected

- **Silent merge by equal email** — email equality is not proof that the user
  controls both existing GRAF accounts and can cause unauthorized data access.
- **Copy all rows into survivor workspace** — mixes tenant boundaries and can
  change sharing, roles, billing and deletion semantics.
- **Physical delete of the secondary user** — breaks audit/FK lineage and makes
  retries and support recovery unsafe.
- **New password or password reset** — product is passwordless and this would
  create a third auth path with new recovery risk.
