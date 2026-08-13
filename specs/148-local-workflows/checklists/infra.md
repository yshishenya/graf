# Infrastructure Requirements Checklist: Локальные workflows

**Purpose**: Проверить полноту локального CI/CD execution contract
**Created**: 2026-08-13
**Feature**: [spec.md](../spec.md)

## Execution Surface

- [x] CHK001 Каждый удаляемый remote workflow имеет локальный replacement. [Spec §SC-001]
- [x] CHK002 Требования различают fast feedback, full validation и production CD. [Spec §FR-003, §FR-004]
- [x] CHK003 Repository setting и отсутствие workflow YAML заданы как независимые safeguards. [Spec §FR-002]

## Reliability

- [x] CHK004 Требования определяют serialization и cleanup при interruption. [Spec §FR-011]
- [x] CHK005 Negative scenarios блокируют upload и live-feed mutation. [Spec §SC-004]
- [x] CHK006 Документация и historical evidence разделены явно. [Spec §FR-012, §FR-013]

## Validation

- [x] CHK007 Focused, fast, full и settings checks имеют измеримые expected outcomes. [Spec §SC-002–SC-005]
- [x] CHK008 Реальная подпись и production deploy исключены из feature validation. [Spec §Assumptions]
