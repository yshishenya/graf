# История изменений

Здесь фиксируются заметные изменения продукта.

Продуктовые релизы используют календарные версии вида `vYYYY.MM.DD.N`.
Вспомогательные библиотеки и инструменты могут использовать SemVer, если это
прямо указано в их документации.

## [Unreleased]

### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.6] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Зафиксирован post-deploy closeout для `050`: PR, release, deployed SHA,
  production health и итоговый статус `pilot_blocked` записаны в evidence и
  текущий статус продукта.

### Операции
- Production deploy `050` прошел с `deploy_result=pass` и
  `readiness_verdict=infra_smoke_ready`.

## [2026.06.25.5] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Завершена фича `050`: единая проверка MVP-пути, интерфейса приложения,
  веб-кабинета и текущей продуктовой правды перед заявлением о готовности.
- Зафиксирован результат фичи `050`: текущий продукт остается в статусе
  `pilot_blocked`. Прослушивание, таймкоды, нижняя шкала спикеров, совпадение
  веба и встроенного окна macOS, честный статус macOS-кабинета и документы
  готовности проверены. Еще не закрыты: живое доказательство пользовательского
  production-пути, свежий путь от записи до просмотра, сохраненные итоги на
  текущем production-кандидате и замер скорости на часовой записи.

### Операции
- _Пока нет записей._

## [2026.06.25.4] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В просмотре встречи активный таб `Запись и расшифровка` теперь показывает
  саму расшифровку, а не блок итогов. Нижняя шкала записи яснее показывает
  строки спикеров и интервалы, когда каждый говорил (`feature:049`).

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.3] - 2026-06-25


### Добавлено
- В продукт добавлены сохраненные итоги встречи для MVP. Веб-кабинет и
  встроенное окно macOS показывают краткое резюме, ключевые пункты, решения,
  действия, follow-up, риски, вопросы и ссылки на таймкоды только когда это
  подтверждается расшифровкой (`feature:049`).

### Изменено
- _Пока нет записей._

### Исправлено
- _Пока нет записей._

### Безопасность
- _Пока нет записей._

### Документы
- Уточнена текущая продуктовая правда после closeout `feature:048`: playback
  больше не описан как локальная незакрытая работа, а связан с опубликованным
  релизом и production smoke.
- Обновлена readiness-правда для `feature:049`: blocker
  `notes-action-output` закрывается stored outcomes, но production rollout
  остается отдельным gate до финального пользовательского доказательства.

### Операции
- _Пока нет записей._

## [2026.06.25.2] - 2026-06-25


### Добавлено
- _Пока нет записей._

### Изменено
- _Пока нет записей._

### Исправлено
- В macOS-приложении статус кабинета теперь не считается успешным только
  потому, что задан адрес сервера. Пока сервер проверяется, приложение показывает
  проверку; если сервер недоступен, показывает недоступность; если нужен вход,
  показывает это отдельно (`feature:047`).

### Безопасность
- _Пока нет записей._

### Документы
- _Пока нет записей._

### Операции
- _Пока нет записей._

## [2026.06.25.1] - 2026-06-25


### Добавлено
- Прослушивание результата теперь должно быть видно на обычной обработанной
  записи без ручного включения скачивания аудио. Пользователь слушает запись
  прямо в просмотре встречи, а скачивание и экспорт остаются отдельными
  настройками доступа (`feature:048`).
- Серверный маршрут прослушивания поддерживает частичную отдачу аудио, чтобы
  браузер мог быстро начинать воспроизведение и перематывать запись без прямых
  ссылок на хранилище (`feature:048`).

### Изменено
- Экран результата стал удобнее для проверки встречи: расшифровка остается
  главным содержимым, проигрыватель закреплен внизу, таймкоды ведут к нужному
  месту записи, а дорожки говорящих помогают быстро понять, где кто говорит
  (`feature:048`).

### Исправлено
- Исправляется разрыв после `046`: раньше проигрыватель был доказан на
  тестовой встрече с вручную включенной политикой аудио, но мог не появляться
  на реальных записях пользователя (`feature:048`).

### Безопасность
- Прослушивание остается через сервер: ответы не содержат подписанные ссылки,
  ключи файлов в хранилище, приватные пути, сырой текст встречи или
  диагностический звук (`feature:048`).

### Документы
- Обновлен текущий статус продукта и evidence 046/048: 046 оставлена как
  основа playback-пути, а 048 зафиксирована как исправление видимости для
  обычной записи (`feature:048`).

