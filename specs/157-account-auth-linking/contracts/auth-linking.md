# Contract: linking and duplicate recovery

The web cabinet and embedded desktop surface use the same server rules and
error codes. Desktop routes are the existing `/desktop/...` equivalents where
the current settings surface requires them.

## Proof requirements

- Existing authenticated session proves the current account.
- Verified OAuth callback proves the provider subject.
- Email code proves control of the email address.
- Equal normalized email alone never proves ownership of the second account.

## Outcomes

| Code | User-visible meaning | Session mutation |
| --- | --- | --- |
| `identity_linked` | Способ входа подключён к текущему аккаунту. | Keep current session. |
| `identity_already_linked` | Этот способ уже подключён. | Keep current session. |
| `identity_conflict` | Способ уже принадлежит другому аккаунту; нужно подтвердить оба способа. | No new session. |
| `ambiguous_email_recovery_required` | Найдено несколько аккаунтов; вход заблокирован до восстановления. | No session. |
| `proof_required` / `proof_invalid` / `proof_expired` | Не удалось подтвердить второй способ. | No merge mutation. |
| `merge_preview_ready` | Показывается состав и блокеры merge. | No merge mutation. |
| `merge_blocked` | Есть конфликт прав, billing, календаря или удаления. | No merge mutation. |
| `merge_completed` | Аккаунты объединены по утверждённой политике. | Issue one fresh session for survivor; revoke stale sessions. |

Errors must render as localized Russian HTML on cabinet pages and as the
existing problem contract on API calls. They must not reveal account IDs,
provider subjects, raw email codes, tokens or meeting content.
