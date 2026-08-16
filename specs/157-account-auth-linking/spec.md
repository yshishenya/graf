# Feature Specification: Связанные способы входа

**Feature Branch**: `157-account-auth-linking`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Связать email-code и OAuth входы в один аккаунт с безопасным подтверждением владения, продумать все сценарии и отображение в настройках"

## Clarifications

### Session 2026-08-16

- Q: Должны ли связанные способы входа быть видимы и управляемы в настройках в v1, или linking должен работать только во время входа? → A: Linking должен работать автоматически во время входа после необходимых подтверждений; в настройках пользователь должен видеть способы входа и иметь возможность привязать или удалить OAuth-способ.
- Q: Что делать, если оба аккаунта уже содержат данные? → A: Выполнять безопасный auto-link без переноса данных только для пустого вторичного аккаунта; если данные есть в обоих аккаунтах, показывать явное подтверждение и выполнять entity-by-entity merge с сохранением данных и блокировкой нерешённых конфликтов.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Вход существующего пользователя вторым способом (Priority: P1)

Пользователь, который уже вошёл через email-код или OAuth, может подтвердить второй способ входа и продолжить пользоваться тем же аккаунтом, не создавая дубликат.

**Why this priority**: Дубликаты сейчас блокируют production-вход и создают риск потери доступа к встречам.

**Independent Test**: На чистых тестовых данных пройти email → OAuth и OAuth → email, затем убедиться, что оба способа открывают один и тот же аккаунт и его встречи.

**Acceptance Scenarios**:

1. **Given** пользователь вошёл по email-коду, **When** он завершает OAuth-поток с подтверждённым адресом, **Then** OAuth identity привязывается к текущему аккаунту и новый пользователь не создаётся.
2. **Given** пользователь вошёл через OAuth с подтверждённым email, **When** он подтверждает тот же email одноразовым кодом, **Then** email identity привязывается к OAuth-аккаунту и пароль не запрашивается.
3. **Given** OAuth email совпадает с email identity другого аккаунта, **When** пользователь подтверждает владение почтой и OAuth-профилем, **Then** система запускает явный безопасный сценарий объединения и не выбирает аккаунт молча.

---

### User Story 2 - Понятное разрешение конфликта аккаунтов (Priority: P1)

Пользователь с уже существующими дубликатами понимает причину блокировки, подтверждает оба способа входа и сохраняет доступ к данным выбранного основного аккаунта.

**Why this priority**: Текущая ошибка `500` оставляет пользователя без объяснения и без рабочего пути восстановления.

**Independent Test**: Создать два аккаунта с одним подтверждённым email, войти каждым способом, пройти конфликтный сценарий и убедиться, что результат однозначен, аудируем и не теряет встречи.

**Acceptance Scenarios**:

1. **Given** email соответствует нескольким активным аккаунтам, **When** пользователь начинает вход, **Then** система показывает понятное сообщение о конфликте и предлагает подтвердить второй способ, не создавая сессию наугад.
2. **Given** пользователь подтвердил оба способа, **When** он подтверждает объединение, **Then** identities привязываются к одному аккаунту, встречи и права сохраняются по определённой политике, а старые сессии конфликтующего аккаунта завершаются.
3. **Given** пользователь отменил объединение или не прошёл вторую проверку, **When** сценарий заканчивается, **Then** исходные аккаунты и их данные остаются без изменений, а пользователю показана повторяемая безопасная инструкция.

---

### User Story 3 - Управление способами входа в настройках (Priority: P2)

Пользователь видит, какие способы входа привязаны к аккаунту, и может добавить или безопасно отключить способ.

**Why this priority**: Прозрачное управление снижает повторное создание дубликатов и даёт пользователю контроль после успешного входа.

**Independent Test**: В настройках открыть список способов входа, добавить OAuth к email-аккаунту, проверить обновлённый список и попробовать опасные операции отключения.

**Acceptance Scenarios**:

1. **Given** пользователь авторизован, **When** он открывает раздел способов входа, **Then** видит подтверждённые способы, дату/состояние подтверждения и доступные действия.
2. **Given** у аккаунта есть только один способ входа, **When** пользователь пытается его отключить, **Then** система блокирует действие и объясняет, что сначала нужно добавить другой подтверждённый способ.
3. **Given** OAuth-провайдер сообщает новый или неподтверждённый email, **When** профиль синхронизируется, **Then** прежний статус подтверждения email не переносится на новый адрес без новой проверки.

---

### User Story 4 - Одинаковый безопасный поток в вебе и macOS-приложении (Priority: P2)

Пользователь проходит те же email/OAuth/linking сценарии в браузере и во встроенном WebView macOS-приложения, сохраняя безопасное возвращение в приложение.

**Why this priority**: Различия между вебом и приложением уже приводили к невозможности войти локально.

**Independent Test**: Повторить успешный, конфликтный, отменённый и ошибочный сценарии в вебе и GRAF Local, не разрешая WebView произвольную внешнюю навигацию.