### Операции
- _Пока нет записей._

## [2026.06.24.2] - 2026-06-24


### Добавлено
- Встречу теперь можно слушать прямо на странице результата: сервер отдает
  безопасный звук для проверки, а не прямую ссылку на файл в хранилище
  (`feature:046`).
- Таймкоды в расшифровке стали кликабельными: пользователь может перейти в
  нужное место записи и быстро проверить конкретную реплику (`feature:046`).
- Веб-кабинет и встроенное окно macOS-приложения показывают одинаковое
  состояние прослушивания и одинаковые переходы по таймкодам (`feature:046`).

### Изменено
- Для записей с двумя дорожками звук для проверки должен включать и локальный
  микрофон, и входящий звук. Если сервер не может безопасно собрать оба источника,
  плеер не притворяется готовым (`feature:046`).

### Исправлено
- _Пока нет записей._

### Безопасность
- Прослушивание результата теперь закрыто теми же правилами доступа, удаления,
  обработки и наличия аудио. Для чужих, удаляемых, неготовых, ошибочных или
  неполных встреч сервер не отдает аудио (`feature:046`).
- Логи и evidence по прослушиванию остаются metadata-only: без сырого аудио,
  текста встреч, ключей хранения, signed URL и приватных путей (`feature:046`).

### Документы
- Обновлен текущий MVP-статус: прослушивание по таймкодам закрыто локальной
  реализацией 046, но общий MVP еще требует финальных проверок, релиза и
  доказательств на проде.

### Операции
- _Пока нет записей._

## [2026.06.24.1] - 2026-06-24


### Добавлено
- Запись теперь проходит весь путь до результата: приложение загружает запись,
  сервер запускает обработку, а в кабинете появляются расшифровка и разделение
  говорящих (`feature:045`).
- Сервер сам стартует обработку после успешной загрузки. Если обработка уже
  идет, второй запуск не создается (`feature:045`).
- В веб-кабинете и во встроенном окне приложения показано, что уже готово:
  загрузка, обработка, расшифровка, говорящие, заметки и ограничения доступа
  (`feature:045`).
- В macOS-приложении появилась более надежная связка записи, очереди загрузки
  и серверного результата. Приложение может подтянуть готовый результат позже,
  даже если запись была загружена раньше (`feature:042`, `feature:045`).
- Проведены отдельные проверки микрофона, Apple Voice Processing и WebRTC AEC3
  для будущей работы над чистым звуком (`feature:037`, `feature:038`,
  `feature:039`).

### Изменено
- Проверка шума, тишины, эха и утечки звука из динамиков в микрофон больше не
  блокирует отправку записи, если сама запись целая и в ней есть нужные файлы
  (`feature:045`).
- Жесткие блокеры остались жесткими: запись не отправляется без разрешений, без
  нужных дорожек, с поврежденными файлами или с ошибками целостности
  (`feature:045`).
- Состояния в приложении стали честнее: отдельно видны локальная запись,
  загрузка, обработка, ошибка, конфликт и готовность результата (`feature:042`).

### Исправлено
- Исправлено обновление уже загруженных записей: если сервер обработал запись
  позже, приложение больше не должно оставлять ее в старом локальном статусе
  (`feature:045`).
- Исправлено сопоставление строк расшифровки и говорящих в кабинете, чтобы
  локальный микрофон и входящий звук не менялись местами в интерфейсе
  (`feature:045`).
- Исправлены русские тексты в кабинете и во встроенном окне приложения: меньше
  технических слов, понятнее состояния доступа, удаления, результата и заметок
  (`feature:045`).
- Исправлены несколько случаев, когда встроенный кабинет в приложении мог
  показать ложное состояние входа или недоступности после переходов внутри
  встроенного браузера (`feature:042`).

### Безопасность
- Диагностика и доказательства проверок остаются без приватного содержимого:
  без сырого аудио, текста расшифровок, ключей, токенов, приватных путей,
  подписанных ссылок и содержимого встреч (`feature:037`, `feature:038`,
  `feature:039`, `feature:042`, `feature:045`).
- Приложение по-прежнему не отправляет аудио напрямую в MediaScribe и не хранит
  ключи MediaScribe на Mac (`feature:045`).

### Документы
- Зафиксировано, что полноценное прослушивание по таймкодам еще не закрыто и
  должно идти отдельной фичей (`feature:045`).
