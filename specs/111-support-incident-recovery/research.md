# Research: безопасное восстановление support incidents

## Decision 1 — Причина фактического сбоя

**Decision**: Исправлять desktop-аутентификацию отчёта, а не GitHub token или private Issue configuration.

**Evidence**:

- Production endpoint существует, а проверка server-side GitHub client прошла с уже смонтированным secret без раскрытия его значения.
- Попытки из установленного приложения получили `401 legacy_header_auth_disabled` до сохранения `SupportIncident`; это соответствует отсутствию нового пользовательского incident в серверном хранилище.
- Установленный клиент отправляет legacy identity headers без session credential. Production специально запрещает этот механизм.

**Rejected**: ослабить production auth или включить legacy headers. Это отменило бы уже установленную session security boundary.

## Decision 2 — Где выполняется authenticated request

**Decision**: Отправлять safe report через текущий same-origin `WKWebView` embedded cabinet.

**Why**: WebKit уже владеет HTTP-only session cookie и получает session-bound CSRF token в cabinet document. `fetch(..., credentials: "same-origin")` использует их внутри WebKit. Native code передаёт только already-redacted report and receives only the bounded status/result.

**Rejected**:

- Копировать cookie в `URLSession` или читать его из shared cookie storage. Такой код ранее уже был удалён, а при новом source state создаёт `csrf_token_missing`; он также смешивает web session with native networking.
- Освободить support endpoint от CSRF. Это расширит CSRF attack surface для authenticated cookies.
- Выдать desktop приложению GitHub credentials или server secret. Это нарушает secret boundary.
- Вводить новый general-purpose device token lifecycle. Для одного metadata-only support route это больше риск и scope, чем безопасный WebKit bridge.

## Decision 3 — Безопасность WebKit bridge

**Decision**: Использовать `WKWebView.callAsyncJavaScript` с typed argument map and a fixed script; never concatenate report content into executable JavaScript.

**Controls**:

- Bridge attaches only to the configured same-origin embedded cabinet and rejects login/external/absent surface before fetching.
- Fixed endpoint and fixed request method are compiled into the script.
- Report is JSON-encoded as an argument; idempotency key is derived server-side-safe report fingerprint.
- WebKit retains cookie and CSRF token; no token/cookie/header is returned to Swift or AppLog.
- Response body is decoded only into the known support response/problem shape and never logged verbatim.

## Decision 4 — Accepted report before Issue egress

**Decision**: Persist the server-redacted report and assign its `CUST-*` correlation number before validating or calling GitHub.

**Why**: GitHub delay/configuration must not erase an already valid user report. The response is `201` only when a private Issue is synchronized and `202` when the server accepted the report but Issue sync is pending.

**Retry model**: A pending incident is retried through an authenticated `sync` action containing only the existing correlation number; the server reloads its retained safe report. It does not ask the desktop to reconstruct or resend diagnostic content. This avoids a new globally privileged worker and keeps external GitHub egress in the existing `rec-api` secret boundary.

**Rejected**: a new global worker or distributed polling service. The existing RLS roles intentionally do not give `rec-api` global maintenance visibility, and distributing the GitHub secret to a processing worker would expand the trust boundary for a narrow recovery flow.

## Decision 5 — Detailed private Issue content

**Decision**: Reuse the existing server redactor and private issue renderer, adding the server correlation number and sync truth to the generated block.

**Why**: It already enforces allowed keys, safe fingerprints, bounded affected identities and redaction. The issue must remain structured and actionable without copying private recording content.

## Decision 6 — Observable readiness

**Decision**: Keep startup configuration validation and expose the support integration configuration state only through the existing internal readiness detail; actual private-repo validation remains part of a safe sync attempt.

**Why**: It distinguishes configuration from availability without exposing a secret or making a public health endpoint perform an external GitHub call for every probe.
