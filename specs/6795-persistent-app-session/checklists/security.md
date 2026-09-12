# Security requirements checklist

Reviewer-owned. Generated 2026-09-11; implementation must not check items.

- [x] CHK001 Срок бездействия, источник времени, активность и погрешность определены измеримо? [FR-001]
- [x] CHK002 Описаны запрет продления истёкшего/отозванного входа и все проверки доступа? [FR-002, FR-006]
- [x] CHK003 Определены cookie/native доставка, потерянный ответ и отсутствие смены токена? [FR-003]
- [x] CHK004 Полно определены параллельность, выход, смена аккаунта, origin и отказ commit? [FR-004]
- [x] CHK005 Отделена смена аккаунта от обновления срока? [FR-005]
- [x] CHK006 Совместимость старой сессии, privacy и границы установки/выпуска проверяемы? [FR-006, FR-007]

## Independent requirements review — 2026-09-11

Reviewer: auth_investigation, independent read-only investigation/review agent. Reviewed spec.md, plan.md, data-model.md, research.md, quickstart.md, tasks.md and contracts/session-renewal.md against the current native request and cookie flow. Checked items mean requirements are sufficiently defined, not that implementation or runtime validation passed.

- RESOLVED R1 / CHK003: the revised contract explicitly accepts authenticated 304 alongside 2xx; spec.md and quickstart.md require repeated registry 304 responses without cabinet navigation. This closes the delivery gap in the requirements. Runtime proof remains part of T004/T005.
- RESOLVED R2 / CHK004: FR-004, US2 and the revised contract explicitly scope strict current-token/generation protection to the native bridge. They disclose that concurrent browser Set-Cookie responses may cause another login while a revoked session remains denied server-side. This is a defined limitation, not a claim of atomic browser cookie updates.
- Coverage mapping: FR-001/002/003/004/006 → T002/T003; FR-003/004/005 → T004; FR-007 and SC-001/002/003 → T005/T006. No orphan requirement found. Follow-up requirements review: PASS; no remaining requirements blockers. This does not mark implementation, tests, installation or release gates complete.
- Native implementation review must verify every requestExecutor response path, same scheme/host/port, same existing token in both stores, logout/account generation at application time, and no auth-change event for expiry-only updates. No application source was edited during this review.
