# Feature Specification: Авторизация и доказательства автозаписи

**Feature Branch**: `145-assisted-autostart-hardening`

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Сохранить восьмисекундный таймер и автозапись Feature 124, но сделать путь правильным: реально проверять workspace-политику и подтверждение пользователя, честно фиксировать причину старта, учитывать storage readiness и защищать поведение полноценными тестами. Внешних пользователей пока нет."

## Context And Product Decision

Feature 124 остаётся владельцем пользовательского контракта: для подтверждённого native-приложения prompt показывает восьмисекундный countdown, «Записать сейчас», «Пропустить» и «Всегда писать это приложение», а по окончании countdown запись стартует автоматически. Эта feature не удаляет и не ослабляет такой контракт.

Текущая реализация не может достоверно доказать действующую workspace-политику, принятие пользователем правил, реальную готовность локального хранилища и точную причину старта. Feature 145 закрывает эти разрывы до появления внешних пользователей. Она не расширяет автозапись на browser targets, неизвестные приложения, произвольный системный звук или participant-facing rollout.

## User Scenarios & Testing

### User Story 1 - Разрешать автозапуск только после явной авторизации (Priority: P1)

Как внутренний пользователь GRAF, я хочу один раз принять актуальные правила ассистированной автозаписи и работать только в workspace, где такая функция явно разрешена, чтобы таймер сохранял удобство без несанкционированного старта.

**Why this priority**: Без реальной workspace-политики и versioned-подтверждения приложение не может доказать право начать чувствительный capture-процесс.

**Independent Test**: Для одного и того же verified target последовательно проверить отсутствующую, действующую, отозванную и просроченную авторизацию. Countdown и автоматический старт допустимы только при действующей политике и принятой пользователем актуальной версии правил; ручная запись остаётся доступной согласно workspace-политике.

**Acceptance Scenarios**:

1. **Given** внутренний workspace явно разрешает assisted auto-start и пользователь принял текущую версию правил, **When** verified target уверенно обнаружен, **Then** Feature-124 prompt показывает восьмисекундный countdown и может автоматически начать запись.
2. **Given** workspace-политика отсутствует, запрещает auto-start или истекла, **When** detector видит встречу, **Then** GRAF может показать состояние обнаружения, но не показывает активный countdown и не начинает запись автоматически.
3. **Given** пользователь не принимал текущую версию правил или отозвал подтверждение, **When** detector видит встречу, **Then** автоматический старт заблокирован с понятным локальным объяснением и доступным переходом к настройке.
4. **Given** пользователь ранее выбрал приложения для постоянной автозаписи, **When** новая авторизация ещё не принята, **Then** выбранные target IDs сохраняются, но остаются неактивными до выполнения policy и acknowledgement gates.
5. **Given** политика или подтверждение отозваны во время восьмисекундного countdown, **When** countdown истекает, **Then** запись не начинается и фиксируется безопасная причина блокировки.

---

### User Story 2 - Честно объяснять каждую причину старта (Priority: P1)

Как пользователь и оператор продукта, я хочу отличать ручное нажатие, автоматический старт по таймеру и автозапуск по сохранённому правилу, чтобы аудит и диагностика не представляли автоматическое действие как ручное подтверждение.

**Why this priority**: Неверная attribution разрушает доказательства согласия, затрудняет расследование инцидентов и противоречит требованию auditable assisted auto-start.

**Independent Test**: Запустить одну синтетическую запись каждым из трёх способов и проверить, что локальная session/evidence-модель содержит различимые причины старта, реальную policy/acknowledgement версию и не утверждает, что пользователь нажал кнопку при timeout или saved-target старте.

**Acceptance Scenarios**:

1. **Given** пользователь нажал «Записать сейчас», **When** запись начинается, **Then** evidence указывает явное пользовательское действие в prompt.
2. **Given** пользователь ничего не нажал и countdown истёк, **When** запись начинается, **Then** evidence указывает автоматический старт по timeout и не маркирует его как нажатие пользователя.
3. **Given** target имеет сохранённое разрешение, **When** запись начинается без prompt, **Then** evidence указывает saved target policy как причину старта.
4. **Given** любой автоматический или ручной detector-assisted старт заблокирован, **When** создаётся диагностическое событие, **Then** оно сохраняет фактического инициатора, blocker, recovery action и действовавший policy snapshot без raw audio, transcript text, meeting content или credentials.
5. **Given** запись успешно началась, **When** оператор просматривает metadata-only evidence, **Then** он может определить workspace policy version, acknowledgement version/state, target, confirmation state, notice state, indicator state и наличие one-action Stop.

---

### User Story 3 - Повторно проверять реальные capture gates в момент старта (Priority: P1)

Как пользователь, я хочу, чтобы запись по таймеру не стартовала при недостатке места, изменившихся разрешениях, завершившейся встрече или другой активной записи, даже если prompt был допустим восемь секунд назад.

