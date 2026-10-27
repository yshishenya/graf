# Quickstart: Проверка Share Feature 125

## Scope

This guide validates the first safe delivery: internal authenticated
summary-only sharing, capability-aware UI, calendar-backed internal suggestions,
recipient-bound links, revoke/expiry and security negatives. The B2C exact-email
path is implemented behind its operator gate with metadata-only delivery,
exact-identity acceptance, one-step auth/automatic first-account bootstrap and
replay-safe grant exchange. The current exact-email preset opens a full
recipient-bound recording page with summary, timestamped transcript, playback,
canonical audio download and combined export; each egress request rechecks
authorization, lifecycle and policy. Exact-email external delivery is enabled
in the controlled production rollout after the deploy-gate passed; public links,
address-book permission and referral conversion remain disabled unless their
independent gates are explicitly enabled in a synthetic environment.

All names, addresses, meeting IDs and meeting content in this guide are
synthetic. Do not use a real mailbox, token, transcript, audio file or private
calendar contact.

## Prerequisites

From the repository root:

```sh
cd /Users/yshishenya/.codex/worktrees/fa7e/crisp
specify --version
```

Use the repository's normal test environment and fixtures. The default settings
must keep the following false; production overrides only the first flag after
the external-delivery gate passes:

```text
share_external_invitations_enabled=false  # synthetic/default
share_public_links_enabled=false
share_team_audience_enabled=false
```

## Focused automated checks

Run the focused unit/contract/integration checks after each implementation
phase:

```sh
cd apps/server
pytest -q \
  tests/unit/test_recording_workflow_access.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_recording_share_invitation_contract.py \
  tests/integration/test_meeting_share_links.py
```

Add the Feature 125 tests named by `tasks.md` for:

- capability projection and no request when external invitations are disabled;
- recipient search bound to meeting and `can_share`, escaped search text and
  bounded results;
- display-name/email/calendar deduplication;
- internal summary-only grant, API-returned recipient-bound link and Copy link;
- revoke, rotation, expiry and parallel duplicate action;
- accepted invitation inheriting bounded expiry;
- accepted invitation returning a separate grant token and replaying the same
  grant URL only for the same verified recipient;
- domain invariant enforcement independent of request schema;
- token/log/header/analytics negative checks using synthetic values.

Then run:

```sh
git diff --check
```

## Manual acceptance matrix

Use one synthetic owner, one active workspace user, one calendar-matched active
user and one unknown external address.

### A. Share opens only on explicit action

1. Open a meeting detail page in browser cabinet and embedded desktop cabinet.
2. Activate `Поделиться` once.
3. Confirm one modal appears, the recipient field receives focus and the opener
   regains focus after close/Escape.
4. Reload with JavaScript disabled or with a stale fragment and confirm the
   server still controls access and Share does not auto-open.

### B. Internal recipient

1. Search synthetic display name and synthetic verified email.
2. Confirm result is limited to active current-workspace identities.
3. Confirm a calendar-matched result has a `Календарь` source label.
4. Choose the result and explicitly open summary-only access.
5. Confirm the access list updates, Copy link uses only the returned URL, and
   the recipient can view summary but not transcript/playback/download/export.
6. Revoke and confirm the next controlled request is blocked.

### C. External exact-email capability

1. In the synthetic environment, enter `recipient@example.test` and confirm the
   request is the explicit full-recording/view-only preset with download/export
   capabilities and carries no meeting content.
2. Confirm the delivery state distinguishes `sent` (Postal accepted the
   request) from `outcome_unknown` (the network result was not confirmed).
3. Confirm exact verified-email acceptance creates no workspace membership and
   creates a separate bounded grant token.
