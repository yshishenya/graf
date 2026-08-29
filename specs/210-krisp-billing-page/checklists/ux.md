# UX Requirements Checklist: KRISP-like billing

**Purpose**: Проверить полноту и измеримость требований к reference-fidelity, responsive и accessibility до реализации
**Created**: 2026-08-29
**Feature**: [spec.md](../spec.md)

## Information architecture and truthfulness

- [x] CHK001 Определен ли порядок всех обязательных секций overview и единственное основное действие? [Completeness, Spec §FR-001, Contract §Overview]
- [x] CHK002 Описаны ли comparison и checkout как отдельные, короткие и независимо проверяемые этапы? [Coverage, Spec §US2, §SC-002]
- [x] CHK003 Зафиксированы ли реальные тарифы, цены, claims и замена seat management на workspace/owner surface? [Truthfulness, Spec §FR-004–FR-005]
- [x] CHK004 Запрещены ли извлечение и повторное использование конкурентных исходников, assets, branding и private data? [Provenance, Spec §FR-003, §Out of Scope]

## Layout and responsive coverage

- [x] CHK005 Определены ли пять точных web viewport и критерии horizontal overflow/clipping? [Measurability, Spec §FR-014, §SC-003]
- [x] CHK006 Определены ли minimum/standard/fullscreen desktop и expanded/collapsed inspector? [Coverage, Spec §FR-015, Desktop contract]
- [x] CHK007 Указаны ли 200% zoom/text, длинные суммы/даты и узкий embedded WebView? [Edge Case, Spec §Edge Cases, Quickstart]
- [x] CHK008 Разделены ли обязательные категории fidelity ledger и допустимые основания отклонений? [Clarity, Spec §SC-008–SC-009]

## Interaction and accessibility

- [x] CHK009 Определены ли keyboard order, visible focus, accessible name/role/state и live-region требования? [Coverage, Spec §FR-013]
- [x] CHK010 Определены ли native semantics для периода, disclosure, errors и disabled/pending действий? [Clarity, UI contract]
- [x] CHK011 Зафиксированы ли dark/light, reduced motion, forced/high contrast и 200% text expectations? [Coverage, Spec §Edge Cases]
- [x] CHK012 Сохранен ли полноценный no-JS путь через links/forms без зависимости от enhancement? [Resilience, Spec §FR-016]

## State quality and evidence

- [x] CHK013 Покрыты ли empty, unavailable, conflict, validation/provider error, success и pending/reconciliation states конкретным следующим шагом? [Coverage, Spec §FR-006, §FR-012]
- [x] CHK014 Установлены ли объективные browser console, geometry, installed desktop и material-mismatch closeout criteria? [Measurability, Spec §SC-003–SC-008]
