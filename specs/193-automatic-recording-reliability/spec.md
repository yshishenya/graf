# Feature Specification: Надёжность автоматической записи

**Feature Branch**: `193-automatic-recording-reliability`

**Created**: 2026-08-23

**Status**: Draft

**Input**: User description: "Не всегда запускается автоматическая запись. В одних и тех же приложениях иногда запускается, а иногда нет. Провести полный анализ от начала до конца, найти причины, решение и исправить так, чтобы всё работало."

## Context And Product Decision

Feature 124 сохраняет пользовательский контракт: для подтверждённого native-приложения GRAF показывает восьмисекундный countdown с немедленным стартом, пропуском и выбором «Всегда писать это приложение»; по истечении countdown запись начинается автоматически. Feature 145 требует действующие workspace policy и acknowledgement перед любым countdown или автоматическим стартом.

Текущая реализация нарушает этот контракт несколькими независимыми способами: она может обещать countdown без действующей авторизации, объединяет независимые системные сигналы в одно состояние, одноразово поглощает временно отклонённые события, не гарантирует восстановление потока после завершения или wake и может сохранять устаревшую native auth-сессию после изменения web-сессии. Эта feature исправляет единый путь от входного сигнала до старта, остановки и диагностического результата, не расширяя перечень разрешённых целей и не ослабляя capture/privacy gates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Авторизованный автозапуск без ложных обещаний (Priority: P1)

Как пользователь GRAF, я хочу видеть countdown и обещание автоматического старта только тогда, когда текущая workspace policy и моё acknowledgement реально разрешают его, чтобы встреча либо надёжно начала записываться, либо заранее показала понятную причину блокировки.

**Why this priority**: Сейчас интерфейс может показать, что запись начнётся автоматически, а затем молча отменить старт из-за gate, который не проверялся при показе prompt.

**Independent Test**: Для одного verified target проверить действующую, отсутствующую, просроченную, обновлённую и отозванную policy/acknowledgement. Countdown появляется только при действующей точной паре; безопасный путь стартует один раз, остальные не обещают старт и показывают metadata-only blocker.

**Acceptance Scenarios**:

1. **Given** verified target активен, policy действует и exact acknowledgement сохранён, **When** target стабилен в течение debounce, **Then** GRAF показывает разрешённый prompt/countdown или применяет сохранённое target-разрешение и начинает запись ровно один раз.
2. **Given** policy или acknowledgement отсутствуют, просрочены, отозваны или не совпадают, **When** verified target обнаружен, **Then** GRAF не показывает активный countdown с обещанием старта и не начинает запись автоматически.
3. **Given** policy или readiness изменились во время countdown, **When** countdown истекает, **Then** GRAF повторно проверяет текущее состояние, блокирует небезопасный старт и показывает понятный результат.
4. **Given** пользователь нажимает «Записать сейчас», **When** ручной detector-assisted старт разрешён текущей recording policy, **Then** причина старта остаётся `prompt_button` и не подменяется автоматической причиной.
5. **Given** автоматический старт временно заблокирован переходным состоянием, **When** blocker исчезает, пока та же встреча активна, **Then** кандидат оценивается повторно без необходимости завершать и заново открывать встречу.

---

### User Story 2 - Стабильное определение одной встречи по всем системным сигналам (Priority: P1)

Как пользователь, я хочу, чтобы одна и та же встреча определялась одинаково независимо от порядка системных событий, запуска GRAF во время уже идущего звонка, sleep/wake или краткого сбоя наблюдателя.

**Why this priority**: Независимые источники активности могут приходить в разном порядке. Потеря одного события сейчас способна отменить другой активный источник, преждевременно остановить запись или навсегда заблокировать следующую встречу того же приложения.

**Independent Test**: В синтетической последовательности переставить местами start/end от всех поддерживаемых источников, завершить и восстановить наблюдатель, выполнить wake и начать GRAF во время активной встречи. Во всех вариантах кандидат имеет одинаковый жизненный цикл и не создаёт дублирующую запись.

**Acceptance Scenarios**:

