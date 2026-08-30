# Operational Readiness Requirements Checklist: Быстрый и доказуемый CI/CD

**Purpose**: Проверить полноту, ясность и непротиворечивость требований перед реализацией high-risk CI/CD slice
**Created**: 2026-08-30

## Requirement Completeness

- [x] CHK001 Описаны ли требования для каждого уровня evidence: focused, fast и full, без подмены одного другим? [Completeness, Spec §FR-002]
- [x] CHK002 Описаны ли требования к выбору компонентов и консервативной эскалации для shared, unknown, high-risk и unresolvable diff? [Completeness, Spec §FR-003]
- [x] CHK003 Перечислены ли все входы, к которым должна быть привязана full-CI receipt? [Completeness, Spec §FR-005, Data Model §FullCIReceipt]
- [x] CHK004 Описано ли, какие production gates receipt не заменяет и не ослабляет? [Completeness, Spec §FR-008]
- [x] CHK005 Описана ли граница между активной операционной документацией и неизменяемыми историческими evidence/receipts? [Completeness, Spec §FR-010–FR-012]

## Requirement Clarity

- [x] CHK006 Является ли поведение bare CI command однозначным и измеримым? [Clarity, Spec §FR-001, SC-001]
- [x] CHK007 Определено ли, что означает valid, missing, stale и mismatched receipt, включая стабильные причины отказа? [Clarity, Contract §ci-receipt.py]
- [x] CHK008 Определены ли результат и timing metadata для успешных, ошибочных и частично завершённых прогонов? [Clarity, Spec §FR-004, Data Model §StageResult]
- [x] CHK009 Ясно ли отделён report-only noisy performance proof от hard functional gates и контролируемой performance-линии? [Clarity, Spec §FR-009, Research §Decision 5]
- [x] CHK010 Ясно ли указано, что batching является рекомендацией, а не блокировкой hotfix? [Clarity, Spec §FR-013]

## Requirement Consistency

- [x] CHK011 Согласованы ли spec, research, data model и CLI contract по сроку жизни и exact-input validation receipt? [Consistency, Spec §FR-005–FR-007, Research §Decision 3]
- [x] CHK012 Не противоречит ли component-aware fast требованию fail-closed на неоднозначных путях? [Consistency, Spec §FR-003, Contract §ci-local.sh]
- [x] CHK013 Совместимы ли receipt reuse и обязательные clean-tree, remote-sync и exact-SHA проверки? [Consistency, Spec §FR-007–FR-008, Contract §cd-remote.sh]
- [x] CHK014 Не заявляет ли текущий slice immutable-image delivery без требований к registry и secret custody? [Consistency, Spec §FR-014, Research §Decision 6]

## Acceptance Criteria Quality

- [x] CHK015 Можно ли объективно доказать отсутствие тестового запуска для bare command? [Measurability, Spec §SC-001]
- [x] CHK016 Можно ли объективно доказать, что unchanged exact candidate выполняет full не более одного раза? [Measurability, Spec §SC-003]
- [x] CHK017 Охватывают ли критерии все invalid-receipt пути и safe fallback? [Acceptance Criteria, Spec §SC-004]
- [x] CHK018 Определён ли измеримый documentation-consistency outcome без переписывания истории? [Measurability, Spec §SC-006]
- [x] CHK019 Зафиксировано ли, что целевое ускорение сравнивается с измеренным baseline, а не с выдуманной цифрой? [Measurability, Spec §SC-009]

## Scenario And Edge Case Coverage

- [x] CHK020 Описаны ли primary, alternate, exception и recovery flows для fast selection и deploy receipt reuse? [Coverage, Spec §User Stories 1–2]
- [x] CHK021 Описано ли поведение при сигнале, падении этапа и частичной metadata, исключающее false-pass receipt? [Coverage, Spec §Edge Cases]
- [x] CHK022 Описано ли поведение receipt из другого worktree или после изменения runner, lockfile, toolchain либо test surface? [Coverage, Spec §Edge Cases]
- [x] CHK023 Описано ли поведение при нескольких затронутых известных компонентах без дублирования стадий? [Coverage, Spec §Edge Cases]
- [x] CHK024 Описано ли, что receipt не позволяет продолжить deploy после сбоя независимого release gate? [Recovery, Spec §Edge Cases]

## Security, Privacy And Dependencies

- [x] CHK025 Ограничен ли receipt metadata-only полями и явно ли запрещены credentials, private content, signed URLs и secret paths? [Security, Spec §FR-006]
- [x] CHK026 Определено ли fail-closed поведение для повреждённого или подменённого локального evidence? [Security, Spec §FR-007, Contract §ci-receipt.py]
- [x] CHK027 Перечислены ли существующие зависимости без добавления нового сервиса или пакета? [Dependency, Plan §Technical Context]
- [x] CHK028 Явно ли исключены production execute, commit, push, tag и release из текущей авторизации? [Scope, Spec §Assumptions, Plan §Release Gate]

## Ambiguities And Conflicts

- [x] CHK029 Нет ли неразрешённых `NEEDS CLARIFICATION`, placeholder или конфликтующих значений lane/receipt lifetime? [Ambiguity]
- [x] CHK030 Есть ли однозначный follow-up trigger для отдельного immutable-image slice? [Boundary, Spec §FR-014]