**Why this priority**: Countdown создаёт временное окно, в котором безопасность и готовность могут измениться.

**Independent Test**: Показать prompt при корректных начальных условиях, затем по одному изменить storage, policy, permissions, target activity, indicator/Stop readiness и active-session state до истечения countdown; каждый небезопасный вариант блокирует запись, а неизменный безопасный вариант стартует ровно один раз.

**Acceptance Scenarios**:

1. **Given** prompt уже показан, **When** реальный storage risk становится критическим до старта, **Then** запись не начинается и пользователь видит recovery action.
2. **Given** prompt уже показан, **When** target перестаёт быть активным или prompt закрывается, **Then** timer отменяется и не может позднее начать запись.
3. **Given** ручная или другая detector-assisted запись началась во время countdown, **When** countdown истекает, **Then** второй session не создаётся.
4. **Given** все gates остаются действующими, **When** истекают восемь секунд, **Then** запись начинается один раз с локальным индикатором до первого принятого записанного кадра и one-action Stop.
5. **Given** пользователь использует VoiceOver или не различает цветовой progress, **When** prompt открыт, **Then** оставшееся время и будущий автоматический старт доступны текстом и через accessibility-значение.

---

### User Story 4 - Не допустить повторной регрессии (Priority: P2)

Как reviewer, я хочу поведенческие проверки таймера, авторизации и evidence вместо одних поисков строк в исходнике, чтобы будущий рефакторинг не оставил формально зелёный, но небезопасный путь.

**Why this priority**: Существующие source-contract assertions подтверждают наличие символов, но не доказывают порядок событий и fail-closed поведение.

**Independent Test**: Запустить focused suite с управляемым временем и синтетическими policy/storage/target состояниями; тесты падают при повторном старте, ложном initiator, пропущенном re-check или удалении Feature-124 countdown.

**Acceptance Scenarios**:

1. **Given** управляемые часы, **When** проходит 7.999 секунды, **Then** automatic start ещё не вызван; после восьми секунд он вызван ровно один раз при действующих gates.
2. **Given** Start, Skip, disappearance и policy revocation происходят до timeout, **When** время продвигается дальше восьми секунд, **Then** ни один отменённый путь не вызывает поздний старт.
3. **Given** три разрешённых причины detector-assisted старта, **When** suite проверяет evidence, **Then** каждая причина имеет отдельную стабильную классификацию.
4. **Given** unknown, browser/manual-only, media playback или diagnostic-only signal, **When** detector обрабатывает его, **Then** новый hardening не расширяет prompt или auto-start eligibility.

### Edge Cases

- Политика загрузилась после запуска приложения, но до появления verified candidate: используется только целая, аутентифицированная и неистёкшая версия.
- Политика обновилась во время countdown: перед стартом применяется новая версия; запрет или несовместимая версия блокируют старт.
- Сервер недоступен: новая assisted auto-start запись разрешена только по последнему аутентифицированному snapshot, который ещё не истёк и явно разрешает внутренний workspace; иначе fail closed.
- Пользователь принял старую версию правил: после повышения требуемой версии автоматический старт блокируется до нового подтверждения.
- Существующие target-scoped настройки не удаляются при блокировке авторизации и не переносятся на другой target.
- Сбой сохранения acknowledgement не считается успешным принятием.
- Сбой сохранения evidence не должен скрывать активную запись или Stop, но обязан дать локальный diagnostic-safe failure state.
- Одновременные button и timeout события разрешаются один раз; проигравший путь не изменяет evidence.
- Manual Start не зависит от acknowledgement assisted auto-start, но по-прежнему подчиняется workspace recording policy и capture prerequisites.

## Requirements

### Functional Requirements

