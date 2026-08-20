# Feature Specification: Подключение email без тупиков

**Feature Branch**: `codex/178-account-linking-journey`

**Created**: 2026-08-20

**Status**: Draft

**Input**: User description: "Реализовать понятный путь подключения email без тупиков и стопперов, если их можно избежать; внимательно проработать UX, UI, IA, CX, дизайн и слова."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Подключить email и сохранить оба пространства (Priority: P0)

Уже вошедший пользователь подтверждает email, который принадлежит ровно одному
другому GRAF-профилю. Вместо технической блокировки он видит понятное
сравнение «сейчас → после подключения», подтверждает действие и получает один
основной профиль со всеми подтверждёнными способами входа. Встречи и файлы
обоих профилей сохраняются в двух отдельных пространствах.

**Why this priority**: Это основной восстановительный сценарий реальных
дубликатов. Сейчас два обычных личных пространства делают его невыполнимым,
хотя пользователь уже подтвердил контроль над обоими профилями.

**Independent Test**: Создать два полноценных профиля с отдельными личными
пространствами и подтверждёнными способами входа, подключить email из текущей
сессии, подтвердить экран и доказать, что способы входа объединены, оба
пространства доступны, все встречи сохранены, а повторный вход работает любым
сохранённым способом.

**Acceptance Scenarios**:

1. **Given** текущая сессия и одноразовый email-код подтверждают два разных профиля, каждый со своим личным пространством, **When** пользователь открывает следующий шаг, **Then** GRAF показывает подключение email как обычный безопасный сценарий, а не как конфликт владения.
2. **Given** экран подтверждения открыт, **When** пользователь читает его, **Then** он видит, что текущий профиль останется основным, все подтверждённые способы входа сохранятся, два пространства останутся отдельными, встречи и файлы не удалятся и после действия потребуется войти снова.
3. **Given** пользователь подтверждает подключение, **When** операция завершается, **Then** текущий профиль становится единственным активным профилем для всех подтверждённых способов входа, оба пространства и их содержимое остаются доступны без смешивания и потери устойчивых идентификаторов.
4. **Given** исходное пространство второго профиля имеет стандартное имя «Моё пространство», **When** оно сохраняется отдельно, **Then** интерфейс даёт ему понятное отличимое имя «Пространство из другого профиля»; заданное пользователем отличимое имя сохраняется.
5. **Given** объединение завершено, **When** прежние сессии отозваны, **Then** пользователь видит понятное приглашение войти снова и может выбрать любой сохранённый способ входа.

---

### User Story 2 - Понять решение и безопасно отказаться (Priority: P1)

Пользователь понимает, почему GRAF просит дополнительное подтверждение после
подключения email, и может оставить профили раздельными без скрытых изменений.

**Why this priority**: Подключение email начинается как простая настройка.
Неожиданный термин «объединение аккаунтов» повышает тревогу и заставляет
пользователя разбираться во внутреннем устройстве продукта.

**Independent Test**: Открыть экран в web и macOS WebView, проверить порядок
чтения и обе кнопки, затем отказаться и убедиться, что профили, способы входа,
пространства, встречи, устройства и сессии не изменились.

**Acceptance Scenarios**:

1. **Given** пользователь пришёл из формы «Подключить email», **When** открывается экран решения, **Then** заголовок объясняет итог «Один профиль — все способы входа», а подзаголовок подтверждает доступ к обоим профилям и сохраняет исходную задачу подключения email.
2. **Given** экран показан, **When** пользователь просматривает его сверху вниз, **Then** один компактный блок последовательно показывает «сейчас / после», два результата о пространствах и данных, предупреждение о повторном входе, раскрываемые подробности и действия без нумерованных шагов или ощущения wizard.
3. **Given** пользователь не хочет продолжать, **When** он выбирает «Оставить профили раздельными», **Then** операция отменяется, email остаётся связан со вторым профилем, данные не меняются и пользователь возвращается к способам входа с понятным статусом.
4. **Given** пользователь раскрывает подробности, **When** секция открывается, **Then** она объясняет настройки, устройства, сессии и сохранение данных простыми словами без внутренних идентификаторов и технических терминов.

---

### User Story 3 - Получить конкретный выход из редкого конфликта (Priority: P1)

Если объединение действительно нельзя выполнить автоматически, пользователь
видит не требование «устранить причину», а конкретное доступное действие либо
понятный путь получения помощи.

**Why this priority**: Без следующего действия даже корректная защитная
блокировка превращается в тупик и выглядит как ошибка пользователя.