1. **Given** два независимых источника подтверждают один bundle ID, **When** один источник становится inactive, а второй остаётся active, **Then** встреча остаётся активной и запись не останавливается.
2. **Given** все источники одного bundle ID стали inactive, **When** истекает end grace period, **Then** кандидат завершается ровно один раз и detector разрешает новую последующую встречу того же приложения.
3. **Given** поток системных событий завершился неожиданно, **When** GRAF продолжает работать, **Then** наблюдение автоматически восстанавливается с ограниченной задержкой и без второго параллельного потока.
4. **Given** Mac вышел из sleep, **When** GRAF получает wake, **Then** наблюдение и текущий snapshot обновляются, а устаревшее detector-состояние не блокирует новую встречу.
5. **Given** GRAF запущен или наблюдатель восстановлен во время уже активного звонка, **When** доступен текущий системный snapshot, **Then** verified target проходит обычный debounce и может запустить разрешённый prompt/autostart без необходимости переподключать микрофон.

---

### User Story 3 - Единая web/native auth-сессия и свежая policy (Priority: P1)

Как авторизованный пользователь, я хочу, чтобы native-запросы GRAF использовали ту же актуальную сессию, что и встроенный web-кабинет, чтобы target registry и policy не оставались в старом cache из-за скрытой устаревшей cookie.

**Why this priority**: Web-кабинет может быть авторизован, пока native API получает `401`; тогда клиент не видит актуальную policy и автозапуск остаётся недоступным или ведёт себя по старому cache.

**Independent Test**: Последовательно выполнить login, замену сессии, logout и повторный login с cookies одинакового имени и разной областью. Native-запрос всегда выбирает актуальную same-origin cookie, удаляет отсутствующую в web-хранилище сессию и после восстановления получает свежий registry.

**Acceptance Scenarios**:

1. **Given** web-хранилище содержит новую auth cookie, а native-хранилище — старую, **When** bridge синхронизирует сессию, **Then** native-хранилище больше не может выбрать старое значение для этого origin.
2. **Given** пользователь вышел и web-хранилище больше не содержит auth cookie, **When** bridge синхронизирует сессию, **Then** соответствующая native cookie удаляется и не продолжает отправляться скрытно.
3. **Given** существует несколько cookies одного имени, **When** native-клиент строит same-origin запрос, **Then** он детерминированно выбирает применимую cookie с наиболее специфичной областью и игнорирует пустые, просроченные или неприменимые значения.
4. **Given** web/native session восстановлена, **When** registry refresh повторяется, **Then** актуальный registry и policy заменяют устаревший cache, а UI обновляет доступность acknowledgement.
5. **Given** auth или registry всё ещё недоступны, **When** detector видит встречу, **Then** assisted start остаётся fail closed, ручная запись и Stop сохраняются, а пользователь видит честное состояние без утечки session value.

---

### User Story 4 - Диагностика полного пути и защита от регрессии (Priority: P2)

Как оператор и reviewer, я хочу по безопасным локальным событиям понять, на каком шаге кандидат был обнаружен, разрешён, отложен, отклонён, запущен или завершён, чтобы следующий сбой не требовал догадок и ручного поиска по несвязанным логам.

**Why this priority**: Текущие логи показывают отдельные prompt-события, но не доказывают входные source transitions, detector decision, consumer rejection, stream lifecycle и итог автоматического старта.

**Independent Test**: Прогнать положительные и отрицательные синтетические сценарии и собрать diagnostic-safe журнал. Для каждого candidate ID восстанавливается последовательность от source event до start/stop outcome без raw audio, meeting content, transcript или credentials.

**Acceptance Scenarios**:

1. **Given** системный source transition получен, **When** detector обновляет кандидата, **Then** журнал содержит только source kind, bundle ID, state, candidate state и timestamp/result code.
2. **Given** trigger не принят из-за prompt, transition, storage, permissions, auth или policy, **When** consumer его отклоняет, **Then** журнал содержит стабильный blocker и признак retryability.
3. **Given** stream завершён или восстановлен, **When** lifecycle меняется, **Then** журнал различает requested stop, unexpected finish, retry и successful restart.
4. **Given** запись стартовала или не стартовала, **When** попытка завершена, **Then** журнал различает `prompt_button`, `prompt_timeout`, `saved_target_policy`, blocker и фактический capture result.
5. **Given** диагностические данные экспортируются, **When** выполняется safety scan, **Then** в них отсутствуют raw audio, transcript text, meeting title/content, cookies, tokens, credentials, signed URLs и live secret paths.

### Edge Cases