4. For a new synthetic recipient, open the invitation URL and confirm the
   minimal transition shell automatically submits the existing CSRF-bound
   acceptance form. Confirm the magic link creates the personal account
   automatically before the response redirects to the stable
   `/shared-meetings/{meeting_id}?workspace_id=...` page. With JavaScript
   disabled, confirm the same page exposes only the single `Открыть запись`
   fallback action. Confirm the result page exposes summary, timestamped
   transcript, playback, audio download and the existing combined export
   control, but no workspace/calendar/service details. No password, code or
   separate `/sign-up` step is shown or required. Confirm the account-created
   notification is queued after commit and contains only the masked address,
   meeting title and links to GRAF/settings.
5. Revoke the accepted grant and confirm the page, playback, audio download and
   content-export endpoints all block the next request. Repeat with expiry and
   deletion.
6. In a second synthetic run with external delivery disabled, confirm no POST
   is made to `/share-invitations`, the value is preserved and the UI offers an
   internal alternative.

### D. Lifecycle and race negatives

1. Use synthetic invitations with pending, sent, expired, revoked and
   outcome-unknown states.
2. Confirm each has a distinct bounded next action.
3. Accept immediately before expiry and confirm grant expiry is no later than
   invitation expiry.
4. Accept after expiry, after revoke and after meeting deletion; all responses
   are generic unavailable and no meeting metadata leaks.
5. Submit duplicate actions from two tabs and confirm one active grant/invite
   and bounded audit evidence.

### E. Calendar and address-book privacy

1. Link a synthetic calendar event with internal, declined, stale and external
   participants.
2. Confirm only the current authorized context is suggested and source/freshness
   is visible.
3. Confirm attendee presence does not create a grant or change recording state.
4. In browser-only mode, confirm no Contacts permission is requested and typed
   email remains available according to policy.
5. Only after a new scope decision returns native picker T046, use a synthetic
   fixture to confirm only the selected address enters the recipient flow and
   no full contact list is sent. T046 is NOT_PLANNED for the current MVP; this
   scenario is conditional and has no runtime PASS claim.

### F. Accessibility and presentation

Check browser and embedded surfaces in dark/light themes, 320 CSS px width,
200% zoom, keyboard-only navigation, VoiceOver labels, increased contrast and
reduced motion. Confirm no horizontal scroll, focus loss, hidden disabled action
that still fires a request, or reuse of competitor code/assets without rights.
Observable reference fidelity follows Constitution VII, including literal
functional wording; required accessibility/privacy deviations remain explicit.

## Security checks

Use synthetic marker strings and inspect application/proxy test logs, response
headers, browser history/autocapture fixtures and audit JSON:

- zero raw share/invitation/referral tokens outside the intended one-time
  response;
- no transcript/audio/summary text/private contact data in email or pre-auth
  landing/analytics; authenticated full recipients see only their granted
  result package;
- no directory enumeration without authorized meeting context;
- no wildcard search expansion;
- no cross-tenant or wrong-recipient access;
- no stale token access after revoke, expiry, rotation or deletion;
- rate-limit response is bounded and privacy-preserving.

## Repository gate and release boundary

Исторические команды и результаты ниже сохранены для исходных поставок.
Для текущего среза используйте явную полосу проверок из действующего
`docs/agent-guidance/release-and-validation.md`; команда без `--fast`/`--full`
больше не выбирает полосу автоматически. Текущая проверка T048 описана отдельно
в конце этого файла.

Команда из исходного плана, не текущая команда запуска:

```sh
infra/scripts/ci-local.sh
```

For a release of this slice, run the documented CD dry-run first and attach
validation evidence, Russian changelog and rollback readiness. Exact-email
external delivery may be enabled only with the server-side Postal and HMAC
secret settings; public links, address-book/provider lookup and referral
attribution remain disabled.

## Validation record — 2026-07-24

- Focused Feature 125 share/access/auth matrix: 50 passed; the targeted
  invitation-auth/provider-workspace regression passed separately.
- `swift test --package-path apps/macos`: 624 passed, 0 failed;
  `ContractValidation`: pass; legacy-audio guard: pass.
