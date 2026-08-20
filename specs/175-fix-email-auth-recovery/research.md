# Research: Надёжный вход по email и восстановление аккаунта

## Decision 1: исправлять контекст завершения, а не RLS policy

**Decision**: Перед сменой контекста flush-ить изменения, которым нужен текущий
workspace/account-merge context, а callback state завершать через точный
`AuthCallbackLookupContext(state_nonce)`. Provider-link state после merge
flush-ится под `AccountMergeTenantContext`, затем завершается после возврата в
его исходный `WorkspaceAuthContext(..., auth_bootstrap)`.

**Rationale**: Production traceback показывает `StaleDataError`: ORM пытается
обновить callback row после перехода с login workspace на personal workspace.
RLS правильно скрывает эту строку. Узкие контексты уже существуют и являются
предназначенным контрактом; менять policy или давать account-merge доступ к
чужому callback-state не требуется.

**Alternatives considered**:

- Расширить RLS policy для `account_merge` — отвергнуто: увеличивает область
  доступа и не исправляет обычный login, где target personal workspace отличается
  от исходного login workspace.
- Использовать maintenance role — отвергнуто конституцией и Feature 157.
- Коммитить сессию до callback — отвергнуто: оставляет orphan session при сбое.

## Decision 2: один минимальный helper для результата email callback

**Decision**: В `auth_email_flow.py` использовать один приватный helper,
который flush-ит текущие изменения, применяет точный callback lookup context и
только затем меняет result/used_at/error_code. `_consume...` helpers не делают
commit; endpoint готовит redirect/error response и выполняет единственный commit,
чтобы вся операция оставалась одной транзакцией.

**Rationale**: Обычный login и email-link merge имеют одну и ту же ошибку
после переключения tenant context. Общая точка устраняет повторение и защищает
все terminal outcomes без новой архитектуры.

**Alternatives considered**:

- Исправить только строку production traceback — отвергнуто: sibling merge
  outcomes останутся сломанными.
- Спрятать commit внутри helper — отвергнуто: усложняет rollback и callers.

Ошибочный и истёкший код сначала пишет metadata-only audit под исходным
`WorkspaceAuthContext`, flush-ит его, затем завершает callback под exact nonce.

## Decision 3: считать только других пользователей

**Decision**: Сначала дедуплицировать кандидатов по user id, затем исключить
текущего authenticated user и только после этого применять матрицу 0/1/>1.

**Rationale**: Текущая проверка `len(candidate_users) > 1` выполняется до
исключения current user и ошибочно превращает безопасный случай current+one
other в неоднозначность.

**Alternatives considered**:

- Оставить текущую проверку и добавить исключение для двух — отвергнуто как
  менее ясное и снова ошибочное при нескольких identities одного пользователя.

## Decision 4: восстановить реальные provider actions на recovery screen

**Decision**: В ambiguous-email error path загрузить существующий provider
snapshot и передать его в `render_login_page`; улучшить текст так, чтобы он
называл доступное действие, не обещая автоматического объединения.

**Rationale**: `providers=[]` делает указание «подтвердите второй способ»
тупиком. Существующие Яндекс ID/VK actions уже реализуют CSRF/state/nonce и
safe-next contract, поэтому новый recovery UI не нужен.

**Alternatives considered**:

- Новый мастер восстановления или modal — отвергнуто как лишняя система.
- Только изменить текст — отвергнуто: пользователь всё равно не получает действия.

## Decision 5: forced-RLS regression обязателен

**Decision**: Добавить test path с non-owner app role в disposable PostgreSQL,
плюс обычные HTTP/UX tests. Проверка должна доказать completed state, session,
single use и rollback; merge/link paths должны доказать возврат к доступному
state после `AccountMergeTenantContext`.

**Rationale**: Owner-role интеграционные тесты зелёные, хотя production RLS
падает. Только app-role test воспроизводит trust boundary.

**Alternatives considered**:

- Source-string assertion на порядок context calls — отвергнуто: не доказывает
  PostgreSQL поведение.
- Полный CI на каждой итерации — отвергнуто: focused disposable DB check быстрее
  и точнее; full gate остаётся на release boundary.

## Decision 6: никакого auto-confirm между аккаунтами

**Decision**: Удалить внутренние вызовы `confirm_merge_intent()` из email- и
OAuth-linking callbacks. Ровно один другой аккаунт всегда создаёт/обновляет
intent и ведёт на preview, даже если текущие bounded counts равны нулю.

**Rationale**: Нулевые counts не доказывают отсутствие всех пользовательских
данных, прав или будущих ссылок. Явное подтверждение проще, безопаснее и
соответствует новому recovery contract.

**Alternatives considered**:

- Сохранить auto-link для пустого duplicate — отвергнуто: это реальное
  cross-account изменение без preview, а production repair не должен быть
  неявным.

## Decision 7: embedded route и preview завершаются в существующем UI

**Decision**: Передавать `desktop_link` для embedded email-code rendering и
дополнить существующий merge template bounded объяснением survivor, способов
входа, отдельных workspaces и revocation. Не создавать новый wizard.

**Rationale**: Серверные `/desktop/...` route variants и preview page уже есть;
проблема в неверно выбранном flow и неполном тексте, а не в отсутствии системы.

## Historical evidence

- `ab2dce09` зафиксировал intended `flush → narrow context → callback update`
  pattern, но текущий login применяет target workspace context вместо исходного
  callback lookup.
- `095f167a` добавил Feature 157 email-link candidate and merge paths, включая
  раннюю ambiguous проверку и terminal state updates после account-merge context.
- `1171b895` влил Feature 157; последующие изменения до current master не
  исправляли эти границы.
