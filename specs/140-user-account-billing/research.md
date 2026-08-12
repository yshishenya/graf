# Research: личный кабинет, биллинг и growth mechanics

**Дата проверки**: 2026-08-06

**Метод**: официальная документация YooKassa, публичные pricing/help-страницы
продуктов, read-only clean-room аудит web-версии Krisp и свежего
`origin/master` GRAF (`8a405550`). Частные скриншоты, содержимое встреч,
идентификаторы и платёжные данные не сохранялись.

## R1. Product ownership и YooKassa

- **Decision**: GRAF владеет catalog, consent, checkout intent, invoice,
  subscription schedule, one-attempt renewal, entitlement, promo/referral и
  reconciliation. YooKassa выполняет hosted payment/binding, хранит opaque
  payment method и сообщает provider payment/receipt/refund truth.
- **Rationale**: YooKassa даёт payment primitives и recurring payment by saved
  method, но расписание и отказ от будущих списаний остаются обязанностью
  магазина. Hosted redirect не проводит PAN/CVC через GRAF.
- **Alternatives considered**: provider-owned subscription (нет нужного
  GRAF lifecycle); embedded card form/local vault (лишний PCI/security scope);
  generic PSP interface (один provider на launch, преждевременная абстракция).

Источники: [процесс платежа](https://yookassa.ru/developers/payment-acceptance/getting-started/payment-process),
[основы автоплатежей](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/basics),
[оплата сохранённым способом](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-with-saved).

## R2. Hosted checkout, saved method и один renewal attempt

- **Decision**: launch использует server-created RUB payment с
  `confirmation.type=redirect`, `capture=true` и `save_payment_method=true`
  только после отдельного recurring consent. Доступ включается после
  authenticated provider read со статусом `succeeded`; return URL показывает
  только `Проверяем оплату`. Сохраняется лишь confirmed
  `payment_method.saved=true` opaque id и безопасная маска.
- **Decision**: GRAF создаёт ровно одну automatic renewal operation на период.
  Confirmed failure или отсутствие confirmed success к `paid_through` сразу
  проецирует `Free`; grace/dunning/new-key retries отсутствуют. Transport
  `unknown` разрешается тем же operation/key/GET и блокирует pay-again.
- **Rationale**: пользователь заранее видит сумму, периодичность и способ
  отказа; повторное списание — новый payment с saved method id. Успех без
  сохранённого метода честно даёт текущий период и `method_required`.
- **Alternatives considered**: активация по redirect/webhook body; T+1/T+3/T+5
  retry ladder; small-payment-and-refund binding. Все отклонены как источник
  дублирования или сюрприза. Zero-amount binding остаётся отдельным real-shop
  capability gate; если он недоступен, self-service replacement выключен.

Источники: [сохранение при платеже](https://yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/save-payment-method/save-during-payment),
[отклонённые платежи](https://yookassa.ru/developers/payment-acceptance/after-the-payment/declined-payments).

## R3. Идемпотентность и provider truth

- **Decision**: перед каждым provider POST GRAF сохраняет бессрочный logical
  operation id, provider idempotence key, canonical request hash/snapshot и
  expected environment/shop/amount/currency. В течение provider window повтор
  использует тот же body/key; после expiry blind POST с новым key запрещён до
  GET/list/reconciliation proof или owned manual closure.
- **Decision**: webhook — bounded signal. Endpoint allowlists event/type/size,
  сохраняет dedupe reference и быстро отвечает; worker выполняет authenticated
  GET, проверяет context/amount/currency/metadata и применяет monotonic state
  под DB lock. IP allowlist — defense in depth, не authority.
- **Decision (2026-08-12)**: production webhook использует поддерживаемый
  YooKassa HTTPS-порт `8443`. Отдельный listener на существующем сервере
  сохраняет реальный source IP и применяет опубликованный provider allowlist,
  не меняя общий SNI-router сайта на `443`. Официальный notification envelope
  состоит из `type`, `event`, `object`; локальный dedupe key детерминированно
  выводится из `event + object.id`, поскольку верхнеуровневого event id нет.
- **Rationale**: YooKassa хранит idempotence result 24 часа, тогда как локальная
  exactly-once защита должна пережить этот срок, duplicate/out-of-order webhook
  и restart.
- **Alternatives considered**: webhook-body authority; новый idempotence key
  после timeout; хранение raw webhook. Они отклонены.

Источники: [формат и идемпотентность](https://yookassa.ru/developers/using-api/interaction-format),
[webhooks](https://yookassa.ru/developers/using-api/webhooks),
[списки объектов](https://yookassa.ru/developers/using-api/lists).

## R4. Возврат — только внешний merchant backoffice

- **Decision**: кабинет показывает configured refund/support email, safe invoice
  reference, предупреждение не отправлять card data/meeting content и
  `Написать письмо`. GRAF не принимает заявку, не создаёт case, не хранит
  переписку/основание, не обещает SLA, не рассчитывает сумму, не одобряет и не
  исполняет возврат, не вызывает `POST /v3/refunds`, не формирует refund receipt
  и не показывает status/timeline/result.
- **Decision**: support переписывается по email и вручную выполняет полный или
  частичный возврат в merchant cabinet YooKassa. Отключение будущих списаний —
  отдельное self-service действие `Отключить автопродление`; письмо ничего не
  меняет в recurring authority.
- **Decision**: GRAF хранит только read-only `observed_provider_refund`,
  подтверждённый через `refund.succeeded` signal + GET/list и ежедневный refund
  registry. Observation идемпотентно связывается с original payment и может
  служить входом в отдельно разрешённую entitlement/referral correction; это
  не calculation и не execution. Никакого user-facing refund state нет.
- **Rationale**: это соответствует прямому решению владельца и минимизирует
  product/trust boundary. Merchant cabinet официально поддерживает ручные
  полные/частичные возвраты и чековый состав.
- **Alternatives considered**: public refund form, GRAF refund case/status,
  operator UI/API/CLI и automated refund API. Они сознательно исключены.

Источники: [возвраты в кабинете YooKassa](https://yookassa.ru/docs/support/merchant/payments/refunds),
[refund API — изученная, но исключённая возможность](https://yookassa.ru/developers/payment-acceptance/after-the-payment/refunds).

**Важная проверка launch**: публичная webhook-страница не гарантирует отдельной
фразой доставку события для каждого ручного cabinet refund. Поэтому система не
зависит от webhook: периодический refund list и официальный ежедневный registry
обязательны. Canary должен доказать manual full + partial refund → observation
через webhook или poll → GET → receipt state → registry.

Источники: [API reference](https://yookassa.ru/developers/api),
[ежесуточные реестры](https://yookassa.ru/developers/payment-acceptance/after-the-payment/reports),
[реестры в кабинете](https://yookassa.ru/docs/support/merchant/payments/reports/overview).

## R5. Чеки и финансовая сверка

- **Decision**: payment receipt items являются immutable invoice snapshot; их
  positive totals после скидки точно равны provider amount. Verified primary
  login email используется только как restricted masked contact snapshot.
  `vat_code`, `payment_subject`, `payment_mode`, naming и rounding не
  угадываются — checkout default-off до finance/accounting/legal approval.
- **Decision**: money и fiscal state разделены. `payment.succeeded` подтверждает
  payment/access; `receipt_registration=pending|canceled` создаёт internal
  finance gap. Для ручного refund GRAF только читает refund receipt truth;
  состав и формирование принадлежат YooKassa backoffice.
- **Alternatives considered**: считать email delivery доказанным; создавать
  refund receipt из GRAF; включить checkout с placeholder VAT. Отклонены.

Источники: [чеки при платежах](https://yookassa.ru/developers/payment-acceptance/receipts/54fz/yoomoney/payments),
[чеки при возвратах](https://yookassa.ru/developers/payment-acceptance/receipts/54fz/yoomoney/refunds).

## R6. IA/UX и clean-room reference

- **Decision**: существующий GRAF shell получает один account menu:
  `Профиль`, `Безопасность`, `Уведомления`, `Тариф и оплата`, `Пригласить
  друзей`, `Выйти`. Внутри billing hub: `Обзор`, `Использование и хранение`,
  `Способ оплаты`, `История`, `Скидки`. Plans/checkout/storage — task pages из
  CTA, а не новые постоянные разделы.
- **Rationale**: Krisp объединяет plan, renewal, method и invoice history;
  Otter/Granola/Fireflies отделяют cancellation от конца уже оплаченного
  периода. Это подтверждает знакомую IA, но не задаёт визуальный стиль GRAF.
- **Alternatives considered**: отдельные `Подписка`/`Биллинг`/`Платежи`, team
  seats в personal launch, копирование competitor card/layout/copy. Отклонены.

Источники: [Krisp subscription](https://help.krisp.ai/hc/en-us/articles/5626527210908-How-Krisp-subscription-works),
[Krisp pricing](https://krisp.ai/pricing/),
[Otter cancellation](https://help.otter.ai/hc/en-us/articles/360048593573-Cancel-your-Otter-Pro-subscription),
[Granola cancellation](https://docs.granola.ai/help-center/understanding-granolas-subscription-cancellation-terms),
[Fireflies cancellation](https://guide.fireflies.ai/articles/6637635140-how-to-cancel-fireflies-subscription).

## R7. Тарифы 2026: unlimited core + finite storage

- **Decision**: launch сохраняет предсказуемый `Free → explicit Trial →
  Личный`; paid meetings/minutes/transcription/AI имеют mode `unlimited`, а
  единственная коммерчески расходуемая paid dimension — playback storage.
  Второй paid tier только ради GB не создаётся; один add-on выбирает итоговую
  ёмкость.
- **Rationale**: AI SaaS движется к hybrid pricing, но hybrid/credit economy
  увеличивает cognitive load. Для personal meeting product subscription + один
  expansion metric проще. Krisp и Fireflies публично сочетают unlimited
  capabilities с конечным/расширяемым storage.
- **Alternatives considered**: minute overage, AI credit wallet, second paid
  storage tier, cash referral balance. Отклонены для launch.

Источники: [Stripe — AI pricing models](https://stripe.com/en-sg/resources/more/ai-pricing-models),
[Stripe — SaaS packaging](https://stripe.com/en-fr/resources/more/saas-pricing-and-packaging-strategy),
[Paddle — SaaS pricing](https://www.paddle.com/blog/saas-pricing-models-strategies-fltr),
[Fireflies storage pricing](https://fireflies.ai/pricing?slug=storage).

## R8. Storage и фактический capture package

- **Decision**: authoritative quota — decimal bytes active validated normalized
  `meeting-review.m4a` из существующего `TrackArtifact.byte_length`/lifecycle.
  Не создавать duplicate object inventory. Добавить только transactional
  reservation и reconciled projection/cache.
- **Decision**: Free = 250 MB, Trial = 500 MB, `Личный` = 2 GB; один co-termed
  add-on выбирает total 5/20/100/500 GB. Hour equivalents показываются только
  как non-authoritative estimates.
- **Evidence**: current v5 successful package содержит `manifest.json`,
  `meeting-review.m4a` и один `meeting-transcription.wav`; failed package может
  иметь только manifest. Internal provisional playback estimate ≈29.4 MB/h;
  reproducible benchmark evidence is still required. Поэтому 250 MB≈8.5h,
  500 MB≈17h, 2 GB≈68.1h. Transcription WAV ≈115.2 MB/h, но его customer quota
  contribution = 0; он остаётся lifecycle-accounted recovery artifact.
- **Decision**: accepted deletion/account-close finalization немедленно убирает
  access и quota и отправляет current/legacy primary artifacts в existing purge
  journal, bypassing normal source recovery retention. Backups истекают по
  policy и не являются user recovery.
- **Alternatives considered**: quota по минутам, combined WAV+M4A quota,
  display-only `WorkspaceUsageDaily` как enforcement, новый storage engine.
  Отклонены.

## R9. Trial, Free usage, promo и referral

- **Decision**: trial включается одной явной кнопкой ровно один раз на verified
  `UserIdentity`, без card/recurring consent; unverified identity получает один
  verification CTA. Expiry всегда → Free.
- **Decision**: Free window = 18 000 exact accepted whole seconds в календарный
  месяц с границей `00:00 Europe/Moscow`, без rollover/meeting rounding.
  Admission reserves declared duration; commit принимает только unique
  successful source ranges; failures/releases не списываются.
- **Decision**: promo уменьшает один invoice; referral intro discount не
  stack-ится с promo. Referrer получает не деньги, а 7 days monthly / 30 days
  annual после 14-day maturity, cap 180 days/rolling year. Provider-confirmed
  refund может остановить maturity или создать bounded append-only reversal.
- **Alternatives considered**: automatic trial at signup, card-required trial,
  cash payout, minute wallet и mutable reward balance. Отклонены.

## R10. Repository reuse и minimum architecture

- **Decision**: reuse `ensure_personal_workspace`, membership/session switch,
  `get_web_owner_tenant_scope`, `require_web_csrf`, current tenant context/RLS,
  cabinet `web_routes/settings.py`, templates/fragments/tokens, Temporal client,
  maintenance reconciler, deletion fence/purge journal, `TrackArtifact`, MinIO,
  Postal and `httpx`.
- **Decision**: один новый `billing/` package: catalog, lifecycle, entitlement,
  usage/storage reservation, direct `yookassa.py`, reconciliation and notices;
  DB entities в `db/models/billing.py`; webhook ingress только bounded enqueue.
- **Decision**: новая Alembic revision создаётся от актуальных heads после
  rebase. Старое имя `0020_user_account_billing.py` не использовать: fresh
  master уже содержит `0043_*`/merge revisions.
- **Alternatives considered**: second cabinet shell/SPA, customer identity,
  duplicate storage inventory, second deletion engine, Temporal workflow на
  каждый poll. Отклонены как дубли существующих patterns.

Точные reuse points: `auth/workspace_onboarding.py`, `auth/dependencies.py`,
`db/tenant_context.py`, `db/models/identity.py`, `db/models/admin.py`,
`db/models/ingest.py`, `db/models/deletion.py`, `db/models/lifecycle.py`,
`cabinet/web_routes/settings.py`, `workflows/temporal_client.py`,
`workflows/maintenance_worker.py`.

## R11. Независимая product/market перепроверка 2026

**Дата повторной проверки**: 2026-08-07.

Сравнительные страницы зафиксированы одной проверкой `observed_at_utc=
2026-08-07T17:27:43Z`. Для каждой строки учитываются locale/география, выбранный
monthly/annual или региональный selector, аудитория и seat semantics, cadence,
валюта/tax disclosure и точная единица лимита. Внешние страницы не дают
основания переносить FX/PPP или налоговые предположения в российскую цену.

- **Observed trial benchmark**: Krisp публикует 7-day trial без
  карты с unlimited transcription/recording. Это сопоставимо с
  GRAF Trial, но не с GRAF `Free`.
- **Observed perpetual-free benchmark**: Otter Basic публикует 300
  transcription minutes/month; Notta Free — 120 minutes/month и до
  3 minutes per conversation; Fireflies Free разделяет
  transcription credits/unlimited-transcript mode и total stored-meeting minutes,
  а его актуальная help page указывает 400 minutes storage. Эти
  единицы нельзя напрямую сравнивать с GRAF playback bytes без
  одинаковой retention и media-size модели.
- **Observed individual-paid benchmark**: на проверенных USD
  pages Krisp Core указывает $16 monthly/$8 monthly equivalent
  when billed annually и 10 GB; Otter Pro показывает несколько блоков
  регионального selector (в одном блоке $16.99/$8.49 и в другом $8.33/$4.17),
  1 200 in-app minutes и unlimited storage; Notta Pro — 1 800 minutes/month;
  Fireflies Pro — $18 monthly/$10 annual equivalent и 8 000 storage minutes.
  Это mutable per-seat offers другой географии/валюты, с неодинаковыми tax и
  unit semantics; они не доказывают Russian willingness-to-pay и не
  обосновывают FX/PPP вывод для 790 ₽/7 900 ₽.
- **Inference**: рыночный benchmark подтверждает паттерны,
  но не подтверждает GRAF price/packaging. `Free 300 минут`,
  `Личный` 2 GB, 5/20/100/500 GB ladder и ценность
  system-audio-first capture/privacy/control/no-archive continuation остаются
  гипотезами. Они требуют Russian target-segment/WTP и usability
  evidence, а add-on ladder — ещё и demand по capacity distribution.
- **Decision retained as launch hypothesis**: один paid plan и одна
  expansion dimension — storage — остаются самой простой
  моделью для проверки, а не доказанным value-metric fit. Stripe
  рекомендует начинать с простой модели, но отдельно
  предупреждает о flat-pricing risk для power users. Production gate
  поэтому должен включать p50/p90/p99 accepted minutes, compute,
  storage, egress и backup COGS per usage cohort, gross-margin floor и
  fair-use sensitivity, а не только стоимость archive bytes.
- **Decision retained**: trial запускается явно, без карты и
  автосписания; cancellation остаётся self-service без
  обязательной причины и с доступом до конца периода. Это
  совпадает с прозрачным pattern Krisp и избегает dark
  patterns. Refund не смешивается с cancellation: GRAF даёт
  safe reference/email, а merchant backoffice вручную делает полный
  или частичный возврат в YooKassa.

Источники: [Krisp pricing](https://krisp.ai/pricing/),
[Krisp subscription](https://help.krisp.ai/hc/en-us/articles/5626527210908-How-Krisp-subscription-works),
[Otter pricing](https://otter.ai/pricing),
[Notta pricing](https://www.notta.ai/en/pricing/),
[Fireflies pricing](https://fireflies.ai/pricing?slug=storage),
[Fireflies storage limits](https://guide.fireflies.ai/articles/2631950139-learn-about-transcription-credits-storage-and-rate-limits-for-meetings),
[Stripe AI pricing 2026](https://stripe.com/en-sg/resources/more/ai-pricing-models),
[YooKassa merchant refunds](https://yookassa.ru/docs/support/merchant/payments/refunds).

## R12. Россия-first proxy evidence (2026-08-07)

- Авито Работа × МТС Линк: опрос более 7 000 работающих показывает 16%
  постоянной удалённой работы, ещё 9% сезонного hybrid; видеоконференции
  нужны 26%, автоматическая запись/саммаризация — 15%. Это поддерживает
  сегмент digital-first специалистов, но не измеряет платную конверсию.
- Опрос Ventra/Купибилет, опубликованный «Ведомостями» (июль 2025, 1 250
  респондентов из 17 регионов): 30% тратят от 15 минут на итоги каждой
  встречи, 9% — более 30 минут; 82% готовы иногда делегировать это ИИ, 6%
  уже пользуются такими сервисами. Это подтверждает JTBD «не писать итоги
  вручную», но не доказывает WTP и preference к GRAF.
- Обзор ТеДо рынка транскрибации выделяет безопасность, скорость,
  устойчивость и интеграции, а также сегментацию МСБ/крупных заказчиков.
  Поэтому privacy/control остаются проверяемой гипотезой ценности, а
  enterprise исключён из self-service launch.
- AHD × Yandex B2B Tech оценивают рынок ПО РФ в 808 млрд ₽ за 2025 год и
  отмечают рост cloud/SaaS при требованиях к безопасности и предсказуемым
  расходам. Это макро-контекст и не является TAM/WTP GRAF.

Источники: [Авито Работа × МТС Линк](https://www.cnews.ru/news/line/2026-06-29_avito_rabota_i_mts_link),
[Ведомости](https://www.vedomosti.ru/society/news/2025/08/12/1130975-svoimi-delami),
[ТеДо, press-center](https://tedo.ru/press-center/news-031126),
[AHD × Yandex B2B Tech](https://yandex.ru/company/news/25-02-2026-01).

**Статус**: proxy evidence улучшает обоснование сегмента и JTBD, но T084/T085
не закрыты без интервью/comprehension/WTP и telemetry-backed COGS.

## Resolved unknowns and launch gates

Архитектурных research unknowns нет. Product-market hypotheses
о целевом сегменте/JTBD, WTP, base/add-on packaging, campaign economics и
launch business thresholds остаются неразрешёнными blocking research
questions. Ценностная иерархия уже зафиксирована как проверяемая гипотеза,
но её preference evidence ещё не собрана. Следующие технические
и внешние параметры также намеренно не придумываются и
блокируют production checkout: add-on prices/COGS/value, transcription-source
retention deadline, real-shop recurring/zero-binding/manual-refund observation,
merchant entity, public offer/recurring/refund-email wording, 54-ФЗ/VAT/receipt
mapping, security/RLS/privacy/accessibility/brand review и закрытие глобального
`pilot_blocked`. Это named approval/canary gates, а не разрешение браузеру или
коду подставить placeholder.