- `infra/scripts/ci-local.sh`: pass after synchronizing with `master` — macOS
  624 passed; PostgreSQL 2,255 parallel + 41 strict passed, 2 skipped; Ruff,
  Python compile, RLS boundary, compose config and deployment evidence scan
  passed. The runtime OpenAPI drift found during merge was fixed by adding the
  five missing `SummaryCandidateResponse.reason_code` enum values and the
  focused drift test passed.
- CD dry-run and execute: pass for branch `125-meeting-sharing` and deployed
  SHA `2db3d4ccd2541fbc7701b5803ef8049d2c2cc709`; migration head
  `0035_meeting_share_security`, backup/restore rehearsal, disposable RLS
  probe, runtime/worker readiness, production smoke and automatic dispatch
  passed. Automatic retry, backfill, range and normalization maintenance are
  recorded by the deploy gate as required post-deploy follow-up checks.
- External exact-email rollout verification: provider configuration,
  credential-encryption key,
  generated share-identity HMAC secret, durable actor/device invitation limit,
  at-most-once delivery fence, token-scrubbing and revoke/deletion evidence
  passed in production config gates for both API and worker. Postal network
  reachability returned an auth-protected response without sending a message;
  a live email was intentionally not sent without a consented test recipient.
  Public links, address-book/provider lookup and referral attribution remain
  disabled.
- macOS local artifact `2026.07.24.3` was built as
  `apps/macos/.build/installer/graf-local.pkg` with `GRAF Local Code Signing`;
  SHA-256 is `4cb73bdc94d8d18aba3597794d34fc1abfb9f0276f3f9351bac9445dbf51a197`;
  the package is unsigned and has no Developer ID or notarization evidence.
- Synthetic browser/embedded contract coverage includes both `/meetings/.../share`
  and `/desktop/.../share`; no meeting content, live credentials or real
  contacts were used. Live production public-link, Contacts/provider and
  referral gates remain disabled; exact-email is the only enabled external path.

## Validation record — 2026-07-24 post-review hardening

- Focused PostgreSQL/RLS/auth/Share regression matrix: `22 passed`; the
  broader focused Feature 125 and security/access matrix also passed. The
  checks cover the read-only invitation continuation context, durable auth-code
  throttling, provider email-verification updates, Share retry/confirmation
  states, notification outcome reporting and initial calendar suggestions.
