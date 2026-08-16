# Feature Specification: Восстановление записи встречи и входа по email

**Feature Branch**: `codex/154-meeting-email-auth-regression`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Восстановить окно с таймером и автоматический старт/завершение записи встречи в macOS-приложении и исправить вход по email с подтверждением."

## Context And Product Decision

Feature 154 исправляет регрессию в уже существующих capture и email-code flows.
Она сохраняет system-audio-first capture, восьмисекундный prompt, target-scoped
автозапись, видимый indicator, one-action Stop и существующую workspace-policy
защиту. Нового audio engine, auth-протокола или обхода безопасности не вводится.

## User Scenarios & Testing

### User Story 1 - Вернуть prompt, таймер и автоматический старт встречи (Priority: P1)

Как пользователь macOS-приложения, я хочу снова видеть уведомление о найденной
встрече с восьмисекундным таймером, чтобы запись начиналась после таймера или
сразу по кнопке.

**Why this priority**: Без prompt пользователь не понимает, что встреча обнаружена,
а основной сценарий автоматической записи не запускается.

**Independent Test**: Синтетическое событие разрешённого meeting target при
действующей policy и acknowledgement показывает prompt, отображает оставшееся
время, запускает запись ровно один раз после 8 секунд и сохраняет причину старта.

**Acceptance Scenarios**:

1. **Given** verified native target активен и capture/policy gates разрешены,
   **When** detector проходит debounce, **Then** появляется отдельное видимое
   окно с текстом автоматического старта и отсчётом от 8 секунд.
2. **Given** prompt открыт, **When** пользователь нажимает «Записать сейчас»,
   **Then** запись стартует сразу с причиной `prompt_button`, а поздний timeout
   не создаёт второй session.
3. **Given** prompt открыт и все gates остаются действующими, **When** проходят
   8 секунд, **Then** запись автоматически стартует один раз с причиной
   `prompt_timeout`.
4. **Given** target имеет сохранённое target-scoped разрешение и действующую
   assisted policy, **When** target проходит detector debounce, **Then** prompt
   не нужен, запись стартует один раз с причиной `saved_target_policy`.

### User Story 2 - Корректно завершать запись после окончания встречи (Priority: P1)

Как пользователь, я хочу, чтобы запись завершалась после подтверждённого окончания
встречи, финализировала локальные артефакты и не продолжалась бесконечно.

**Why this priority**: Открытая после встречи запись создаёт риск лишнего захвата,
неполного финализирования и потери доверия к автоматическому режиму.

**Independent Test**: После активного synthetic target подать inactive event и
продвинуть controlled clock за существующий grace period; detector выдаёт end один
раз, общий capture stop вызывается один раз и финализация сохраняет текущий artifact.

**Acceptance Scenarios**:

1. **Given** detector-assisted session записывает активный verified target,
   **When** target остаётся inactive дольше grace period, **Then** app запрашивает
   stop для этой bundle ID и переводит session в существующий путь финализации.
2. **Given** end signal пришёл повторно или запись уже остановлена, **When** app
   обрабатывает событие, **Then** второй stop/finalization не запускается.
3. **Given** target закончил работу во время countdown, **When** countdown
   истекает, **Then** prompt отменяется и запись не стартует позднее.

### User Story 3 - Восстановить вход по email-коду (Priority: P1)

Как пользователь web-кабинета или embedded macOS cabinet, я хочу запросить
одноразовый код на email, ввести код из письма и попасть обратно в meetings,
чтобы авторизация завершалась в той же сессии.

**Why this priority**: Неработающий email login блокирует доступ к кабинету и
локальному приложению, даже если сам сервер доступен.

**Independent Test**: Запрос кода создаёт state, delivery получает код, verify
с тем же email/state устанавливает корректный session cookie и делает безопасный
redirect; неверный, истёкший или повторно использованный код остаётся отказом.

**Acceptance Scenarios**:

1. **Given** email принадлежит допустимой identity или разрешённому signup flow,
   **When** пользователь отправляет форму email, **Then** сервер сохраняет
   state-bound code flow и показывает экран подтверждения без раскрытия секрета в
   production.
2. **Given** пользователь вводит правильный код из письма в той же browser/WebKit
   сессии, **When** verify завершается, **Then** выставляется соответствующий
   session cookie и открывается безопасный `next` path.
3. **Given** код неверен, истёк, уже использован, email/state не совпадают или
   delivery недоступна, **When** пользователь повторяет действие, **Then** вход
   не создаёт сессию и показывает понятное восстановимое состояние.