- Зафиксировано, что настоящее эхоподавление и шумоподавление не входят в этот
  релиз и остаются отдельной работой (`feature:044`).
- Зафиксированы оставшиеся MVP-блокеры: чистый звук или честное ограничение,
  прослушивание по таймкодам, заметки/действия или явное отложенное решение,
  финальная проверка владельцем и подписанный установщик.

### Операции
- Серверная часть выпущена на прод как `v2026.06.24.1`.
- Перед выкаткой прошли локальные проверки, сборка продовой конфигурации,
  резервное копирование, проверка восстановления, запуск сервиса и проверка
  работоспособности.
- К релизу приложен локальный пакет macOS для внутренней проверки. Он не
  подписан сертификатом Apple Developer ID и не заверен Apple для внешнего
  распространения.

## [2026.06.18.1] - 2026-06-18


### Added
- _No entries yet._

### Changed
- _No entries yet._

### Fixed
- _No entries yet._

### Security
- _No entries yet._

### Docs
- Добавлены правила release/versioning: CalVer `vYYYY.MM.DD.N` для
  продуктовых apps/services, SemVer `vMAJOR.MINOR.PATCH` для tooling,
  extensions и bootstrap, а человекочитаемый postfix теперь должен жить в
  GitHub Release title, не в stable tag.

### Ops
- _No entries yet._

## [0.1.0] - 2026-06-18


### Added

- Добавлены macOS shortcuts масштаба embedded meeting workspace:
  `Command-Plus` / `Command-Equals` увеличивают масштаб, `Command-Minus`
  уменьшает, `Command-0` сбрасывает к 100%; настройка хранится локально,
  применяется к `WKWebView.pageZoom` без route reload и оставляет native
  Record/Stop/upload truth/local readiness вне масштабируемой поверхности
  (`feature:043`, `T001-T017`).
- Добавлена production-доставка browser-login email-кодов через server-side
  Postal API: отдельные `.env` настройки для Rec, Docker secret для API key,
  fail-closed состояние при недоступной почтовой доставке и подключение
  `rec-api` к внешней сети Postal (`feature:036`).
- Добавлен browser-login по email-коду для web cabinet: `/login`,
  `/login/email/start`, `/login/email/verify`, HttpOnly/Secure owner-session
  cookie, browser-device binding, redirect protected web routes to login, and
  visible OAuth/provider stubs for later implementation (`feature:036`).
- Добавлена browser-регистрация по email-коду без видимого Workspace ID:
  `/sign-up`, `/sign-up/email/start`, `/sign-up/email/verify`, автоматическое
  создание пользователя и membership в серверно заданном workspace, русская
  страница ввода 6-значного кода и Krisp-like HTML-письмо через Postal
  (`feature:036`).
- Добавлен product-owned слой meeting-app mute truth для macOS: `Pause`/`Resume`
  рядом с постоянным `Stop`, подавление локального микрофона во время паузы,
  metadata-only `privacySegments`, target capability matrix, fail-closed
  `meetingMuteTruth` decisions, fixture validator и QA evidence templates без
  claims о third-party meeting-app mute support (`feature:022`, `T001-T048`).
- Добавлен launch-readiness gate `034-mvp-loop-readiness`: metadata-only
  readiness JSON/Markdown report, launch gap register, clean-room reference
  comparison, desktop/web/policy lifecycle evidence notes, bounded claim rules,
  and evidence-backed next-slice recommendation (`feature:034`, `T001-T059`).
- Добавлен validation-only evidence pack `035-mvp-loop-live-evidence`: proof
  установленного `/Applications/2brain Rec.app` Record/Pause/Resume/Stop loop,
  metadata-safe desktop screenshots, latest local artifact validation,
  production route check for `rec.2brain.pro/meetings`, fixture-backed web
  list/detail/governance evidence, and generated readiness/gap outputs
  (`feature:035`, `T001-T032`).
- Добавлен server-owned слой retention/deletion execution: whole-meeting
  deletion requests, immediate access blocking for deleting/deleted meetings,
  metadata-only verification reports, retention policy snapshots and scans,
  local desktop purge task/ack flow, backup expiry truth, dependency truth for
  MediaScribe/Langfuse/workflow/temp/diagnostics, post-egress copy limits,
  lifecycle activity rows, safe retry guidance, and RLS coverage for deletion
  lifecycle tables (`feature:018`, `T001-T066`).
