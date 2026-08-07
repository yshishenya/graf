# Infrastructure Requirements Quality Checklist: Надёжная очистка production smoke-данных

**Purpose**: Проверить полноту требований для Postgres/MinIO cleanup и deploy rollback.
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [X] Требования определяют границу smoke identity для БД и storage. [Completeness, Spec §Key Entities]
- [X] Порядок удаления зависимостей и media revisions задан явно. [Clarity, Spec §FR-001]
- [X] Требования описывают отсутствие миграции/FK changes. [Consistency, Spec §FR-007]
- [X] Backup, restore, health, smoke и rollback evidence включены в success criteria. [Coverage, Spec §SC-003]

## Failure and Recovery Coverage

- [X] Revision-linked child row с несовпадающим meeting id указан как edge case. [Edge Case]
- [X] Повторный запуск и отсутствие residue определены измеримо. [Measurability, Spec §FR-004]
- [X] Невозможность безопасной очистки требует fail-closed rollback. [Recovery, Spec §FR-006]

## Scope and Safety

- [X] Требования не разрешают глобальный или чужой data deletion. [Security, Spec §FR-002]
- [X] Изменение ограничено maintenance cleanup path, без product deletion changes. [Scope, Spec §FR-007]