- **FR-001**: System MUST preserve the complete Feature-124 contract: verified native target allowlist, per-target reversible permission, visible eight-second countdown, automatic expiry start, immediate «Записать сейчас», «Пропустить» and «Всегда писать это приложение».
- **FR-002**: Assisted auto-start MUST require an authenticated, versioned, non-expired workspace policy that explicitly permits assisted automatic recording for the current internal workspace.
- **FR-003**: Assisted auto-start MUST require a device-local persisted acknowledgement by the authenticated user for the exact current device and acknowledgement version; missing, stale, failed-to-save or revoked acknowledgement MUST block automatic start.
- **FR-004**: Existing detection and target-scoped preferences MUST be preserved during migration but MUST NOT be treated as evidence of workspace authorization or user acknowledgement.
- **FR-005**: Missing, malformed, unauthenticated, incompatible, revoked or expired policy state MUST fail closed for new assisted auto-start while preserving truthful detection state, manual recording availability where permitted, active indicator and Stop.
- **FR-006**: The system MUST re-evaluate policy, acknowledgement, current target eligibility/activity, permissions, storage readiness, suppression, active-session state, visible indicator and one-action Stop immediately before every timeout or saved-target automatic start.
- **FR-007**: Storage readiness MUST use the actual current local disk/buffer risk decision and MUST NOT be represented by a constant healthy value.
- **FR-008**: Detector-assisted start MUST carry exactly one stable reason: `prompt_button`, `prompt_timeout` or `saved_target_policy`.
- **FR-009**: Scope approval and recording evidence MUST distinguish per-event user confirmation from prior policy/acknowledgement authorization and MUST NOT describe timeout or saved-target starts as a button confirmation.
- **FR-010**: Every detector-assisted attempt MUST preserve metadata-only evidence for policy snapshot identity/version/expiry, acknowledgement version/state, target identity, start reason, auto-start flag, confirmation state, notice state, capture-route/readiness result, indicator state, Stop availability, device identity and blocker/recovery result.
- **FR-011**: Policy, acknowledgement and start evidence MUST exclude raw audio, transcript text, meeting title/content, credentials, tokens, signed URLs and live secret paths.
- **FR-012**: The countdown MUST resolve at most once and MUST be cancelled by Start, Skip, prompt disappearance, target end, settings disablement, app termination or a competing active recording.
- **FR-013**: The prompt MUST expose the remaining countdown time and automatic-start consequence in visible text and accessibility semantics without relying on color or animation alone.
- **FR-014**: Unknown, unverified, browser/manual-only, diagnostic-only, suppressed, media-playback and arbitrary-audio signals MUST remain ineligible for prompt timeout and saved-target automatic start.
- **FR-015**: External/customer workspaces MUST remain ineligible for assisted auto-start in this feature; enabling them requires a separate notice/legal-policy rollout decision and validation slice.
- **FR-016**: Manual Record/Stop MUST remain available under the existing workspace recording policy and MUST NOT require assisted-auto-start acknowledgement.
- **FR-017**: Acceptance validation MUST deterministically cover timeout boundaries, cancellation races, policy changes, storage failures, duplicate triggers and evidence classification without waiting on real meetings.
- **FR-018**: Active capture MUST retain a persistent local visible indicator and one-action Stop before the first accepted recorded frame, independent of network availability.

### Key Entities

- **Assisted Auto-Start Policy Snapshot**: Authenticated workspace authorization with stable identity, version, scope, allowed state, issue/expiry times and notice classification.
- **User Acknowledgement**: Persisted decision by an authenticated user for an exact assisted-auto-start rules version, including acceptance/revocation state and timestamp.
- **Detector-Assisted Start Decision**: One attempt tied to target, start reason, current authorization/readiness result and single-resolution state.
- **Capture Evidence**: Metadata-only account of the applied policy, acknowledgement, start reason, confirmation state, readiness, indicator/Stop state and blocker outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of automatic-start attempts without a valid workspace policy and current user acknowledgement are blocked before capture begins.
- **SC-002**: In 100% of safe prompt scenarios, no automatic start occurs before 8.000 seconds and exactly one start occurs at expiry unless the prompt is resolved or a gate changes.
- **SC-003**: 100% of button, timeout and saved-target starts produce distinguishable, truthful start-reason and confirmation evidence.
- **SC-004**: 100% of tested policy revocation, acknowledgement revocation, critical storage, permission loss, target end, active-session conflict and indicator/Stop failure scenarios remain fail closed.
- **SC-005**: 100% of existing valid target IDs survive migration unchanged, while none become active without the new authorization gates.
- **SC-006**: VoiceOver and visual inspection both expose that recording will start automatically and the remaining whole-second countdown without relying on color alone.
- **SC-007**: Focused behavioral tests, capture/privacy checks and full local CI pass without new third-party runtime dependencies.
- **SC-008**: Synthetic evidence scans contain zero raw meeting content, audio, transcript text or credentials.

## Assumptions

- There are no external/customer users, so this feature may require existing internal users to acknowledge the new version before automatic recording resumes.
- Feature 124 remains the product owner of timer, prompt, per-target settings and automatic-start UX; Feature 145 only strengthens authorization, readiness and evidence.
- The current authenticated workspace/user identity and existing native registry are reused rather than duplicated.
- A last-known-good workspace policy may authorize offline start only until its explicit expiry; a missing or expired snapshot blocks new automatic starts.
- Internal MVP records that no participant-facing notice was used; this does not authorize future external/customer rollout.
- No new audio engine, capture path, detector heuristic or third-party dependency is needed.

## Out Of Scope

- Removing, shortening or making the Feature-124 countdown optional.
- Generalized detection or automatic recording for browsers, arbitrary applications, media or system audio.
- External/customer rollout, jurisdiction selection, participant-facing notice delivery or legal-policy exceptions.
- Reintroducing the removed virtual-driver/separate-routing implementation.
- Changing transcription, upload, AI, retention or deletion behavior.
- Production deployment, public package publication or release creation in this implementation slice without separate approval.
