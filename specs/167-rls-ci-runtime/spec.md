# Feature Specification: Надёжный RLS release gate

**Feature Branch**: `codex/fix-rls-ci-runtime`

**Created**: 2026-08-18

**Status**: Implementation committed and validated locally; PR pending

**Input**: User description: "Release gate должен доходить до RLS-проверки на disposable PostgreSQL и использовать корректное окружение проекта."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Выполнить полный release gate (Priority: P1)

Оператор релиза запускает полный локальный gate с отдельной disposable PostgreSQL-базой и получает достоверный результат RLS-проверки. Gate не должен зависеть от случайного системного Python-окружения компьютера.

**Why this priority**: Без рабочей RLS-проверки нельзя безопасно считать release candidate проверенным и передавать его в production gate.

**Independent Test**: Запустить полный gate с loopback disposable-базой; проверка RLS должна выполниться и завершиться результатом `pass`, после чего остальные release-only проверки должны продолжиться.

**Acceptance Scenarios**:

1. **Given** задана loopback disposable PostgreSQL-база и доступны зависимости проекта, **When** оператор запускает полный gate, **Then** RLS-проверка запускается в окружении проекта, выполняет миграции и прямые проверки, а результат не блокируется ошибкой отсутствующей Python-зависимости.
2. **Given** RLS-проверка завершилась успешно, **When** gate переходит к следующим шагам, **Then** compose-проверка и deployment evidence scan выполняются для того же commit.

### User Story 2 - Сохранить безопасное блокирующее поведение (Priority: P1)

Оператор не должен случайно проверить или изменить production-базу, если disposable URL не задан или URL указывает на запрещённую production-базу.

**Why this priority**: Безопасная остановка важнее удобства запуска и защищает production от destructive probe.

**Independent Test**: Запустить RLS boundary без URL и с URL базы `twobrain_rec`; проверить блокирующий результат и отсутствие миграций/проб.

**Acceptance Scenarios**:

1. **Given** RLS URL отсутствует, **When** запускается RLS boundary, **Then** gate сообщает `blocked` с причиной отсутствия disposable базы и не выполняет probe.
2. **Given** URL указывает на базу `twobrain_rec`, **When** запускается RLS boundary, **Then** запуск завершается неуспешно до миграции или destructive probe.

### Edge Cases

- Системный Python доступен, но не содержит server-зависимостей; gate должен использовать воспроизводимое окружение проекта.
- Полный gate прерывается после создания disposable базы; база и временные роли должны быть удалены cleanup-процессом.
- Пароль disposable базы содержит символы, требующие URL-кодирования; секрет не должен попасть в stdout, logs или committed evidence.
- Deployment evidence scan должен выполняться даже после исправления runtime boundary и не должен ослабляться ради прохождения gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Full release gate MUST execute RLS hardening validation with the repository-managed Python runtime and its declared server dependencies.
- **FR-002**: RLS validation MUST preserve fail-closed behavior when no disposable database URL is provided.
- **FR-003**: RLS validation MUST reject the live production database name before migrations or destructive probes.
- **FR-004**: The gate MUST preserve the existing order of server validation, RLS validation, compose validation, and deployment evidence scanning.
- **FR-005**: Validation output MUST remain metadata-only and MUST NOT expose database passwords, credentials, raw logs, or meeting data.
- **FR-006**: Cleanup MUST remove the disposable database and any probe role created for the validation run when the gate exits, including failure paths.

### Key Entities *(include if feature involves data)*

- **Release gate run**: One validation execution identified by its exact commit and mode; it has ordered stages and a final pass or blocked result.
- **Disposable RLS database**: A loopback-only non-production database used for migrations and direct RLS probes; it is never the live `twobrain_rec` database.
- **Validation runtime**: The project-managed execution environment that provides the dependencies required by RLS validation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a configured disposable loopback database, 100% of full gate runs reach RLS validation and do not fail because the system Python lacks a project dependency.
- **SC-002**: With no RLS database URL or with the live production database name, 100% of runs stop before migrations or destructive probes and report a blocking reason.
- **SC-003**: A successful full gate continues through compose configuration and deployment evidence scanning for the same exact commit.
- **SC-004**: In validation logs and committed evidence, 0 database passwords, credentials, raw logs, or meeting-content fields are exposed.
- **SC-005**: After both successful and failed runs, 0 databases or temporary probe roles created for the run remain in the local PostgreSQL cluster.

## Assumptions

- The project already declares and locks the Python dependencies required by the RLS validation script.
- Release operators provide only loopback disposable PostgreSQL URLs for destructive probes; production database access is handled by a separate guarded deployment workflow.
- The existing server test runner remains responsible for its own isolated PostgreSQL container and is not replaced by this feature.
- macOS, server, compose, and evidence stages remain the release gate's existing validation surfaces; this slice changes only the runtime used by the RLS boundary.