- `infra/scripts/ci-local.sh`: pass — macOS `624 passed`; PostgreSQL `2,260
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  Ruff, Python compile, compose config and deployment-evidence scan passed.
- Repeat security/code/Ponytail review: no critical findings. The lookup RLS
  context is `USING`-only, rate-limit scopes use keyed HMAC, invitation rows
  commit before Temporal dispatch, and unknown delivery outcomes do not trigger
  an automatic duplicate email.
- Product/accessibility review is complete at the static/contract level,
  including error, retry, keyboard, combobox, focus-return and clean-room
  checks. Screenshot-based authenticated browser review was not executable in
  this environment because no authenticated local GRAF tab was available and
  the production URL was blocked by the in-app browser policy; this is not
  claimed as rendered visual evidence.
- This section records the pre-deploy review evidence. The release CD gate has
  since completed successfully; the production closeout below is now the source
  of truth for the deployed SHA and migration head.

## Production closeout — 2026-07-24

- `infra/scripts/cd-remote.sh --execute --branch
  codex/125-meeting-sharing-review-fixes`: pass. Production runtime SHA is
  `9a44d9af9c0bce0c4a75b6d497657492f44c818a`; migration head is
  `0037_auth_rate_limit_buckets`.
- Backup/restore rehearsal, RLS probe, database-role boundary, Temporal and
  processing-worker readiness, media-worker boundary, production smoke,
  automatic dispatch and final `health/live` plus `health/ready` checks passed.
  Backup reference:
  `/opt/projects/2brain-rec/backups/20260724T113944Z`.
- Runtime configuration verification passed in both API and delivery worker:
  external invitations and email login are enabled, Postal is configured and
  the public base URL is configured. No live email was sent without a
  consented synthetic recipient.
- The rebuilt macOS package is
  `/Users/yshishenya/.codex/worktrees/fa7e/crisp/apps/macos/.build/installer/graf-local-release-125-v4.pkg`,
  version `2026.07.24.4`, SHA-256
  `112a5f2419d8517a0ef5d9fde26ebac0564bf966d01897576ecb7878c2e5d936`.
  It is local-only signed/unsigned for distribution purposes; Developer ID,
  notarization and public artifact publication are not claimed.

## Production delivery incident follow-up — 2026-07-24

- A metadata-only production check found that an external invitation could stay
  queued in the UI and then become `outcome_unknown` without reaching the
  mailbox. Worker logs showed DNS failure before the Postal request reached the
  provider; no meeting content or email body was included in the investigation.
- Root cause: `rec-processing-worker` had the Postal API settings and secret but
  was not attached to the external `postal-network`, so `postal-web` was not
  resolvable from that worker.
- Fix: production Compose now attaches the worker to both `rec-private` and
  `postal-network`; the Compose contract test asserts this boundary and that the
  Postal network remains external.
- The hotfix was deployed at exact SHA
  `7b601cf94b7f1a8183dc55e8651d2851c4b0eee7` with backup
  `/opt/projects/2brain-rec/backups/20260724T121617Z`; CD backup/restore, RLS,
  migrations, readiness, smoke and automatic dispatch passed.
- Post-deploy metadata-only checks confirmed the worker is healthy, joined to
  `postal_postal-network` and `twobrain-rec-private`, and resolves `postal-web`.
  No live email was sent by the operator. Existing `outcome_unknown` rows are
  not resent automatically; cancel the old invitation and create a new explicit
  invitation after the hotfix.
## Candidate validation — 2026-07-24 magic-link slice

- Focused synthetic magic-link, RLS, account-bootstrap, email-template and Share
  contract matrix: `25 passed`; static UI/contract checks: `24 passed`.
- `infra/scripts/ci-local.sh`: pass — macOS `631 passed`; PostgreSQL `2,419
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  Ruff, Python compile, JavaScript syntax, Compose config and deployment-evidence
  scan passed. The live destructive RLS probe was not run in this local
  environment (`postgres_test_database_required`); this did not fail the gate.
- The candidate migration head is `0041_share_account_created_email`; it is not
  deployed. No live mailbox delivery was sent. Email assertions use synthetic
  recipients and verify masked addresses, safe meeting metadata, post-commit
  notification state, replay rejection and no duplicate send after an unknown
  provider outcome.
- Static/contract UX evidence covers the native dialog, copy hierarchy,
  confirmation and delivery states, keyboard combobox, focus restoration,
  narrow viewport and browser/embedded parity. A rendered authenticated browser
  screenshot was not claimed because no authenticated local GRAF session was
  available in this environment.

## Validation record — 2026-07-25 invitation acceptance recovery and recording package

- Focused invitation/Share regression matrix: `33 passed`, including the
  anonymous preview, magic-link account bootstrap, full recording page,
  transcript/playback/audio/export routes, revoke recheck, updated CTA copy and
  the post-commit notification failure-isolation case.
- `infra/scripts/ci-local.sh`: pass — macOS `637 passed`; PostgreSQL `2,420
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  pinned Ruff, Python compile, Compose config and deployment-evidence scan
  passed.
- The local RLS hardening boundary reported `blocked` because no live
  disposable PostgreSQL URL was provided to that separate destructive probe;
  the same CI run completed its isolated PostgreSQL test phases successfully.
- No live mailbox delivery, deployment or authenticated browser screenshot was
  used. The external recording package was validated only with synthetic
  PostgreSQL fixtures; production rollout still requires explicit approval.

## Validation record — 2026-07-26 release closeout

- Focused invitation/Share regression matrix: `44 passed`, with only the known
  pytest/httpx deprecation and fixture-rewrite warnings.
- `infra/scripts/ci-local.sh`: pass — macOS `639 passed`; PostgreSQL `2,426
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  ContractValidation, Ruff, Python compile, Compose config and deployment-
  evidence scan passed.