4. **Given** локальный development profile явно включён и использует loopback,
   **When** пользователь входит тестовым локальным email-кодом, **Then** local
   fixed code разрешается только локальным сервером, а production flow остаётся
   случайным и email-delivery-backed.

## Edge Cases

- Registry или policy snapshot временно недоступны: capture не стартует без
  действующей assisted authorization, но detector не должен терять lifecycle
  cleanup и manual Record/Stop.
- Policy/acknowledgement изменились между показом prompt и timeout: повторная
  проверка блокирует старт с metadata-only причиной.
- Prompt закрыт, target исчез, app уходит в background или появилась другая
  запись: countdown отменяется и не выполняет поздний callback.
- Target end и stop callback приходят одновременно: stop/finalization idempotent.
- Email delivery временно не отвечает: state не должен выглядеть успешно
  отправленным; пользователь может запросить новый код после rate limit.
- Production cookie flags и local loopback cookie должны выбираться из request
  origin, без импорта browser cookies и legacy headers.

## Requirements

### Functional Requirements

- **FR-001**: System MUST preserve the Feature-124 verified target, visible
  eight-second countdown, immediate Start, Skip and target-scoped auto-record
  contract.
- **FR-002**: Detector preflight MUST allow the first prompt to be evaluated from
  capture readiness without silently requiring a prior assisted acknowledgement;
  automatic capture MUST still re-check the current workspace policy and
  acknowledgement immediately before start.
- **FR-003**: Prompt, timeout and saved-target starts MUST resolve once and carry
  distinct `prompt_button`, `prompt_timeout` and `saved_target_policy` evidence.
- **FR-004**: Verified target end MUST route through the existing stop and
  finalization path, scoped to the detector target, with no duplicate stop.
- **FR-005**: Existing visible recording indicator, one-action Stop, system-audio-
  first capture, storage readiness, permissions and fail-closed authorization MUST
  remain intact.
- **FR-006**: Email code start MUST bind normalized email, provider, workspace and
  opaque state; production delivery failures MUST not create a usable login.
- **FR-007**: Email code verify MUST accept only the matching unexpired pending
  state, issue the correct request-scoped cookie and use the existing safe return
  path resolver.
- **FR-008**: Embedded local macOS auth MUST use the same server email-code/session
  flow and WebKit session; no cookie copying, bypass header or second protocol is
  allowed.
- **FR-009**: Local fixed email code MUST remain gated by non-production,
  loopback-only local configuration; production must always use random code plus
  configured delivery.
- **FR-010**: Tests MUST cover timer boundary/cancellation, auto-start/end
  idempotency, policy re-check and email start/verify/error/cookie behavior.

### Key Entities

- **Detector-assisted start decision**: target, bundle, start reason, current
  policy/acknowledgement and capture readiness.
- **Capture session**: existing local session lifecycle with target evidence,
  visible state, stop and finalization artifacts.
- **Email callback state**: existing one-time provider-bound state containing
  hashed code, workspace, redirect and expiry.
- **Browser/WebKit session cookie**: existing request-selected authenticated
  session transport; cookie naming and Secure behavior must follow the origin.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In 100% of synthetic eligible prompt runs, the window is presented,
  shows 8 seconds, and timeout starts exactly one capture session at 8.000 seconds.
- **SC-002**: In 100% of synthetic target-end runs, one end event causes at most
  one stop/finalization and no recording remains active after the grace period.
- **SC-003**: Button, timeout and saved-target starts are distinguishable in 100%
  of metadata-only evidence checks.
- **SC-004**: Valid email code verification establishes a usable authenticated
  browser/WebKit session in 100% of focused integration scenarios.
- **SC-005**: Invalid, expired, replayed, mismatched and undeliverable email flows
  create zero authenticated sessions.
- **SC-006**: Production behavior remains unchanged when local-only flags are off,
  and no raw code, token, email secret or meeting content is added to committed
  evidence.

## Assumptions

- Feature 145 remains the authority for assisted-auto-start policy and evidence;
  this feature repairs its integration without removing fail-closed checks.
- The existing server email-code flow, Postal client, session model and WebKit
  navigation boundaries are reused.
- Local verification uses synthetic target metadata and local test identities;
  no private meeting audio or transcript is recorded into evidence.
- Production deployment, release publication and real external email delivery
  changes are out of scope for this branch.

## Out Of Scope

- New audio routing, virtual drivers, meeting heuristics or capture engines.
- Password auth, new OAuth providers, browser-cookie import or bypass tokens.
- Changes to transcription, upload, AI, retention, deletion or deployment.
- Public release/notarization/deployment without separate approval.
