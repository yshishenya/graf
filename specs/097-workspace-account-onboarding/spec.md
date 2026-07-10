# Feature Specification: Workspace Account Onboarding

**Feature Branch**: `097-workspace-account-onboarding`
**Created**: 2026-07-09
**Status**: Draft
**Input**: User description: "Продумать B2C/B2B модель workspace: простая регистрация должна остаться простой, а присоединение к корпоративному workspace должно быть отдельным управляемым действием."

## Implementation Note

The 090 security closeout added a narrow fail-safe for the current browser
email signup flow: signup start and verify both respect the existing workspace
enrollment policy instead of silently creating access when self-enrollment is
closed.

That hotfix does not complete 097. The product still needs the full personal
space / corporate workspace onboarding model described here, including
idempotent personal-space creation, explicit corporate join offers, active-space
selection, migration planning for legacy default-workspace users and admin
workspace enrollment management.

## Clarifications

### Session 2026-07-09

- Decision: Простая авторизация по email остается также регистрацией нового пользователя.
- Decision: Пользователь не вводит `workspace_id` в публичной форме регистрации или входа.
- Decision: Создание аккаунта и присоединение к workspace - разные продуктовые действия.
- Decision: B2C-пользователь после регистрации получает личное пространство по умолчанию, даже если внутри оно будет представлено как workspace.
- Decision: B2B workspace управляется администратором: приглашения, роли, отозванный доступ, pending users, audit.
- Decision: Нельзя автоматически добавлять нового пользователя в корпоративный workspace только потому, что он подтвердил email.
- Decision: Существующий `WorkspaceInvitation` из feature `064-workspace-admin-panel` является базовой моделью для B2B-присоединения, если planning не докажет обратное.
- Decision: Личное пространство создается или находится атомарно вместе с подтвержденным аккаунтом, становится активным пространством по умолчанию и принадлежит этому пользователю.
- Decision: Pending invitation после регистрации или входа показывается как отдельное предложение присоединиться; membership создается только после явного принятия приглашения или другой разрешенной workspace policy.
- Decision: В v1 корпоративное присоединение должно быть invite/admin-approval-first. Approved-domain discovery остается безопасным P2: выключено по умолчанию и не может само раскрывать закрытый workspace или добавлять участника без политики.
- Decision: Текущий configured default workspace для browser signup/login считается legacy/bootstrap поведением, которое 097 должен заменить для публичной регистрации.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Простая регистрация для B2C пользователя (Priority: P1)

Как новый пользователь, который сам пришел в продукт, я хочу ввести email, подтвердить код и сразу попасть в свой кабинет, чтобы начать пользоваться GRAF без знания workspace, organization, ролей и корпоративных настроек.

**Why this priority**: Если регистрация сложная или требует `workspace_id`, B2C-онбординг ломается. Пользователь пришел не "в организацию", а "в продукт".

**Independent Test**: Новый email проходит регистрацию, подтверждает код, получает активную сессию и видит пустой личный кабинет без доступа к чужим корпоративным данным.

**Acceptance Scenarios**:

1. **Given** новый email без аккаунта, **When** пользователь подтверждает email-код, **Then** система создает аккаунт и личное рабочее пространство без запроса `workspace_id`.
2. **Given** пользователь зарегистрировался сам, **When** он открывает список записей, **Then** он видит только свои записи и личный контекст.
3. **Given** пользователь с личным аккаунтом позже принимает корпоративное приглашение, **When** он переключается между пространствами, **Then** личные и корпоративные данные остаются разделены.
4. **Given** подтверждение email повторяется из-за обновления страницы, повтора формы или сетевого сбоя, **When** регистрация завершается повторно, **Then** система переиспользует тот же аккаунт и личное пространство без дублей.
5. **Given** у email уже есть pending corporate invitation, **When** пользователь завершает обычную регистрацию, **Then** он сначала попадает в личное пространство, а invitation показывается как отдельное действие присоединения.

---

### User Story 2 - Присоединение к корпоративному workspace по приглашению (Priority: P1)

Как сотрудник компании, я хочу принять приглашение в workspace через обычный вход или регистрацию, чтобы попасть в корпоративный кабинет без создания второго аккаунта и без ручного ввода внутренних идентификаторов.

