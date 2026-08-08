# Чек-лист качества требований: post-plan readiness личного кабинета и биллинга

**Purpose**: формальный cross-domain review полноты, ясности, непротиворечивости и измеримости требований feature 140 после планирования и перед реализацией.
**Created**: 2026-08-06
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md)
**Audience / Timing**: product, UX, engineering, security, finance, legal и release reviewers; обязательный gate перед `$speckit-implement`.

**Note**: пункты оценивают качество написанных требований и согласованность артефактов, а не поведение реализации.

## Requirement Completeness

- [x] CHK001 Определён ли полный account lifecycle для нового самостоятельного пользователя: personal workspace, Owner authority, profile/security/preferences, session/device management, multi-workspace switch и account close? [Completeness, Spec §FR-001–FR-019]
- [x] CHK002 Полностью ли описан commercial lifecycle `Free → explicit Trial → Личный → cancel/failure → Free`, включая verification gate, current-period access, recurring authority и отсутствие скрытого списания? [Completeness, Spec §FR-020–FR-048]
- [x] CHK003 Зафиксирована ли внешняя refund boundary во всех пользовательских и операционных требованиях: только email + safe invoice reference, без GRAF request/case/form/status/timeline/SLA/calculation/approval/execution? [Completeness, Spec §FR-052–FR-056, FR-074, Contract Billing §External refund boundary]
- [x] CHK004 Определён ли полный storage lifecycle: exact chargeable playback bytes, reservation, active/superseded/deleted truth, thresholds, add-on, over-capacity, no-archive processing и deletion precedence? [Completeness, Spec §FR-093–FR-100, FR-106]
- [x] CHK005 Полны ли promo/referral requirements для eligibility, best-one-only discount, first-touch, 14-day maturity, 7/30-day credit, cap, expiry, abuse review и provider-confirmed refund reversal? [Completeness, Spec §FR-057–FR-069, FR-101, FR-108]
- [x] CHK006 Перечислены ли для каждого account/billing screen actor, scope, primary/secondary actions, exact labels и normal/loading/empty/error/degraded/terminal states, включая внешний mail-client fallback? [Completeness, Spec §FR-007–FR-018, FR-073–FR-086, Contract IA §Screen inventory]

## Requirement Clarity

- [x] CHK007 Однозначно ли выражение `Без лимита` ограничено minutes/meetings/transcription/AI и всегда сопровождается точной finite playback capacity, technical ceilings и narrow fair-use boundary? [Clarity, Spec §FR-024–FR-028, FR-107]
- [x] CHK008 Заданы ли единые authoritative storage values в decimal bytes и соответствующие display values: Free 250 MB, Trial 500 MB, `Личный` 2 GB, total-capacity add-on 5/20/100/500 GB? [Clarity, Spec §FR-093, Product Decisions]
- [x] CHK009 Однозначно ли определено, что quota source truth — active validated `meeting-review.m4a` bytes из существующего artifact lifecycle, а `meeting-transcription.wav`, legacy sources, replicas, backups и transient objects дают zero customer contribution? [Clarity, Spec §FR-094–FR-095, Data Model §Storage reservation]
- [x] CHK010 Зафиксированы ли точные последствия одной renewal operation для `succeeded|canceled|unknown` в `paid_through`, включая immediate Free, no grace, no automatic retry и запрет pay-again при unknown? [Clarity, Spec §FR-040–FR-048]
- [x] CHK011 Определено ли содержимое refund email action без двусмысленности: configured address, safe subject/reference, запрещённые card/provider/meeting fields, mail-client unavailable fallback и отсутствие in-product sent/result state? [Clarity, Spec §FR-052–FR-054, FR-074, Contract IA §Interaction rules]
- [x] CHK012 Разделены ли понятия `observed provider refund`, referral reversal и separately authorized entitlement/add-on correction так, чтобы observation не выглядел как расчёт, исполнение, автоматическая потеря доступа или восстановление recurring consent? [Clarity, Spec §FR-055–FR-056, FR-064, FR-069, FR-102]

## Requirement Consistency

