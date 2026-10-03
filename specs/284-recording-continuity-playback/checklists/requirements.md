# Specification Quality Checklist
Feature: ../spec.md. Reviewer-owned; generated unchecked.
- [x] CHK001 Scope contains two independently testable user goals and bounded out-of-scope decisions.
- [x] CHK002 FR001–009 and SC001–005 are measurable with defined negative cases and no unresolved user decision.
- [x] CHK003 Assumptions preserve tariff, ownership, deletion, consent and release boundaries.

## Уточнение T011 — независимое ревью 2026-10-03
- [x] CHK004 Отказ физической записи через361s отделён от успешной эмуляции детектора; порядок чтения writer остаётся проверяемой гипотезой, а не объявленной причиной (spec, уточнение T011; SC005; quickstart7).
- [x] CHK005 FR009/SC005 и T011 задают исполняемое воспроизведение без потерь источника, сохранение обоих файлов и проверку длительности; отрицательные overflow/gap/format/clock/missing-source/stop проверки сохраняются. Повторный физический45min PASS обязателен до merge/release (spec, plan T011, tasks Phase6, quickstart7).
