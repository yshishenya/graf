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

## Независимая проверка требований T047 — 2026-10-27

- [x] T047: в проекте названы точные delegated read-only scopes, разрешённые
  операции/поля/лимиты, отдельное согласие и серверное владение credentials;
  исключены write, directory и application permissions.
- [x] T047: проект задаёт числовые сроки постоянного и временного хранения,
  очистку при отключении/смене контекста и отбрасывание поздних ответов;
  границы копий GRAF и провайдера описаны раздельно.
- [x] T047: будущий provider search привязан к actor/workspace/meeting и
  актуальному can_share/deletion до запроса и показа результата; provider email
  не становится verified GRAF identity, grant или recording consent.

Предреализационная проверка T047 пока BLOCK: research §4 лишь называет общие
readonly scopes; contract §8 описывает native picker без Google/Microsoft
операций, точного TTL и disconnect policy. Общее сохранение авторизации
задано spec, но provider-specific границы нужно связать с этим контрактом.
Все 20 прежних пунктов повторно рассмотрены в их существующей области;
прошлые отметки качества/приёмки T048 и выключенный provider gate сохранены.
Допустим следующий шаг: уточнить проект в research/contract и повторить
независимое ревью. Это не разрешение реализации/включения provider lookup.
Подробный независимый отчёт: `f125-t047-precheck.md` (внешний отчёт).

## Независимая итоговая проверка проекта T047 — 2026-10-27

Первоначальный BLOCK выше снят после непосредственного повторного чтения
research §4, contract §8.1, spec, plan, tasks, data-model и quickstart.
Официальные страницы Google searchContacts и Microsoft List contacts
перечитаны независимо: выбранные read-only scopes и операции допустимы.
Contract задаёт поля/20 результатов, cache TTL 0 и память диалога 60 секунд,
очистку выбранного/позднего результата и безопасное отдельное отключение.
Контекст/актуальные права/удаление перепроверяются до запроса и результата;
email провайдера не подтверждает identity и не создаёт доступ или consent.
Дополнительно устранены два пробела: общий deadline с warmup 5 секунд
без фонового повтора и запрет query/URL/body в журналах/ошибках/диагностике.
Повторно рассмотрены все **23 пункта: 23 checked / 0 unchecked** именно
как требования проекта. Будущие исполняемые проверки перечислены в §8.1
и остаются обязательными; их выполнение, provider runtime и rollout не
заявляются. Старые ограничения и история T048 сохранены. Итог и хеши:
`f125-t047-precheck.md` (внешний отчёт, итоговое дополнение).

## Независимая проверка решения T046 — 2026-10-27

- [x] T046: требования для любого будущего контактного источника сохраняют
  явное разрешение, минимальный объём, запрет полного импорта, серверную
  авторизацию, отдельность подсказки и доступа, bounded lifecycle и безопасный
  отказ; contract §8.1 T047 остаётся обязательным перед будущим включением.

Повторно рассмотрены все 23 прежних пункта по spec, plan и contract.
Действующие FR-024–FR-027/FR-030/FR-034–FR-035 и §8/§8.1 достаточно
определяют защитные границы. Текст отмены ещё предстоит проверить против
этих неизменённых условий. Это PASS качества исходных ограничений, а не
разрешение native/provider runtime, отмена известного дефекта безопасности
или приёмка всей F125. Требования не удалялись.
Итог: **24 checked / 0 unchecked**; общий gate пока BLOCK по requirements.
Подробности: `f125-t046-checklist-review.md` (внешний отчёт).


## Независимая итоговая проверка решения T046 — 2026-10-27

Текст отмены проверен против всех **24 пунктов: 24 checked / 0 unchecked**.
Spec/plan/research/contract сохраняют явное разрешение, минимальный объём,
запрет полного импорта, серверную авторизацию, безопасный отказ и отдельность
подсказки, identity, consent и доступа. Операционная часть contract §8.1 T047
от «Права и запросы» до §9 полностью совпадает с основой; его сроки, очистка,
отключение, поздние ответы, журналы и будущая исполняемая приёмка сохранены.
Ни известный дефект безопасности, ни обязательная приёмка не отменяются.
Первоначальный общий BLOCK по требованиям снят итоговым ревью; это приёмка
документального решения, а не native/provider runtime, OAuth или rollout.
Подробности: `f125-t046-checklist-review.md` (внешний отчёт).