**Why this priority**: B2B-онбординг должен быть управляемым и безопасным, но не должен заставлять пользователя понимать внутреннюю модель tenancy.

**Independent Test**: Админ создает приглашение на email; пользователь с этим email проходит вход или регистрацию; после подтверждения email он явно принимает приглашение и становится участником нужного workspace с заданной ролью.

**Acceptance Scenarios**:

1. **Given** pending invitation на email, **When** пользователь подтверждает этот email, **Then** система предлагает присоединиться к указанному workspace.
2. **Given** пользователь принимает приглашение, **When** приглашение совпадает по email и не истекло, **Then** создается workspace membership с ролью из приглашения.
3. **Given** приглашение истекло, отозвано или не совпадает с подтвержденным email, **When** пользователь пытается присоединиться, **Then** membership не создается и пользователь остается в личном пространстве или получает безопасное состояние отказа.
4. **Given** один email приглашен в несколько workspace, **When** пользователь подтверждает email, **Then** он видит отдельные доступные приглашения и выбирает, какие принять, без неявного присоединения ко всем.
5. **Given** пользователь пришел по invitation link, **When** он входит или регистрируется, **Then** link помогает найти invitation, но acceptance все равно проверяет подтвержденную identity и не требует raw `workspace_id`.

---

### User Story 3 - Админ управляет корпоративным workspace (Priority: P1)

Как администратор корпоративного workspace, я хочу приглашать пользователей, видеть pending/active/revoked состояния, назначать роли и отзывать доступ, чтобы компания могла управлять участниками без поддержки вручную.

**Why this priority**: Для B2B ценность workspace появляется только тогда, когда админ контролирует состав команды и доступ.

**Independent Test**: Админ приглашает пользователя, меняет состояние приглашения, завершает onboarding, меняет роль в допустимых рамках и видит audit событий.

**Acceptance Scenarios**:

1. **Given** админ workspace, **When** он приглашает email, **Then** приглашение появляется в pending списке с понятным статусом.
2. **Given** пользователь стал участником, **When** админ отзывает доступ, **Then** пользователь теряет доступ к корпоративному workspace, но его личный аккаунт не удаляется.
3. **Given** админ пытается удалить или понизить последнего Owner, **When** это действие оставило бы workspace без владельца, **Then** система блокирует действие.

---

### User Story 4 - Безопасное обнаружение корпоративного workspace (Priority: P2)

Как пользователь с корпоративным email, я хочу понять, есть ли для моей компании workspace, но без риска случайно попасть в чужую компанию или раскрыть существование закрытого workspace.

**Why this priority**: Доменные сценарии удобны для B2B, но опасны, если автоматически раскрывают tenant или добавляют людей без политики.

**Independent Test**: Пользователь регистрируется с корпоративным доменом; если workspace не разрешил auto-join, система не добавляет его автоматически и не раскрывает лишнюю информацию. Если политика домена включена админом, пользователь проходит понятный controlled join.

**Acceptance Scenarios**:

1. **Given** корпоративный workspace не включил доменную регистрацию, **When** новый пользователь регистрируется с таким доменом, **Then** он получает личный аккаунт, но не membership в корпоративный workspace.
2. **Given** корпоративный workspace включил approved-domain join, **When** пользователь подтверждает email на разрешенном домене, **Then** система предлагает присоединиться или отправляет заявку согласно политике workspace.
3. **Given** несколько workspace используют похожие домены или поддомены, **When** пользователь регистрируется, **Then** система не делает неоднозначное автоматическое присоединение.

---

### User Story 5 - Пользователь понимает активное пространство (Priority: P2)

Как пользователь с личным и корпоративным доступом, я хочу ясно видеть, где я сейчас работаю, чтобы случайно не загрузить личную запись в корпоративный workspace или наоборот.

**Why this priority**: Ошибка активного workspace может стать privacy incident: запись попадет не туда.

**Independent Test**: Пользователь состоит в двух пространствах, переключает активное пространство, загружает запись и видит, что запись принадлежит выбранному пространству.

**Acceptance Scenarios**:

