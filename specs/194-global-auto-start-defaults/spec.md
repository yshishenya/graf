# Feature Specification: Глобальный автозапуск и безопасные defaults

**Feature Branch**: `194-global-auto-start-defaults`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Включить assisted auto-start во всех workspace и сделать функцию включённой по умолчанию при установке приложения."

## Context And Product Decision

Feature 193 исправила путь detector-assisted записи, но server policy всё ещё
публикуется только для одного явно настроенного workspace, а чистая установка
не выбирает verified native targets для target-scoped auto-record. Эта feature
делает scope policy явно глобальным по операторскому флагу и добавляет first-run
defaults без автоматической подделки согласия. Все существующие capture,
privacy, visible-indicator, one-action Stop и target allowlist gates сохраняются.

Глобальный scope разрешён только отдельным deployment attestation-флагом. В этой
feature notice mode остаётся `internal_no_participant_notice`; customer/external
rollout с participant-facing notice/legal policy остаётся отдельным gated slice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Policy для каждого workspace (Priority: P1)

Как оператор внутреннего deployment, я хочу одной явно подтверждённой policy
разрешить assisted auto-start во всех workspace, чтобы новые и существующие
workspace не зависели от случайно выбранного workspace ID.

**Why this priority**: Сейчас policy появляется только в одном workspace, поэтому
одинаковая настройка приложения ведёт себя по-разному после переключения tenant.

**Independent Test**: При включённом global scope получить registry под двумя
разными валидными workspace и убедиться, что оба получают policy с одинаковым
global policy reference, но с разными subject/device references; при выключенном
scope сохраняется прежняя точная workspace граница.

**Acceptance Scenarios**:

1. **Given** enabled policy и явные global-scope approval, **When** authenticated
   client запрашивает registry в любом workspace, **Then** response содержит
   `assistedAutoStartPolicy.scope=all_workspaces`.
2. **Given** enabled policy без global-scope approval, **When** server стартует,
   **Then** configuration fails closed и не публикует policy.
3. **Given** global policy для двух workspace, **When** user или device меняется,
   **Then** `policyRef` остаётся scope/version-bound, а subject/device refs
   меняются и не содержат raw identifiers.
4. **Given** обычный scoped режим, **When** запрашивается другой workspace,
   **Then** policy отсутствует, как в Feature 145.

---

### User Story 2 - Defaults чистой установки (Priority: P1)

Как новый пользователь, я хочу, чтобы обнаружение встреч и автозапись для всех
verified native meeting apps были включены сразу после установки, чтобы не искать
скрытый переключатель для каждого приложения.

**Why this priority**: Пустой target allowlist на новой установке выглядит как
сломанная автозапись и делает результат зависимым от ручной настройки.

**Independent Test**: Создать settings store без файла, применить registry из
нескольких prompt-capable native targets и проверить detect-and-ask, enabled
target-scoped auto-record и полный набор target IDs. Повторное применение не
перезаписывает изменённый пользователем список.

**Acceptance Scenarios**:

1. **Given** settings file отсутствует, **When** первый verified registry
   загружен, **Then** detection mode включён, все prompt-capable native targets
   выбраны, а defaults помечены применёнными.
2. **Given** пользователь снял target или выключил detection, **When** registry
   обновился, **Then** его выбор не перезаписывается.
3. **Given** старая settings file без marker defaults, **When** приложение
   обновляется, **Then** старые явные настройки сохраняются без неожиданного
   включения новых targets.
4. **Given** policy отсутствует или acknowledgement не принят, **When** defaults
   применены, **Then** countdown и capture не стартуют автоматически.

---

### User Story 3 - Понятный prompt на первой встрече (Priority: P1)

Как новый пользователь, я хочу сразу увидеть обычный prompt о найденной встрече
и предстоящей записи, чтобы принять решение в контексте конкретного звонка, а не
искать отдельное блокирующее окно до начала работы.

**Why this priority**: Автоматическая запись требует текущего user/workspace/device
acknowledgement; его нельзя синтезировать из факта установки или выбора targets.

**Independent Test**: На чистой установке с active policy проверить появление
prompt без предварительного посещения settings, действия «Записать сейчас» и
«Пропустить», а также отдельное включение «Всегда писать это приложение».

**Acceptance Scenarios**:

1. **Given** active policy и новая установка без acknowledgement, **When** verified
   target стабилен, **Then** обычный prompt появляется автоматически без отдельного
   consent-экрана до detection.
2. **Given** prompt показан без acknowledgement, **When** пользователь нажимает
   «Записать сейчас», **Then** текущая запись может стартовать как явное ручное
   действие, но acknowledgement для будущего auto-start не создаётся.
3. **Given** prompt показан без acknowledgement, **When** пользователь нажимает
   «Пропустить» или ничего не делает, **Then** запись не стартует автоматически.
4. **Given** пользователь отмечает «Всегда писать это приложение» и подтверждает
   prompt, **When** policy и gates действуют, **Then** создаётся exact acknowledgement
   и последующие timeout/saved-target starts проходят обычные gates Feature 193.
5. **Given** policy, workspace, device или acknowledgement version изменились,
   **When** registry обновился, **Then** старое acknowledgement не подходит и
   требуется новое явное решение в prompt/settings.

### Edge Cases

- Global flag включён без approval, с просроченными датами или с одновременным
  workspace ID; server остаётся fail closed.
- Policy response для global scope приходит при смене workspace: policy reference
  может быть общим, но subject/device binding обязан быть новым.
- Registry содержит browser/manual-only, blocked или diagnostic targets; defaults
  выбирают только verified native prompt-capable targets.
