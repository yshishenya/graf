# Research: Надёжное подключение способов входа

## R1. Причина production HTTP 500

**Decision**: После обычной membership/session проверки provider-link start
переключается в существующий `auth_bootstrap` context до insert/flush
`auth_callback_states`.

**Evidence**: Web dependency устанавливает `request`, а RLS callback state
разрешает только `auth_public`, `auth_bootstrap` или exact callback lookup.
Login start уже использует разрешённый workspace auth context. API link start
имеет тот же дефект после `_require_active_customer_membership`.

**Rejected**: Расширить RLS policy на `request` — это делает callback states
доступнее, чем требуется, и ослабляет auth boundary.

## R2. Cross-profile provider-link eligibility

**Decision**: Разрешать merge preview для любого initiating provider только
когда текущая active session и сохранённая active source identity принадлежат
survivor и совпадают по provider. Для OAuth достаточен exact provider/subject
callback proof; `is_verified` остаётся обязательным для email-originated
доказательства. Exact callback target остаётся source identity другого профиля
и повторно проверяется при confirm.

**Evidence**: Existing merge proof contract не требует email-only initiating
session; текущая ветка `source_session.provider == "email"` является product
restriction и оставляет OAuth users в conflict dead end.

**Rejected**: Всегда переносить foreign identity без merge — account takeover.
Также отклонено создание новой session-to-identity schema: для текущей проверки
достаточны existing proof bindings и user/provider/verified invariants.

## R3. Provider-aware presentation

**Decision**: Фактический provider берётся из `source_external_identity_id`,
который уже связан с intent и проверяется перед mutation. User-facing label
берётся из существующей `PROVIDER_LINK_LABELS`, fallback — «способ входа».

**Rejected**: Выводить первый provider из preview — у второго профиля их может
быть несколько, и это не обязательно подключаемый способ.

## R4. Stale proof recovery

**Decision**: Старый confirm скрывается. Для OAuth показывается POST «Начать
заново» прямо в существующий start endpoint; для email/unknown — возврат к
форме способов входа. Старые intent/state/proof не переиспользуются.

**Rejected**: Повторить confirm — mismatch не исчезает и образует цикл.

## R5. Проверка runtime и интерфейса

**Decision**: Совместить contract/template проверки с strict PostgreSQL app-role
RLS test и browser capture wide/390px. Mocked SQLite journey не доказывает
production policy boundary.

**Rejected**: Ограничиться unit test helper — он не воспроизводит реальный
`InsufficientPrivilegeError`.
