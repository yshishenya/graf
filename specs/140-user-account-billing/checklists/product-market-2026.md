# Чек-лист качества требований: product, market и public-launch 2026

**Purpose**: независимо проверить, что feature 140 описывает понятный, честный и коммерчески проверяемый account/billing experience перед public rollout.
**Created**: 2026-08-07
**Feature**: [spec.md](../spec.md), [research.md](../research.md), [IA/UX/UI/CX contract](../contracts/account-ia-ux-ui-cx.md)
**Audience / Timing**: product owner, growth, UX, finance, legal, support и release reviewers; gate перед включением production checkout.

**Note**: это «тесты требований», а не QA реализации. `[x]` означает, что текущие артефакты дают однозначный ответ; `[ ]` означает незакрытый product requirement или launch evidence.

## Product Positioning And Audience

- [ ] CHK001 Определён ли один первичный self-service сегмент для launch с его job-to-be-done, частотой встреч, willingness-to-pay и причиной выбрать GRAF, а не только общее «самостоятельный пользователь»? [Gap, Spec §Scope Summary, §Actors And Authority]
- [x] CHK002 Зафиксирована ли проверяемая ценностная иерархия `system-audio-first capture → контроль/приватность → transcript/notes → predictable billing`, которая формулирует проверяемую гипотезу причин выбора GRAF при более щедрых storage/free предложениях части конкурентов, с явным разделением гипотезы и факта? [Hypothesis, Research §R11, product-market.md §JTBD]
- [x] CHK003 Явно ли отделены personal self-service launch и team/enterprise sales-assisted future без ложных seat/admin обещаний? [Scope, Spec §Product Decisions, §Out Of Scope]
- [x] CHK004 Обосновано ли clean-room использование Krisp/Otter/Notta/Fireflies как pattern evidence, а не как источник копируемой IA, copy или trade dress? [Consistency, Research §R6–R7, Spec §FR-081]

## Packaging, Price And Value Metric

- [x] CHK005 Описана ли одна понятная launch модель `Free + Личный + storage add-on` без credit wallet, minute overage, второго paid tier и скрытой матрицы usage charges? [Clarity, Spec §Launch Tariff Levels, Research §R7]
- [x] CHK006 Задана ли единственная paid expansion metric — exact playback storage bytes — и отделена ли она от unlimited minutes/meetings/transcription/AI? [Clarity, Spec §FR-024–FR-030, FR-093–FR-100]
- [x] CHK007 Сопровождается ли каждое `Без лимита` точным scope, finite archive capacity и двумя recovery choices при заполнении? [Clarity, Spec §FR-030, FR-106, IA Contract §CX copy principles]
- [x] CHK008 Едины ли Free/Trial/Личный/add-on values, decimal units, measured-hour disclaimers, annual saving и catalog versioning в pricing, checkout, account и receipt requirements? [Consistency, Spec §Product Decisions, §Launch Tariff Levels, FR-023, FR-093]
- [ ] CHK009 Требует ли launch gate dated comparable evidence по plan type, geography, currency/tax, cadence, audience и unit semantics, а также target-segment acceptance для 250 MB/500 MB/2 GB, 5/20/100/500 GB и 790 ₽/7 900 ₽ — не только COGS/finance approval? [Gap, Research §R11, Spec §FR-023, FR-100]
- [x] CHK010 Запрещает ли spec публиковать placeholder price/add-on и требует ли new immutable catalog/offer version при любом изменении? [Launch Gate, Spec §FR-020, FR-023, FR-100]

## Acquisition, Trial And Upgrade Journey

- [x] CHK011 Отделена ли registration от explicit once-per-verified-identity trial без карты, recurring consent и автосписания? [Trust, Spec §FR-022, SC-013]
- [x] CHK012 Описаны ли trial eligibility, already-used, active, ending, expired, unverified и concurrent activation states с exact dates/timezone и one safe next action? [Coverage, Spec §US2, FR-022, IA Contract §Screen inventory]
- [x] CHK013 Определены ли контекстные upgrade requirements для Free 80%/100% processing quota, trial T-3/T-1/expiry и первого blocked archival job, включая exact CTA, обещание и non-coercive alternative? [IA Contract §Interaction rules]
- [x] CHK014 Разделены ли activation value и payment conversion: trial даёт product value, а покупка всегда требует fresh price/consent summary? [Consistency, Spec §US2–US3, FR-031–FR-038]
- [x] CHK015 Не превращаются ли promo/referral в обязательный onboarding step и отделены ли они от core account/capture journey? [IA, Spec §FR-010–FR-013, IA Contract §Navigation model]

