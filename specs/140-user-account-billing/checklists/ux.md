# Чек-лист качества требований: IA, UX, UI и CX

- [x] CHK001 Account-scoped и workspace-scoped разделы имеют одну каноническую IA. [FR-007–FR-013]
- [x] CHK002 Для каждого account/billing screen заданы actor, content, actions и state families. [FR-010–FR-018, FR-024, FR-028, FR-039, contract]
- [x] CHK003 Trial/renewal/cancel/refund показывают exact consequence до действия. [FR-022, FR-030, FR-045, FR-047, FR-055]
- [x] CHK004 Empty/loading/error/success/unknown/degraded состояния имеют деньги+доступ+next action. [FR-039, FR-073]
- [x] CHK005 Explicit labels исключают vague подтверждения и hidden cancellation. [FR-045–FR-046, FR-086]
- [x] CHK006 Desktop browser-only boundary понятна и не ломает Record/Stop. [FR-012, FR-026]
- [x] CHK007 Keyboard, focus, labels, live status, target size и color-independent state заданы. [FR-028, FR-082–FR-084]
- [x] CHK008 Mobile/compact/200%/long-RU/reduced-motion/no-JS coverage задан. [FR-085]
- [x] CHK009 GRAF clean-room/brand-distance и theme/localization требования явны. [FR-014, FR-081]
- [x] CHK010 Usability outcome измеряет findability и cancel path. [SC-002, SC-005, SC-010]

Результат: PASS — экранный контракт покрывает каждое меню, действие и критическое состояние.

## Перепроверка новых CX решений 2026-08-06

- [x] CHK011 `Без лимита` всегда называет scope и визуально отделено от finite storage/fair-use disclosure. [FR-024, FR-030, contract screens]
- [x] CHK012 Storage meter, what-counts, 80/95/100%, delete/manage/add-on and over-capacity states имеют равноправные recovery actions. [FR-093–FR-100]
- [x] CHK013 Renewal failure copy сообщает immediate `Free`, no retry; unknown state удаляет `Оплатить снова`. [US5, FR-040–FR-048]
- [x] CHK014 Refund email instruction не просит сумму/повтор verified data и ясно отделена от cancel-now; GRAF не обещает SLA и не показывает provider settlement. [US6, FR-053–FR-056]
- [x] CHK015 Referral screen объясняет +7/+30, cap, expiry, paid/bonus-until and non-cash nature. [US8, FR-063–FR-069, FR-101]

Результат перепроверки: PASS — IA/UX/UI/CX контракт покрывает каждое новое состояние и действие.

## Финальная проверка обещаний интерфейса 2026-08-06

- [x] CHK016 Unlimited claim is adjacent to the exact 2 GB `Личный` archive boundary (and 250/500 MB Free/Trial values) and two full-storage recovery choices. [FR-030, FR-106]
- [x] CHK017 Transient path explicitly says audio will not remain available for playback. [FR-106]
- [x] CHK018 Fair-use restriction exposes capability, reason, review deadline and appeal rather than an invented balance. [FR-107]
- [x] CHK019 Cancel-scheduled bonus displays no next charge, while active renewal displays shifted exact date. [FR-101, FR-108]
- [x] CHK020 Refusal and late-after-refusal outcomes persist in UI/email and never rely on a toast. [FR-103–FR-104]

Результат финальной проверки: PASS — pre-purchase and recovery copy stay internally consistent.
