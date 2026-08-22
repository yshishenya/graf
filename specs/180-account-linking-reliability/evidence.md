# Evidence: Надёжное подключение способов входа

**Дата**: 2026-08-21
**Branch**: `180-account-linking-reliability`
**Base HEAD**: `f043691a3b6f9caaec40a396a636614d1b6594e9`
**Lane**: high-risk auth/RLS/product flow, полный Spec Kit.

## Инцидент и root cause

Production HTTP 500 при подключении Яндекс ID возникал при создании
`auth_callback_states` из обычного request-контекста, которому forced RLS
запрещает эту операцию. Исправление переводит web и API start в bounded
`auth_bootstrap`, создаёт callback state, затем возвращает exact request
context для session/membership/source-identity проверок.

Миграция `0076_account_linking_rls` дополнительно:

- разделяет callback/provider-link/account-merge policies по операциям;
- разрешает callback доступ только по exact state nonce;
- связывает account-merge context с exact session, callback identity,
  provider-link state, survivor/source users и intent;
- сохраняет fail-closed organization/workspace boundaries.

## Реализованный путь

- web/API/embedded provider-link start, callback и confirm;
- direct link и cross-profile merge для email, Яндекс ID и VK ID;
- preview, blockers, confirm, cancel, restart и relogin;
- invalid/denied/expired/reused/unavailable/reauth recovery;
- concurrency locks, `populate_existing`, idempotency и atomic mutation;
- recovery-safe unlink и сохранение последнего способа восстановления;
- provider-aware copy, terminal OTP recovery и missing callback recovery.
- browser-bound OAuth и email completion; unbound API callback не устанавливает
  browser session;
- purpose-separated server-keyed HMAC для login, signup и authenticated
  email-link codes;
- exact active verified `provider=email` proof: email metadata Яндекс/VK не
  доказывают владение другим профилем;
- exact initiating identity через session claims fingerprint, включая несколько
  identity одного provider;
- единый first-party redirect validator, public OAuth throttling и provider I/O
  вне event loop;
- atomic revoke provider sessions/device bindings и direct relogin после unlink;
- resolved-blocker/stale-preview restart без заведомо неработающего confirm.
- workspace switch пересчитывает session fingerprint для целевой workspace;
  unlink проходит по всем активным workspace пользователя и отзывает provider
  sessions/device bindings с детерминированным порядком блокировок.
- callback throttling использует только IP и exact state buckets; browser
  получает first-party recovery response с `Retry-After`.

## Validation

### Production-equivalent PostgreSQL/RLS matrix

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/contract/test_account_merge_contract.py \
  tests/contract/test_account_routes.py \
  tests/contract/test_auth_contracts.py \
  tests/integration/test_account_lifecycle.py \
  tests/integration/test_account_merge.py \
  tests/integration/test_rls_postgres_policies.py \
  tests/integration/test_web_owner_session_context.py \
  tests/unit/test_provider_links.py
