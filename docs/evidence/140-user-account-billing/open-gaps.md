# Открытые launch-gates Feature 140

Статус на 2026-08-11: public launch **BLOCKED**. Это не продуктовый refund
case и не обещание пользователю; документ служит только внутренним
metadata-only реестром незакрытых доказательств.

Автономная реализация account-close/source lifecycle, playback quota admission,
renewal/payment-method authority и billing primitives закрыта задачами T029,
T036, T038, T039, T047, T051, T053 и T075–T077. Storage add-on projection
готова, но self-service purchase остаётся закрытой до ценовой версии каталога.
Refund webhook
backstop проходит bounded cursor pagination YooKassa (до 20 страниц, с защитой
от повторного cursor); payments/refunds registry теперь импортируется только
раздельными metadata-only наборами с completeness hash и gap ownership.
Агрегированные admin metrics, maintenance workflows и отдельный readiness
diagnostic доступны, но live dashboard/alert routing и stop-all-charges drill
остаются операционными launch-gates T078.
Операционный canary runbook и quickstart теперь описывают разделение test/prod,
capability evidence, four-eyes sign-off, emergency stop и rollback; фактический
canary/sign-off остаётся T078. Автоматическая часть T079 усилилась
recoverable promo error, keyboard-safe copy и focus/reflow checks; T080 получил
provider-boundary forbidden-field guard для browser PostHog, provider-ID
path validation и bounded analytics ingress. Остаются
evidence/gates: moderated accessibility/usability и landing review, live
security/RLS review, product-market segment/JTBD, WTP/COGS, upgrade-copy и
финальный cross-artifact closeout (T078–T085, T087).

Referral flow теперь разделяет стабильную workspace-scoped `ReferralLink` и
per-invitee `ReferralAttribution`; email и новый OAuth signup используют общий
binder, а checkout читает собственную attribution после очистки cookie. Для
закрытия функционального риска остаётся обязательный disposable PostgreSQL/RLS
и concurrent signup evidence; внешний canary и product copy gates по-прежнему
не закрыты.

Checkout, binding и renewal mutation нельзя включать, пока владельцы Product,
Finance/Accounting, Legal, Security и QA не внесут версии решений и exact-SHA
evidence в launch runbook.

## Повторный runtime-аудит 2026-08-07

После повторной проверки выявлены дополнительные блокеры, которые нельзя
заменять contract/unit evidence:

- initial checkout теперь имеет bounded provider-GET backstop для сохранённого
  `provider_id`; если POST в YooKassa завершился таймаутом до сохранения этого
  ID, операция всё ещё остаётся `unknown` и требует ручного gap resolution;
- renewal planner создаёт одну deterministic `renewal` operation в reminder
  window, а outbound charge разрешён только в `paid_through` и только для
  `scheduled` без provider ID; локальные unit/PostgreSQL/CI проверки проходят,
  но provider test-shop success/decline/timeout и canary evidence ещё не
  предъявлены;
- receipt registration truth теперь сохраняется монотонно и metadata-only,
  а receipt contact snapshot/54-ФЗ поведение всё ещё требует merchant
  test-shop canary;
- processing free-cap и paid-unlimited helpers подключены к admission и
  проходят focused regression; public checkout всё равно остаётся выключенным
  до controlled canary и finance/legal/security/QA sign-off;
- storage admission подключён к публикации canonical playback, но нужен
  PostgreSQL/RLS прогон с истёкшим trial/paid cutoff и replacement/deletion
  сценариями;
- proxy-level allowlist для webhook описан в runbook, но его фактическая
  конфигурация и live RLS не предъявлены.

## Ремедиация 2026-08-08

Финальный полный CI после этой ремедиации прошёл: 650 Swift-тестов,
ContractValidation, 2833 серверных теста (1 skipped), strict PostgreSQL,
Ruff/Python compile и deployment evidence scan — PASS. OpenAPI contract drift
после nullable billing-полей закрыт и отдельно проверен focused PostgreSQL
прогоном 10/10.