**Independent Test**: Поочерёдно создать состояния активной оплаты, календаря,
закрытия/удаления, несовместимых ролей и дубликата локальной записи; проверить,
что каждое состояние остаётся fail-closed, не меняет данные и показывает
правильное действие на web и macOS.

**Acceptance Scenarios**:

1. **Given** активная оплата требует отдельного решения, **When** GRAF блокирует подключение, **Then** экран объясняет это простыми словами и предлагает открыть соответствующие настройки оплаты.
2. **Given** активное подключение календаря требует повторного подтверждения, **When** GRAF блокирует подключение, **Then** экран предлагает открыть настройки календаря.
3. **Given** идёт закрытие аккаунта или удаление встречи, **When** операция временно небезопасна, **Then** экран сообщает, что данные не изменены, предлагает вернуться к настройкам и объясняет, когда можно повторить попытку.
4. **Given** конфликт нельзя решить самостоятельно, **When** пользователь открывает экран, **Then** он получает действие «Получить помощь» и безопасный номер обращения без раскрытия email, внутренних идентификаторов или содержимого встреч.
5. **Given** причина исчезла, **When** пользователь повторяет подтверждение, **Then** GRAF строит новый актуальный предпросмотр и не переиспользует истёкшее или заблокированное подтверждение.

---

### User Story 4 - Получить одинаковый доступный опыт в web и macOS (Priority: P2)

Экран и все его действия одинаково понятны в браузере и встроенном macOS
кабинете, корректно перестраиваются на узкой ширине и работают с клавиатурой и
ассистивными технологиями.

**Why this priority**: Это один серверный путь на двух поверхностях; расхождения
возвращают прежние тупики и делают восстановление непредсказуемым.

**Independent Test**: Пройти confirm, cancel, actionable-blocker и повторный
вход в desktop и mobile-width web viewport, проверить маршруты, фокус, порядок
чтения, подписи, раскрытие подробностей, отсутствие перекрытий и консольных
ошибок.

**Acceptance Scenarios**:

1. **Given** широкая или узкая ширина, **When** экран отображается, **Then** сравнение сохраняет логический порядок и на узкой ширине превращается в последовательность «сейчас → после подключения» без горизонтальной прокрутки.
2. **Given** пользователь работает клавиатурой или экранным диктором, **When** он проходит экран, **Then** заголовок, статусы, раскрываемые подробности и действия имеют понятные подписи, видимый фокус и предсказуемый порядок.
3. **Given** список способов входа различается между профилями, **When** экран строится, **Then** он показывает только фактически подтверждённые способы из текущего реестра и не рисует несуществующие провайдеры.
4. **Given** экран открыт во встроенном приложении, **When** пользователь подтверждает, отменяет, открывает настройки причины или возвращается, **Then** навигация остаётся на разрешённых `/desktop/...` маршрутах до безопасного завершения.

### Edge Cases

- У второго профиля нет встреч, но есть личное пространство.
- У обоих пространств стандартное имя «Моё пространство».
- У исходного пространства уже есть пользовательское отличимое имя.
- Один профиль владеет несколькими корпоративными пространствами или состоит в
  общих пространствах с одинаковой либо разной ролью.
- Состояние оплаты, календаря, удаления, роли или встречи меняется после
  предпросмотра, но до подтверждения.
- Подтверждение истекло, отменено, повторено или отправлено одновременно в двух
  запросах.
- После объединения пользователь возвращается старой кнопкой браузера на
  устаревший экран.
- Способ входа отключён между предпросмотром и подтверждением.
- Инициирующая сессия либо точная callback proof-запись отозвана или изменилась
  между предпросмотром и подтверждением.
- Подтверждение отправлено после истечения intent либо повторено с другим
  idempotency key.
- Поддержка не настроена: экран не обещает несуществующую заявку и предлагает
  безопасный возврат в настройки.
- На узкой ширине длинные русские подписи и системный масштаб не должны
  обрезать действия или менять порядок решения.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST treat two verified profiles that each own one personal workspace as a normal confirmable account-linking scenario when no other blocker is present.