- Добавлен browser/server-owned слой доступа, шаринга, скачивания и экспорта
  встреч: owner/team/shared/denied access states, login-required share grants
  and revoke, server-mediated artifact downloads, policy-filtered export
  packages, metadata-only access/egress activity и truthful post-egress deletion
  copy (`feature:017`, `T001-T045`).
- Добавлен macOS desktop cabinet embedding: приложение открывает `Встречи`
  внутри native shell, встраивает server-owned list/detail route classes,
  сохраняет native Record/Stop/upload truth вне WebKit surface, показывает
  bounded unavailable state и связывает uploaded queue items с review только
  при наличии server meeting identity (`feature:033`, `T001-T042`).
- Добавлен server-owned web cabinet для review встреч: авторизованный список,
  ready/partial/processing/failed detail states, transcript/speaker timeline,
  truthful unavailable notes, gated governance/future slots и desktop-embedded
  routes без native capture controls (`feature:016`, `T001-T048`).
- Добавлена обязанность вести Changelog в репозитории для всех значимых изменений.
- Добавлена macOS desktop upload queue: durable local queue, truthful retry/upload states,
  server-mediated ingest mapping and compact queue UI (`feature:014`, `T001-T030`).
- Добавлен server-side MediaScribe processing pipeline: durable workflow/job/result
  state, idempotent Temporal workflow identity, server-side dual-track submit,
  poll/import, content-safe status API, failure classification, restart-safe job
  reuse, and dependency truth for future deletion (`feature:015`, `T001-T087`).
- Добавлен backend tenant-isolation RLS hardening слой: PostgreSQL policies,
  request/worker/auth bootstrap/session lookup/callback lookup/maintenance DB
  contexts, rollout validation helper, and future-table ADR (`feature:031`,
  `T001-T052`).
- Добавлен MVP experience/design handoff для `2brain Rec`: clean-room audit,
  native/web route boundaries, status matrices, screen specs, embedded
  server-owned speaker assignment для desktop shell и активный Figma v8 clean
  Russian implementation baseline с 98 валидными click reactions
  (`feature:030`, `T001-T085`).

### Changed

- GitHub issue and pull request workflow now follows the Russian-only issue
  canon: issue forms use Russian sections, PR descriptions must be written in
  Russian, `Fixes`/`Closes`/`Resolves` are reserved for issues fully closed by
  a PR, partial work must use `Refs`/`Part of`, and every closed issue requires
  a detailed Russian closure comment that explains what changed, why it
  matters, how it was checked, what is out of scope, and which PR/Spec Kit task
  it closes. The project also now ships a PR template and a synced
  `github-issue-canon` extension `v0.2.0` copy for future task-to-issue syncs.
- `docs/current-product-status.md` and the MVP readiness report now record
  `022-meeting-mute-truth` as closed, remove stale `018`/`022` next-slice
  guidance, and recommend validation-only `035-mvp-loop-live-evidence` while
  keeping live desktop/web evidence, notes/action truth, and production
  user-journey proof as launch gates (`feature:022`, `feature:034`,
  `T045-T051`).
- `docs/current-product-status.md` and the 035 readiness report now close the
  stale installed-desktop evidence gap, keep production owner review blocked on
  `401 missing_auth_context`, and recommend `036-owner-review-live-polish` as
  the next launch slice (`feature:035`, `T026-T032`).
- Web cabinet and auth pages now follow the Krisp reference more closely while
  staying clean-room: Russian copy, centered dark auth cards, email/signup mode
  transitions, six-slot verification input, denser meetings list, upcoming
  events card, floating assistant input, and future-control slots for provider,
  sharing, filters, sorting and upload (`feature:036`).
- Desktop owner-review shell now follows the reference layout more closely:
  slimmer sidebar, embedded meetings surface without duplicate native cards,
  compact collapsible right rail, denser web meeting workspace, and a
  profile/settings menu with Russian clean-room copy (`feature:036`).
- Native desktop shell and embedded web cabinet now share the same Krisp-like
  warm dark palette and SF/system typography tokens: sidebar/right rail
  `#202224`, native/WebView background `#191a1c`, cards `#242629`, and a
  shared violet accent for compact rail states and web controls (`feature:036`).
- Desktop sidebar width now adapts to its Russian labels and pending-action
  badge with min/max bounds, so normal windows show the full menu text while
  narrow resolutions fall back to the compact width (`feature:036`).
