# Security And Privacy Requirements Checklist: MVP Live Owner Journey And UI Proof

**Purpose**: Validate privacy/security requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are forbidden evidence classes explicitly listed, including raw audio, transcript text, private outcomes, account identifiers, cookies, tokens, signed URLs, object keys, private titles, and local private paths? [Completeness, Spec §FR-012]
- [x] CHK002 Are desktop MediaScribe boundaries preserved so desktop never sends audio directly or stores MediaScribe credentials? [Completeness, Plan §Technical Context]
- [x] CHK003 Are server-mediated playback and no signed URL/object-key exposure preserved? [Completeness, Plan §Constraints]
- [x] CHK004 Are KRISP reference privacy, reference fidelity, independent implementation and third-party asset provenance under current governance stated as requirements rather than reviewer preference? [Coverage, Spec §FR-011; Constitution VII; PRD §§29–30]

## Requirement Clarity

- [x] CHK005 Is metadata-only evidence defined clearly enough to allow statuses, counts, timings, redacted references, and command summaries while excluding content? [Clarity, Data Model §Validation Rules]
- [x] CHK006 Are production owner-session blockers classified without requiring cookies or account identifiers in committed evidence? [Clarity, Spec §FR-006]

## Scenario Coverage

- [x] CHK007 Are auth-required, server-unavailable, denied/deleting/deleted, and unavailable dependency states covered? [Coverage, Spec §Edge Cases]
- [x] CHK008 Are deletion and lifecycle boundaries protected from outcome/playback proof changes? [Consistency, Plan §Post-Design Constitution Check]

## Acceptance Criteria Quality

- [x] CHK009 Can forbidden-content checks be objectively run before commit/release? [Acceptance Criteria, Quickstart §11]

## Независимое ревью 2026-11-17 — F052/T020

Исполнитель: /root/f140_account_db_budget_research; основа 72079434d3fa151725c16ed6044da175c8955e51. CHK004 не подтверждён целиком: privacy часть определена, но brand-distance правило F052 расходится с действующими constitution VII, PRD §§29–30 и product-gates. Запреты private content, credentials и использования assets без прав остаются обязательными. Формулировки пунктов не изменены.

Итог: 8 отмечено, 1 не отмечен. Это качество требований, а не фактическая privacy/production приёмка; допуск к реализации: STOP.

## Повторное независимое ревью после уточнений — 2026-11-17

Исполнитель: /root/f140_account_db_budget_research; HEAD72079434d3fa151725c16ed6044da175c8955e51. Предыдущий STOP выше сохранён как история.

По явному назначению владельца исправлена только устаревшая часть CHK004. Старая точная формулировка: «Are KRISP reference privacy and brand-distance rules stated as requirements rather than reviewer preference? [Coverage, Spec §FR-011]». Brand-distance заменена действующими reference fidelity, independent implementation и asset provenance; privacy сохранена. Основание: Constitution VII/PRD29–30, текущий FR-011 и interface contract36–45. CHK004 подтверждён.

Итог security: 9 отмечено / 0 не отмечено. Общий набор остаётся STOP из-за UX CHK010; это не фактическая security/privacy или production приёмка.

## Независимое ревью второй правки требований — 2026-11-17

Исполнитель /root/f140_account_db_budget_research; HEAD 72079434d3fa151725c16ed6044da175c8955e51. Все 9 пунктов заново проверены: metadata-only/secret/content запреты, server-mediated playback, desktop MediaScribe граница, access/deletion и действующая reference fidelity/asset rights сохранены. Новое сравнение UUID происходит в памяти, не выводит input/response ID; GET-only и запрет Cookie redirect сохранены. Наблюдение говорящих не разрешает менять реальные встречи. Старые notes/STOP сохранены как история, wording не менялся.

Итог security 9/0; общий набор 50/0, PASS качества требований. Это не фактическая privacy/security или production приёмка.
