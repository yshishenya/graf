# Feature Specification: Полный пакет записи для внешнего получателя

**Feature Branch**: `133-share-egress-access`

**Created**: 2026-07-27

**Status**: Draft

**Input**: User report: "По ссылке вижу «Воспроизведение временно недоступно». Нужно дать возможность воспроизвести и скачивать аудио, транскрипт и все отчёты."

**Risk / validation lane**: `high-risk-feature` — auth, privacy, storage egress and user-facing export behavior.

## Problem Statement

После принятия внешнего приглашения страница записи может открыться успешно,
но запросы из этой страницы на воспроизведение, скачивание и экспорт повторно
проверяют доступ в другом контексте. В результате получатель видит запись и
итоги, но не может воспользоваться уже выданным полным доступом.

## Scope And Non-Goals

Входит:

- полный `full_meeting` доступ внешнего получателя к доступному каноническому
  аудио через существующее серверное воспроизведение;
- скачивание аудио и текстовой расшифровки;
- скачивание текущих отчётов GRAF через существующий content-export поток:
  расшифровка, итоги и объединённый отчёт во всех форматах, которые сервер
  показывает для соответствующего типа отчёта;
- повторная проверка exact-recipient, grant scope, срока действия, revoke,
  удаления, политики артефактов и наличия объекта перед каждой выдачей;
- сохранение доступа получателя вне рабочей области владельца и сохранение
  ограничений `summary_only`;
- regression-проверки для playback, audio/transcript downloads и content
  exports после magic-link входа.

Не входит:

- новый публичный URL, signed URL или отдельная permission-модель;
- доступ к рабочей области, служебным данным, аудиту, внутренним storage keys
  или исходному неканоническому аудио;
- расширение `summary_only` до расшифровки или аудио;
- изменение сроков grant, формата писем, количества уведомлений или регистрации;
- новые форматы отчётов, новый генератор отчётов, миграции или зависимости;
- обход отзыва, истечения, удаления, RLS или политики артефактов.

## User Scenarios & Testing

### User Story 1 — Получатель использует полный пакет записи (Priority: P1)

Получатель внешнего приглашения после одноразового входа открывает страницу
записи и может прослушать доступное аудио, скачать аудио и расшифровку, а также
сохранить итоги, расшифровку или объединённый отчёт в предложенных форматах.

**Why this priority**: Это основная ценность приглашения с полным доступом;
страница без рабочего playback/export превращает корректно выданный grant в
неработающий пользовательский сценарий.

**Independent Test**: Синтетически принять приглашение `full_meeting`, открыть
shared page, выполнить server playback, audio download, transcript download и
по одному export для transcript и combined; проверить успешный ответ и
отсутствие workspace membership.

**Acceptance Scenarios**:

1. **Given** активный точный `full_meeting` grant и готовый canonical playback
   artifact, **When** получатель нажимает воспроизведение, **Then** сервер
   отдаёт аудио через существующий playback route, включая поддерживаемый Range.
2. **Given** тот же grant, **When** получатель скачивает аудио или расшифровку,
   **Then** сервер отдаёт соответствующий файл с attachment-заголовком.
3. **Given** тот же grant и готовые результаты, **When** получатель сохраняет
   итоги, расшифровку или объединённый отчёт, **Then** сервер отдаёт выбранный
   поддерживаемый формат без раскрытия внутренних метаданных.

### User Story 2 — Ограничения остаются действующими (Priority: P1)

Владелец может отозвать доступ, а срок, удаление и политика артефактов должны
останавливать выдачу независимо от того, какая именно кнопка была нажата.

**Why this priority**: Исправление egress не должно превращаться в обход
границ приватности или в повторно используемый bearer-доступ.

**Independent Test**: После успешного full-пакета отозвать grant и повторить
page, playback, downloads и export; для summary-only отдельно проверить, что
полный пакет не открывается.

**Acceptance Scenarios**:

1. **Given** revoke, истёкший grant, удаление или несовпадение получателя,
   **When** выполняется любой content egress запрос, **Then** доступ не
   выдаётся и не появляется новая сессия, membership или grant.
2. **Given** политика артефакта запрещает конкретный тип выдачи, **When**
   получатель запрашивает этот тип, **Then** сервер сохраняет fail-closed отказ,
   а разрешённые типы не меняют свою проверку.
3. **Given** `summary_only` grant, **When** получатель запрашивает аудио,
   расшифровку или полный экспорт, **Then** запрос остаётся недоступным.

## Edge Cases

- Повторный запрос playback с Range не должен терять proof получателя.
- Отзыв между открытием страницы и нажатием кнопки должен выигрывать гонку.
- Отсутствующий или устаревший canonical audio object остаётся честно
  недоступным; egress не возвращает исходный upload и не создаёт новый artifact.
- Если отчёт ещё не готов, интерфейс показывает текущую readiness-причину, а не
  обещает скачивание.
- API-клиент владельца, team member и admin не должен изменить поведение из-за
  нового optional proof-параметра.
- В audit и committed evidence не попадают текст встречи, raw audio, email,
  токены, signed URL или storage keys.

## Requirements

### Functional Requirements

- **FR-001**: Для активного exact-recipient `full_meeting` grant сервер MUST
  сохранять recipient proof до каждого общего egress-перепроверочного шага.
- **FR-002**: Full-получатель MUST иметь доступ к playback, audio download,
  transcript download и существующему content-export потоку при готовых
  артефактах и разрешающей политике.
- **FR-003**: Content exports MUST сохранить текущие scope/format compatibility
  и включать transcript, summary и combined без добавления нового формата.
- **FR-004**: Каждая выдача MUST независимо перепроверять точного получателя,
  active grant, `full_meeting`, expiry, revoke, deletion, policy, revision
  freshness и storage readiness там, где это применимо.
- **FR-005**: `summary_only` MUST NOT получить playback, audio/transcript
  download или full content export вследствие этого изменения.
- **FR-006**: Рабочая область владельца, workspace membership, audit, storage
  internals и исходные media objects MUST оставаться недоступными внешнему
  получателю.
- **FR-007**: Отказ из-за реально отсутствующего или неподготовленного
  артефакта MUST оставаться fail-closed и сообщаться существующим safe error
  контрактом.
- **FR-008**: Реализация MUST использовать существующий access/egress путь, не
  создавать обходной middleware, public link или параллельную ACL-модель.

## Success Criteria

- **SC-001**: Focused external full-invitation matrix успешно проходит для
  playback, audio download, transcript download, transcript export и combined
  export.
- **SC-002**: После revoke 100% повторенных shared egress запросов из матрицы
  получают отказ без выдачи содержимого.
- **SC-003**: Summary-only regression сохраняет полный запрет аудио,
  расшифровки и full export.
- **SC-004**: Existing owner/team/admin egress tests и полный local CI проходят
  без изменения их access semantics.
- **SC-005**: В production log/audit review нет нового раскрытия private
  content или storage internals; evidence остаётся metadata-only.

## Assumptions And Clarifications

- Под «все отчёты» понимаются уже существующие пользовательские content exports:
  `transcript`, `summary`, `combined` и их текущие доступные форматы. Новые
  отчётные сущности в этот slice не добавляются.
- Playback использует существующий canonical review M4A и серверный route;
  отсутствие готового canonical artifact не исправляется выдачей raw upload.
- Страница приглашения уже является разрешённой поверхностью; задача —
  восстановить её downstream egress, а не изменить email/onboarding UX.
