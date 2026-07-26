# Feature Specification: Надёжное принятие invitation magic-link

**Feature Branch**: `129-share-magic-rls`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "Исправить HTTP 500 в external invitation magic-link flow: не допускать autoflush auth-аудита в неверном RLS workspace context, добавить regression на первый вход и удалить лишнюю/дублирующую обработку, если она найдена"

## Problem Statement

После открытия внешней invitation-ссылки новым получателем GRAF иногда отвечает
HTTP 500 вместо разрешённой страницы встречи. Ошибка возникает в промежутке
между созданием личного аккаунта/сессии и принятием приглашения. Для пользователя
это выглядит как сломанная ссылка, хотя invitation и аккаунт должны обрабатываться
одним безопасным сценарием.

Нужно сделать первый вход по invitation предсказуемым, сохранить tenant/RLS
изоляцию аудита и не возвращать внутреннюю ошибку пользователю. Вторичная
account-created notification не должна ломать уже успешно выданный доступ.

## Scope And Non-Goals

Входит:

- исправление HTTP 500 в первом magic-link входе внешнего invitation;
- сохранение корректной записи auth-аудита в том workspace, к которому она
  относится;
- regression-проверка нового получателя, существующего получателя, повторного
  открытия, expiry/revoke и недоступной notification-ветки;
- проверка соседних callers общего rate-limit/audit/context потока;
- удаление только недостижимого или дублирующего кода, если это подтверждено
  callers и тестами;
- release/deploy evidence для production hotfix.

Не входит:

- изменение scope, срока действия, recipient-bound identity или egress-политик;
- автоматическое добавление получателя в рабочую область;
- изменение формата письма, summary/transcript, playback или download;
- ослабление RLS, отключение аудита, обход CSRF или перенос секретов в код;
- новый общий механизм авторизации вне invitation flow.

## Clarifications

### Session 2026-07-26

- Production logs show the failure occurs before the committed-access
  notification branch: a pending auth-audit row is autoflushed after the
  session switches from the recipient personal workspace to the invited
  meeting workspace. The fix must preserve RLS and close this transaction
  boundary rather than weaken the policy.
- The default implementation assumption is a flush while the personal
  workspace context is active; a separate transaction is only needed if the
  focused regression proves that flush is insufficient.
- "Удалить лишний код" is bounded to duplicate/dead handling discovered in the
  invitation path; no unrelated cleanup is included in this hotfix.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Получатель открывает приглашение без 500 (Priority: P1)

Новый получатель открывает одноразовую ссылку из письма и получает разрешённую
страницу итогов или записи. Личный аккаунт и браузерная сессия создаются только
внутри явного continuation-действия, а внутренняя ошибка RLS не показывается как
HTTP 500.

**Why this priority**: Сейчас основной customer-facing сценарий блокируется
после отправки рабочей ссылки и разрушает доверие к приглашению.

**Independent Test**: В синтетическом окружении создать invitation для адреса
без существующей GRAF identity, открыть ссылку и проверить успешный разрешённый
результат, один auth-аудит personal workspace и отсутствие 500.

**Acceptance Scenarios**:

1. **Given** адрес приглашения ещё не связан с GRAF identity, **When** получатель
   открывает одноразовую ссылку, **Then** создаются personal account/session,
   invitation принимается, и браузер получает разрешённый результат без HTTP 500.
2. **Given** в процессе есть записи для personal workspace и исходного
   workspace встречи, **When** выполняются запросы после переключения контекста,
   **Then** каждая запись сохраняется только при совпадении с активным RLS
   контекстом и не вызывает autoflush-ошибку.
3. **Given** account-created notification недоступна после commit, **When** доступ
   уже принят, **Then** результат остаётся успешным, а notification получает
   честный bounded failure status.

### User Story 2 - Повторный и существующий получатель сохраняют безопасное поведение (Priority: P1)

Получатель с уже существующей identity или повторно открывающий ссылку получает
только тот же recipient-bound результат, который разрешён текущим grant. Повторная
обработка не создаёт новый аккаунт, grant или лишние audit rows.

**Why this priority**: Исправление первого входа не должно открыть повторное
использование токена или изменить защиту от replay/revoke.

**Independent Test**: Прогнать accepted invitation для существующего пользователя,
повторить continuation, затем проверить replay, wrong recipient, expiry и revoke.

**Acceptance Scenarios**:

1. **Given** identity и personal session уже существуют, **When** открывается
   действующая ссылка, **Then** выдаётся разрешённый результат без второго аккаунта
   и без обхода exact-recipient проверки.
2. **Given** continuation уже использован, **When** ссылка отправляется повторно,
   **Then** сервер возвращает существующий безопасный not-found/expired результат,
   а не новую сессию или grant.