- Синхронизирован Speckit workflow с обязательными этапами `clarify`,
  `checklist`, `analyze`, `taskstoissues`, чтобы требования и контроль качества
  были сквозными.
- RLS validation wording now separates destructive test/disposable probes from
  production read-only RLS state truth (`feature:032`, `T001-T014`).

### Fixed

- Dev MinIO policy now includes bucket metadata and multipart permissions
  required by local readiness/upload checks, so `docker-compose.dev.yml`
  can reach `ready` after the local stack is rebuilt (`feature:043`).
- Desktop sidebar navigation now uses native clickable rows, tracks embedded
  WebKit route changes, and lets `Мои встречи` return from a meeting detail
  route back to the recordings list inside the app (`feature:042`).
- Desktop meetings shell now keeps local-only queued/blocked recordings visible
  above the embedded server cabinet until a server meeting identity exists, so
  a saved recording no longer disappears from the app when upload is blocked by
  local quality/privacy truth (`feature:042`).
- Desktop recording upload now uses the packaged production origin when no
  shell environment is present, reuses the embedded web owner session cookie for
  native upload requests, refreshes stale local queue eligibility, and uploads
  safe degraded recording packages so saved recordings can appear in web and
  desktop review instead of remaining local-only blocked items (`feature:042`).
- Desktop embedded cabinet now preserves desktop auth headers across WebKit
  link navigations to `/desktop/meetings` and meeting detail routes, so clicking
  a recording row no longer falls back to a false login/unavailable state
  (`feature:042`).
- Desktop embedded cabinet now ignores non-main-frame WebKit response failures,
  so favicon/apple-touch icon probes cannot replace a valid login/meetings
  surface with a false unavailable state; production web cabinet also answers
  standard icon probes without `404` noise (`feature:042`).
- Local macOS install now force-registers the copied `2brain Rec.app` bundle with
  LaunchServices, reducing stale Dock/Spotlight launches after rebuilding the
  desktop app (`feature:042`).
- Desktop app now installs standard macOS `Edit`/`Window` menus, so embedded
  cabinet fields receive `Cmd+V`, `Cmd+A`, copy, cut, paste and related
  responder-chain commands in `/Applications/2brain Rec.app` (`feature:036`).
- Desktop embedded cabinet now allows production `/login` routes, ignores
  WebKit `about:blank` navigation noise, and sends expired-session recovery to
  `/login?next=/desktop/meetings`, so the installed `/Applications/2brain Rec.app`
  renders browser-login instead of a false blocked-route state (`feature:036`).
- В `.github` и процессе разработки зафиксирован порядок этапов и коммитов для
  Spec Kit.
- MediaScribe client now follows the live production contract for polling and
  result import via `/jobs/{job_id}` and normalizes `start`/`end`/`speaker`
  fields into persisted processing rows (`feature:015`).
- Исправлены имена unique constraints для MediaScribe processing migration,
  чтобы production PostgreSQL migration не падала на конфликте имен
  (`feature:015`).
- Укорочен Alembic revision id для `0004`, чтобы он помещался в стандартный
  `alembic_version.version_num`, и Temporal production wrapper теперь читает
  local-file secrets с корректными правами (`feature:015`).
- Production env template больше не рассылает service-specific secret-file
  paths во все app containers, а ошибки production secret validation называют
  конкретное field name без раскрытия secret values (`feature:015`).
- Malformed successful MediaScribe submit/result payloads now map to safe
  retryable `mediascribe_malformed_response` processing state instead of
  escaping as unmanaged validation exceptions (`feature:015`).
- Missing or unreadable MediaScribe API key files now map to safe
  `blocked_config` instead of unmanaged file-system exceptions (`feature:015`).
- Production `rec-api` no longer mounts the MediaScribe API key Docker secret;
  only `rec-processing-worker` receives that secret (`feature:015`).

### Security

- Postal API key for browser-login delivery is mounted only as a Docker secret;
  deploy/runtime scans now reject accidental `TWOBRAIN_POSTAL_API_KEY`
  environment exposure, and desktop clients never receive Postal settings
  (`feature:036`).
- Browser cabinet content stays behind an email-issued owner session: protected
  web routes redirect HTML requests to login, email-code failures do not reveal
  whether an address exists, and browser OAuth provider routes are explicit
  future stubs instead of partially enabled auth paths (`feature:036`).