**Acceptance Scenarios**:

1. **Given** linking начат в macOS-приложении, **When** OAuth/email flow завершён, **Then** сессия возвращается в приложение и открывает исходный локальный или production маршрут.
2. **Given** внешний OAuth или email flow завершился ошибкой, **When** пользователь возвращается в приложение, **Then** приложение показывает причину и повторный путь, не показывая общий экран недоступных встреч.
3. **Given** пользователь находится вне активного auth flow, **When** страница пытается открыть внешний адрес, **Then** WebView блокирует навигацию.

### Edge Cases

- Один email связан с двумя активными пользователями; система не выбирает пользователя по времени создания или случайно.
- Email OAuth-провайдера отсутствует, не подтверждён, изменился или отличается от email, подтверждённого кодом.
- Пользователь уже вошёл в один аккаунт и пытается привязать OAuth identity, которая уже принадлежит другому аккаунту.
- Два параллельных запроса пытаются привязать один OAuth identity или один email identity.
- Код истёк, уже использован, введён неверно, превышен rate limit или доставка завершилась неопределённо.
- Пользователь закрывает вкладку, отменяет OAuth, теряет сеть или возвращается по устаревшему callback.
- В конфликтующих аккаунтах есть встречи, активные загрузки, календарь, billing-состояние, приглашения или разные права.
- У пользователя остаётся один способ входа; отключение последнего способа запрещено.
- Повторный запуск одного и того же linking intent не должен создавать новую identity или повторно объединять данные.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST represent one user account as a canonical identity with zero or more linked, provider-specific sign-in identities, while preserving the current email-code and OAuth methods.
- **FR-002**: System MUST require proof of control of the email address through a valid one-time code before linking an email identity to an OAuth account or merging two accounts.
- **FR-003**: System MUST accept a verified OAuth assertion as proof of control of that provider account, but MUST NOT silently merge accounts solely because normalized email strings match.
- **FR-004**: System MUST reuse an already authenticated account when a user adds a new provider identity from an explicit linking flow, and MUST NOT create a duplicate user in that flow.
- **FR-005**: When an unauthenticated login discovers multiple active accounts for one email, the system MUST fail closed with a user-facing conflict explanation and a recovery action; it MUST NOT issue a session for an arbitrary account.
- **FR-006**: The conflict recovery flow MUST require both applicable proofs, be single-use and time-bounded, preserve the selected survivor's meetings and permissions, and leave source data unchanged if the user cancels or verification fails.
- **FR-007**: When only one account has user-owned data, the system MAY auto-link identities without moving data; when both accounts have data, the system MUST require explicit confirmation before a data-preserving merge.
- **FR-008**: Account merging MUST use an entity-by-entity policy: preserve meeting, recording, artifact, processing, invitation, and audit identifiers; attach all eligible sign-in identities to the survivor; preserve shared workspace boundaries and memberships; merge only compatible personal-account state; and never silently combine unrelated workspaces.
- **FR-009**: Account merging MUST block and explain unresolved conflicts in active billing/subscription state, provider/calendar ownership, workspace roles, deletion state, or incompatible account settings until an explicit safe resolution exists.
- **FR-010**: The system MUST prevent linking an OAuth identity that is already linked to a different account unless the explicit, fully verified conflict-recovery flow is completed.
- **FR-011**: The system MUST expose the linked sign-in methods and their verification state in account security settings, allow adding a supported OAuth method, and allow removing an OAuth method after re-authentication when another usable sign-in method remains.
- **FR-012**: The system MUST prevent removal of the last usable sign-in method and MUST require re-authentication or equivalent proof for unlinking a method.
- **FR-013**: If a provider email changes, the system MUST clear the prior email verification state atomically and require verification of the new address before treating it as verified.
- **FR-014**: All link, unlink, conflict, merge, cancellation, rejection, and failure outcomes MUST be recorded as metadata-only security audit events without storing codes, tokens, provider secrets, or meeting content.
- **FR-015**: Linking and merging MUST preserve CSRF/state/nonce protections, apply scoped rate limits, prevent replay, and invalidate sessions and stale intents according to the approved security policy.
- **FR-016**: Web and macOS WebView flows MUST share the same account-linking rules and user-facing reasons, while the WebView retains the existing active-auth-only external navigation boundary.
- **FR-017**: Existing production users with duplicate accounts MUST have a safe recovery path that does not require a password and does not delete meetings as a side effect of failed or cancelled linking.
- **FR-018**: User-facing conflict, proof, cancellation, unlink, and recovery messages MUST be localized in Russian, accessible to keyboard and assistive-technology users, and distinguish a blocked login from an unavailable service.

### Merge Policy

Слияние аккаунтов не означает безусловное смешивание всех сущностей. Перед
подтверждением пользователь видит краткий preview: какие данные сохранятся,
какие останутся в отдельных пространствах и какой конфликт блокирует операцию.