3. **Given** invitation отозван, истёк или открыт другой identity, **When**
   выполняется continuation, **Then** доступ остаётся закрыт и внутренние данные
   встречи не раскрываются.

### User Story 3 - Сопровождение может доказать исправление без утечки данных (Priority: P2)

Команда может проверить, что production error был устранён, не сохраняя в
evidence token, email, аудио, transcript или содержимое встречи.

**Why this priority**: Auth/RLS regression требует проверяемого release evidence,
но production logs и документы должны оставаться metadata-only.

**Independent Test**: Запустить focused contract/integration matrix, затем
production smoke/health и проверить отсутствие raw invitation material в
выходных evidence-файлах.

**Acceptance Scenarios**:

1. **Given** synthetic first-entry matrix завершён, **When** формируется evidence,
   **Then** в нём есть статусы, counts, release SHA и error class без bearer token,
   email, transcript или signed URL.
2. **Given** общий audit/rate-limit helper используется несколькими callers,
   **When** regression прогоняется, **Then** соседние share/auth paths проходят
   без ослабления RLS и без нового duplicate helper.

### Edge Cases

- Пользователь уже существует, но personal workspace или device ещё создаётся.
- Один SQLAlchemy session содержит pending audit rows перед сменой tenant context.
- Rate-limit запрос выполняется первым после переключения контекста и вызывает
  autoflush.
- Notification workflow, Temporal или его bookkeeping недоступны после commit.
- Invitation просрочен, отозван, удалён или continuation nonce повторно применён.
- JavaScript выключен: остаётся существующая fallback-кнопка без побочного GET.
- Production database остаётся на текущем migration head; hotfix не ослабляет
  policy и не требует destructive data repair.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Система MUST завершать действующий first-entry invitation flow
  разрешённым результатом или контролируемым доменным 4xx, но не HTTP 500 из-за
  смены tenant/RLS context.
- **FR-002**: Auth-аудит MUST сохраняться в workspace, к которому относится
  событие, до переключения на другой workspace context либо в отдельной явно
  проверенной транзакционной границе.
- **FR-003**: RLS MUST оставаться включённым и принудительным; исправление MUST
  NOT добавлять broad bypass, maintenance role, отключение policy или raw SQL
  исключение для пользовательского пути.
- **FR-004**: Account/session/grant/continuation semantics MUST сохранять exact
  recipient, expiry, revoke, deletion, CSRF и replay protections.
- **FR-005**: После успешного commit failure вторичной account-created
  notification MUST NOT менять уже возвращаемый результат доступа на HTTP 500;
  её статус MUST оставаться честным и bounded.
- **FR-006**: Общий rate-limit/audit/context код MUST быть проверен по всем
  callers; удаление или объединение лишнего кода допустимо только при сохранении
  поведения каждого caller.
- **FR-007**: Regression suite MUST покрывать новый аккаунт, существующий аккаунт,
  replay, wrong recipient, expiry/revoke, no-JS fallback и notification failure.
- **FR-008**: Release evidence MUST содержать только metadata-only результаты,
  достаточные для связывания теста, commit, production SHA и health/smoke.

### Key Entities

- **Auth audit event**: событие входа/identity, принадлежащее конкретному
  workspace и user context.
- **Invitation continuation**: одноразовое server-side состояние, связывающее
  безопасный GET с явным POST continuation.
- **Recipient-bound grant**: ограниченный доступ к meeting artifacts, не создающий
  membership в исходном workspace.
- **Tenant/RLS context**: активная область workspace/user/device, определяющая
  допустимые чтение и запись в пользовательской транзакции.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% synthetic first-entry invitation cases завершаются доменным
  успехом или ожидаемым 4xx; ни один не завершается неожиданным HTTP 500.
- **SC-002**: В regression matrix есть минимум один случай с pending audit row и
  сменой workspace context; он проходит без RLS violation.
- **SC-003**: Existing-account, replay, wrong-recipient, expiry/revoke и
  notification-failure сценарии сохраняют текущие ожидаемые результаты.
- **SC-004**: Focused checks и полный repository CI проходят до merge; production
  deploy на immutable release SHA подтверждается backup/restore, smoke и live/ready.
- **SC-005**: В committed evidence и release artifacts нет raw invitation token,
  email, audio, transcript, signed URL или credential.

## Assumptions

- Существующий CSRF-bound POST continuation остаётся единственной точкой
  побочного эффекта для anonymous invitation link.
- Текущие RLS policies и migration head являются источником истины; schema
  migration не нужна, если проблема решается корректной транзакционной границей.
- Production hotfix выпускается через обычный Spec Kit, GitHub PR, immutable
  CalVer release и guarded deployment gate.
- Удаление лишнего кода ограничено этим flow и выполняется только после поиска
  всех callers и focused regression.
