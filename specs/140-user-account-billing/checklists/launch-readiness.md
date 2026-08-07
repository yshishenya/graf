# Чек-лист качества требований: готовность личного кабинета и биллинга к публичному запуску

**Назначение**: формальный cross-domain review полноты, ясности, непротиворечивости и измеримости требований feature 140 перед реализацией.
**Создан**: 2026-08-06
**Спецификация**: [spec.md](../spec.md)
**Аудитория и момент**: product, UX, security, finance, legal, engineering и release reviewers; обязательный gate перед `$speckit-implement`.

**Примечание**: пункты оценивают качество написанных требований, а не поведение реализации.

## Полнота требований

- [x] CHK001 Определены ли eligibility-состояния trial для ещё не подтверждённого `UserIdentity`, включая причину недоступности, безопасный CTA верификации и обновление eligibility после подтверждения? [Completeness, Spec §FR-022, Contract IA §Billing overview/Plans]
- [x] CHK002 Определены ли отдельные approaching/exhausted thresholds, обязательная copy и recovery CTA для Free processing quota, не смешанные со storage thresholds 80/95/100%? [Completeness, Spec §FR-028, US2]
- [x] CHK003 Определены ли IA и decision point для `Обработать без сохранения аудио` во всех исходных flows — завершение desktop-записи, manual upload и full-storage recovery, а не только на billing usage screen? [Coverage, Spec §FR-106, US2 AC6, Contract IA §Usage]
- [x] CHK004 Зафиксирована ли approved boundary, что после role loss/account close нет claimant-recovery route в GRAF: остаются только безопасная invoice reference и внешний support email, без восстановления доступа или money mutation? [Completeness, Security, Spec §FR-003–FR-005, Contract HTTP §Browser routes]
- [x] CHK005 Распространены ли tenant/RLS requirements на все новые workspace/user-scoped сущности, включая trial activation, Free range ledger, playback inventory, current/legacy transcription-source lifecycle, observed-refund/time-credit и worker paths? [Coverage, Spec §FR-078, Data Model §Transaction boundaries]
- [x] CHK006 Зафиксировано ли, что `awaiting_customer_info` и evidence upload не являются GRAF-состояниями: допустимый канал — внешний support email, а GRAF хранит ноль correspondence/request fields и не обещает SLA? [Completeness, Privacy, Spec §FR-053, Contract Notifications §Support flow]
- [x] CHK007 Полны ли durable-workflow requirements для reservation expiry, WAV retention/purge, playback/source reconciliation, notices и incidents: deterministic identity, restart/replay, terminal states, owner и deadline? [Completeness, Non-Functional, Spec §FR-087–FR-089, Contract Operations §Scheduled operations]
- [x] CHK008 Определён ли единый incident lifecycle для missed transient/WAV purge, orphan lifecycle row и quota/reconciliation gap: severity, owner, containment, notification, evidence, closure и launch-blocking rule? [Completeness, Measurability, Spec §FR-070, FR-089, FR-106, Contract Operations §Incident lifecycle]

## Ясность и однозначность