- Meeting-app mute truth remains fail-closed: diagnostics/redaction allow only
  metadata fields, fixture validation rejects raw audio/transcripts/meeting
  content/credentials/signed URLs, unsupported targets never become
  `mute_respecting`, and upload queue completeness is not reinterpreted by
  mute-truth metadata (`feature:022`, `T006-T011`, `T022-T042`).
- Readiness evidence for `034` is metadata-only by contract: unsafe screenshots
  are rejected, reference-comparison evidence IDs are validated, committed
  evidence cannot include private Krisp screenshots or private meeting content,
  and production claims stay bounded to `infra_smoke_ready` until stronger
  evidence exists (`feature:034`, `T005-T014`, `T028`, `T055`).
- Readiness evidence for `035` keeps live web owner review metadata-only:
  private Chrome session data, account identifiers, screenshots, cookies,
  tokens, transcript text, audio, and production destructive governance actions
  are not committed (`feature:035`, `T020-T025`, `T039`).
- Retention/deletion reports and lifecycle activity are metadata-only by
  default: they do not expose raw audio, transcript text, summaries, local
  paths, object-store keys, signed URLs, provider payloads, dependency job IDs,
  bearer tokens, credentials, or private desktop proof payloads. Deletion
  requests fail closed when audit/report evidence cannot be written before
  lifecycle mutation, and desktop local purge acknowledgements reject private
  path/content payloads (`feature:018`, `T011-T015`, `T020-T028`,
  `T037-T045`, `T053-T059`).
- Access/sharing/download/export routes now re-check effective viewer access,
  never expose object-store keys, signed URLs, raw local paths, bearer tokens,
  MediaScribe identifiers, or private artifact content in egress responses, and
  fail closed when metadata-only audit cannot be written before share/revoke/
  download/export actions (`feature:017`, `T008`, `T020-T024`, `T028-T039`).
- RLS coverage now includes meeting share grants, artifact policies, egress
  audit events, and export packages via `0006_access_sharing_downloads`
  (`feature:017`, `T004-T006`).
- Desktop cabinet embedding adds an explicit embedded route allowlist for
  `/desktop/meetings` and meeting detail routes, blocks native capture/local
  diagnostics/share/export/download/delete destinations inside the embedded
  surface, and records sanitized screenshot evidence without Krisp private
  captures, account identifiers, transcript text, raw audio, signed URLs, or
  live local paths (`feature:033`, `T005`, `T008`, `T034-T041`).
- Cabinet API и web routes используют существующий tenant/device auth context,
  скрывают foreign meeting existence через privacy-preserving 404 и не отдают
  transcript text в list responses, storage keys, signed URLs, workflow/run ids
  или MediaScribe external ids (`feature:016`, `T011`, `T029`, `T030`).
- MediaScribe credentials remain server-side through secret-file configuration;
  processing status, audit metadata, logs, and evidence must not expose raw
  audio, transcript text, signed URLs, API keys, bearer tokens, passwords, or
  live secret paths (`feature:015`, `T040`, `T065-T071`, `T086`).
- RLS hardening adds database-level tenant isolation coverage for accepted
  identity, auth/session/device, ingest, meeting, processing, transcript, audit,
  and dependency tables, while keeping product/admin bypass out of scope
  (`feature:031`, `T016-T037`).
- RLS post-review hardening now requires explicit auth-session lookup context,
  complete maintenance actor/reason/feature metadata, and fail-closed worker
  tenant scope before tenant-owned processing DB operations (`feature:031`,
  `CR-003`, `CR-005`, `CR-006`).
- RLS post-review hardening now preserves controlled auth/link conflict outcomes
  for globally unique provider identities, requires membership or bounded auth
  bootstrap guards for organization-scoped policies, and rejects unknown tenant
  context kinds at runtime (`feature:031`, `CR-004`, `CR-007`, `CR-008`).
- Provider link conflict/rejected paths now commit metadata-only auth audit
  evidence before returning controlled error responses (`feature:031`, `CR-009`).
- RLS validation now blocks before migrations or probes when
  `RLS_TEST_DATABASE_URL` points at the live `twobrain_rec` database
  (`feature:031`, `#734`, `#735`).
- Production RLS enforcement is now recorded as verified enabled and forced
  through read-only PostgreSQL catalog metadata: production Alembic
  `0005_rls_hardening` and all covered tables report RLS enabled/forced
  (`feature:032`, `T015-T020`).

