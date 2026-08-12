# Billing security and redaction review

**Дата**: 2026-08-12
**Lane**: high-risk backend/privacy; checkout remains disabled by default.

Проверено локально:

- webhook body ограничен 256 KiB, JSON разбирается без сохранения raw payload;
- checkout callback URL строится только из настроенного HTTPS `public_base_url`,
  а не из входящего `Host`; webhook replay fingerprint включает только bounded
  event/status/amount metadata и не сохраняет provider body;
- provider confirmation URL допускается только по HTTPS и YooKassa host allowlist;
- YooKassa API base URL также ограничен HTTPS и allowlist хостов, без userinfo,
  query или fragment;
- payment method хранит только Fernet-sealed opaque reference и маску `•••• 1234`;
- refund path — только внешнее `mailto`; product refund mutation/case/status отсутствуют;
- billing audit/analytics payloads используют allowlist и не принимают card,
  secret, email body, meeting content или provider object identifiers;
- destructive billing/account actions требуют CSRF, owner scope и повторной
  проверки authority/version;
- отключённые external identities исключены из auth callbacks, account/share
  lookups, verified-recipient email delivery и notification email selection;
  явное подтверждение email в signup/share flow реактивирует только identity
  того же active account и не создаёт duplicate provider subject;
- billing tables включены в RLS inventory.
- Browser PostHog autocapture теперь проходит тот же forbidden-field guard,
  что и server-built activation events; email-like DOM metadata получает
  fail-closed `posthog_autocapture_rejected` и не отправляется provider.
- Trial eligibility дополнительно требует active+verified `ExternalIdentity` и
  ownership `Workspace`; `UserIdentity.status=active` сам по себе не считается
  подтверждением.
- Designated `billing_owner_id` проверяется на финансовых страницах и
  mutation paths; successor-owner checkout остаётся отдельным re-consent
  сценарием и переводит ownership только после создания hosted payment.
- Оба webhook-маршрута fail-closed без `X-Billing-Webhook-Secret`; production
  reverse proxy обязан передавать этот заголовок только после allowlist сетей
  YooKassa и TLS-проверки. Authoritative provider GET остаётся reconciliation,
  а не заменой ingress-аутентификации.
- Provider object IDs проходят общий ASCII allowlist (`[A-Za-z0-9._-]`, 1–160
  символов) до сохранения и до credential-bearing GET; path traversal/query
  injection в payment/receipt URL закрыты отрицательным тестом.
- Product-analytics POST ingress ограничен 256 KiB до Pydantic и имеет bounded
  process-local IP limiter (120 запросов/60 секунд); production edge всё равно
  обязан применять distributed limit для нескольких API replicas.
- Дополнительный static/runtime review подтвердил: webhook provider event IDs
  проходят общий ASCII allowlist; canceled initial checkout закрывает локальные
  operation/invoice сразу; entitlement grant разрешён только для
  `initial_checkout`; smoke cleanup удаляет referral time-credit children до
  workspace.
- Desktop billing handoff allowlist покрывает plans/discounts/checkout return и
  checkout status; paid usage показывает фактически принятое время без
  fabricated paid allowance.

Финальная техническая проверка T080:

- standard Codex Security scan `50d7bf52-a460-4a8a-b538-4e3bf0a33be0`
  завершён без reportable findings по семи trust boundaries: secrets/config,
  webhook/provider, auth/CSRF, tenant RLS, analytics, audit/logging и
  support-email;
- focused security/CSRF/RLS/webhook/audit/redaction suite — `38 passed`;
- disposable PostgreSQL billing RLS suite — `10 passed`;
- production metadata-only probe: `106/106` прикладных таблиц имеют enabled и
  forced RLS; checkout и emergency stop выключены, billing secrets mounted
  read-only;
- production edge negative matrix: untrusted `:8443` webhook — `403`, legacy
  webhook на `:443` — `404`, direct backend без injected secret — `401`;
  `/health/live` и `/health/ready` — `200`.

Scan выполнялся последовательным fallback без независимого subagent baseline,
потому что в момент запуска session policy запрещала delegation. Он был
закреплён на `a4dc8b89`; последующие изменения до release tag `v2026.08.12.1`
были нерелевантными для проверенных trust boundaries и дополнительно прошли
focused security regression. Это закрывает технический review T080, но не
самоутверждает независимую Security-подпись и не заменяет positive provider
delivery/canary: они остаются fail-closed launch-gates T078.