1. **Given** пользователь состоит в нескольких пространствах, **When** он открывает кабинет, **Then** активное пространство видно в интерфейсе.
2. **Given** пользователь переключил workspace, **When** он загружает запись, **Then** запись создается только в выбранном пространстве.
3. **Given** пользователь потерял доступ к корпоративному workspace, **When** он возвращается в продукт, **Then** личный аккаунт остается доступен, а корпоративный workspace недоступен.
4. **Given** последним активным пространством был corporate workspace, доступ к которому отозван, **When** пользователь открывает кабинет или desktop app, **Then** система безопасно возвращает его в личное пространство и показывает недоступность corporate workspace без утечки его данных.
5. **Given** загрузка или запись начата в одном пространстве, **When** активное пространство меняется в другом окне или сессия устаревает, **Then** текущая операция не переносится молча в другое пространство и требует явного продолжения или повторного выбора.

## Edge Cases

- Пользователь регистрируется email, на который уже есть pending invitation.
- Пользователь регистрируется email, на который есть несколько pending invitations.
- Пользователь сначала создал личный аккаунт, а потом получил корпоративное приглашение.
- Пользователь уже состоит в одном workspace и получает приглашение в другой.
- Один email приглашен в несколько workspace.
- Приглашение истекло между отправкой кода и подтверждением email.
- Админ отозвал приглашение, пока пользователь проходил регистрацию.
- Пользователь регистрируется с корпоративным доменом, но компания не включила auto-join.
- Компания включила domain policy, но домен общий, арендованный, образовательный или небезопасный для автоматического присоединения.
- Пользователь меняет email или добавляет provider login после регистрации.
- Пользователь удален из корпоративного workspace, но остается B2C-пользователем.
- Пользователь был создан старым flow в configured default workspace до 097.
- У пользователя уже есть корпоративный аккаунт, но еще нет личного пространства.
- Пользователь пытается загрузить файл сразу после регистрации, до выбора/создания корректного пространства.
- Desktop app имеет старую сессию с workspace, доступ к которому уже отозван.
- Desktop app имеет queued upload для corporate workspace, из которого пользователя удалили до отправки.
- Повтор регистрации или callback повторно приходит после сетевого сбоя, refresh или двойного клика.
- Audit/evidence не должны содержать коды входа, magic links, токены, raw email lists или приватные записи.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Система MUST поддерживать простую регистрацию через email verification без поля `workspace_id` в пользовательской форме.
- **FR-002**: Система MUST разделять canonical user account и workspace membership как разные сущности продукта.
- **FR-003**: Новый B2C-пользователь MUST получать личное пространство по умолчанию после регистрации, чтобы сразу пользоваться продуктом.
- **FR-003a**: Personal-space creation MUST be idempotent: повтор регистрации, callback retry или повторный вход не создают второй личный workspace для той же canonical user identity.
- **FR-003b**: Пользователь MUST be the owner of their personal space and MUST be able to keep using it after leaving or losing access to any corporate workspace.
- **FR-004**: Личное пространство MUST быть изолировано от корпоративных workspace по данным, ролям, audit, квотам, списку записей, retention/deletion state и upload/processing ownership.
- **FR-004a**: Личное пространство MUST NOT expose corporate team-management concepts such as inviting coworkers, role assignment, shared quota administration, or workspace audit unless a later feature explicitly enables them for personal plans.
- **FR-005**: Корпоративный workspace membership MUST создаваться только через явный controlled path: invitation, approved-domain policy, admin approval или другой явно описанный policy flow.
- **FR-005a**: Corporate workspace enrollment in the first implementation MUST default to invitation/admin-approval semantics; approved-domain join MUST remain disabled unless planning defines domain ownership proof and ambiguity handling.
- **FR-006**: Система MUST NOT автоматически добавлять нового пользователя в корпоративный workspace только на основании подтвержденного email.
- **FR-006a**: Matching pending invitations MUST NOT auto-create membership during signup/login; the user must explicitly accept each workspace join after identity verification.
- **FR-007**: Пользователь MUST NOT вводить raw `workspace_id` для регистрации, входа или принятия приглашения.
- **FR-007a**: System-generated invitation links, slugs, or safe labels MAY help route the user, but the user-facing flow MUST NOT expose internal tenancy IDs as required input.
- **FR-008**: Invitation acceptance MUST verify that the confirmed login identity matches the invitation target before membership is created.
- **FR-009**: Если пользователь с новым email имеет matching pending invitation, система MUST allow account creation and then handle workspace join as a separate explicit step.
- **FR-010**: Если пользователь с existing account принимает invitation, система MUST attach the membership to the existing account and avoid duplicate users for the same verified identity.
- **FR-011**: Админ workspace MUST be able to create, view, revoke, resend, expire, and complete invitations through workspace-scoped admin UI/API.
- **FR-012**: Админ workspace MUST be able to view active, pending, revoked, blocked, and inactive users for that workspace without seeing unrelated personal spaces.
- **FR-013**: Система MUST preserve last-owner protection for corporate workspaces.
- **FR-014**: Система MUST show the active workspace/personal space in the user-facing cabinet when a user can access more than one space.
- **FR-014a**: After new B2C registration, the active space MUST default to the personal space. After later logins, the active space MAY restore the last valid space, but MUST fall back to personal space when corporate access is revoked or unsafe.
- **FR-015**: Upload, recording, processing, retention, deletion, and audit records MUST be scoped to the active space selected or implied at the time of creation.
- **FR-015a**: Existing or queued upload/recording work MUST NOT be silently retargeted to another space if the original space becomes unavailable; the user must see a recoverable blocked state or choose a new destination before retry.
- **FR-016**: Joining a corporate workspace MUST NOT automatically move existing personal recordings into the corporate workspace.
- **FR-017**: Leaving or being removed from a corporate workspace MUST NOT delete the user's personal account or personal recordings.
- **FR-018**: Domain-based discovery MUST default to privacy-safe behavior: do not reveal closed workspace existence unless policy allows it.
- **FR-019**: Approved-domain join MUST be controlled by workspace admin policy and MUST handle ambiguous/shared domains safely.
- **FR-020**: Email signup, provider signup, and provider login MUST use the same workspace-enrollment policy semantics.
- **FR-020a**: Email signup MUST stop treating the configured browser login workspace as an implicit destination for public registration once personal-space creation is available.
- **FR-021**: Existing B2B invitation behavior from `064-workspace-admin-panel` MUST be reused or explicitly superseded during planning.
- **FR-022**: Audit events MUST distinguish account creation, personal space creation, invitation creation, invitation acceptance, workspace join, role change, access revocation, and denied join attempts.
- **FR-023**: Diagnostics, logs, screenshots, test evidence, and specs MUST NOT contain verification codes, magic links, auth tokens, raw provider tokens, live credentials, private meeting content, or full raw invite lists.
- **FR-024**: Migration planning MUST account for existing users who were created in the current default workspace before this feature.
- **FR-024a**: Migration MUST produce a metadata-only reviewable report before changing membership or recording ownership, and MUST NOT move existing recordings between personal and corporate spaces without explicit product acceptance.
- **FR-025**: The product copy MUST use human terms such as "личное пространство", "команда" or "workspace" consistently and MUST NOT expose internal tenancy IDs as product concepts.
- **FR-026**: Every space-scoped request after authentication MUST validate current membership and active-space authority server-side; client-provided active-space labels are hints, not authorization proof.
- **FR-027**: Session/device state MUST be invalidated, downgraded, or forced through recovery when the selected corporate workspace membership is revoked, blocked, expired, or no longer matches the authenticated user.
- **FR-028**: The implementation MUST preserve metadata-only audit and diagnostics for all enrollment, invitation, active-space switch, denied join, and revoked-access events.