### Docs

- Added feature `022` evidence scaffold, target matrix, manual validation
  template, and current-product-status update for the boundary between
  product-owned Pause truth and future meeting-app mute adapters (`feature:022`,
  `T041-T044`).
- Reorganized Codex/Spec Kit operating guidance: root `AGENTS.md` now acts as
  a concise router, detailed rules live under `docs/agent-guidance/`, GitHub
  issue canon moved to `docs/agent-guidance/github-issue-canon.md`, and active
  guidance now treats Linear as retired workflow residue.
- Added sanitized feature `017` evidence index and refreshed current product
  status so access, login-required sharing, server-mediated downloads, and safe
  exports are no longer listed as deferred launch gaps (`feature:017`,
  `T040-T045`).
- Обновлены feature `033` implementation evidence, clean-room screenshot notes,
  and current product status so `016` is no longer treated as the next product
  slice after desktop cabinet embedding (`feature:033`, `T034-T037`).
- Обновлён `AGENTS.md`:
  - добавлен раздел `Versioning And Changelog`;
  - закреплён процесс обязательного обновления `CHANGELOG.md`;
  - закреплён системный подход к SemVer и git-тегам релизов.
- Обновлены server README и current product status для границ `015`, fake
  dependency flow, и разделения будущих `016/017/018` поверхностей.
- Зафиксированы production deployment и real-recording e2e evidence для
  `015` без сохранения transcript text в tracked docs.
- Добавлены RLS rollout runbook, ADR `003-tenant-isolation-rls`, and current
  product-status notes for RLS rollout gates (`feature:031`, `T043`,
  `T049-T052`).
- Corrected stale `031` RLS rollout wording in product status, ADR, runbook,
  and quickstart so current docs reflect verified production enabled/forced
  state while preserving test-only destructive probe boundaries
  (`feature:032`, `T021-T027`).

### Ops

- `017` развернут на `2brain.dev` (`master` at `39b8c5f`) и проверен
  production infra smoke: `rec-api` healthy, Alembic
  `0006_access_sharing_downloads`, `/health/live` ok и `/health/ready` ready
  (`feature:017`).
- Production smoke для desktop upload queue теперь выпускает временную Rec
  `AuthSession` вместо использования инфраструктурного smoke secret как bearer
  (`feature:014`, `T036-T038`).
- Добавлены production/dev Compose placeholders для Temporal и processing
  worker без live secrets (`feature:015`, `T010`, `T071`, `T085`).
- Remote CD теперь запускает Temporal и processing worker, которые нужны для
  production-проверки обработки (`feature:015`).
- Production Temporal теперь запускается на Postgres backend через Docker
  secret wrapper, а CD блокирует статический `POSTGRES_PWD` в compose config
  (`feature:015`).
- Production processing worker теперь может читать local-file Docker secrets,
  включая MediaScribe API key, при запуске из Compose (`feature:015`).
- Production processing worker больше не наследует smoke/awareness credential
  file settings, которые не нужны для MediaScribe processing (`feature:015`).
- Production smoke cleanup теперь удаляет 015 processing rows перед meeting
  cleanup, чтобы real processing e2e не оставлял residue в Postgres (`feature:015`).
- `015` развернут на `2brain.dev` (`master` at `4cda38c`) и проверен полным
  production e2e на реальной записи приложения: upload, pickup, Temporal
  worker, live MediaScribe, result import, content-safe status и cleanup
  прошли успешно (`feature:015`).
- Local CI and migration verification now reference RLS validation without
  using destructive live production probes (`feature:031`, `T041-T045`).
- RLS migration verification now blocks when the validation helper returns a
  blocked verdict, and the helper delegates to a real PostgreSQL policy suite
  when `RLS_TEST_DATABASE_URL` is supplied (`feature:031`, `CR-001`, `CR-002`).
- PostgreSQL RLS probes now use a non-owner probe role and a SQL-only UUID GUC
  helper, so validation checks enforced RLS behavior without superuser/owner
  bypass and avoids PL/pgSQL migration hangs observed on local PostgreSQL 14
  (`feature:031`, `CR-001`).
- Added production read-only RLS state verification output for covered-table
  counts, enabled/forced counts, failed tables, deployed commit, and Alembic
  revision (`feature:032`, `T015-T020`, `T028-T037`).

## [Unreleased Template]

### Added
### Changed
### Fixed
### Security
### Docs
### Ops