- Исправлены локальные P1 hardening gaps: chunked webhook body bounded до
  `256 KiB`, startup-проверка непустых provider/webhook/referral secrets и
  support email, write-RLS для глобального billing catalog, явные промо/карта
  действия и безопасные reconciliation labels. Renewal operations исключены
  из общего stale-классификатора maintenance; resume теперь требует
  подтверждённый способ оплаты и отдельное согласие; замена активной карты
  честно отключена до доказанной zero-amount binding capability; webhook без
  workspace metadata отвечает retryable `503`, а не теряет событие; renewal
  catalog ищет последнюю effective approved версию, а не только самый новый
  невалидный ряд.
- Storage add-on остаётся fail-closed до появления утверждённых ценовых ключей
  в versioned catalog: UI не создаёт quote/invoice/payment с неподтверждённой
  ценой. Это отдельный merchant/product gate, а не «бесплатное» увеличение
  лимита.
- Не закрыты без внешнего доступа: live proxy/firewall/TLS и PostgreSQL RLS
  probe, test-shop/real-shop canary, merchant/finance/legal/security/QA
  sign-offs, moderated usability/landing, интервью/WTP/usage/COGS и финальный
  Spec Kit closeout. Поэтому public launch остаётся **BLOCKED**.
- Remote readiness audit 2026-08-08 is historical: at that time the billing
  branch and mounts were not deployed. Current exact-SHA runtime evidence is
  recorded in `deployment-2026-08-11-closeout.md`; checkout remains disabled until the
  external canary and sign-offs are complete.
- Local evidence after the renewal/catalog hardening: disposable PostgreSQL
  focused lifecycle suite — 47 passed; `infra/scripts/ci-local.sh --fast` —
  1024 passed, Ruff and Python compile passed. Повторный полный CI также
  завершился PASS: 650 Swift-тестов, ContractValidation PASS, 2833 серверных
  теста прошли, 1 skipped, strict PostgreSQL 42 passed и deployment evidence
  scan PASS. Это implementation evidence, не замена provider canary или
  four-eyes sign-off.

## Runtime evidence 2026-08-11 (historical snapshot)

- `/opt/projects/2brain-rec` на `2brain.dev` был чистым, `master`, exact SHA
  `b511d78bfd9b741bbfa848f91c0164ae21f5302c`; migration head был
  `0057_referral_workspace_scope`. Это исторический снимок до closeout-ветки.
- `/api/v1/health/live`, `/api/v1/health/ready` и `/` отвечают HTTP 200; compose
  services API, maintenance, media-worker, processing-worker, Temporal, MinIO и
  PostgreSQL healthy.
- Production smoke 2026-08-11 завершён PASS: config validation, migration/RLS
  disposable probes и cleanup verification. Metadata-only cleanup удалил 43
  database rows и 3 object keys; residue list пуст. Raw IDs, payloads и secrets
  в evidence не сохраняются.
- `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`; YooKassa provider mutation и
  merchant canary не выполнялись. Результат означает runtime readiness, а не
  public billing launch.

## Runtime recheck 2026-08-11 (latest closeout)

- На deployed SHA `d135b4b18c4ff3231fc303d9cd1f0a0d3194599f` migration head
  `0065_status_refresh_prefix`; live RLS metadata-only probe PASS:
  `104/104` таблиц enabled+forced. Это не закрывает
  edge allowlist/header и независимый security sign-off.
- Этот deploy также проверил отложенную награду referral после status refresh,
  связку ledger с attribution lifecycle, coarse risk-review hold и
  recovery-safe billing UX; focused tests и disposable PostgreSQL RLS suite
  зелёные. Global campaign caps/manual review,
  OAuth/concurrency evidence и ручная accessibility/usability проверка landing
  остаются отдельными launch gates; server-rendered valid/invalid/unavailable
  states и три auth CTA уже реализованы.
- Production nginx пока не содержит подтверждённой YooKassa CIDR allowlist и
  injected `X-Billing-Webhook-Secret`; реальные уведомления поэтому не должны
  включаться. Checkout остаётся `false`.