### Key Entities *(include if feature involves data)*

- **UserAccount**: Canonical person-level account controlled by verified sign-in identities.
- **SignInIdentity**: Verified email or provider identity attached to one canonical user account. It is used for login and invitation matching, not as workspace membership by itself.
- **PersonalSpace**: Default private space for a B2C user. It may be internally represented by workspace primitives, but users understand it as their own space. It has exactly one owning user in v1 and is the safe fallback active space.
- **Workspace**: Shared team/company space with members, roles, admin policy, files, audit, quotas, and invitations. Corporate workspaces are invite/admin/policy governed by default.
- **WorkspaceMembership**: User's role/state inside one workspace.
- **WorkspaceInvitation**: Admin-created or policy-created pending request to join a workspace.
- **WorkspaceJoinOffer**: User-facing pending invitation or policy-approved join option shown after login/registration, before membership is created.
- **WorkspaceEnrollmentPolicy**: Rules that decide who can join a workspace: invite-only, approved domain, admin approval, or open self-enrollment for intentionally public/personal contexts.
- **ActiveSpaceContext**: The space currently used for listing, uploading, processing, deleting, and auditing records.

## Out of Scope *(mandatory)*

- Building the implementation in this initial specify step.
- Adding a complex registration form.
- Asking users to type or paste raw `workspace_id`.
- Full billing/seat purchasing flow for corporate plans.
- Full SSO/SAML/SCIM implementation unless a later feature explicitly scopes it.
- Full organization directory sync, SCIM provisioning, HRIS sync, or enterprise lifecycle automation.
- Broad domain auto-join rollout without admin policy, domain ownership proof, and shared-domain safeguards.
- Public meeting sharing or external-recipient invitation links.
- Automatic migration of personal recordings into corporate workspaces.
- Support-agent or global superadmin workflows.
- Deleting user accounts or personal spaces as a side effect of leaving a workspace.

