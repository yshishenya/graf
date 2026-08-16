# Feature Specification: Локальный контур разработки

**Feature**: `152-local-development-workflow`
**Risk lane**: high-risk-feature (auth, storage, Docker, desktop)

## User Stories

1. Разработчик поднимает локальный API, входит через email-code без OAuth и
   проверяет веб-кабинет.
2. Разработчик запускает macOS-приложение из исходников или disposable debug
   `.app` на том же loopback API.
3. Production deploy выполняется реже, после локальной проверки накопленных изменений.

## Requirements

- Local Compose MUST be separate from production and bind infrastructure to loopback.
- Existing email-code/session/CSRF/tenant/device flow MUST be reused; OAuth, Postal
  and password auth are not required locally.
- Development code display and HTTP cookie `graf_dev_owner_session` MUST require
  non-production environment plus the explicit local flag; production keeps its
  `__Host-` Secure cookie.
- Startup MUST migrate, seed idempotent `local@graf.test`, ensure the MinIO bucket,
  and launch API; processing, outcomes, billing and analytics default off.
- The macOS launcher MUST set explicit loopback cabinet/upload origins and reject
  silent fallback to packaged production.
- The local app builder MUST create a disposable debug `.app` under `.build/local`
  with a separate bundle identifier, no update feed, and a launcher that always
  supplies loopback cabinet/upload origins; it MUST NOT install into
  `/Applications` or reuse the public installer path.
- Production auth, capture, signing, Sparkle, secrets, CD and public defaults MUST
  remain unchanged.

## Success Criteria

- One command reaches local `/login` and login completes with `local@graf.test`.
- Local web and app use the same loopback API and cannot silently use production.
- One local build command produces a launchable `.app` without changing the
  public app or installer artifacts.
- Focused tests, lint, compile and `ci-local.sh --fast` pass.

## Out of Scope

Password auth, shared bypass tokens, legacy header bypass, new auth protocol,
production deployment and a production-like processing cluster.