## Billing Trust, Cancellation And Refund Boundary

- [x] CHK016 Показывает ли initial checkout до оплаты exact today/next amount, period, discount fate, storage, recurrence, consent, cancellation и external-refund boundary, а каждое последующее money action — свои applicable amount/date/consequence? [Completeness, Spec §US3–US4, FR-030–FR-038, FR-047, FR-097]
- [x] CHK017 Описан ли self-service cancel без mandatory reason, retention offer и скрытого повторного списания, с exact paid-through consequence и не более трёх screens? [Trust, Spec §FR-045, SC-005]
- [x] CHK018 Различаются ли `Отключить автопродление`, `Удалить способ оплаты`, `Написать письмо` о возврате и `Закрыть аккаунт` без взаимозаменяемых обещаний? [Clarity, Spec §FR-018–FR-019, FR-045–FR-046, FR-052–FR-056]
- [x] CHK019 Едина ли external-refund boundary в spec, plan, research, data model, contracts и tasks: только safe email/reference в GRAF, а eligibility/calculation/communication/execution — вне продукта? [Consistency, Spec §FR-052–FR-056, Research §R4]
- [x] CHK020 Требует ли public-launch gate утверждённый external support/refund runbook, address ownership, legal copy и response obligations, не выдавая их за in-product SLA? [Dependency, Spec §FR-080, §Dependencies]

## Promotions And Referrals

- [x] CHK021 Определена ли ровно одна price discount на invoice с best-eligible selection и объяснением неприменённой альтернативы? [Clarity, Spec §FR-057–FR-060]
- [x] CHK022 Полны ли promo states и race requirements: valid, expired, ineligible, exhausted, reserved, concurrent redemption, stale preview и safe non-disclosing error? [Coverage, Spec §US7, FR-057–FR-059]
- [x] CHK023 Раскрывает ли referrer screen до share полные 14-day maturity, 7/30 days, 180-day cap, 12-month expiry, non-cash и reversal rules, а invitee landing до attribution — свой discount, first-touch/expiry/privacy без identity disclosure? [Completeness, Spec §FR-061–FR-069, IA Contract §Screen inventory]
- [x] CHK024 Отделены ли paid-through, bonus-until и next-charge, включая cancel-scheduled без скрытого renewal job? [Clarity, Spec §FR-101, FR-108]
- [x] CHK025 Заданы ли business guardrails для promo/referral campaign: incremental paid conversion, CAC/payback, K-factor/cannibalization, earned→matured→redeemed reward liability, fraud-loss/support-contact ceilings и stop/rollback threshold? [Product Metrics Contract]

## IA, UX, UI And CX Coverage

- [x] CHK026 Имеет ли каждый account/billing screen route, actor/scope, primary content, exact actions и normal/loading/empty/error/degraded/terminal states? [Completeness, IA Contract §Screen inventory]
- [x] CHK027 Различены ли user-scoped account и workspace-scoped billing, а Owner/Admin/Member видят только допустимые деньги/actions без утечки чужой authority? [Consistency, Spec §Actors And Authority, FR-001–FR-013]
- [x] CHK028 Объясняет ли каждое asynchronous/degraded state отдельно money truth, access truth, pending work и one safe next action? [CX, Spec §FR-039–FR-049, FR-073]
- [x] CHK029 Описаны ли desktop→browser handoff, offline/browser unavailable, expired handoff и return-to-recording states без поломки local Record/Stop? [Coverage, Spec §FR-012, FR-026, IA Contract §Desktop billing summary]
- [x] CHK030 Последовательны ли help placement, explicit button labels, persistent financial outcomes, non-toast critical states и one-primary-action rule? [Consistency, Spec §FR-073–FR-074, FR-086, IA Contract §Interaction rules]