- **FR-002**: The currently authenticated profile MUST remain the primary profile after confirmation.
- **FR-003**: All verified, usable sign-in methods from both profiles MUST remain attached to the primary profile without duplicates.
- **FR-004**: Both original workspaces MUST remain distinct and accessible after confirmation; workspace and meeting identities MUST remain stable and unrelated workspaces MUST NOT be silently combined.
- **FR-005**: The current profile's personal workspace MUST remain its personal workspace; the source profile's workspace MUST be preserved as a separate accessible space without granting personal-workspace-only privileges twice.
- **FR-006**: If the preserved source space still has the standard name «Моё пространство», System MUST present it as «Пространство из другого профиля»; a distinct user-defined name MUST be preserved.
- **FR-007**: Meetings, recordings, files, processing results, memberships and already granted access MUST remain available according to their original workspace boundaries.
- **FR-008**: System MUST NOT silently move, combine or inherit active billing, calendar credentials, deletion/closure state or incompatible roles; those states MUST remain explicit blockers until a safe resolution exists.
- **FR-009**: The confirmation page MUST lead with the user's task of connecting email and MUST explain why a second confirmed profile requires a decision.
- **FR-010**: The page MUST present account/sign-in changes, workspace/data preservation and session consequences in one compact reading flow without redundant numbered sections or wizard semantics.
- **FR-011**: The page MUST show only actual verified sign-in methods and bounded counts; it MUST NOT expose raw account/workspace identifiers, provider subjects, tokens, codes, meeting content or hidden account metadata.
- **FR-012**: The primary action MUST be «Подключить email» and the safe secondary action MUST be «Оставить профили раздельными».
- **FR-013**: Cancellation MUST leave both profiles and all related data unchanged, consume or terminate the current one-use intent safely, and return a clear result on the account settings page.
- **FR-014**: Successful confirmation MUST revoke active sessions and device trust for both profiles and direct the user to sign in again with any preserved method.
- **FR-015**: Every true blocker MUST render a plain-language reason and at least one action that the current user can actually take; if self-service is unsafe, the page MUST offer configured support with a metadata-only reference.
- **FR-016**: If configured support is unavailable, System MUST state that limitation and provide a safe return path without claiming that a request was created.
- **FR-017**: The server MUST re-check proofs, blocker state and preview freshness immediately before mutation and MUST fail closed without partial changes if anything changed.
- **FR-018**: Confirmation, cancellation, expiry, retry and concurrent requests MUST remain single-use, idempotent and all-or-nothing.
- **FR-019**: Browser and macOS embedded surfaces MUST share the same decisions, wording and outcomes while keeping embedded navigation on allowed first-party routes.
- **FR-020**: The comparison MUST stack into a logical sequence on narrow widths without horizontal scrolling, clipped content or detached actions.
- **FR-021**: The page MUST preserve semantic headings, status/alert announcements, keyboard operation, visible focus and labels that do not rely on color or icon alone.
- **FR-022**: Security and product audit records MUST remain metadata-only and MUST NOT store real email addresses, codes, tokens, raw identifiers, meeting content or user/customer screenshots; synthetic visual-QA captures MUST stay outside committed evidence and contain no real account data.
- **FR-023**: Existing successful email, Yandex ID and VK login and provider-link paths MUST remain unchanged when no cross-profile recovery is required.
- **FR-024**: User-facing wording MUST use «профиль», «способ входа» and «пространство» consistently and MUST NOT expose internal terms such as merge intent, survivor, ownership conflict, provider subject or RLS.
- **FR-025**: Every merge intent MUST be bound to the exact initiating authenticated session, verified source identity and consumed callback proof record. A provider-link-originated intent MUST additionally bind the exact `provider_link_state_id`, whose confirmed `target_provider_identity_id` MUST equal that verified source identity; an email-link-originated intent MUST leave the provider-link field null. Confirmation and the account-merge RLS gate MUST re-check every required binding immediately before mutation. A legacy intent missing any required session, identity or callback binding MUST return `proof_required` without account/data mutation; a missing, unusable or mismatched required provider-link or target-identity binding MUST also fail closed without account/data mutation.
- **FR-026**: Expired confirmation and completed replay with a different idempotency key MUST NOT be presented as success; the former MUST return an expired recovery path and the latter MUST return a safe conflict without mutation.
- **FR-027**: Browser-bound provider-link callbacks MUST validate the same nonce cookie issued at start, and embedded provider-link start MUST activate the existing external-auth continuation without broadening navigation allowlists.
- **FR-028**: A preserved `linked` workspace MUST remain accessible through active membership but MUST NOT receive personal billing/trial/referral/account-close privileges or corporate admin/invitation privileges.
- **FR-029**: Billing preflight MUST block any source workspace with recurring authority, non-free/future entitlement, usable payment method, nonterminal operation/webhook or other mutable payment state; a nominal `state=\"free\"` value alone MUST NOT be treated as sufficient.
- **FR-030**: Trial, referral attribution and fair-use decisions MUST follow merged account lineage so confirmation cannot grant a second trial/referral benefit or bypass an existing restriction; historical records MUST remain auditable.
- **FR-031**: Active access-bearing user references, including memberships, accepted meeting shares and pending workspace join offers, MUST transfer or deduplicate deterministically; historical actor/audit references MUST remain on the source profile.
- **FR-032**: Whole-account closure MUST be available only from the primary personal workspace with its exact owner marker and owner membership, never from a preserved `linked` workspace.
- **FR-033**: Fresh preview and confirmation MUST lock and fingerprint both personal workspace roots and every mutable domain row used by blocker or disposition decisions; no unclassified foreign key to `user_identities` may silently change authorization or eligibility after merge.
- **FR-034**: Active personal summary templates and notification/calendar preferences MUST transfer or deduplicate deterministically. Each optional billing-notification channel (`optional_email_enabled` and `optional_in_app_enabled`) MUST remain enabled only when it was enabled in both profiles (logical AND). Template key/version collisions and unfinished uploads or exports MUST block before mutation, while terminal upload/export history keeps its original actor.
- **FR-035**: Whole-account closure MUST durably freeze its personal/linked content-workspace scope before any internally committing deletion fan-out, block new membership activation once finalization starts, require transfer of any separately owned corporate workspace, and deactivate every remaining membership before the identity is marked closed.

