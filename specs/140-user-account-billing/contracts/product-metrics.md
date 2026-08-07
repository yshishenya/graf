# Контракт продуктовых метрик и launch-решений

Дата версии: 2026-08-07  
Владелец схемы: Product owner  
Окно первичной проверки: первые 30 дней после controlled canary

Этот документ задаёт privacy-safe измерения. События содержат только
версию схемы, анонимный cohort key, тип тарифа/цикла, агрегированный статус
и timestamp. В них запрещены email, имена, meeting content, сумма, промокод,
реферальный токен, provider id, карта, receipt contact и свободный текст.

## Outcomes и определения

| Outcome | Определение и знаменатель | Окно/когорта | Launch target | Guardrail и решение |
|---|---|---|---:|---|
| Signup → verification | verified identities / начавшие signup | 24 часа, неделя signup | ≥60% | <45% две недели: остановить paid acquisition и проверить recovery flow |
| First capture → activation | пользователи с успешным capture и transcript/notes / пользователи с первым успешным capture | 7 дней, неделя first capture | ≥45% | <30%: не менять цену, провести usability review |
| Trial → aha | trial-пользователи с capture + transcript/notes / активированные trial | до 7 дней | ≥50% | <35%: пересмотреть onboarding, не увеличивать upgrade pressure |
| Trial → paid | первые paid personal / завершившие trial | 14 дней после trial end | ≥12% | <6% при n≥100: остановить campaign variant и исследовать value fit |
| Monthly/annual mix | annual paid starts / все paid starts | 30 дней, paid-start cohort | ≥25% annual | annual discount/price менять только после COGS и WTP gate |
| Paid retention | paid cohort с активным capture или notes в D30/D90 / paid cohort | 30/90 дней | ≥55% / ≥35% | ниже guardrail: freeze price experiments и review churn reasons без content collection |
| Storage attach/change | paid workspaces с add-on или capacity change / paid workspaces | 30 дней, paid cohort | ≥8% | attach <3%: не расширять ladder, проверить capacity demand |
| Manual reactivation | workspaces, восстановленные новой явной оплатой после confirmed failure / workspaces с confirmed failure | 14 дней | ≥15% | <8%: проверить recovery copy; повторный charge без consent запрещён |
| Billing contact rate | billing-support contacts / paid workspaces | 30 дней | ≤5% | >8%: stop/rollback последнего billing change; содержимое писем не импортируется |
| Refund/chargeback signal | observed provider refunds + chargebacks / paid payments | 30 дней, по provider metadata | ≤3% | >5%: production stop и finance/legal review; GRAF не создаёт refund case |

## Promo и referral guardrails

- Incremental paid conversion сравнивается с holdout без кампании; minimum sample —
  100 eligible users на вариант и 14 дней наблюдения.
- CAC/payback считается только по агрегированным campaign cohort; launch target
  payback ≤3 paid months.
- K-factor (`новые verified users / отправившие приглашение`) target ≥0.15;
  cannibalization (paid users, которые купили бы без reward) ≤20%.
- Liability считается как earned → matured → applied time-credit days; pending
  liability не может превышать 30 дней среднего paid-through cohort на одного
  referrer. Fraud-loss ≤1% paid revenue, support-contact ≤5% campaign cohort.
- Любой guardrail выше порога на двух последовательных окнах останавливает
  campaign/referral issuance, но не отзывает уже применённое время без
  authoritative refund/reversal и отдельного audit.

## Privacy-safe experiment protocol

1. Cohort assignment хранит случайный opaque key и версию эксперимента, а не
   идентификатор пользователя в аналитике.
2. Решение принимается только при minimum sample и полном attribution window;
   ранние числа помечаются `insufficient_evidence`.
3. Вариант считается выигравшим только при target и guardrail pass; при
   конфликте guardrail важнее conversion.
4. Для price/packaging/add-on экспериментов нужны отдельные dated benchmark,
   WTP, p50/p90/p99 usage, compute/storage/egress/backup COGS и gross-margin
   evidence. Без них catalog остаётся `default-off`.

## Public-launch decision threshold

Public launch возможен только при одновременном выполнении: activation ≥45%,
trial→paid ≥12% при минимум 100 завершивших trial, paid D30 ≥55%, billing
contact ≤5%, refund/chargeback ≤3%, gross margin после COGS/backup/egress ≥70%,
и отсутствии красного legal/finance/security/provider/reconciliation gate.
Любой `pilot_blocked` или просроченный owner evidence сохраняет checkout,
binding и renewal в `default-off`.
