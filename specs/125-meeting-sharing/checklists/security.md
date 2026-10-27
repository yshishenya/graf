# Security Requirements Quality Checklist: Обмен встречами

**Purpose**: Validate that the security/privacy requirements are complete and
testable before implementation and rollout
**Created**: 2026-07-23
**Feature**: [spec.md](../spec.md)

## Authorization and isolation

- [x] Meeting search is explicitly bound to the actor, workspace and meeting
- [x] Internal identity results are limited to authorized active membership
- [x] Every content and mutation surface rechecks server authorization
- [x] Wrong-recipient, expired, revoked, deleted and missing states are privacy-preserving
- [x] Calendar/contact suggestions are explicitly separated from grants and consent

## Tokens, egress and lifecycle

- [x] Scope, audience, download and export invariants are defined independently
- [x] Accepted invitation expiry is explicitly bounded by invitation expiry
- [x] Revoke, rotation, deletion and stale-link behavior are specified
- [x] Raw tokens, email addresses and meeting content are excluded from audit/analytics/evidence
- [x] URL/log/referrer/autocapture token leakage controls are explicitly required
- [x] Delivery `sent`, `failed` and `outcome-unknown` meanings are distinct
- [x] Anonymous invitation acceptance uses a one-time continuation, a
  double-submit CSRF check and no bearer token in the form/login target; GET
  only prepares the continuation and the browser auto-submit/fallback invokes
  the existing POST
- [x] The invited address is encrypted at rest, cleared after acceptance/revoke/
  expiry, and is never reconstructed from client-controlled identity input
- [x] Automatic personal-account bootstrap and account-created notification are
  separate post-commit operations with deterministic, replay-safe delivery

## Abuse, privacy and rollback

- [x] Search, invite, acceptance, rotation and link-resolution rate-limit domains are named
- [x] Public-link abuse approval is required both for creation and resolution
- [x] Contact permission, source freshness and disconnect behavior are bounded
- [x] Referral attribution is opaque, idempotent and separate from access credentials
- [x] External/public/contact/referral rollout and rollback gates are independent
- [x] Deletion copy is bounded to GRAF-controlled systems and retained observability is named

## Rollout gate evidence — 2026-07-24

- Exact-email external delivery is enabled only through the operator flag and
  requires Postal, public URL, credential-encryption key and a generated
  persistent share-identity HMAC secret. The browser and macOS client receive
  none of these secrets.
- The delivery fence commits `sending` before egress; accepted provider
  response is `sent`, pre-egress configuration failure is `failed`, and a
  timeout/5xx/malformed response is `outcome_unknown` with no automatic resend.
- The anonymous magic-link action consumes the opaque continuation once, binds
  the invited address from encrypted server state, creates only a personal
  account, and commits the summary grant/session before starting the account-
  created notification workflow. The notification stores only status/failure
  metadata and masks the address in the email body.
- Durable actor/device rate limiting allows at most 10 invitation attempts per
  hour; duplicate active invitations are fenced by normalized identity hash,
  meeting and a partial unique index.
- Contract/integration evidence covers token URL/log/referrer scrubbing,
  metadata-only email and pre-auth landing content, exact verified-recipient
  acceptance, the full recording page/egress rechecks, bounded expiry, revoke
  and deletion. Public links, contacts and referral attribution remain
  disabled.

## Notes

All items pass as requirement-quality checks. The evidence above approves only
the bounded exact-email rollout; public links, contacts and referral remain
separate gates.

## Независимая проверка требований T048 — 2026-10-27

Повторно проверены все 20 пунктов качества требований; все подтверждены по
spec, plan и contract. Для T048/#4454 обязательны настоящий текущий поиск
`summary-sharing.js` → `/meetings/{meeting_id}/summary-sharing/recipients`,
повторная проверка владельца/`can_share`, границ пространства и удаления, а
также отсутствие скрытого обращения к провайдеру или импорта контактов.
Старый `/share-recipients` и проверки строк не заменяют текущий путь.

Будущая приёмка должна наблюдать отсутствие запросов Contacts/провайдера и
изменений grants, invitations, delivery, membership, consent и состояния
контактных/календарных источников после поиска и выбора подсказки. Штатный
служебный учёт частоты поиска разрешён и не является импортом контактов.
Проверки используют только синтетические данные; новый индекс контактов,
хранилище или provider connection не требуются. Это PASS требований для
начала тестового среза, а не PASS будущей реализации или разрешение rollout.
T042–T047 остаются вне приёмки. Подробный отчёт:
`f125-t048-precheck.md` (внешний отчёт); исполняемые проверки описаны в
[quickstart T048](../quickstart.md#проверка-t048--2026-10-27).

## Независимая итоговая проверка T048 — 2026-10-27

В новых тестах авторизация и общий поиск не подменены: проверены разрешённый
владелец, чужой пользователь/пространство, неизвестный адрес и удаление.
Снимок строк 23 связанных таблиц сохраняет grants, invitations, delivery,
membership, consent и calendar/source state; служебный rate-limit исключён
осознанно. Ловушки сетевых транспортов и Temporal запрещают скрытый выход.
Отрицательный контроль вызвал оба ожидаемых HTTP-отказа от provider request
и браузерный отказ от Contacts access; исходный расширенный профиль затем
прошёл 67/67. Замечаний в границах T048 нет; 20 checked / 0 unchecked.
Рабочие провайдеры, контакты, доставка и production не проверялись и не включались.
Итоговый отчёт:
`f125-t048-final-review.md` (внешний отчёт); результаты и границы сохранены в
[quickstart T048](../quickstart.md#проверка-t048--2026-10-27).