## Dependencies *(mandatory)*

- `029-email-auth-account-linking` for email auth and account identity semantics.
- `064-workspace-admin-panel` for admin-created workspace invitations and user management.
- Current auth policy model, especially `allow_provider_self_enrollment`, pending review for email/provider parity.
- Current browser signup/login behavior that hides `workspace_id` in UI but still relies on `web_login_workspace_id`; 097 must replace this for public registration.
- Existing workspace-scoped storage, processing, retention, deletion, and audit boundaries.
- Product privacy gates in `docs/agent-guidance/product-gates.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of new B2C users can register without seeing or entering `workspace_id`.
- **SC-002**: 100% of new B2C registrations land in an isolated personal space, not an unrelated corporate workspace.
- **SC-003**: 100% of corporate workspace joins require invitation, approved domain policy, admin approval, or another explicitly configured enrollment policy.
- **SC-004**: 0 corporate workspace memberships are created solely because a user verified an email.
- **SC-005**: 100% of invitation completions verify identity match before membership creation.
- **SC-006**: 100% of upload/recording creation uses the active space context visible or implied to the user.
- **SC-007**: 100% of users with multiple spaces can identify the active space before uploading a recording.
- **SC-008**: 0 logs, diagnostics, specs, or evidence artifacts contain auth secrets, verification codes, raw provider tokens, private meeting content, or live credential paths.
- **SC-009**: 100% of repeated signup/callback retries for the same verified identity reuse the same user account and personal space.
- **SC-010**: 100% of revoked corporate memberships lose access to corporate lists, uploads, recordings, retention, deletion, and audit while preserving personal-space access.
- **SC-011**: 100% of pre-097 default-workspace users are classified in a migration report before any membership or recording ownership change ships.

## Assumptions

- "Личное пространство" is the user-facing name for the B2C default scope.
- Internally, reusing existing Organization/Workspace primitives for personal spaces is likely preferable, but implementation details belong to planning.
- Corporate workspaces are invite/admin/policy governed by default.
- Domain-based auto-join is useful only when an admin explicitly enables it and domain ownership/safety is proven. It is not required for the first safe B2B onboarding slice.
- Existing users in the current default workspace need a migration decision before enforcement changes ship.
- The first user-visible release should prefer the smallest safe model: personal space for self-serve users, invitation/admin-approval for corporate teams, and no automatic domain membership.

## Initial Implementation Direction For Later Planning

- Keep email auth as signup.
- Stop treating signup as implicit membership in an arbitrary configured workspace.
- Introduce or formalize personal-space creation for standalone users.
- Reuse `WorkspaceInvitation` for B2B joins.
- Bring email signup to parity with provider callbacks: enrollment policy decides whether membership is allowed, not the signup endpoint itself.
- Keep current configured-workspace login only as an explicit legacy/bootstrap path during migration, not as the default destination for public signup.
- Add migration evidence before changing existing users who currently live in the configured default workspace.
