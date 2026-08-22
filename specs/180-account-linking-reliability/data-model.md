# Data Model: Надёжное подключение способов входа

Миграция `0076_account_linking_rls` добавляет nullable foreign key
`auth_callback_states.verified_external_identity_id` на `external_identities.id`
и индекс для него. Callback proof теперь связан с точной внешней identity,
которую повторно проверяет подтверждение объединения.

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

- После merge у survivor не может быть более одного personal root.
- Второй personal root становится linked; если survivor root отсутствовал,
  единственный перенесённый personal root может стать его personal root.

## State transitions

```text
provider start -> initiated -> callback_verified
  -> confirmed/direct link
  -> confirmed/merge_preview_ready -> merge completed
  -> confirmed/merge_blocked
  -> rejected | expired

stale proof -> no mutation -> fresh provider/email start
```
