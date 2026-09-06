# Governance Requirements Checklist: Надёжный Spec Kit workflow

**Purpose**: Проверить полноту, ясность и трассируемость governance-требований до декомпозиции implementation
**Created**: 2026-08-30
**Feature**: [spec.md](../spec.md)
**Review Ownership**: Checklist является reviewer-owned requirements-quality artifact. `[x]` означает, что reviewer подтвердил качество требования, а не завершение реализации.

## Scope And Preservation

- [x] CHK001 Определены ли границы между GRAF repository, bootstrap source checkout и исключёнными production/community surfaces? [Completeness, Spec §Scope]
- [x] CHK002 Зафиксировано ли сохранение legacy user-level skills и пользовательских worktree changes без автоматического удаления? [Clarity, Spec §FR-002, Edge Cases]

## Workflow Semantics

- [x] CHK003 Задан ли единый упорядоченный GRAF workflow со всеми обязательными project stages и release gates? [Completeness, Spec §FR-005]
- [x] CHK004 Разделены ли reviewer-owned checklist markers и implementation task completion? [Consistency, Spec §FR-006]
- [x] CHK005 Определена ли граница применения сокращённого upstream workflow без обещания ложной полноты? [Clarity, Spec §FR-007]
- [x] CHK006 Определён ли append-only convergence loop и критерий его завершения? [Measurability, Spec §FR-008]

## Drift Detection And Validation

- [x] CHK007 Перечислены ли fail-closed классы drift, которые обязан обнаруживать focused guard? [Coverage, Spec §FR-009, SC-004]
- [x] CHK008 Разделены ли responsibilities штатного bootstrap doctor и project-specific guard без дублирования integrity logic? [Consistency, Plan §Summary]
- [x] CHK009 Есть ли measurable idempotence criterion для повторного bootstrap refresh? [Measurability, Spec §FR-010, SC-003]
- [x] CHK010 Определена ли validation lane с quickstart, focused checks, fast CI и явным исключением deploy/full release gate? [Completeness, Plan §Validation Plan]

## Notes

- Review выполнен до task generation. Implementation не изменяет markers этого checklist.
