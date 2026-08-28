# Feature Specification: API Healthcheck Budget

**Feature Branch**: `codex/209-api-healthcheck-budget`

**Created**: 2026-08-28

**Status**: Draft

**Input**: Production rollout `v2026.08.28.11` автоматически откатился: API
успешно запускался и отвечал `ready`, но текущая проверка прекращала ожидание
раньше фактического ответа и ложно помечала контейнер unhealthy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Не откатывать исправный API из-за слишком короткой проверки (Priority: P1)

Оператор выпускает проверенный релиз и ожидает, что штатно отвечающий API будет
признан готовым. Проверка должна дождаться ответа в пределах ограниченного
операционного бюджета, но по-прежнему блокировать зависший или неготовый API.

**Why this priority**: Ложный unhealthy останавливает весь guarded rollout и
не позволяет доставить исправление пользователям, хотя rollback сохраняет прод.

**Independent Test**: Конфигурационный контракт подтверждает согласованный
внутренний и внешний budget. Production smoke подтверждает успешный rollout без
ослабления `/ready` до простой liveness-проверки.

**Acceptance Scenarios**:

1. **Given** API возвращает успешную готовность примерно за 3.5 секунды,
   **When** healthcheck запускается, **Then** ответ принимается и контейнер
   становится healthy.
2. **Given** API не отвечает в пределах ограниченного бюджета или возвращает
   неготовность, **When** healthcheck запускается, **Then** контейнер остаётся
   unhealthy и rollout блокируется.
3. **Given** production rollout не проходит другой обязательный gate, **When**
   выполняется rollback, **Then** существующая rollback-защита сохраняется.
4. **Given** remote worktree содержит только старый корневой
   `twobrain-rec-deploy.lock`, который больше не используется, **When** новый
   repository-owned deploy начинает bootstrap, **Then** этот один известный
   legacy-файл не блокирует checkout кандидата, а любое другое изменение
   продолжает блокировать rollout.

### Edge Cases

- Внутренний timeout запроса должен быть меньше общего timeout healthcheck.
- Дополнительный budget не должен менять endpoint с readiness на liveness.
- Неуспешный HTTP status и зависание дольше верхней границы остаются ошибкой.
- Изменение не должно затрагивать billing, YooKassa, миграции или данные.
- Исключение clean-worktree guard допустимо только для точного untracked пути
  `twobrain-rec-deploy.lock`; tracked-изменение или любой соседний путь остаются
  блокирующими.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Healthcheck MUST принимать успешный readiness-ответ с текущей
  наблюдаемой длительностью 3.5–3.6 секунды.
- **FR-002**: Ожидание MUST оставаться ограниченным и завершаться ошибкой, если
  readiness не отвечает в течение 8 секунд.
- **FR-003**: Общий healthcheck budget MUST превышать внутренний request budget,
  чтобы внешний runner не завершал процесс раньше внутренней проверки.
- **FR-004**: Проверка MUST продолжать использовать `/api/v1/health/ready` и
  MUST NOT заменяться liveness-проверкой.
- **FR-005**: Неуспешный readiness status MUST продолжать блокировать rollout.
- **FR-006**: Изменение MUST NOT менять API readiness semantics, runtime secrets,
  billing configuration, database schema или rollback policy.
- **FR-007**: Контрактная проверка MUST фиксировать оба budget и readiness path.
- **FR-008**: Remote bootstrap MUST игнорировать только точный untracked
  legacy-путь `twobrain-rec-deploy.lock`, потому что активный lock расположен в
  `.git/twobrain-rec-deploy.lock`.
- **FR-009**: Любое другое tracked или untracked изменение remote worktree MUST
  продолжать блокировать deploy до reset, migration или container mutation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% readiness-проб с подтверждённым ответом за 3.5–3.6 секунды
  завершаются успешно.
- **SC-002**: 100% проб без ответа после 8 секунд завершаются ошибкой.
- **SC-003**: Повторный guarded rollout проходит API health gate либо
  откатывается по реальной неготовности, но не из-за прежнего трёхсекундного
  cutoff.
- **SC-004**: Production после изменения сохраняет `live=200`, `ready=200` и
  YooKassa test-shop configuration.
- **SC-005**: Guarded deploy проходит stale legacy-lock bootstrap без ручного
  удаления файла и по-прежнему останавливается на любом другом dirty path.

## Assumptions

- Пять последовательных внутренних production-проб показали 3.52–3.60 секунды.
- В логах кандидата нет startup exception; health history содержит
  `TimeoutError` ровно на текущем трёхсекундном request budget.
- 8 секунд дают ограниченный запас для текущей readiness-проверки, а общий
  budget 10 секунд сохраняет отдельную внешнюю границу.

## Out of Scope

- Изменение состава readiness checks или их параллелизация.
- Ослабление rollback, health или deployment gates.
- Ручная правка production compose вне репозитория.
- Изменение desktop billing fix, тарифов, промокодов или YooKassa environment.
- Ручное удаление legacy lock с production host.