- The local RLS hardening boundary reported `blocked` because it was not given
  a live production or separate disposable PostgreSQL URL; no destructive
  production probe was attempted. The isolated PostgreSQL test phases passed.
- Browser smoke used only synthetic local data: the summary invitation CTA and
  full-recording recipient page returned HTTP 200 without console errors. No
  live mailbox delivery or private meeting content was used.

## Validation record — 2026-07-26 direct invitation-link acceptance

- Focused direct-link regression matrix: `21 passed`, including summary/full
  invitation shells, no metadata preview, raw-token hygiene, POST-only magic
  acceptance, account bootstrap, replay, revoke and recording egress checks.
- `infra/scripts/ci-local.sh`: pass — macOS `639 passed`; PostgreSQL `2,438
  passed, 1 skipped` in parallel and `41 passed, 1 skipped` in strict mode;
  ContractValidation, Ruff, Python compile, Compose config and deployment-
  evidence scan passed.
- The local RLS hardening boundary reported `blocked` because no live
  production or separate disposable PostgreSQL URL was supplied; no
  destructive production probe was attempted. The isolated PostgreSQL phases
  completed successfully.
- The production browser navigation used for diagnosis timed out, so no live
  rendered screenshot or console-clean claim is made. This change is validated
  only with synthetic local fixtures until the release deploy gate is approved.

## Проверка T048 — 2026-10-27

Область: #4454, существующая T048, полоса `Active Spec Kit slice`.
Изменены только тесты и доказательства: код продукта, схема, зависимости и
настройки не меняются. Проверен действующий путь `summary-sharing.js` →
`/summary-sharing/recipients` → `owner_meeting` → `search_share_recipients`,
а также прежний `/share-recipients`, который использует тот же поиск.

Из корня репозитория, в штатном изолированном PostgreSQL:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused -q \
  tests/unit/test_recording_workflow_access.py \
  tests/unit/test_meeting_sharing.py \
  tests/contract/test_recording_share_ui_contract.py \
  tests/contract/test_recording_share_invitation_contract.py \
  tests/contract/test_meeting_sharing_contract.py \
  tests/contract/test_summary_sharing_runtime_contract.py \
  tests/integration/test_meeting_share_links.py \
  tests/integration/test_invitation_delivery_workflow.py \
  tests/integration/test_summary_sharing.py \
  tests/integration/test_summary_sharing_account_merge.py
