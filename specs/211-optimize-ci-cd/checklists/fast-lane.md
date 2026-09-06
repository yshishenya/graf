# Fast Lane Requirements Checklist: Быстрый и доказуемый CI/CD

**Purpose**: Проверить качество follow-up требований после production feedback
**Created**: 2026-08-31

`[x]` означает reviewer approval качества требований, а не завершённую
реализацию. `$speckit-implement` читает, но не меняет состояния пунктов.

## Requirement completeness and clarity

- [x] CHK001 Определено ли без исключений, что явный fast не может запускать full? [Clarity, Spec §FR-003]
- [x] CHK002 Описаны ли ограниченные проверки для server, macOS, infrastructure/tooling, docs и unknown paths? [Completeness, Spec §FR-003]
- [x] CHK003 Определён ли понятный результат для unavailable diff без ложного fast PASS и без скрытого full? [Edge Case, Spec §Edge Cases]

## Consistency and acceptance

- [x] CHK004 Согласованы ли spec, plan, contract и quickstart по правилу `requested=fast effective=fast`? [Consistency, Spec §SC-002]
- [x] CHK005 Различают ли требования fast feedback evidence и обязательный exact-SHA release full? [Consistency, Spec §FR-002, §FR-005]
- [x] CHK006 Можно ли объективно доказать отсутствие full stages во всех fast contract scenarios? [Measurability, Spec §FR-011, §SC-002]
