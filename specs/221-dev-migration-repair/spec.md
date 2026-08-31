# Feature Specification: Восстановить воспроизводимое состояние локальной Dev-базы

**Feature Branch**: `221-dev-migration-repair`

**Created**: 2026-08-31

**Status**: Draft

**Input**: Устранить migration drift локального Dev volume безопасным, обратимым и воспроизводимым способом, чтобы единый Dev harness мог выполнить `build → promote → status → smoke`.

## Actors and Goals

- **Dev operator** — возвращает локальную базу в состояние, совместимое с текущим migration graph.
- **Feature agent** — фиксирует факты и выполняет только approved repair в изолированной Dev boundary.
- **Reviewer** — принимает repair decision, backup/rollback evidence и ограничения.
- **Release operator** — убеждается, что Dev repair не затронул production и не меняет release evidence.

## User Scenarios & Testing

### User Story 1 — Подтвердить drift (Priority: P1)

Оператор получает metadata-only снимок текущей revision, migration graph, compose boundary и schema fingerprints без чтения пользовательских строк.

**Independent Test**: read-only probe воспроизводит неизвестную revision и показывает отсутствующий файл/цепочку в коде.

**Acceptance Scenarios**:

1. **Given** существующий Dev volume, **When** запускается probe, **Then** он записывает current revision, heads, graph mismatch и exact source SHA.
2. **Given** production compose или endpoint, **When** probe обнаруживает их, **Then** операция завершается fail-closed.

### User Story 2 — Выбрать обратимый repair (Priority: P1)

Оператор выбирает repair path только после backup/restore rehearsal на изолированной копии и сравнения schema/object fingerprints.

**Independent Test**: synthetic repair decision содержит owner, причину, границу данных, backup digest, rollback target и abort conditions.

**Acceptance Scenarios**:

1. **Given** backup не восстанавливается, **When** предлагается repair, **Then** решение блокируется.
2. **Given** неизвестная revision может означать пропущенную миграцию, **When** сравниваются миграционные файлы и schema, **Then** выбирается compatibility repair или безопасная пересборка только после review.

### User Story 3 — Выполнить repair в Dev (Priority: P1)

После approval оператор применяет repair только к локальной Dev-копии, проверяет `alembic current`, upgrade idempotency и backend readiness.

**Independent Test**: изолированная Dev-БД проходит upgrade head дважды, current совпадает с кодовым head, production boundary остаётся неизменной.

**Acceptance Scenarios**:

1. **Given** approved repair plan, **When** выполняется upgrade, **Then** current revision совпадает с ожидаемым head.
2. **Given** upgrade или health check падает, **When** срабатывает rollback, **Then** предыдущая Dev-копия восстанавливается и причина сохраняется.

### User Story 4 — Разрешить единый Dev smoke (Priority: P2)

Оператор подтверждает, что backend, frontend, worker и GRAF Dev app используют один exact SHA и проходят health/smoke.

**Independent Test**: `build --live → promote --live → status → smoke --live` создаёт metadata-only evidence с одинаковыми SHA.

**Acceptance Scenarios**:

1. **Given** repaired Dev database, **When** выполняется promote, **Then** active manifest и все компоненты сообщают один SHA.
2. **Given** rollback после smoke failure, **When** проверяется status, **Then** активен предыдущий manifest и приложение не обращается к production.

## Edge Cases and Failure States

- Unknown revision остаётся в volume: не использовать blind `stamp`, ручную запись `alembic_version` или `down -v`.
- Migration graph имеет несколько heads: repair блокируется до явного merge/expand-contract решения.
- Backup содержит пользовательские данные: evidence хранит только digest и размеры, не содержимое.
- Upgrade частично применился: rollback выполняется из проверенного backup, а не обратным SQL «на глаз».
- Backend запускается, но representative API не готов: promote не публикует active pointer.
- Dev origin не loopback или bundle ID не `pro.2brain.graf.dev`: операция fail-closed.
- Source SHA изменился во время repair: evidence stale, процесс начинается заново.

## Requirements

### Functional Requirements

- **FR-001**: Probe MUST фиксировать current revision, migration heads, source SHA и graph mismatch metadata-only.
- **FR-002**: Probe MUST reject production compose, production origins, non-loopback targets and unknown data boundaries.
- **FR-003**: Repair decision MUST содержать owner, reason, affected boundary, backup evidence, rollback target, abort conditions and approval.
- **FR-004**: Backup/restore rehearsal MUST пройти в изолированной Dev-копии до любого изменения существующего volume.
- **FR-005**: Repair MUST быть идемпотентным: повторный `upgrade head` не меняет schema после успеха.
- **FR-006**: Current revision MUST совпадать с ожидаемым кодовым head после repair.
- **FR-007**: Failed repair MUST restore the previous Dev state or remain blocked with a recoverable backup.
- **FR-008**: Existing volume MUST NOT be deleted or rewritten until approved repair evidence exists.
- **FR-009**: Live promote MUST verify backend readiness, representative API, component SHA equality and app identity before publishing active pointer.
- **FR-010**: Smoke evidence MUST be metadata-only and contain no credentials, raw audio, transcripts or user rows.
- **FR-011**: Changed source SHA, failed health or mismatched component MUST invalidate repair and Dev evidence.
- **FR-012**: Production migration, deploy, data deletion and manual migration-pointer edits MUST remain outside this feature.

### Key Entities

- **Migration Drift Snapshot** — current revision, graph heads, source SHA, compose boundary and schema fingerprints.
- **Repair Decision** — approved mechanism, owner, reason, backup/rollback evidence and abort conditions.
- **Dev Backup** — isolated recoverable copy identified by digest and timestamp.
- **Repair Evidence** — current/head result, idempotency, health/smoke and exact SHA metadata.

## Success Criteria

- **SC-001**: 100% drift probes contain exact SHA, current revision, heads and graph mismatch without user content.
- **SC-002**: No repair starts without a verified restore rehearsal and reviewer-approved decision.
- **SC-003**: Approved Dev repair reaches the expected head and passes two consecutive idempotent upgrades.
- **SC-004**: Failed repair restores the previous Dev state or leaves an explicit blocked state with a valid backup.
- **SC-005**: Live Dev smoke proves one SHA across backend, frontend, worker and GRAF Dev app.
- **SC-006**: No production endpoint, production compose, volume deletion or manual pointer edit is used.

## Assumptions

- Current observed drift is `0074_calendar_sync_maintenance`; code graph contains `0074_linked_workspace_proofs → 0075_calendar_sync_maintenance` and head `0085_merge_summary_mediascribe`.
- A clean temporary Dev database is allowed for rehearsal; existing volume is preserved.
- Feature 216 governance and one-manifest Dev contracts are authoritative.
- Any compatibility revision or data transformation becomes a separate approved child feature if it exceeds the repair boundary.

## Scope

### In Scope

- Read-only inventory, isolated backup/restore rehearsal, repair decision, Dev-only repair and live smoke evidence.
- Runbook and governance checks protecting production and exact-SHA boundaries.

### Out of Scope

- Production migrations/deploys, deletion of volumes or user data, manual `alembic_version` edits.
- Legacy retirement, Temporal history deletion or public macOS release.

## Legacy Impact

- **Classification**: `untouched`
- Existing migration compatibility is preserved; no new alias, fallback or migration path is introduced.
- Any legacy migration contour discovered during repair is linked to Feature 220 and handled separately.