```

Первичный результат: **301 passed**. После независимого security/code/UX review,
Ponytail simplification и финальной remediation выполнен повторный объединённый
прогон account/RLS suites: **323 passed**, 2 dependency warnings, 265.37 s;
isolated PostgreSQL container удалён harness-ом. Покрыты exact app
role/NOBYPASSRLS, browser/API separation, exact provider/email proof,
session fingerprint, start/callback throttling, denial, replay, concurrency,
stale/blocked restart, revoke и bounded rate-limit bucket growth.

Две финальные DoS-регрессии — browser OAuth start до state/adapter и остановка
attacker-controlled buckets после blocked IP — отдельно прошли в isolated
PostgreSQL: **2 passed**, затем вошли в объединённые **323 passed**.

### Дополнительные view-model/provider units

```sh
cd apps/server
.venv/bin/pytest -q tests/unit/test_settings_view_models.py tests/unit/test_provider_links.py
```

Результат после синхронизации canonical provider label: **13 passed**,
2 dependency warnings.

### Static/browser checks

- `infra/scripts/ci-local.sh --fast` после remediation: **1132 passed**, server lint pass,
  Python compile pass, legacy-audio architecture guard pass; isolated
  PostgreSQL container удалён harness-ом.
- Первый fast-gate обнаружил устаревший packaged schema-head assertion
  `0074_linked_workspace_proofs`; guard синхронизирован с
  `0076_account_linking_rls`, targeted test и полный fast-gate прошли.
- Ruff по всем изменённым Python files: pass.
- `node --check .../cabinet.js`: pass.
- `git diff --check`: pass.
- OTP static/UI contract и blocker-state primary/secondary hierarchy:
  **2 passed**, 2 dependency warnings.
- Browser wide/390, DOM, console и screenshots:
  [design-qa.md](design-qa.md).

## Review и ограничения

- Независимый security review обнаружил login/session swapping, offline email
  code brute force, OAuth/email metadata proof confusion, unsafe redirect forms,
  unreleased provider sessions, отсутствующий public throttling и blocking I/O;
  все P0-P2 исправлены и закрыты regression tests.
- Финальный security pass дополнительно обнаружил отсутствие throttling на
  browser OAuth start и рост attacker-controlled buckets после blocked IP. Оба
  P2 исправлены, покрыты PostgreSQL-регрессиями и независимо перепроверены;
  остаточных P0-P2 нет.
- Независимый code/UX review обнаружил resolved-blocker и stale-preview тупики,
  неточную same-provider session lineage, устаревший OTP static contract и
  слабую иерархию blocker actions; исправления включены до closeout.
- Официальный bounded Codex Security scan
  `c531df02-7cee-4f70-aeb8-d44ed7394f64` завершён с **0 активных findings**.
  Он покрывает account-linking/auth-merge surface, а не весь server package;
  две последние remediation отдельно проверены на текущем working tree.

- Commit, release, migration execution в production и deploy не выполнялись:
  для них требуется отдельное approval.
- Конкретная production-запись пользователя не изменялась.
- In-app Browser policy заблокировала прямой visual capture
  `/desktop/settings/account`; embedded parity подтверждается shared templates
  и automated route/runtime tests, но не заявляется как отдельный visual proof.

### Повторная проверка после PR review

- Unit/contract subset: **105 passed**, 2 dependency warnings.
- Изолированный PostgreSQL account/workspace/merge harness: **64 passed**,
  контейнер удалён harness-ом.
- Strict app-role/NOBYPASSRLS migration/provider-link subset: **2 passed**,
  32 deselected.
- Ruff по затронутым Python files и `git diff --check`: pass.
- Новый review после commit `6b66f8c7` подтвердил три замечания: гонку unlink/OAuth
  session issuance, чрезмерную отзывку другой same-provider identity и потерю
  Telegram из attachable settings UI. Все три исправлены в текущем working tree.
- Повторный локальный PostgreSQL harness для затронутых auth/UI suites: **87
  passed**, 2 dependency warnings; в том числе новые Telegram web/embedded и
  same-provider fingerprint regression cases.
- `infra/scripts/ci-local.sh --fast`: **1167 passed**, server lint, Python
  compile и legacy-audio guard: pass.
- Ruff по затронутым Python files и `git diff --check`: pass.
- Production migration/deploy, release tag и GitHub Release по-прежнему не
  запускались.

### One-personal-space correction

- Merge contract/integration/onboarding matrix: **97 passed**.
- Strict app-role/RLS regression subset: **4 passed**.
- Synthetic 4 + 10 path: survivor personal space contains **14** meetings
  after merge; no meeting deduplication; audio, transcript, processing and
  summary rows retain their meeting IDs and move to the survivor root.
- Source personal root is deleted when no dependent rows remain. If a legacy
  non-meeting reference remains, the root is hidden as an ownerless `linked`
  row and excluded from user-facing listing/activation.
- Workspace contract/UI path: one personal space plus separately listed
  corporate access through membership/invitation.
- Current-worktree browser smoke: local server on `127.0.0.1:8082`, disposable
  database, login → settings → account/security → workspace; Yandex start
  reached external consent without HTTP 500; wide and 390 px captures had no
  relevant console errors.
- `infra/scripts/ci-local.sh --fast`: **1167 passed**; lint, compile and
  legacy-audio guard passed.
- This correction has not been committed, migrated in production, released or
  deployed. No production user record was changed.