- [x] CHK013 Согласована ли external-refund модель между Product Decisions, US6, FR-050–FR-056, plan, data model и всеми contracts без остаточных refund-case/operator-mutation требований? [Consistency, Spec §US6, Plan §Summary, Data Model §Observed Provider Refund]
- [x] CHK014 Согласовано ли во всех артефактах, что storage использует существующий `TrackArtifact`/artifact lifecycle и не вводит второй authoritative object inventory, включая формулировку `reservation/inventory` в plan architecture? [Consistency, Plan §Architecture step 3, Data Model §Existing entities]
- [x] CHK015 Совпадают ли тарифные ёмкости и estimated-hour disclaimers во всех source/downstream документах без заменённых 1/10 GB assertions? [Consistency, Spec §Launch Tariff Levels, FR-093–FR-100]
- [x] CHK016 Используется ли единый no-grace vocabulary, а отсутствие `past_due`, dunning ladder, priority refund case и keep-period workflow явно отражено в spec, plan, contracts, checklists и tasks? [Consistency, Spec §FR-039–FR-048, FR-104]
- [x] CHK017 Согласованы ли referral terms во всех артефактах: invited 10% first eligible period, inviter 7/30 days after 14 days, no cash, 180-day rolling cap и bounded reversal? [Consistency, Spec §FR-060–FR-069, FR-101, FR-108]
- [x] CHK018 Не противоречат ли payment-history/receipt requirements запрету показывать refund outcome: пользователь видит payment/receipt truth и email instruction, но не refund badge/filter/timeline/result? [Consistency, Spec §FR-050–FR-055, Contract IA §History]
- [x] CHK019 Согласована ли deletion precedence между account close, meeting deletion, playback quota release, current/legacy source purge, formal mandatory hold, backups и retained observability/finance truth? [Consistency, Constitution §IV, Spec §FR-018–FR-019, FR-094]

## Acceptance Criteria Quality

- [x] CHK020 Можно ли объективно оценить отсутствие refund product surface через нулевые counts для request/case/status/SLA entities, routes, operator mutation commands, refund API calls и user-facing outcomes? [Measurability, Spec §SC-008, FR-053–FR-055]
- [x] CHK021 Покрывают ли success criteria exact storage truth для 250 MB/500 MB/2 GB/5–500 GB, `TrackArtifact` source, reservation concurrency, WAV zero contribution, logical deletion и non-authoritative hour estimates? [Acceptance Criteria, Spec §SC-006, SC-017–SC-018]
- [x] CHK022 Позволяют ли criteria однозначно оценить once-per-verified-identity trial across concurrent tabs, linked methods/workspaces, unverified state, exact expiry и zero charge attempts? [Acceptance Criteria, Spec §SC-013]
- [x] CHK023 Измеряют ли criteria одну invoice/operation/entitlement transition, authoritative provider read, immediate-Free cutoff, no retry и late-result precedence для всех payment races? [Acceptance Criteria, Spec §SC-003–SC-004, SC-011]
- [x] CHK024 Достаточно ли измеримы UX outcomes для нахождения plan, unlimited scope, storage/add-on, next charge, cancellation, no-archive/referral target и email-only refund instruction, а также для доступности каждого critical action/fallback? [Acceptance Criteria, Spec §SC-002, SC-005, SC-010]

## Scenario Coverage

- [x] CHK025 Полон ли primary journey `signup → verification → explicit trial → plan/checkout → paid entitlement → renewal/cancel`, включая роль, workspace scope и согласия на каждом переходе? [Primary Flow, Spec §US1–US5]
- [x] CHK026 Полны ли alternate/recovery requirements для abandoned/canceled/unknown payment, duplicate/out-of-order webhook, provider-key expiry, saved=false, late success with/without refusal и manual resume? [Recovery Coverage, Spec §FR-032–FR-049]
- [x] CHK027 Описан ли complete observation journey ручного full/partial merchant-cabinet refund: webhook signal or missed-webhook poll, authoritative GET/list, receipt truth, daily registry, internal gap и zero customer refund state? [Recovery Coverage, Spec §US6, FR-055–FR-056, FR-087–FR-091]
- [x] CHK028 Полны ли storage-full/over-capacity scenarios на Free, Trial и `Личном`: local Record/Stop, archival block, no-archive choice, transcript/notes retention, Free seconds, delete и capacity recovery? [Scenario Coverage, Spec §FR-096, FR-099, FR-106]
- [x] CHK029 Определены ли role-loss/account-close scenarios для future-charge veto, non-transferable payment method, successor consent, invoice access limits и external refund email без новой authorization path? [Exception Flow, Spec §FR-003–FR-006, FR-018, FR-053]
- [x] CHK030 Полны ли promo/referral exception scenarios: expiry, caps, concurrent redemption, conflicting discounts, self-referral, risk review, refund before/after maturity, partial credit use и cancel-scheduled application? [Exception Coverage, Spec §FR-057–FR-069, FR-101, FR-108]
- [x] CHK031 Описаны ли provider/dependency outage and recovery scenarios для webhook, GET/list, receipts, registry, notifications, Temporal timers, database/object storage и emergency stop без uncertain charge или silent stale truth? [Recovery Coverage, Spec §FR-033–FR-044, FR-070–FR-072, FR-087–FR-092]

