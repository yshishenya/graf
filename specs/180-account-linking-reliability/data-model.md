# Data Model: Надёжное подключение способов входа

Миграция `0076_account_linking_rls` добавляет nullable foreign key
`auth_callback_states.verified_external_identity_id` на `external_identities.id`
и индекс для него. Callback proof теперь связан с точной внешней identity,
которую повторно проверяет подтверждение объединения.

Миграция `0077_provider_unlink_cross_workspace` добавляет отдельный bounded
RLS-контекст для отзыва сессий и device bindings выбранного provider во всех
активных workspace текущего пользователя.

## Existing entities and invariants

### AuthCallbackState

- Короткоживущее и одноразовое OAuth state.
- Insert/read разрешены только bounded auth context или exact state lookup.
- Provider-link start связывает его с тем же workspace и browser nonce.

### WorkspaceProviderLinkState

- Связывает initiating user/session/source identity, callback state и candidate
  provider.
- До confirm хранит candidate subject; после terminal outcome чувствительные
  candidate fields очищаются.
- Cross-profile confirm устанавливает exact target identity перед merge intent.

### AccountMergeIntent

- Связывает survivor/source, initiating session, source external identity,
  callback proof и optional provider-link state.
- `preview_ready` подтверждается только при совпадении fingerprint и всех proof.
- `completed/cancelled/expired/rejected/blocked/failed` — terminal states.

### Workspace

- У пользователя ровно один personal root с активным owner membership.
- Corporate roots не принадлежат пользователю как личные: доступ к ним задаётся
  отдельным active membership/invitation.
- При merge source personal root не становится linked-пространством для UI:
  его личные workspace-scoped данные переводятся в survivor personal root,
  встречи и связанные артефакты складываются без дедупликации, после чего
  source root удаляется в той же транзакции. Активные billing и calendar
  credentials остаются fail-closed blockers и не переносятся.

## State transitions

```text
provider start -> initiated -> callback_verified
  -> confirmed/direct link
  -> confirmed/merge_preview_ready -> merge completed
  -> confirmed/merge_blocked
  -> rejected | expired

stale proof -> no mutation -> fresh provider/email start
```
