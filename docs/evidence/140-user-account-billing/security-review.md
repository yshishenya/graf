# Billing security and redaction review (automated interim)

**Дата**: 2026-08-15
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
- Дополнительная проверка закрыла transport-bypass: destructive account routes
  принимают только cookie-сессию браузера и отклоняют Bearer/
  `X-Auth-Session`, а также смешанный запрос с cookie. Регрессия покрыта
  unit-тестом и disposable PostgreSQL account-lifecycle прогоном (13 passed).

Команды evidence: `uv run ruff check src tests`, focused billing/security/UI и
PostHog autocapture tests (43 targeted checks), `git diff --check`. Стандартный
Codex Security preflight завершён со статусом `ready` (warn: в текущем desktop
runtime доступно 3 usable worker slots вместо рекомендованных 6); независимый
read-only baseline просмотрел 54 файла и дал два исправленных findings.
Production approval требует отдельной проверки deployment secrets,
PostHog/Yandex configuration, distributed edge rate limit и RLS against a live
PostgreSQL instance. Локальные contract/unit/webhook checks и static baseline
не заменяют live security review.
