# UX Requirements Checklist: MVP Live Owner Journey And UI Proof

**Purpose**: Validate UI/UX requirement quality before implementation
**Created**: 2026-06-25
**Feature**: [spec.md](../spec.md)

## Requirement Completeness

- [x] CHK001 Are web desktop, web compact, macOS embedded, and native macOS shell surfaces all specified? [Completeness, Spec §User Story 3, FR-009]
- [x] CHK002 Are transcript, playback, timestamp seek, speaker timeline, diarization, and outcomes required in the same ready review flow? [Completeness, Spec §FR-007]
- [x] CHK003 Are unavailable states defined for auth, server health, missing transcript, missing playback, missing timeline, and missing outcomes? [Coverage, Spec §Edge Cases]

## Requirement Clarity

- [x] CHK004 Is false-ready behavior explicitly forbidden rather than left to subjective UI judgement? [Clarity, Spec §FR-006, FR-013]
- [x] CHK005 Is speaker timeline visibility required in measurable terms, including bottom timeline lanes tied to the reviewed meeting? [Clarity, Spec §FR-010, SC-004]
- [x] CHK006 Are the approved observable Krisp reference, justified deviations, independent code, privacy and documented third-party asset rights clearly required under Constitution VII and PRD §§29–30? [Clarity, Spec §FR-011; Interface Contract §Approved Observable Krisp Reference]
- [x] CHK007 Are native macOS recording/upload truth requirements separated from embedded web review requirements? [Consistency, Interface Contract §macOS Embedded Cabinet]

## Scenario Coverage

- [x] CHK008 Are web/embedded divergence and cached-ready cases addressed as requirements? [Coverage, Spec §Edge Cases]
- [x] CHK009 Are compact layout risks covered without introducing subjective "looks good" language? [Measurability, Spec §SC-003]
- [x] CHK010 Are speaker assignment and multi-speaker expectations covered at the interaction-pattern level without requiring post-MVP editing? [Scope, Interface Contract §Approved Observable Krisp Reference]

## Acceptance Criteria Quality

- [x] CHK011 Can UI quality be objectively classified with pass/fail/blocker evidence instead of taste-based review? [Acceptance Criteria, Spec §SC-003, SC-004]

## Независимое ревью 2026-11-17 — F052/T020

Исполнитель: /root/f140_account_db_budget_research; основа 72079434d3fa151725c16ed6044da175c8955e51. CHK006 не подтверждён: blanket запрет brand/trade dress в FR-011/interface contract конфликтует с constitution VII, PRD §§29–30 и product-gates §UX Reference Fidelity. Запреты private content, извлечённых assets и использования чужих материалов без прав сохраняются. Формулировки пунктов не изменены.

Итог: 10 отмечено, 1 не отмечен. Это качество требований, а не приёмка UI; допуск к реализации: STOP.

## Повторное независимое ревью после уточнений — 2026-11-17

Исполнитель: /root/f140_account_db_budget_research; HEAD72079434d3fa151725c16ed6044da175c8955e51. Предыдущий STOP выше — история прежнего снимка.

По явному назначению владельца исправлен CHK006. Старая точная формулировка: «Is the KRISP reference boundary clear enough to prevent copying brand, screenshots, assets, private content, or trade dress? [Clarity, Spec §FR-011]». Blanket brand-distance/trade-dress часть противоречила Constitution VII/PRD29–30; новый вопрос сохраняет privacy, независимый код и документированные права на материалы. CHK006 подтверждён новым FR-011 и interface contract36–45.

CHK010 снят: при переписывании interface contract исчезло прежнее явное «speaker assignment»; текущие spec/research/interface/quickstart определяют полосы и диаризацию, но не ожидания назначения говорящих как наблюдения взаимодействия без нового editing scope. Указанный в CHK010 раздел KRISP Clean-Room Reference также переименован. Общее разрешение следовать референсу не доказывает этот составной пункт. Нужна узкая правка владельца требований и новое ревью; сам CHK010 не переписан.

Итог UX: 10 отмечено / 1 не отмечен (CHK010). Общий допуск: STOP. Проверка требований не подтверждает UI/production acceptance.

## Независимое ревью второй правки требований — 2026-11-17

Исполнитель /root/f140_account_db_budget_research; HEAD 72079434d3fa151725c16ed6044da175c8955e51. Все 11 пунктов заново проверены. CHK010 подтверждён текущим interface §Approved Observable Krisp Reference: прямо названы assignment affordances, связь выбранного говорящего с transcript rows/activity lanes, видимое unavailable состояние и различимость нескольких говорящих. Spec Clarifications, research и quickstart согласованы. Это наблюдение существующих разрешённых взаимодействий, без нового editor, изменения реальных данных или заявления о выполненной UI-приёмке.

По явному узкому разрешению заменена только ссылка CHK010: старая точная ссылка «§KRISP Clean-Room Reference», новая «§Approved Observable Krisp Reference». Причина — переименование раздела при обновлении правил референса. Исходный вопрос, ID и scope сохранены. Прежние notes и STOP сохранены как история.

Итог UX 11/0; общий набор 50/0, PASS только качества требований текущего снимка. Реальная UI/production приёмка не выполнена.
