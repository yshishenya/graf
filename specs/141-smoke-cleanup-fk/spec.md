# Feature Specification: Надёжная очистка production smoke-данных

**Feature Branch**: `141-smoke-cleanup-fk`

**Created**: 2026-08-07

**Status**: Draft

**Input**: User description: "Довести исправление до конца и устранить блокер production deploy"

## User Scenarios & Testing

### User Story 1 - Успешный smoke deploy после очистки (Priority: P1)

Оператор выкатывает проверенный релиз и получает завершённый production smoke без ошибки внешнего ключа при удалении синтетических данных.

**Why this priority**: Пока cleanup падает, deploy gate блокирует релиз и запускает rollback даже при исправном приложении.

**Independent Test**: На disposable Postgres создать smoke-встречу с media revision и revision-связанными processing-записями, выполнить cleanup и убедиться, что cleanup завершается без исключения и не оставляет строк.

**Acceptance Scenarios**:

1. **Given** smoke-встреча имеет media revision и зависимую запись, **When** оператор запускает cleanup, **Then** зависимая запись удаляется до media revision и cleanup завершается со статусом `pass`.
2. **Given** smoke cleanup завершился, **When** deploy запускает staged smoke и rollback guard, **Then** cleanup не вызывает FK-ошибку и release gate может перейти к health/smoke проверкам.

### User Story 2 - Безопасный повторный cleanup (Priority: P2)

Оператор может повторно запустить cleanup после частичного или уже завершённого smoke без удаления данных, не относящихся к smoke identity.

**Why this priority**: Retry и rollback должны быть безопасными, а остатки синтетических данных не должны накапливаться между deploy-попытками.

**Independent Test**: После успешной очистки повторить команду с тем же run id и проверить нулевой остаток строк/объектов; отдельно убедиться, что записи другой identity сохранены.

**Acceptance Scenarios**:

1. **Given** smoke identity уже очищена, **When** cleanup запускается повторно, **Then** команда завершается без ошибки, не удаляет строки и не создаёт ложный residue.
2. **Given** в хранилище или БД есть данные другой identity, **When** cleanup выполняется для smoke run id, **Then** чужие данные остаются нетронутыми.

## Edge Cases

- Зависимая запись может ссылаться на media revision через `media_revision_id`, даже если её собственный `meeting_id` не совпадает с найденной smoke-встречей; cleanup должен учитывать оба безопасных пути связи.
- Таблица из старой или неполной схемы может отсутствовать; существующее fail-closed поведение с проверкой доступных таблиц должно сохраниться.
- В cleanup может не быть найдено ни одной smoke-встречи; команда должна сохранить текущую идемпотентность и выполнить только безопасную очистку identity/storage.
- Ошибка удаления должна откатывать транзакцию БД и оставлять deploy rollback guard активным; нельзя продолжать release как успешный.

## Requirements

### Functional Requirements

- **FR-001**: Система MUST удалять smoke-зависимости, связанные с найденной встречей либо с принадлежащими ей media revisions, до удаления самих media revisions.
- **FR-002**: Система MUST сохранять существующие ограничения smoke identity и не удалять данные другой организации, workspace, пользователя, устройства или run id.
- **FR-003**: Система MUST завершать успешный cleanup без исключения внешнего ключа, если все найденные smoke-зависимости доступны для удаления.
- **FR-004**: Система MUST сохранять идемпотентность: повторный cleanup после полного удаления должен завершаться без residue и без удаления чужих данных.
- **FR-005**: Система MUST сохранять проверку доступности таблиц, очистку storage prefix и metadata-only cleanup evidence.
- **FR-006**: Система MUST оставлять deploy gate заблокированным и запускать предусмотренный rollback, если cleanup действительно не может безопасно завершиться.
- **FR-007**: Изменение MUST быть ограничено cleanup smoke path и regression-проверками; оно MUST NOT менять пользовательское удаление встреч, схему БД или production FK constraints.

### Key Entities

- **Smoke identity**: синтетические организация, workspace, пользователь, устройство и run id, принадлежащие deploy smoke.
- **Meeting**: синтетическая встреча, обнаруженная по smoke identity.
- **Media revision**: версия media-артефактов встречи, на которую могут ссылаться processing и normalization записи.
- **Smoke residue**: строки БД или объекты storage, оставшиеся после cleanup и требующие явного evidence/owner.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Disposable Postgres smoke cleanup проходит не менее чем в 3 сценариях: обычная встреча, revision-связанная зависимость с несовпадающим `meeting_id`, повторный запуск; во всех сценариях результат `pass` и residue отсутствует.
- **SC-002**: Полный `infra/scripts/ci-local.sh` завершается успешно с включённым regression-тестом cleanup.
- **SC-003**: Production `infra/scripts/cd-remote.sh --execute --branch master` проходит backup, restore rehearsal, migration, health и smoke gates без FK-ошибки cleanup; при любой другой ошибке rollback остаётся успешным.
- **SC-004**: После успешной выкатки `https://rec.2brain.pro/api/v1/health/ready` возвращает готовность, а staged smoke подтверждает отсутствие cleanup residue.

## Assumptions

- Smoke cleanup работает в существующем maintenance-контексте и использует уже настроенные секреты deployment.
- Media revision является безопасным источником принадлежности для revision-связанных зависимостей только внутри найденной smoke-встречи и её workspace.
- Исправление не требует миграции, изменения FK или ручного удаления production-данных.
- Production deploy будет повторён только после focused validation и полного локального CI.

## Out of Scope

- Изменение пользовательского процесса удаления встреч.
- Изменение структуры Postgres, каскадных ограничений или миграций.
- Исправление иных независимых production smoke failures, если они будут выявлены после устранения текущей FK-ошибки.