```

Результат: **67 разных проверок PASS, 0 SKIP**; изолированный контейнер удалён
штатным runner. Python и пакеты соответствуют текущему `uv.lock`.
Браузерный тест использует существующий Playwright 1.63.0 и настоящий Jinja2
fragment с `summary-sharing.js`; новые зависимости не добавлены.

- В Chromium выбор подсказки и ввод неизвестного синтетического email
  добавляют только локально выбранных получателей. Наблюдаются только загрузка
  страницы и ожидаемые GET `/link`, `/auto-send`, `/recipients`; нет POST,
  сторонних HTTP-запросов, обращения к Contacts, разрешениям или native bridge.
- Настоящий API возвращает ровно разрешённую workspace identity; неизвестный
  адрес даёт пустой результат. Пользователь без права отправки, другой tenant,
  чужая встреча и удаляемая встреча получают общий отказ без списка людей.
- До и после поиска совпадают строки таблиц встречи, identities, membership,
  consent, provider links, календаря, grants, invitations, публикаций,
  batches/deliveries, уведомлений и egress audit. Служебная запись ограничения
  частоты поиска допускается. В проверке нет подключённого календарного
  поставщика или разрешённого источника контактов.
- Ловушки реальных HTTP-транспортов и Temporal запрещают скрытые provider
  запросы и запуск доставки. Отрицательный контроль временно подставил вызов
  поставщика контактов в оба маршрута и Contacts API в браузере: все три
  проверки ожидаемо отказали; тестовые файлы восстановлены побайтно, затем
  весь приведённый профиль прошёл. Продуктовые файлы при этом не менялись.

Это приёмка только T048. Она не заменяет ручную матрицу всей F125, проверку
работающего приложения, выпуск или production. T042–T047 остаются открытыми;
Contacts/provider, referral и внешняя отправка этой проверкой не включаются.
Перед слиянием нужны `governance-fast`, `macos-pr`, `pr-metadata` на точном
SHA и проверенной основе, затем общий `scripts/validate-pr-checks.py`.

## Проверка проекта T047 — 2026-10-27

Область: #4453, полоса `Active Spec Kit slice`, только проект будущего
подключения контактов. Обязательные результаты T047 находятся в research §4
и contract §8.1: delegated read-only scopes, операции/поля/лимиты, TTL,
отключение/поздние ответы, русский текст согласия и серверная авторизация.
Это ручная проверка документов, предусмотренная исходной issue, а не
исполнение Google/Microsoft integration. T046 и включение остаются отдельно.

1. Сверить scopes и допустимые операции с официальными ссылками research §4.
   Убедиться, что контактное право не добавляется к обычному входу, не
   обещает выборочное OAuth-разрешение, не разрешает запись или directory.
2. Проверить contract §8.1: TTL 0 для постоянного/server cache, 60 секунд
   для памяти диалога; ограничения источника/контекста и ранняя очистка;
   поздний ответ не восстанавливает результат. Срок проверяется при выборе.
   Общий срок поиска с warmup — 5 секунд; timeout/429/401 не запускают
   фоновый повтор. Поисковая строка, URL/body поставщика исключены из обычных
   журналов, traces, diagnostics и autocapture, включая ошибки.
3. Прочитать текст согласия целиком: права аккаунта, временная память,
   запрет неявного доступа, предел отключения и сохранённый ручной ввод.
4. Проверить все три независимых checklist и нулевой незакрытый остаток
   требований именно T047. Старые отметки T048 не являются его приёмкой.
5. Выполнить `git diff --check`, `python3 scripts/check-development-process.py`
   и `python3 scripts/check_spec_kit_governance.py`; проверить точную связь
   T047/#4453 и сохранение остальных task IDs/описаний/открытых задач.

Продуктовые тесты T048 выше не являются доказательством работы провайдера
и не требуют повтора из-за документальной правки. Исполняемая матрица перед
будущим включением задана в contract §8.1 и остаётся невыполненной. Перед
принятием проекта требуются независимое ревью, отсутствие CRITICAL/HIGH
в анализе среза и три GitHub-проверки точного SHA/основы; затем merged PR
и proposed/actual live `validate-issue-closeout.py` для #4453.

### Результат документальной проверки T047

Все пять шагов выше выполнены: исходные критерии #4453 сопоставлены с
research §4/contract §8.1, новые строки проверены на секреты и частные данные.
Независимый проверяющий повторно открыл официальную документацию Google/
Microsoft и подтвердил проект: requirements 17/0, security 23/0, UX 21/0,
всего 61/0. Первоначальные замечания и дополнения по сроку ожидания/журналам
устранены; итоговый отчёт `f125-t047-precheck.md` хранится вне репозитория.
Повторный анализ: 42 FR, 21 SC, 77 исходных task IDs; в срезе T047
CRITICAL 0 / HIGH 0 / MEDIUM 0. `git diff --check`, проверки процесса и
governance PASS; prerequisites подтверждают активную F125. Отмечена только
T047. Продуктовые тесты и OAuth-запросы не запускались, результаты T048
не присвоены этому проекту. PR/merge/live-closeout остаются последующими
обязательными шагами; runtime-матрица §8.1 не выполнена.

## Проверка решения T046 — 2026-10-27

Полоса: Active Spec Kit slice, только отмена дополнительного плана #4451.
Сверить решение spec с plan/research/contract §8, условным E5 и ссылками на
data-model/scenarios: native Contacts сейчас не обещан. Проверить сохранение
ручного email, текущих подсказок, всех защитных требований и полного §8.1 T047.
Сравнить с основой все 77 строк задач: T046 остаётся `[ ]`, остальные отметки,
описания и порядок неизменны; отдельно указаны владелец, причина и возврат.

Для принятия решения нужны независимые requirements/security/UX checklists,
анализ без CRITICAL/HIGH, `git diff --check`, проверки процесса/governance и
три GitHub-проверки точного SHA/основы. После слияния перечитать #4451,
добавить обоснованный комментарий, закрыть как NOT_PLANNED и проверить
state/reason/comment. Валидатор COMPLETED для отмены неприменим.
Никакие продуктовые/аппаратные тесты не заявляются: их результаты T048
не принимают native picker. Установленное приложение, OAuth, выпуск и сервер
не меняются. Остальные незавершённые критерии F125 сохраняются.

## Проверка проекта T043 — 2026-10-27

Область: #4449, полоса `Active Spec Kit slice`, только договор будущей
referral-атрибуции в data-model §7 и contract §9.1. Исходная issue допускает
ручное ревью документов. Эта матрица проверяет полноту проекта; работающий
сбор, хранение, удаление и доставка событий ею не принимаются.

| Случай | Ожидаемый договор |
|---|---|
| Новый точный получатель; явное auth-действие создаёт аккаунт, затем разрешённый summary view | Одна signup conversion; CTA, setup и first own capture — отдельные этапы |
| Вход в существующий аккаунт, только GET/click/письмо или подсказка | Ноль новых signup; нет неявных grant/account/membership/consent/delivery |
| Повтор, две вкладки, потеря ответа; несколько приглашений/workspaces | Одна conversion на invitation/grant и исходное auth-событие нового канонического аккаунта; атомарный учёт, без вращения токена |
| Пересылка, другая identity/workspace, подмена scope | Общий отказ; ссылка не заменяет серверную exact-identity проверку и не расширяет доступ |
| Self/связанные verified identities, неоднозначная identity, bot/существующий rate limit | Ноль signup conversion; без fingerprint, объединения людей по домену или нового антифрод-сервиса |
| До срока и ровно `now == eligible_until` | До срока допустим только полный разрешённый переход; на границе — отказ; срок равен минимуму 90 дней/expiry приглашения/expiry grant и не продлевается повтором |
| Revoke/rotation, начало удаления встречи/аккаунта, потеря internal membership; позднее событие | Использование сразу прекращается; старое событие/новая ссылка не восстанавливают связь |
| Выключенное измерение, потеря основания, rollback или недоказанная идемпотентность | Нет выдачи/обработки/передачи; разрешённый просмотр работает независимо |
| История `until_decision` и отдельное обязательное удаление | Возрастной очистки нет; случай удаления требует основания, охвата, срока, ответственного, результата; неизвестный срок не позволяет закрыть случай |
| Очереди/отчёты, restore, backup и внешние копии | Управляемые копии включены в охват; перед обработкой после restore повторно применены запреты; запрос поставщику не равен подтверждённому удалению |
| Поля, события и одобрения | Нет PII/raw token/content/client tracker; серверные ссылки не передаются поставщику; T042, T044 и T045 остаются открытыми |

Сверить каждый случай с contract §9.1, spec FR-021–023/029–032/042,
SC-008/019, исходной T043 и F273 FR-036/048–050. Проверить согласованность
US2/US5, scenarios §8.4 и Phase 7: signup подтверждён новым аккаунтом и
разрешённым просмотром; CTA/setup не являются его условием. Проверить три независимых checklist, анализ
среза без CRITICAL/HIGH, `git diff --check`, отсутствие запрещённых данных,
`python3 scripts/check-development-process.py` и
`python3 scripts/check_spec_kit_governance.py`. Сохранить все 77 исходных
описаний/порядок задач; T042/T044/T045 и отменённая T046 остаются `[ ]`.

Перед будущим включением T044/T045 эта же матрица требует исполняемых
проверок. Перед закрытием проектной #4449 требуются три GitHub-проверки
точного SHA/основы, merged PR и proposed/actual live
`validate-issue-closeout.py`. Выпуск, установленное приложение, реальные
пользователи и production этим документальным срезом не проверяются.

### Результат документальной проверки T043

11 случаев матрицы сопоставлены с data-model §7/contract §9.1 и исходной
#4449. Независимый итоговый проверяющий подтвердил requirements 19/0,
security 24/0, UX 22/0 — всего 65/0; 32 контрольные суммы рассмотренных
источников совпали перед учётной отметкой. Исторический BLOCK сохранён:
G1–G5 устранены, последнее расхождение signup исправлено в US2/US5,
scenarios §8.4 и Phase 7. Итоговый отчёт `f125-t043-final-review.md` хранится
вне репозитория. Анализ T043: CRITICAL 0 / HIGH 0 / MEDIUM 0.

`git diff --check`, проверки процесса/Spec Kit и канона GitHub прошли;
77 исходных описаний и порядок сохранены. Отмечена только T043. Продуктовые
тесты и сборки не запускались для проектного изменения; прежние результаты
T048 не присвоены T043. Работающее измерение, T042/T044/T045, установленное
приложение и выпуск не приняты. Exact-SHA/base PR gates, merge и proposed/actual
live-closeout #4449 остаются последующими обязательными шагами.

## Проверка решения T042/T044/T045 — 2026-10-27

Полоса: Active Spec Kit slice, только отмена будущего каталога #4448,
дополнительной F125 share-origin attribution #4450 и её испытаний #4452.
Это NOT_PLANNED, не реализация и не успешное исполнение отменённой матрицы.

1. Сверить решение spec с plan и tasks: исходное намерение воронки признано,
   причина — новый приоритет раннего MVP; область, ответственный и возврат явны.
2. Проверить карту условных обещаний spec: Scope/US2/US5, FR021/022/042,
   conversion-части SC008/019, plan/Phase7/coverage map, data-model §7/§7.3,
   contract §9/§9.1, research §3, scenarios §8.4/§9/§11 пункт8/§13.6.
   Сохраняются auth/CSRF, replay-safe grant/account, audit/privacy/deletion/
   delivery/rate-limit/rollback действующего sharing и общие privacy tests.
3. Сверить T042/исходную #4448 и PR #7768: это отдельный отключённый будущий
   каталог без подключения к действующим путям; конкретный рабочий дефект
   безопасности им не исправляется. Словарь contract §9 и принятый T043
   остаются проектом. Общий forbidden_fields guard и рабочий аудит не меняются.
4. Сверить все 77 исходных task IDs/описаний/порядок и прежние checkbox;
   T042/T044/T045 остаются `[ ]`. Не присваивать отмене тесты PR #7768,
   результаты T043, денежную referral F140 или аналитику F273.
5. Провести независимое ревью трёх checklist и анализ без CRITICAL/HIGH;
   выполнить diff/process/Spec Kit проверки, просмотр новых строк на секреты.
   Runtime-тесты не заявляются: код, API, UI, настройки и данные не меняются.
6. Перед принятием нужны три PR-проверки точного SHA/основы и общий
   `validate-pr-checks.py`. После merge закрыть PR #7768 без слияния со ссылкой
   на решение; перечитать каждую issue, добавить причину/факты/PR/пределы,
   закрыть как NOT_PLANNED и сверить фактические state/reason/comment.
   COMPLETED-валидатор не заменяет эту проверку; исходные `[ ]` не меняются.

Возвращение требует нового решения, предусмотренных одобрений, исходных
проверок T042, договора T043 и всей исполняемой матрицы T045 до включения.
Отмена не разрешает сбор событий и не принимает всю F125 или выпуск.
