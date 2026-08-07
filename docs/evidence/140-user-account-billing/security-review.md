# Billing security and redaction review (automated interim)

**Дата**: 2026-08-07
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

Команды evidence: `uv run ruff check src tests`, 58 focused billing/security/UI
tests и `git diff --check`. Production approval требует отдельной проверки deployment
secrets, PostHog/Yandex configuration и RLS against a live PostgreSQL instance.
Codex Security Deep Scan в этой сессии не стартовал: managed filesystem
permission profile не был предоставлен; локальные contract/unit/webhook checks
выше являются ручным interim evidence, а не заменой live security review.
