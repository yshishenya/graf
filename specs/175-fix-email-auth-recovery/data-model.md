# Data model: auth completion states

Новых таблиц и полей нет. Hotfix уточняет допустимые переходы существующих
сущностей.

## AuthCallbackState

- Связан с исходным login/link workspace и точным `state_nonce`.
- Начальное состояние: `pending`.
- Успешный terminal transition: `pending → completed`, `used_at` задан,
  `error_code` очищен.
- Ошибочные terminal transitions: `pending → failed|expired`, `used_at` задан,
  `error_code` содержит стабильный публичный reason.
- Переход выполняется один раз под точным callback lookup context.
- Session, identity, merge intent и callback transition фиксируются одной
  транзакцией либо все откатываются.

## AuthSession

- Создаётся только для однозначно разрешённого пользователя.
- Относится к выбранному personal/workspace target, который может отличаться от
  workspace callback-state.
- При rollback callback completion не остаётся активной строкой или binding.

## ExternalIdentity candidate set

- Кандидаты дедуплицируются по `UserIdentity.id`.
- Current authenticated user исключается до определения cardinality.
- 0 other users: link/update identity текущего пользователя.
- 1 other user: merge intent and explicit preview/confirmation, regardless of
  current bounded data counts.
- >1 other users: fail-closed ambiguity, без выбора аккаунта.

## AccountMergeIntent

- Создаётся только после двух подтверждений и ровно одного other user.
- Создание/preview выполняются под `AccountMergeTenantContext`.
- Перед возвратом к callback/link state merge rows flush-ятся в merge context.
- Реальное объединение по-прежнему регулируется Feature 157; hotfix не меняет
  entity policy.
- Linking callbacks никогда не вызывают confirm автоматически.

## WorkspaceProviderLinkState

- OAuth linking sibling state остаётся scoped к initiating workspace/user.
- После account-merge операции terminal scrub/status выполняется только после
  flush merge rows и восстановления разрешённого auth-bootstrap context.
