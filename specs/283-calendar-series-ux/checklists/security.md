# SECURITY Checklist: F283

**Purpose**: requirements quality before implementation
**Created**: 2026-10-02
**Feature**: [spec.md](../spec.md)
**Review Ownership**: independent reviewer only. [x] means requirements quality accepted, not implemented.

## Requirements quality

- [x] CHK001 Определены ли сохранение owner/session/workspace/calendar и ACL/deletion на каждой странице? [Completeness, Spec FR-007]
- [x] CHK002 Определены ли стабильный период/anchor, проверка cursor и совместимость all? [Clarity, Spec FR-007, contracts/calendar-series.md]
- [x] CHK003 Описаны ли очистка/недоступность старых данных при обновлении прав и поздние ответы? [Coverage, Spec FR-006/007]
- [x] CHK004 Сохранены ли Join UUID/HTTPS/CSRF/session/native guard и отсутствие автоматической записи? [Consistency, Spec FR-008]
- [x] CHK005 Определены ли маскирование DOM/подсказок и граница приватного research evidence? [Completeness, Spec FR-007/010]
- [x] CHK006 Разделены ли разрешённая разработка, Dev harness и отдельный production release gate? [Consistency, Spec Assumptions, plan.md Validation Plan]

## Notes

Implementation reads this gate and cannot change markers. Reviewer records evidence and totals in a separate report.


## Независимое ревью требований — 2026-10-02

Это PASS качества изложенных требований до создания tasks, а не подтверждение реализации или выполненной приёмки.

- CHK001 — PASS: Spec FR-007, data-model, API contract прямо сохраняют owner/session/workspace/calendar, ACL/deletion/privacy на каждой странице; plan требует авторизацию до payload.
- CHK002 — PASS: Spec FR-007, data-model и plan Phase 1/API contract задают view+immutable UTC anchor в новом подписанном context, прежние owner/session/workspace/series/from/to и bounds, view mismatch422, восстановление anchor и совместимый default all/старый cursor до существующего expiry.
- CHK003 — PASS: Spec US3.2, FR-006/007 и plan Phase 1 JS определяют недоступность старых данных на время повторной проверки, очистку после отказа, AbortController/request identity, отсутствие кеша между периодами и сброс close/switch. Quickstart п.2 включает rights/focus/selection и late response сценарии.
- CHK004 — PASS: Spec FR-008 и Assumptions, plan Constraints/Constitution Check, API contract сохраняют UUID/HTTPS/CSRF/session/native guards, отдельный запуск записи, отсутствие capture/permissions changes и обязательное сохранение прежних Join security tests.
- CHK005 — PASS: Spec US3.3, FR-003/007/010, research вводная часть и plan JS запрещают скрытые поля в DOM/атрибутах/подсказках/доступных именах и сохранение частных встреч в research. Quickstart допускает только synthetic screenshots вне git и metadata-only заметки.
- CHK006 — PASS: Spec Assumptions, plan Release Gate/Validation Plan, quickstart п.4–5 отделяют разработку, единственный GRAF Dev через штатный harness после validated approved commit, exact-SHA PR checks и отдельно разрешённый frozen release-full/cd dry-run production release.

Итог после перечитывания: **6 checked / 0 unchecked**. Подробности и границы: [checklist-review.md](../checklist-review.md).


## Повторное ревью уточнения названий дат — 2026-10-02

PASS качества требований сохраняется: **6 checked / 0 unchecked**. Перечитаны spec/plan/research/data-model/contract/quickstart/tasks и оба checklist.

- CHK001/CHK002/CHK004: уточнение относится к подписям уже разрешённых экземпляров; авторизация, series identity, стабильный период/cursor, совместимость all и Join/recording границы не меняются. Новое canonical master или полномочие из названия не вводятся.
- CHK003/CHK005: US3.3, FR-003/006/007, plan и research совместно задают сброс контекста названий при refresh/view, очистку close/поздних ответов и использование только разрешённого названия. Скрытые поля не должны влиять на раскрываемые подписи, подсказки или доступные имена; прежние требования повторной ACL/privacy проверки сохранены.
- CHK006: tasks T009 явно открыт; требования штатного GRAF Dev и отдельного production gate сохранены. Ручная native acceptance и повторная проверка VoiceOver этим review не заявляются.

Этот результат подтверждает согласованность требований, а не выполненные runtime-проверки. Предыдущая запись ревью сохранена; подробности — в последнем разделе [checklist-review.md](../checklist-review.md).


## Повторное ревью маскированных дат

Проверено уточнение перед реализацией поверх source `64af55f7619ea9d3a60da07b3e907b2daf6d20b8`. **PASS требований: 6 checked / 0 unchecked.**

- CHK003/CHK005: US3.3/FR-007, plan и research используют только номер строки уже отображаемого списка. Запрещены скрытое время, название и provider ID в новой подписи; никакого нового API поля, постоянной идентичности либо полномочия номеру не приписывается. Нумерация продолжается между страницами, сбрасывается при view/refresh, поздние ответы и недоступные строки подчиняются прежнему FR-006/007.
- CHK001/CHK002/CHK004: owner/session/workspace/calendar, ACL/deletion, cursor и Join UUID/HTTPS/CSRF/session/native guards остаются прежними; номер не становится ключом действия или серии, запись автоматически не запускается.
- CHK006: T009 и ручная Dev-приёмка остаются открытыми, production разрешение не выдаётся. VoiceOver не запускался.

Блокеров требований не найдено; никакой результат реализации этим PASS не подтверждён. Подробности — в последнем разделе [checklist-review.md](../checklist-review.md).