- AudioHAL и sensor-indicator сообщают active/inactive в противоположном порядке или повторяют одинаковое состояние.
- Один source никогда не прислал end, затем поток завершился, Mac ушёл в sleep или приложение было перезапущено.
- Кандидат был временно заблокирован активным prompt другого target, началом/остановкой записи, критическим storage или обновлением policy.
- Start был запрошен, но capture не принял первый кадр; встреча остаётся активной и readiness позднее восстанавливается.
- Пользователь пропустил prompt или вручную остановил detector-assisted запись; тот же непрерывный кандидат не должен автоматически перезапускаться.
- Policy обновилась без изменения registry target list и должна участвовать в cache identity.
- Web cookie удалена, заменена, просрочена или имеет тот же name на другом origin/path.
- Native API вернул `401` во время перехода между login/logout; повторная синхронизация не должна создать цикл с устаревшей cookie.
- GRAF стартовал во время долгой уже идущей встречи, для которой start event появился до запуска приложения.
- Два verified приложения активны одновременно; каждый кандидат остаётся независимым, но может существовать только одна активная запись.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST preserve the Feature-124/145 contract: verified native target allowlist, reversible per-target permission, visible eight-second countdown, immediate start, Skip, automatic expiry start, persistent capture indicator and one-action Stop.
- **FR-002**: An active countdown that promises automatic recording and every saved-target automatic start MUST require a current authenticated non-expired workspace policy plus an exact current device-local acknowledgement.
- **FR-003**: Missing, stale, revoked, malformed, future or expired policy/acknowledgement MUST block the countdown and automatic start before the UI promises that recording will begin.
- **FR-004**: The system MUST re-evaluate target activity, policy, acknowledgement, permissions, storage, active-session state, indicator and Stop readiness immediately before every detector-assisted start.
- **FR-005**: Manual Record and Stop MUST remain available under the existing recording policy and MUST NOT require assisted-auto-start acknowledgement.
- **FR-006**: The detector MUST preserve independent active/inactive state for every supported signal source and MUST keep a bundle active while any current source remains active.
- **FR-007**: A meeting candidate MUST end only after all current sources are inactive and the existing end grace period has elapsed.
- **FR-008**: Reordered, duplicated or delayed source transitions MUST produce the same candidate lifecycle and MUST NOT create duplicate prompt/start/stop outcomes.
- **FR-009**: A trigger rejected only because of a temporary readiness, transition, policy/cache/auth or competing-prompt condition MUST remain eligible for re-evaluation while the candidate is active.
- **FR-010**: A trigger accepted by the prompt/start consumer, a user Skip, or a manual Stop MUST suppress duplicate handling for the same continuous candidate until its end boundary.
- **FR-011**: A failed automatic start MUST be classified as retryable or terminal; only retryable failures MAY be reconsidered during the same active candidate, and retries MUST remain single-flight.
- **FR-012**: Unexpected system-observer completion MUST recover automatically with bounded retry delay and MUST NOT leave a stale non-running task that blocks restart.
- **FR-013**: System wake MUST refresh or restart observation and MUST reconcile detector state before new automatic decisions.
- **FR-014**: Observer stop, app termination and a deliberate settings lifecycle stop MUST cancel pending work and reset stale detector state without restarting unexpectedly.
- **FR-015**: App/observer startup during an already active meeting MUST obtain a current bounded system snapshot when available and feed it through the same debounce, allowlist and policy gates as live events.
- **FR-016**: Auto-stop MUST occur at most once and only for a recording tied to the ended bundle after all its sources satisfy the end boundary.
- **FR-017**: Web-to-native session synchronization MUST reconcile additions, replacements and removals of the configured same-origin auth cookie.
- **FR-018**: If the web cookie is absent after logout, the corresponding native cookie MUST be removed and MUST NOT continue authorizing native API calls.
- **FR-019**: Native auth selection MUST be deterministic for multiple same-name cookies and MUST ignore empty, expired, secure-incompatible, domain-incompatible and path-incompatible values.
- **FR-020**: Session values MUST NOT be logged, persisted into diagnostics or forwarded as a general Cookie header; the existing dedicated native auth header boundary MUST remain.
- **FR-021**: A recovered native session MUST trigger or permit a fresh target-registry request so a current policy can replace stale cache without restarting GRAF.
- **FR-022**: Registry/auth failure MUST fail closed for assisted start while preserving manual recording, visible active capture truth and one-action Stop.
- **FR-023**: The system MUST emit bounded metadata-only diagnostics for source transitions, candidate decisions, trigger acceptance/rejection, retryability, observer lifecycle, registry/auth failure codes and final start/stop outcomes.
- **FR-024**: Diagnostics MUST NOT contain raw audio, transcript text, meeting title/content, cookies, tokens, credentials, signed URLs, passwords or live secret paths.
- **FR-025**: Unknown, browser/manual-only, diagnostic-only, suppressed, media-playback and arbitrary-audio signals MUST remain ineligible for prompt countdown and automatic start.
- **FR-026**: Existing selected target IDs MUST survive policy/auth recovery and MUST NOT themselves count as policy or acknowledgement.
- **FR-027**: The fix MUST reuse the current system-audio-first capture path, policy schema, settings store, registry endpoint and native auth boundary without adding a new audio engine, database, endpoint or third-party runtime dependency.
- **FR-028**: Production policy enablement, deployment, public package publication and release creation MUST remain separate approval-gated actions with exact runtime and installed-app verification.