## Accessibility, Privacy And Supportability

- [x] CHK031 Полны ли WCAG 2.2 AA requirements для keyboard, visible/non-obscured focus, labels/errors, status messages, 24×24 targets, consistent help, redundant entry, 200% reflow и no-JS critical paths? [Accessibility, Spec §FR-082–FR-085]
- [x] CHK032 Отделена ли external YooKassa conformance boundary и описан ли accessible support/manual recovery path при provider blocker? [Accessibility, Spec §FR-082, IA Contract §Interaction rules]
- [x] CHK033 Запрещают ли analytics/replay requirements сбор сумм, promo/referral tokens, receipt contact, method data, provider ids, form values и meeting content? [Privacy, Spec §FR-075–FR-079]
- [x] CHK034 Сохраняют ли account close/deletion requirements честную GRAF-controlled boundary, financial retention/retrieval и YooKassa limits без universal-erasure promise? [Deletion Truth, Spec §FR-018–FR-019, SC-018]

## Business Outcomes And Launch Decision

- [x] CHK035 Определены ли privacy-safe product/business outcomes для signup→verification, first successful capture→transcript/notes activation, trial start→aha→paid, monthly/annual mix, paid cohort retention/churn, storage attach/change, manual reactivation after confirmed renewal failure и support contact rate? [Product Metrics Contract]
- [x] CHK036 Заданы ли metric definitions, denominator, attribution window, cohort, owner, target/guardrail и minimum sample/decision rule для ценовых, packaging и campaign experiments? [Product Metrics Contract]
- [x] CHK037 Объективно ли измеряются findability, cancellation speed, payment exactly-once, entitlement truth, storage truth, promo/referral uniqueness, privacy и accessibility? [Acceptance Criteria, Spec §SC-002–SC-011, SC-013–SC-018]
- [x] CHK038 Имеет ли каждый external launch gate named owner, evidence class, freshness/revalidation, revocation state и fail-closed blocking outcome? [Launch Gate, Spec §SC-012, FR-092]
- [x] CHK039 Запрещено ли считать payment smoke доказательством public readiness без legal/finance/security/QA/support/reconciliation и глобальных product gates? [Consistency, Spec §FR-087–FR-092]
- [x] CHK040 Указаны ли явные public-launch decision thresholds для ценности и бизнеса наравне с system correctness: activation, paid conversion, retained use, gross margin/COGS, billing-contact rate и refund/chargeback signal? [Product Metrics Contract]

## Initial Audit Result

- Закрыто требованиями: 38/40; 2 пункта остаются launch-blocking до внешней
  product-market валидации.
- Открыто: CHK001, CHK009. CHK002 закрыт на уровне формулировки и
  проверяемого протокола; доказательство предпочтения сегмента остаётся частью
  T084 и не подменяется этой отметкой.
- Ключевой вывод: transaction/trust/IA requirements и measurement contract взаимно согласованы; public-launch readiness = **BLOCKED**, потому что ещё не подтверждены первичный сегмент/JTBD, ценностная иерархия и dated target-segment/WTP evidence для упаковки.
- Closeout mapping: T084 закрывает CHK001 и проверяет сформулированную гипотезу CHK002;
  это не заменяет evidence предпочтения. T085 —
  CHK009; T086 закрывает CHK025/CHK035/CHK036/CHK040; T087 — CHK013 и
  cross-artifact recheck.

## Evidence Baseline

- [Krisp pricing](https://krisp.ai/pricing/)
- [Krisp subscription lifecycle](https://help.krisp.ai/hc/en-us/articles/5626527210908-How-Krisp-subscription-works)
- [Otter pricing](https://otter.ai/pricing)
- [Notta pricing](https://www.notta.ai/en/pricing/)
- [Fireflies pricing](https://fireflies.ai/pricing?slug=storage)
- [Fireflies storage limits](https://guide.fireflies.ai/articles/2631950139-learn-about-transcription-credits-storage-and-rate-limits-for-meetings)
- [Stripe AI pricing models, 2026](https://stripe.com/en-sg/resources/more/ai-pricing-models)
- [YooKassa merchant refunds](https://yookassa.ru/docs/support/merchant/payments/refunds)
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