| Сущность | Политика v1 |
| --- | --- |
| Способы входа | Все подтверждённые email/OAuth identities привязываются к выбранному survivor. Одинаковая identity не дублируется. |
| Встречи, записи, артефакты и processing | Сохраняются все записи из обоих аккаунтов. ID, содержимое и текущий статус не меняются; автоматическое объединение по названию, времени или похожести не выполняется. Запись остаётся в исходном workspace. |
| Workspaces и memberships | Workspaces не склеиваются. Оба workspace остаются отдельными, а принадлежность survivor к ним переносится только без повышения роли. Конфликт ролей или ownership блокирует merge и требует отдельного разрешения. |
| Шаринг и приглашения | Уже выданный доступ и принятые memberships сохраняются. Непринятые приглашения не принимаются автоматически и остаются в исходном состоянии. |
| Профиль и личные настройки | Явно заданные настройки survivor сохраняются; значение из второго аккаунта используется только если у survivor оно отсутствует или равно системному default. Несовместимые значения показываются как конфликт. |
| Календарь и provider credentials | История и snapshots сохраняются в исходном workspace. Секреты и активные credentials не копируются; подключение после merge требует отдельной повторной авторизации. Конфликт владельца календаря блокирует merge. |
| Billing, подписки, invoices и referral state | История сохраняется в исходных workspace. Балансы, подписки и ownership не суммируются. Активный billing-конфликт блокирует merge до ручного безопасного решения. |
| Deletion/closure state | Наличие активного удаления, закрытия или retention-процесса блокирует merge; операция не может вернуть удаляемые данные в активное состояние. |
| Sessions, devices и trust | Все активные сессии обоих аккаунтов истекают. Устройства не получают автоматически прежний trust; приложение требует повторного входа и, если нужно, повторного подтверждения устройства. |
| Audit и lineage | Append-only история сохраняется с исходными actor IDs. Добавляется отдельное metadata-only событие merge; коды, токены и содержимое встреч в него не попадают. |

Успешный merge выполняется одной идемпотентной операцией после повторного
подтверждения survivor и второго способа входа. До commit система делает
read-only preflight; при любом блокирующем конфликте, отмене, истечении intent,
ошибке или повторе операция не меняет данные. После commit вторичный аккаунт
становится архивной записью, а не удаляется физически, чтобы сохранить
ссылочную целостность и возможность аудита.

### Key Entities

- **Canonical user account**: The durable user identity that owns access, workspaces, meetings, and account-level state after linking or an approved merge.
- **Sign-in identity**: A provider-specific verified relationship for email-code, Yandex, VK, or another supported OAuth provider, linked to exactly one canonical user account.
- **Linking intent**: A short-lived, single-use record describing the requested provider/email link, required proofs, target account, return path, and outcome.
- **Account merge intent**: A higher-risk, short-lived confirmation record that binds two authenticated accounts, the selected survivor, collision decisions, and an auditable outcome.
- **Merge policy**: A visible, deterministic set of per-entity rules describing what is preserved, moved, deduplicated, blocked, or left in place during an approved merge.
- **Identity conflict**: A state in which one normalized email or provider identity resolves to more than one active canonical user account.
- **Account security settings**: The user-facing surface for inspecting and managing linked sign-in identities and recovery safeguards.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of supported email→OAuth and OAuth→email acceptance scenarios resolve to one canonical account without creating a second account.
- **SC-002**: 100% of ambiguous-identity attempts are blocked from arbitrary account access and show a localized recovery reason instead of an unhandled server error.
- **SC-003**: 100% of link and merge mutations require the proofs and single-use intent defined by the security requirements; replayed, expired, cancelled, and partial intents cause no account-data mutation.
- **SC-004**: In the defined test matrix, 100% of meetings, workspace memberships, and access permissions belonging to the selected survivor remain accessible after a successful merge; failed or cancelled merges change none of these records.
- **SC-005**: At least 95% of representative users can identify their linked sign-in methods and complete an intended link or recovery action without support intervention in usability validation.
- **SC-006**: The web and macOS WebView test matrix has zero unexplained differences in account-linking outcomes, error reasons, or post-auth return behavior.
- **SC-007**: No authentication or linking flow exposes passwords, one-time codes, OAuth tokens, provider secrets, meeting content, or raw identity tokens in audit evidence or user-visible error details.

## Assumptions

- Email-code authentication remains passwordless; this feature does not introduce passwords.
- A provider's verified email is treated as an assertion about control of the provider account, not by itself as permission to merge two GRAF accounts.
- Existing meeting, workspace, billing, deletion, and audit boundaries remain authoritative; linking must not weaken their authorization checks.
- The default v1 policy is explicit confirmation for cross-account linking, with no silent merge based only on email equality.
- A merge preserves user data and stable identifiers; it does not silently merge unrelated shared workspaces or unresolved billing state.
- The feature is for the existing web cabinet and macOS WebView surfaces; mobile and new identity providers are out of scope unless already supported by the shared provider registry.
- Production data repair for the currently affected email is performed only after a read-only comparison and explicit survivor confirmation.
