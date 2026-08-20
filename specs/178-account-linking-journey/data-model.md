# Data model: сохранённое пространство после подключения профиля

## Workspace

Существующий `Workspace.kind` расширяется закрытым значением `linked`:

| kind | Назначение | Personal privileges | Corporate admin/invites |
| --- | --- | --- | --- |
| `personal` | Текущее личное пространство активного профиля | Да | Нет |
| `corporate` | Явно созданное командное пространство | Нет | Да |
| `linked` | Сохранённое пространство подтверждённого второго профиля | Нет | Нет |

Инварианты `linked`:

- исходные `id`, `organization_id`, `slug`, timestamps и content references не меняются;
- `owner_user_id` после merge указывает на primary profile;
- active source membership переносится primary profile существующим merge rule;
- стандартное имя меняется один раз, пользовательское отличимое имя сохраняется;
- его нельзя использовать для personal billing/trial/referral и corporate invitations/admin;
- оно доступно и активируется как обычное пространство только при active membership.

## MergePreview

Существующий immutable preview получает bounded поля:

- `survivor_provider_ids`: уникальные active+verified provider IDs primary profile;
- `source_provider_ids`: уникальные active+verified provider IDs source profile;
- `workspace_count_after`: количество разных доступных пространств после merge;
- существующие entity counts, blocker codes, policy version и fingerprint.

Fingerprint включает provider IDs, workspace IDs/kinds и bounded counts, чтобы
изменение identity/workspace state между preview и confirm стало stale preview.
User-facing response не содержит raw workspace IDs.

## State transition

```text
source Workspace(personal, source owner)
  -- fresh confirm in one transaction -->
source Workspace(linked, primary owner)
```

Порядок writes: lock users/workspaces → fresh preview → transform source
personal workspace → move identities/memberships/meeting creator references →
move remaining eligible ownership → revoke sessions/devices → archive source
user → journal/audit → commit.

Любая ошибка откатывает всю последовательность.

## Proof bindings on AccountMergeIntent

Migration `0074` также добавляет nullable foreign keys:

- `initiating_auth_session_id` → exact survivor session;
- `source_external_identity_id` → exact verified identity owned by source;
- `proof_callback_state_id` → exact consumed email/OAuth callback state;
- `provider_link_state_id` → exact provider-link state for OAuth-link flow, null for email-link flow.

Новые intents обязаны заполнить первые три поля. Nullable schema позволяет
безопасно развернуть migration при наличии короткоживущих legacy intents; confirm
для legacy null binding возвращает `proof_required` без mutation.

## User-reference disposition

| Category | Representative rows | Policy |
| --- | --- | --- |
| Canonical auth/access | `ExternalIdentity`, active `WorkspaceMembership`, active `MeetingShareGrant.grantee_user_id`, pending unexpired `WorkspaceJoinOffer.user_id` | Transfer to primary under locks; deduplicate by existing unique key with survivor record winning; inactive/expired rows remain historical |
| Owned active content | `Meeting.created_by_user_id`, active personal `SummaryTemplate.owner_user_id`, calendar and billing notification preferences | Transfer or deduplicate when authorization/runtime still depends on the user ID; template collision blocks; optional notification email uses privacy-safe logical AND |
| Eligibility/enforcement | `TrialActivation`, invitee `ReferralAttribution`, `FairUseReviewRecord` | Keep history; all eligibility/enforcement queries include source lineage via `merged_into_user_id` |
| External mutable authority | subscription recurring/future state, `BillingPaymentMethod`, nonterminal `BillingOperation`/webhook, active calendar credentials, unresolved account/deletion states, incompatible referrals, active template collision, unfinished `UploadSession`, requested export | Block before preview/confirm and expose a concrete recovery action |
| Revocable runtime | `AuthSession`, `RegisteredDevice`, `AuthSessionDeviceBinding` | Revoke for both profiles on success only |
| Historical provenance | audit actors, invitation creators/completers, outcome accepted/requested actors, support reporters, telemetry actors, terminal uploads/exports, inactive sessions/devices, expired offers/grants | Keep source ID; source row remains as merged lineage record |

The policy map used by the contract test lists exact `(table, column)` pairs;
adding a new FK to `user_identities` fails the test until its disposition is
declared.

## Linked capability matrix

- active membership permits listing, switching and access to preserved content;
- personal-only billing, trial, referral and whole-account-close checks require
  `kind=personal` plus exact owner marker/membership;
- corporate admin and invitations require `kind=corporate`;
- linked is neither capability class;
- public referral binding also re-checks the inviter workspace is still personal.
