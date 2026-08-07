# Billing security and redaction review (automated interim)

**Дата**: 2026-08-07
**Lane**: high-risk backend/privacy; checkout remains disabled by default.

Проверено локально:

- webhook body ограничен 256 KiB, JSON разбирается без сохранения raw payload;
- provider confirmation URL допускается только по HTTPS и YooKassa host allowlist;
- payment method хранит только Fernet-sealed opaque reference и маску `•••• 1234`;
- refund path — только внешнее `mailto`; product refund mutation/case/status отсутствуют;
- billing audit/analytics payloads используют allowlist и не принимают card,
  secret, email body, meeting content или provider object identifiers;
- destructive billing/account actions требуют CSRF, owner scope и повторной
  проверки authority/version;
- billing tables включены в RLS inventory.

Команды evidence: `uv run ruff check src tests`, focused billing tests и
`git diff --check`. Production approval требует отдельной проверки deployment
secrets, PostHog/Yandex configuration и RLS against a live PostgreSQL instance.