## Edge Case Coverage

- [x] CHK032 Однозначно ли назначение Free source ranges одному Moscow-month window на границе месяца при partial completion, retry overlap и timezone preference change? [Edge Case, Spec §FR-024, FR-027, SC-014–SC-015]
- [x] CHK033 Определены ли storage edge cases для actual bytes above/below reservation, normalization failure, active artifact supersede, concurrent upload/delete/upgrade и downgrade target below used bytes? [Edge Case, Spec §FR-094–FR-100]
- [x] CHK034 Определена ли precedence при одновременных cancel/refusal, renewal unknown/late success, observed refund, referral maturity, account close и meeting deletion без скрытой money/access mutation? [Edge Case, Spec §FR-044–FR-048, FR-064–FR-069, FR-102–FR-104]
- [x] CHK035 Полны ли fallback requirements, когда mail client, clipboard/share API, browser handoff или hosted YooKassa accessibility path недоступны, без создания внутренней refund form? [Edge Case, Accessibility, Spec §FR-012, FR-074, FR-082–FR-086]

## Non-Functional Requirements

- [x] CHK036 Полны ли security/privacy requirements для session/CSRF/role/RLS, encrypted opaque method, test/prod separation, analytics/replay suppression, safe audit и forbidden email/provider/meeting content? [Security, Privacy, Spec §FR-075–FR-080]
- [x] CHK037 Покрывают ли accessibility/localization/brand requirements каждую account/billing/refund-instruction surface: keyboard, non-obscured focus, labels/errors/live status, 24×24 targets, 200% reflow, no-JS, long Russian copy и clean-room review? [Accessibility, Spec §FR-081–FR-086]
- [x] CHK038 Квантифицированы ли operational requirements для webhook acknowledgement, unknown age, transient purge, fair-use review, receipt escalation, registry completeness, backup/restore, rollback, disk-full и alert ownership? [Non-Functional, Measurability, Plan §Performance Goals, Spec §FR-087–FR-092, FR-106–FR-107]

## Dependencies, Assumptions And Conflicts

- [x] CHK039 Имеет ли каждый default-off launch gate named owner, required evidence, validity/revalidation rule, revocation behavior и blocking consequence для catalog prices, COGS/retention, recurring/binding, receipts/legal, security/QA и global rollout status? [Dependency, Spec §FR-023, FR-038, FR-080, FR-087–FR-092, FR-100]
- [x] CHK040 Зафиксировано ли, что ранее найденные cross-artifact конфликты (refund-case/refund-CLI, 1/10 GB, duplicate inventory и stale migration assertions) устранены в текущих spec/plan/contracts/tasks/checklists и повторно проверены перед реализацией? [Consistency, Tasks §T012–T018, T024–T025, T035–T039, T070–T078]

## Notes

- Отмечайте пункт `[x]` только после того, как требования признаны достаточными либо source artifacts уточнены.
- Для каждого `[Gap]`, `[Ambiguity]` или `[Conflict]` добавляйте рядом finding и ссылку на исправленный source requirement.
- Результат перепроверки 2026-08-06: PASS. Все 40 вопросов получили ответ; checkout и public rollout по-прежнему default-off до внешних approvals/evidence.