### Key Entities

- **Primary profile**: The currently authenticated profile that remains active and receives all verified sign-in methods after confirmation.
- **Source profile**: The other verified profile whose sign-in methods and eligible ownership references are transferred before it becomes an archived lineage record.
- **Preserved source space**: The source profile's former personal space, retained as a distinct accessible space with stable content boundaries and without a second set of personal-only privileges.
- **Account-linking intent**: A short-lived, single-use decision that binds both proofs, the previewed outcome, blocker state and the user's confirmation or cancellation.
- **Recovery action**: A user-visible next step for a true blocker, such as opening billing or calendar settings, waiting for deletion completion, returning safely or requesting configured support.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of test cases with two verified profiles, two personal workspaces and no other blockers reach a confirmable screen rather than `workspace_ownership_conflict`.
- **SC-002**: 100% of successful test merges preserve both workspace IDs, all meeting IDs and access to every seeded meeting, while leaving the two spaces distinct.
- **SC-003**: 100% of cancellation, expiry, stale-preview, replay and injected-failure cases leave profile, identity, workspace, meeting, billing, calendar, deletion, session and device state unchanged except for the intended terminal intent/audit outcome.
- **SC-004**: A representative user can identify what changes, what stays separate and why another login is required in no more than 30 seconds and can complete or decline the decision with one action.
- **SC-005**: Every seeded blocker state shows a specific truthful next action in both web and embedded surfaces; zero tested states end with only «Отменить» or «Устраните причину».
- **SC-006**: Wide desktop and 390px-wide layouts have zero clipped labels, overlaps, horizontal page scrolling or unreachable actions at supported zoom levels.
- **SC-007**: Keyboard and assistive-technology checks find one logical heading order, visible focus for every interactive element and an announced result for confirm, cancel and blocked states.
- **SC-008**: Existing focused email, Yandex ID and VK login/link regression scenarios continue to pass with zero new HTTP 500 responses and zero unintended duplicate sessions or identities.
- **SC-009**: 100% of missing/wrong browser nonce, missing/revoked proof record, expired confirmation and different-key replay cases fail closed, preserve data and show a truthful recoverable result.
- **SC-010**: Seeded linked-workspace tests expose zero personal billing/trial/referral/account-close actions and zero corporate admin/invitation actions while preserving meeting access and workspace switching.
- **SC-011**: The FK-disposition contract accounts for 100% of model foreign keys to `user_identities`: each is classified as transferred/deduplicated, lineage-aware, blocking, revoked or historical-only.

## Assumptions

- The selected visual direction is the approved «сейчас → после подключения»
  comparison in the existing GRAF dark design system.
- The current authenticated profile is always the primary profile; v1 does not
  add a survivor-selection step.
- The two original spaces stay separate. This feature does not combine their
  meetings, files, memberships, billing history or calendar data.
- A preserved source space may change its product classification to maintain
  the one-personal-space invariant, but that technical choice must not change
  its stable identity, stored content or existing authorized access.
- Existing account-linking proof, CSRF, nonce, replay, RLS, audit and
  idempotency boundaries remain authoritative and may only be narrowed or
  strengthened.
- No new authentication provider, password flow or broad account-repair system
  is introduced.

## Out of Scope

- Silent account merging based only on matching email text.
- Letting the user choose an arbitrary primary profile after confirmation.
- Combining two spaces into one, deduplicating meetings or moving content by
  title, date or similarity.
- Automatically resolving active billing, calendar credentials,
  deletion/closure, incompatible roles or duplicate local-recording conflicts.
- Reading or modifying real production account data as part of implementation
  validation.
- Redesigning the general login, registration or full account settings pages
  outside the linking and recovery journey.
