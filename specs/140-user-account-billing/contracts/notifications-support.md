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


## Реферальный бонус: постановка и доставка

Срез T070/#4926 (события) и T068/#4922 (сквозная проверка), FR-064–072,
FR-101 и FR-108. Уведомление описывает уже зафиксированный переход,
не текущее состояние на момент чтения письма.

- Доступность: после окончания ожидания запись стала `available`, но
  бонус ещё не применён. Для Free он ждёт первого собственного подтверждённого
  платного периода либо истекает через 12 месяцев. Если в той же транзакции
  запись стала `applied`, ставится только письмо о применении. Повторный
  проход по `available` не создаёт письмо.
- Применение: запись стала `applied` и сохранён фактический интервал.
  При частичном остатке лимита письмо указывает только применённые дни.
  До применения количество дней в письме не обещается: лимит может измениться.
  При нулевом остатке отклонение не ставит письмо. Для `cancel_at_period_end`
  продлевается только последний срок обслуживания по FR-108; списание не
  планируется. Правила начисления, платежи и чеки не меняются.
- Отмена бонуса: после сохранённого `reversed` письмо сообщает об отмене
  бонуса и направляет к истории. Оно не описывает возврат и не обещает
  сокращение оплаченного срока или денежный долг. В ожидании, при открытой
  проверке, истечении и отклонении этот срез не ставит писем. Правила скидки
  приглашённого не меняются.

Получатель — первоначальный пригласивший, записанный в связанной атрибуции,
пока тот же аккаунт активен и владеет тем же личным пространством журнала.
Идентификатор получателя в очереди неизменен. Новый владелец, плательщик,
приглашённый и другие участники не заменяют пригласившего. При объединении
аккаунтов прежняя атрибуция не даёт права получателю, у которого она
сохранилась лишь как история: не следовать `merged_into_user_id`, не выбирать
нового получателя для уже поставленного письма или нового события по старой
привязке. Независимая действующая атрибуция проверяется по обычным правилам.
Отсутствие права на письмо не меняет право на бонус.

Проверки полномочий выполняются при постановке и при взятии письма на
отправку. Для всех трёх видов нужен текущий активный подтверждённый адрес и
действующее разрешение на необязательную почту. Исключения FR-072 для
обязательных финансовых, защитных и чековых писем сохраняются.

- Подтверждённое отсутствие права, адреса или согласия: письмо не ставится;
  уже поставленное получает терминальное `suppressed`. Получателя не менять.
- Ошибка чтения при постановке: не угадывать состояние. Ошибка откатывает
  транзакцию перехода вместе с очередью; следующий штатный проход источника
  проверяет переход заново. Отдельных повторов или рассылки задним числом нет.
  Если источник не может продолжить, его штатная диагностика фиксирует
  неуспешный проход без содержимого письма.
- Временный отказ проверки взятого письма до транспорта: `retry` со
  счётчиком, не более пяти суммарных попыток, не раньше следующего штатного
  прохода (не менее 60 секунд). При исчерпании — `failed` с безопасным кодом
  причины, без обращения к транспорту. Если состояние очереди не удалось
  записать, не обращаться к транспорту и не считать попытку сохранённой.
- После обращения к транспорту: известный повторяемый отказ использует
  прежний предел попыток; неопределённый исход автоматически не повторяется.

Событие идентифицируется внутренним UUID записи бонуса и видом перехода.
Очередь и финансовый переход сохраняются вместе; откат не оставляет письма,
повтор не создаёт дубликат. В письме допустимы только:

| Событие | Поля письма |
| --- | --- |
| Доступность | Вид события и дата истечения из записи; без обещания количества дней. |
| Применение | Вид события, сохранённое число применённых дней, начало и конец сохранённого интервала. |
| Отмена | Вид события и дата сохранённого перехода; без обещания пересчёта срока или суммы. |

Даты показываются в МСК. Во всех письмах одно действие: открыть `/referrals`
на настроенном публичном адресе GRAF. Ссылка не меняет выбранное пространство.
Если личных пространств несколько, пользователь выбирает нужное штатным
переключателем, а кабинет показывает контекст выбранного пространства и
читает только историю действующего владельца под RLS. При отсутствии права
история не раскрывается. В ссылку и текст не попадают идентификаторы
пространства или провайдера, токены, данные приглашённого или материалы встреч.
Исторические письма без новых полей не дополняются догадками.