- [x] CHK009 Определены ли единые правила показа оставшегося trial-времени: округление дней/часов, exact timestamp и timezone во всех web, desktop и notification surfaces? [Clarity, Spec §FR-022, US2 AC1–3]
- [x] CHK010 Определён ли формат отображения Free usage — `N мин M сек` с отдельной меткой лимита `300 минут` — так, чтобы copy не противоречила exact-second ledger и запрету meeting-level rounding? [Clarity, Spec §FR-024, FR-027]
- [x] CHK011 Однозначно ли указано, к какому Moscow-month window относятся reservation и commit, когда job принят до `00:00`, а partial/terminal accepted result получен после границы? [Clarity, Edge Case, Spec §FR-024, FR-027, SC-014]
- [x] CHK012 Определён ли результат, когда accepted source-range duration больше declared reservation или duration metadata меняется при retry, без отрицательного remaining и двойного списания? [Clarity, Edge Case, Spec §FR-027, SC-015]
- [x] CHK013 Полностью ли описан playback admission mismatch/revision flow: actual object-stat больше/меньше reservation, invalid normalization profile, supersede active `meeting-review.m4a` и атомарная смена quota? [Clarity, Spec §FR-094–FR-096, SC-017]
- [x] CHK014 Измеримо ли определены current/legacy transcription-source purge gates: критерии successful transcript import и verified active playback, событие начала retention deadline, policy-version change и потеря verification? [Clarity, Measurability, Spec §FR-094, FR-100]
- [x] CHK015 Однозначно ли задана граница `refusal before provider mutation wins`, включая DB commit/lock, равные timestamps и уже начавшийся outbound request? [Clarity, Spec §FR-044, FR-045, FR-103]
- [x] CHK016 Уточнено ли, что GRAF не задаёт календарь/timezone/праздники или SLA для внешнего refund-процесса, а provider и merchant clocks остаются внешней операционной truth? [Clarity, Measurability, Spec §FR-053–FR-054]
- [x] CHK017 Определены ли как versioned launch-gate values `four-eyes threshold`/`high-value`, допустимые роли и разделение approver/executor для provider/off-provider paths? [Clarity, Security, Spec §FR-055–FR-056]
- [x] CHK018 Зафиксировано ли, что после late-success-after-refusal нет окна выбора `Оставить оплаченный период`: остаются Free, incident и внешняя support-инструкция без product refund mutation? [Completeness, Edge Case, Spec §FR-104, US5 AC6]

## Непротиворечивость артефактов

- [x] CHK019 Сведены ли product/unit-economics/finance/accounting/legal/storage/privacy approvals к одной canonical матрице без расхождений между Product Decisions, FR-023, FR-080, FR-100 и launch contracts? [Consistency, Spec §Product Decisions, FR-023, FR-080, FR-100]
- [x] CHK020 Согласовано ли обещание `чек доступен` после payment success с допустимыми registration states `pending|canceled` и обязательным пользовательским next action для каждого состояния? [Consistency, US3 AC4, Spec §FR-051]
- [x] CHK021 Согласованы ли во всех source и downstream artifacts текущие ёмкости 250 MB/500 MB/2 GB/5–500 GB и удалены ли заменённые 1/10 GB assertions? [Consistency, Spec §FR-093, Plan §Scale/Scope, Tasks §T035/T038, Checklist UX §CHK016]
- [x] CHK022 Используется ли единый subscription/payment vocabulary без скрытого `past_due`, grace или противоречащих друг другу `unknown`, `method_required` и `renewal_resolution_pending`? [Consistency, Spec §FR-039–FR-048]
- [x] CHK023 Определено ли, как account-scoped referral UI выбирает и показывает target workspace для workspace-bound time credit у пользователя с несколькими personal workspaces? [Consistency, Spec §FR-065, FR-068, US8]
- [x] CHK024 Задана ли precedence-матрица между meeting/account deletion, legal/policy hold, WAV recovery retention и normal purge gate, чтобы данные не переживали удаление молча и legal hold не обходился? [Consistency, Recovery, Constitution §IV, Spec §FR-018–FR-019, FR-094]
- [x] CHK025 Согласована ли no-archive copy во всех surfaces относительно трёх последствий: playback не останется, transcript/notes сохранятся, а Free расходует только exact accepted seconds? [Consistency, Spec §FR-027, FR-106, Contract IA §Interaction rules]
- [x] CHK026 Согласованы ли authority/visibility requirements Owner, Admin, Member, original payer и successor Owner для денег, usage, safe claims и сохранённого способа оплаты? [Consistency, Spec §FR-003–FR-006, Actors And Authority]

## Качество критериев приёмки