### Key Entities

- **Signal Source State**: Current active/inactive ownership for one bundle and one system evidence source, with observation time but no meeting content.
- **Meeting Candidate Lifecycle**: Debounced continuous interval for one verified target, including active sources, handling state, retry classification and end boundary.
- **Detector Trigger Outcome**: Prompt, saved-target start, candidate observation or suppression plus whether the consumer accepted it and whether retry is allowed.
- **Observer Lifecycle**: Started, deliberately stopped, unexpectedly finished, retry scheduled and restored states for the system event stream and current snapshot.
- **Native Auth Cookie Reconciliation**: Same-origin comparison between web and native cookie stores, including replacement/removal actions without exposing values.
- **Automatic Start Evidence**: Metadata-only result tying the candidate, policy/ack state, start reason, readiness decision and capture outcome together.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of tested prompt-timeout and saved-target paths without a valid exact policy/ack pair are blocked before countdown promise or capture start.
- **SC-002**: All tested permutations of two independent source start/end orders yield one identical candidate lifecycle, zero premature ends and zero duplicate starts.
- **SC-003**: A temporary blocker that clears during an active candidate is re-evaluated within 2 seconds; a handled, skipped or manually stopped candidate does not restart before a real end boundary.
- **SC-004**: An unexpected observer finish or system wake restores observation within 5 seconds without parallel duplicate observers.
- **SC-005**: Startup during an active verified call produces a candidate within snapshot completion plus the configured debounce when current platform evidence is available.
- **SC-006**: Login replacement, logout and re-login tests produce zero native requests with the prior session after reconciliation.
- **SC-007**: 100% of tested native registry refreshes after auth recovery use the current session and update or truthfully reject the policy/cache result.
- **SC-008**: Every synthetic positive/negative path can be reconstructed from bounded metadata-only events, and safety scans find zero forbidden content or credential values.
- **SC-009**: Focused macOS suites, server contract tests, Spec Kit quickstart scenarios and the full local CI gate pass without new runtime dependencies.
- **SC-010**: A separately built GRAF Dev app demonstrates policy-gated settings, observer recovery and at least one deterministic end-to-end synthetic trigger-to-start/stop path without replacing `/Applications/GRAF.app`.

## Assumptions

- Feature 124 remains authoritative for prompt/countdown UX; Feature 145 remains authoritative for policy, acknowledgement and truthful start reason.
- Current native apps only are in automatic-start scope; browser expansion is not part of this fix.
- A bounded current-state snapshot may rely on platform evidence already available to the app; absence of trustworthy snapshot evidence remains fail closed rather than guessed.
- Transient retry never overrides Skip, manual Stop, active capture, policy, permissions, storage, indicator or one-action Stop gates.
- Existing production defaults remain disabled until a separate approved release/deploy step provides workspace ID, policy/ack versions, validity interval and installed-app evidence.

## Out Of Scope

- Enabling automatic recording for external/customer workspaces.
- Adding browser extensions, window-title monitoring, Accessibility scraping or network heuristics.
- Changing recording formats, AEC, transcription, upload, AI, retention or deletion behavior.
- Reintroducing the removed virtual-device/separate-routing architecture.
- Committing, deploying, releasing or replacing the installed production app without separate explicit approval.