- Registry не загрузился на первом запуске: settings остаются безопасными, а
  defaults применяются после первой валидной remote/cache registry.
- Старая settings file не содержит новые Codable fields; миграция не меняет
  существующий пользовательский выбор.
- Пользователь закрыл consent без действия, обновил policy во время consent или
  вышел из аккаунта; acknowledgement не создаётся и assisted start блокируется.
- Два workspace используют один device: acknowledgement одного workspace не
  авторизует другой.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Server MUST preserve the existing exact workspace policy mode and
  MUST add an explicit `all_workspaces` scope flag; an absent workspace ID MUST
  NOT be interpreted as a wildcard.
- **FR-002**: Global scope MUST require an explicit operator approval flag,
  complete version/issued/expiry configuration and the existing internal notice
  mode; invalid combinations MUST fail closed at configuration validation.
- **FR-003**: A global policy response MUST bind `subjectRef` and `deviceRef` to
  the authenticated user, workspace and device, while `policyRef` binds only the
  global scope and policy version; raw identifiers MUST NOT be returned.
- **FR-004**: Registry schema MUST expose a validated `scope` value of
  `workspace` or `all_workspaces`, preserving decoding of older cached documents.
- **FR-005**: A new installation MUST default detection to `detect_and_ask` and,
  after a valid registry is available, select every verified native prompt-capable
  target and enable target-scoped auto-record.
- **FR-006**: Defaults MUST be applied at most once per installation and MUST NOT
  overwrite an explicit existing settings file; legacy files without the marker
  MUST be treated as already user-controlled.
- **FR-007**: Defaults MUST never create, copy or infer an assisted auto-start
  acknowledgement.
- **FR-008**: A new installation with an active policy and no acknowledgement MUST
  still show the normal target prompt; showing the prompt MUST NOT create an
  acknowledgement or promise an automatic timeout start.
- **FR-009**: «Записать сейчас» in a prompt without acknowledgement MAY start only
  the current recording as an explicit user action; it MUST NOT create a saved
  acknowledgement or enable future automatic starts.
- **FR-010**: «Всегда писать это приложение» combined with an explicit prompt
  action MAY create the exact existing user/workspace/device-bound acknowledgement;
  a failed save MUST leave future automatic starts blocked.
- **FR-011**: Existing Feature 193 gates MUST remain authoritative immediately
  before prompt timeout, saved-target start and capture: policy, acknowledgement,
  permissions, storage, active session, visible indicator and one-action Stop.
- **FR-012**: Target defaults and global policy MUST remain limited to verified
  native prompt-capable targets; browser/manual-only, unknown, media-playback and
  arbitrary-audio signals remain ineligible.
- **FR-013**: Manual Record/Stop MUST remain available under the existing workspace
  recording policy and MUST NOT depend on the assisted acknowledgement.
- **FR-014**: All diagnostics and prompt/acknowledgement state MUST remain metadata-only; no raw
  audio, transcript, cookie, token, credential, secret path or meeting content may
  be logged or persisted.
- **FR-015**: Production global enablement and public app rollout MUST remain
  separate approval-gated actions; this slice MUST NOT claim customer notice/legal
  readiness for external workspaces.

### Key Entities

- **Global Assisted Auto-Start Policy**: Versioned internal policy with explicit
  scope, issue/expiry, notice mode and operator approval.
- **Installation Defaults Marker**: Local state distinguishing a fresh install
  from an existing user-controlled settings file.
- **Prompt Decision**: A visible per-target meeting notice whose button, skip and
  timeout outcomes are tracked separately; it never silently becomes policy
  acknowledgement.
- **Verified Native Target Set**: Registry-derived IDs eligible for target-scoped
  auto-record; excludes browser/manual/unknown targets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With global scope enabled and approved, 100% of tested authenticated
  workspaces receive a policy, while scoped mode returns it only for the exact
  configured workspace.
- **SC-002**: 100% of invalid global configurations (missing approval, incomplete
  dates/versions, ambiguous workspace ID) fail before server readiness.
- **SC-003**: On a clean settings directory, all and only verified native
  prompt-capable registry targets are selected after the first valid registry;
  a second application never changes a user-edited selection.
- **SC-004**: 100% of fresh-install runs with no acknowledgement show a prompt and
  create zero automatic capture starts before an explicit prompt/settings action.
- **SC-005**: Prompt button, skip and timeout tests produce distinct truthful
  outcomes; only the explicit «Всегда писать» path can create acknowledgement.
- **SC-006**: Existing Feature 193 focused suites and new server/Swift tests pass;
  metadata safety scans find no forbidden content or credentials.
- **SC-007**: A separately built Dev app demonstrates first-run defaults and
  one-time consent without modifying `/Applications/GRAF.app`.

## Assumptions

- Feature 193 remains the owner of source lifecycle, observer recovery and the
  final capture readiness gate.
- The global operator approval is an internal-deployment attestation; external or
  customer notice/legal rollout requires a later approved feature.
- Existing authentication, target registry, settings store and native capture
  boundary are reused; no database migration or new runtime dependency is needed.
- Acknowledgement remains local to the current user/workspace/device and is never
  copied between workspaces.

## Out Of Scope

- Participant-facing notices, legal copy, customer workspace rollout or claims of
  external compliance.
- A global "record all system audio" switch or removal of the verified target
  allowlist.
- Browser extensions, Accessibility scraping, new audio engines, database tables,
  migrations, or changes to transcription/upload/retention/deletion.
- Automatic acknowledgement or silent consent on installation; the first prompt
  is a notice and user-control surface, not a hidden acceptance.
- Production deploy, Sparkle publication or replacement of the installed app in
  this implementation slice.