- [x] CHK027 Можно ли объективно оценить trial requirements для signup-without-activation, linked methods, multiple workspaces, concurrent requests, exact expiry и zero charge attempts? [Acceptance Criteria, Spec §SC-013, FR-022]
- [x] CHK028 Покрывают ли SC-014/SC-015 все измеримые Free-ledger outcomes: window uniqueness, cross-boundary assignment, no rollover, partial ranges, overlap/retry и reservation anomalies? [Acceptance Criteria, Spec §SC-014–SC-015]
- [x] CHK029 Покрывает ли SC-017 объективные outcomes playback-only quota, revisions/supersede, object-stat mismatch, WAV zero contribution и non-authoritative hour estimates? [Acceptance Criteria, Spec §SC-017]
- [x] CHK030 Определены ли измеримые findability outcomes для trial CTA, no-archive path, storage explanation, referral target workspace и refund recovery, а не только общего billing hub? [Acceptance Criteria, Spec §SC-002]
- [x] CHK031 Определяет ли SC-012 объективный evidence record, owner, freshness и pass/fail criterion для каждого approval и global rollout blocker? [Acceptance Criteria, Dependency, Spec §SC-012]

## Покрытие основных, альтернативных и recovery-сценариев

- [x] CHK032 Полон ли primary journey `signup → Free → explicit trial → Free/paid → renewal/cancel`, включая отсутствие карты у trial и fresh consent перед первой оплатой? [Scenario Coverage, Spec §US1–US5, FR-022, FR-031]
- [x] CHK033 Полны ли alternate/recovery requirements для abandoned/canceled/unknown payment, late success with/without refusal, provider-key expiry и manual resume без duplicate charge? [Recovery Coverage, Spec §FR-033–FR-049, US3/US5]
- [x] CHK034 Полны ли over-capacity downgrade requirements: read/export/delete, no auto-delete, archival block, no-archive processing и возврат к paid/add-on capacity? [Scenario Coverage, Spec §FR-096, FR-099, FR-106]
- [x] CHK035 Определены ли recovery requirements при недоступном transient admission: processing не начался, local custody сохранена, Free reservation не consumed, retry/support action понятен? [Recovery Coverage, Spec §FR-027, FR-106]
- [x] CHK036 Покрыты ли promo/referral alternate cases: competing discounts, code expiry/caps, first-touch, self-referral, maturity pause, reversal, cancel-scheduled credit и appeal? [Scenario Coverage, Spec §FR-057–FR-069, FR-101, FR-108]
- [x] CHK037 Полны ли fair-use requirements для notice-before-effect, urgent containment, appeal/review deadline, cleared/confirmed outcomes и неизменности local/data controls? [Scenario Coverage, Spec §FR-107]

## Нефункциональные требования и зависимости

- [x] CHK038 Определены ли accessible fallback requirements для YooKassa blocker, referral copy/share denial, manual link selection, dynamic status announcements и no-JS recovery paths? [Accessibility, Coverage, Spec §FR-082–FR-085]
- [x] CHK039 Полны ли privacy requirements для trial/usage ranges, external safe-reference support channel, WAV evidence, risk signals, notices и incident artifacts, включая retention и forbidden analytics/log fields? [Security, Privacy, Coverage, Spec §FR-075–FR-079]
- [x] CHK040 Заданы ли для real-shop capabilities, reconciliation и default-off gate owner/evidence type, validity/revalidation, revocation behavior, maximum unresolved age, severity-to-blocking matrix и authority повторного enablement? [Dependency, Recovery, Spec §FR-038, FR-080, FR-087–FR-092]

## Notes

- Отмечайте пункт `[x]` только после того, как соответствующие требования либо признаны достаточными, либо уточнены в source artifacts.
- Findings фиксируйте рядом с пунктом со ссылкой на изменённое требование.
- Результат перепроверки 2026-08-06: PASS. Все 40 вопросов получили ответ в spec/plan/contracts/data-model/tasks; launch gates остаются default-off до внешних approvals/evidence.
