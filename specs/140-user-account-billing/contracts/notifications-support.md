# Contract: notifications and support

## Notification matrix

| Event | Recipient | Minimum content | Timing |
|---|---|---|---|
| Trial started/ending | user/Owner | exact start/end, once-only rule, no card/auto-charge, choose-plan link | immediately after explicit start, then T-3 days and T-24h |
| Renewal upcoming | Owner | plan, amount/date, masked method, cancel/manage link | T-3 days |
| Payment succeeded + receipt | Owner/receipt contact by policy | amount/period, receipt availability, next date | after confirmed success |
| Renewal failed → Free | Owner | exact paid cutoff, `Free` now, no automatic retry, manual resume link | after confirmed failure/cutoff |
| Renewal outcome unknown | Owner | `Free` now, no second charge, status/support link | at cutoff and material resolution |
| Cancel/resume/method required | Owner | resulting state and date/amount/action | immediately after ledger change |
| Recurring authority refused | verified payer | refusal effective time, future charges stopped, safe status/support link | immediately and persistently after atomic refusal |
| Charged after refusal | verified payer | access remains Free, recurring authority remains off, safe invoice reference and support email instruction | immediately after authoritative late success |
| Storage threshold/add-on | Owner | used/capacity, effect/price/date, delete/manage link | 80/95/100% and change transitions |
| Fair-use review | affected user/Owner | named capability/reason class, effect, review-by ≤24h, appeal/support link; no meeting content | before non-urgent restriction or immediately for urgent containment |
| Referral reward | participant as authorized | invitee discount or 7/30-day credit, cap/expiry/applied interval | maturity/application/reversal |
| Security/account close | account user | action, sessions/cooling date, recovery link | immediately |

Transactional security/financial/receipt messages ignore marketing preference. Each `(logical event, recipient, channel, template version)` is unique. Retry is bounded; failures are visible to operations and never trigger duplicate business actions.

Links open authenticated browser destinations and contain no provider/token/code/PII. Email does not include meeting content or full referee identity. Localization uses event timestamp plus explicit rendered timezone for consequential dates.

## Support flow

Every financial page offers `Скопировать номер для поддержки`; the reference maps internally to workspace/object but cannot be enumerated. Payment support uses the configured email and asks only for the safe reference—not card details, provider ids, screenshots or meeting content.

For a refund, the product shows the dedicated address, `Написать письмо`, `Скопировать email` and the warning that this message does not stop future charges. Correspondence, acknowledgement, legal deadlines, calculation, decision and manual YooKassa action are entirely external. GRAF stores no email/case/status and sends no refund-transition notification. `Отключить автопродление` is always presented as the separate immediate future-charge control.


## Снимок подтверждений T048 — 01.11.2026

Подтверждение оплаты сохраняет invoice amount_minor/currency=RUB и фактические
границы предоставленной услуги (grant или отдельные storage segments).
Поле планового интервала FR-105 пока не подтверждено во всех счетах:
его показ при отличии остаётся открытой частью T048. Bonus/trial/current subscription
не заменяют оплаченный срок. Непредоставленная услуга сохраняет отдельное
service-reconciliation сообщение. Чек/следующее списание проверяются в истории,
готовность не предполагается из payment success.

Включение продления сохраняет consumed resume quote catalog_snapshot полную
сумму (storage уже включено) и принятый next_attempt_label: календарная дата
с явной зоной или закрытая фраза о ближайшем времени после подтверждения.
Даты услуги показываются в МСК. Оба сообщения описывают событие в прошлом;
состояние тарифа/согласия на момент доставки не обещается. Только безопасные
поля/ссылки, прежние получатель/event identity/транзакция/rollback/dedup.
Старое сообщение без новых полей направляет в кабинет и не восстанавливает
данные из текущего состояния. Backfill/новая рассылка отсутствуют; вся T048,
T068 и фактическая доставка #7524 этим контрактом не принимаются.
