# T119: ограниченный pre-code gate resolver

**Purpose**: независимая оценка ясности и безопасности дизайна authenticated
resolver, до изменений исходников; не приёмка реализации или всего T119.
**Created**: 2026-10-04.
**Feature**: `../spec.md`, FR-002/005/006/015; existing T119,
`../contracts/windows-native-web-bridge.md` §§1/10.
**Lane**: bounded reviewer-owned design/requirements review существующего
high-risk Active Spec Kit slice.
**Review Ownership**: только reviewer. `[x]` означает достаточное качество
описанного дизайна/требований, не работающий код или выполненные испытания.
`$speckit-implement` читает gate, но не меняет markers.

## Критерии ограниченного дизайна

- [x] CHK001 Определены ли один существующий transport, точный GET-only endpoint и сохранение прежних caller defaults без второго HTTP client/service? [Consistency, Plan T119:1166–1174]
- [x] CHK002 Однозначны ли подтверждённый для того же token owner/workspace snapshot и отказ без I/O при invalid/missing identity/workspace/token/event UUID? [Security, bridge §10:407–428]
- [x] CHK003 Полна ли pre-I/O граница назначения и заголовков: trusted configured HTTPS origin, безопасные retained header values, очищенный deviceId и scope только из confirmed identity без foreign caller authority? [Security, bridge §§1/10, Constitution III, Gap]
- [x] CHK004 Задан ли единственный абсолютный steady deadline от первоначального operation start≤15s, без обновления на dispatch/chunks/retry? [Clarity, bridge §10:416–419, Plan T119:1202–1207]
- [x] CHK005 Определены ли pre/post deadline/cancel checks для каждого блокирующего этапа, положительные remaining timeouts и отказ после ошибки настройки, без обещания мгновенного выхода OS wait? [Completeness, bridge §10:416–428, design clarification]
- [x] CHK006 Разделены ли sole worker handle ownership/cooperative cancellation, terminal UI expiry и busy lease до actual completion, без concurrent close или нового worker после expiry? [Lifetime, bridge §10:416–428, Quickstart §13]
- [x] CHK007 Однозначны ли inclusive whole response≤64KiB, complete read/EOF, отказ overflow/truncated prefix и неизменность legacy2MiB behavior? [Bounds, bridge §10:409–411, design clarification]
- [x] CHK008 Определены ли только HTTP200 strict matching typed target и closed safe outcomes для auth/unavailable/dependency/invalid/cancelled, без error/redirect success? [Completeness, bridge §10:407–418]
- [x] CHK009 Заданы ли запрет redirects/cookie jar/cache/log/raw-body egress и отделение target data/auth-expiry header от current consumer authority? [Security, bridge §10:412–428, approved response source review]
- [x] CHK010 Однозначно ли discarded late result после cancel/expiry и отсутствие target до/после parse и перед возвратом, без действий auth/UI/launch из transport? [Consistency, bridge §10:419–428]
- [x] CHK011 Разделены ли измеримые portable resolver decisions и production-native request boundaries, с минимальным test seam вместо второго клиента? [Measurability, Quickstart §13, Plan T119]
- [x] CHK012 Явно ли ограничена приёмка transport slice, сохраняя future owner timer/fences/URL policy/launch/Record/installed gates и source review до functional claims? [Traceability, Tasks T119, Quickstart §13, Constitution VI]

## Notes

Созданы 12 unchecked критериев по speckit-checklist template. Их оценка
выполняется отдельно независимым reviewer по просьбе пользователя.
Это единственный разрешённый output текущего шага; предыдущие gates и
source report сохраняются. Новые требования/spec/plan/tasks/GitHub/code
не изменяются. Вопросы whole Feature 200, hardware/audio/install не исследуются.

## Независимая оценка дизайна — terminal

**DESIGN / REQUIREMENTS PASS: 12 checked / 0 unchecked; C0 / H0 / M0.
Блокирующих C/H расхождений в окончательно уточнённом дизайне нет.**
Проверены все 12 критериев, не реализация. Первоначальный вопрос полноты
pre-I/O origin/header guards разрешён последним уточнением Main, не скрыт
за общей фразой «identity валидна». Source acceptance нового resolver
потребует отдельного обзора после реализации и доказательств ниже.

### Снимок и лично прочитанные основания

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`;
HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, свежо проверены read-only.
Feature pointer и checklist prerequisites указывают на этот Feature 200.
Лично полностью прочитан speckit-checklist SKILL; before/after_checklist
hooks содержат только disabled commit, ничего не исполнялось. Guidance
index/constitution прочитаны лично; прежний applicable AGENTS/guidance
контекст сохранён. Свежие нормативные хеши совпали с предыдущей review:

| Нормативный файл (от feature root, кроме constitution) | SHA-256 |
| --- | --- |
| `spec.md` | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| `plan.md` | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| `tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `quickstart.md` | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| `data-model.md` | `dc91ac60f180e6221e85917c9a91e510e34008430dfb457e7a7cbeb97162e0a7` |
| `contracts/windows-native-web-bridge.md` | `127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4` |
| `.specify/memory/constitution.md` (repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

Повторно прочитаны только resolver-relevant bridge §§1/10:405–428,
plan T119:1158–1207, quickstart §13:440–474, tasks Phase19/T119.
Прежние 24/112 requirements не пересматривались. Path/response source
approval сохранён на cpp05f5eb4..., headeraf7ded..., tests3c9f302...;
его отчёт SHA-256 `4318f9199a92120841d63c06529fdd86e61719d798824b0cd47c1f2773d9fc8f`.

Лично прочитаны private request, IdentityGet/resolveAccountIdentity,
deletionCall и upload request callers внутри DesktopHttpTransport, объявления
UploadResponse/config/callback; только relevant validServerOrigin implementation
и declaration, existing CMake OBJECT pattern и тестовые callback patterns.
Это опорный **pre-edit** снимок, не утверждение, что новый resolver уже существует:

| Файл от repo root | SHA-256 до resolver изменений |
| --- | --- |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `34bfb5d5359c22c5de26bd790227414974d4804abdd6588e8e63734022e9fce1` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.h` | `f4fcfaebbd10a5c1e059beea27c57d5c276784b9c808e2237bb941ad16fa660e` |
| `apps/windows/RecApp/Upload/DesktopUploadQueueService.cpp` | `08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b` |
| `apps/windows/RecApp/Upload/DesktopUploadQueueService.h` | `e975df4077df25c8c021487b88ee8e60c3e51947b319062c2fce2a4600775418` |
| `apps/windows/CMakeLists.txt` | `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295` |

### Основания по критериям и обязательные границы реализации

| Критерий | Основание PASS окончательного дизайна |
| --- | --- |
| CHK001 | Main использует один TU-local private request в DesktopHttpTransport, существующий UploadResponse и GET callback pattern IdentityGet. Existing calendarJoinTargetPath/decoder переиспользуются. Новый callback принимает config/path/absoluteDeadline; body пустой, путь только проверенный event UUID. Нет второго HTTP client, discovery/auth GET или backend/UI реализации. |
| CHK002 | До callback/I/O требуются nonempty control-free bounded sessionToken, valid confirmed user/workspace UUID, nonempty matching config.workspaceId и snapshot, подтверждённый native owner именно для того же token. Недостающий snapshot не инициирует скрытую /auth/me цепочку. Snapshot copied/immutable; текущие generation/context checks не имитируются этим DTO. |
| CHK003 | Окончательно подтверждён исходный approved вариант: reuse validServerOrigin + отдельный HTTPS-only guard, bounded/control-free retained token/clientVersion, deviceId cleared, scopedAccount overwritten только из confirmed user/workspace. Foreign caller scope discarded; GET остаётся read-only без mutation body/операции. Expected-account headers при наличии формируются только из подтверждённых UUID, не произвольного caller scope. Existing native WinHttpCrackUrl/host checks и refusal failures остаются обязательными. Origin приходит из trusted native configuration (§1), не web/event/response. Public declaration move helper не меняет его implementation и не делает helper meeting-URL policy. |
| CHK004 | API требует исходный absolute steady deadline; effective deadline не позже original и now+15s. Past deadline не запускает wire. Повторный clamp не обновляет первоначальный deadline; время очереди/dispatch/chunks входит в общий budget. Это source precondition будущего operation owner, не доказательство уже работающего UI timer. |
| CHK005 | Calendar custom mode пересчитывает remaining перед send/receive/data-available/read и иными блокирующими фазами, проверяет cancel/expiry до/после них, перед/после parse и final result. Expired remainder не превращается в 0/infinite; положительный clamp с учётом округления ms, ошибки SetTimeouts/options/headers/read fail closed. Native wait может вернуться после deadline, но результат не принимается. |
| CHK006 | Worker единолично владеет handles и закрывает их при выходе; никакого watchdog close синхронного request. Flag является cooperative invalidation. Future owner отдаёт UI terminal на15s и сохраняет busy/lease до actual completion; старое завершение не освобождает новую операцию и не запускает следующий worker/launch. Этот owner timer отсутствует в нынешнем transport slice и не объявлен принятым. |
| CHK007 | New mode inclusive≤65536 полного response, не просто decoded fields или Content-Length. Exact65536+EOF принимается;65537/extra byte/error/incomplete read отвергаются без разбора valid prefix. EOF/complete transfer обязателен даже при достижении cap. Старое2MiB equal-cap refusal и прочие caller semantics не исправляются попутно. |
| CHK008 | CalendarJoinResolution имеет closed enum resolved/authRequired/eventUnavailable/dependencyUnavailable/invalidTarget/cancelled. Только полностью успешный HTTP200+strict matching decoder может содержать target.401→authRequired,404→eventUnavailable,503/network/timeout→dependencyUnavailable, malformed→invalidTarget, cancel→cancelled; все иные статусы/3xx nonresolved без target. Не наследовать upload «любой2xx uploaded». |
| CHK009 | Native handle options отключают redirects/cookies с обязательной проверкой результата. Raw response/URL/token не попадают в публичные safe reasons/log/cache/page; UploadResponse body существует только как bounded internal wire data. Auth-expiry только parsed metadata для consumer, применять лишь после current validation;401 не меняет auth глобально из transport. |
| CHK010 | Cancel/expiry имеют приоритет над поздним HTTP200/401/header/parse success. Перед parse и final return target отсутствует после invalidation; partial body/error никогда не становятся resolved. Target — untrusted owned data, не URL/launch authority и не current owner proof. Никаких UI/auth mutations, retry/fallback/cache из transport. |
| CHK011 | Portable callback проверяет production resolver decision layer, а native-boundary TU включает именно существующий request implementation и подменяет WinHTTP calls, не весь HTTP client. CMake OBJECT exclusion предотвращает double definitions. Private optional now function pointer приемлем только для детерминированных native phase tests, default steady_clock::now, без public runtime settings/framework. |
| CHK012 | Accepted только уточнённый resolver design перед кодом; source review нового diff и native-boundary checks остаются впереди. Controller timer/fences, bridge/shim, URL validation/opener/recovery/Record/installed matrix сохраняются как отдельно открытые части T119. Тесты resolver не являются handed_off/T119 completion. |

### Минимальные тесты: два различных уровня доказательств

Это рекомендации к будущей реализации, **не выполненные испытания**.
Не требуется второй клиент, generic transport interface или clock framework.

**Portable decision layer** — один existing-pattern GET callback, возвращающий
UploadResponse; production resolver выполняет все проверки и классификацию:

1. Table of invalid event/config: empty/malformed owner/workspace, mismatch,
   missing confirmed snapshot/token, token/clientVersion CR/LF/NUL, invalid/nonHTTPS
   origin. Callback call count0. Valid config: один exact GET path, тот же absolute
   deadline, cleared deviceId, scopedAccount ровно из confirmed user/workspace,
   foreign caller scope не наследуется.
2. HTTP200 matching valid target; representative malformed/duplicate/mismatch
   body;200 transportFailed;201/204,301/302/307/308,401,403,404,408/429,503,
   status0/network. Только resolved имеет target.401/404/503 сохраняют различие;
  403/прочие failures не делают logout и не становятся success. Caller не
   обязан вызывать это authRequired, если approved contract явно задаёт лишь401.
3. Already cancelled/past deadline — callback0. Callback меняет cancel flag
   перед возвратом valid200 — cancelled без target. Late200 и late401 после
   deadline — dependencyUnavailable без применимых target/auth side effects.
   Portable late tests могут использовать sleep_until короткого deadline;
   проверять discard, не хрупкое требование точного wall-clock elapsed.
4. Fake bodies65535/65536/65537; complete bound и malformed prefix. Fresh
   повторные вызовы вызывают wire заново, нет cached URL. Decoding использует
   уже approved strict decoder, не дублирует весь corpus его fixtures.

**Native boundary** — один test TU с production DesktopHttpTransport.cpp,
TU-local WinHTTP wrappers и исключённым transport OBJECT из common link:

1. Записать actual method/path/headers/options: GET-only fixed endpoint,
   no body/device header/foreign caller scope; validated session,
   workspace/client-version и expected-account headers только confirmed UUID;
   disable redirects|cookies. Option/timeout failure => no subsequent send;
   никаких реальных сетевых запросов из fake wrappers.
2. Table phase interruption send/receive/query-available/read: wrapper возвращает
   success, но cancellation/clock уже invalid; следующая blocking phase не
   вызывается, target отсутствует. Ошибки status query/read/set-timeout fail
   closed; все созданные handles закрыты ровно один раз sole owner после phase.
3. Controlled remaining clock: all timeout values>0, уменьшаются/не обновляют
   deadline; sub-ms remainder не превращается в infinite0. Trickle chunks
   пересекают один original deadline => отказ, даже если каждый read успешен.
   Проверить отсутствие final-success path после expiry на последнем chunk/EOF.
4. Exact65536 complete response против65537, нескольких chunks/overflow и
   read failure после syntactically valid prefix. Не принимать truncation,
   не append overflow в body. EOF за cap можно определить tiny bounded read
   в scratch, не расширяя принятый body cap; конкретный код выбирает Main.
5. Default caller control: request без calendar options сохраняет30s deadline,
   прежние5s/5s/10s/10s phase timeouts и2MiB/equal-cap behavior; calendar options
   не «протекают» на upload/deletion/identity. Link smoke проверяет отсутствие
   дублированных public symbols при test include actual cpp.

Private clock function pointer предпочтителен для точных native phase/trickle
assertions вместо100ms sleep timing на VM. Он не должен становиться новым
public configuration или владеть context/timer. Portable real-time late tests
не доказывают уменьшение WinHTTP timeouts; MSVC compile/1PASS callback-test
не доказывает исполнение production WinHTTP branch. Даже native wrappers
подтверждают control flow, не real network/TLS/PAC latency и не UI15s.

### Точная граница WinHTTP и внешние первичные источники

Microsoft документирует положительные timeout milliseconds и infinite0/-1:
[WinHttpSetTimeouts](https://learn.microsoft.com/en-us/windows/win32/api/winhttp/nf-winhttp-winhttpsettimeouts).
Поэтому до вызова с expired budget нужен отказ, а не cast отрицательной
duration либо округление в0. Per-phase timeouts — не обещание wall-clock
завершения всего synchronous worker на15s; последнее здесь не принимается.

Запрет race при попытке terminate synchronous in-progress request подтверждён
[WinHttpCloseHandle, remarks](https://learn.microsoft.com/en-us/windows/win32/api/winhttp/nf-winhttp-winhttpclosehandle).
Это не запрет нормального cleanup handles самим worker после завершения phase.

Synchronous QueryDataAvailable может ждать данные, а complete read определяется
корректным read/EOF, не одной величиной available:
[WinHttpQueryDataAvailable](https://learn.microsoft.com/en-us/windows/win32/api/winhttp/nf-winhttp-winhttpquerydataavailable),
[WinHttpReadData](https://learn.microsoft.com/en-us/windows/win32/api/winhttp/nf-winhttp-winhttpreaddata).
Следовательно, native tests должны охватить QueryDataAvailable тоже, а whole
response cap не означает разрешение игнорировать хвост ответа.

## Терминальный вывод

После восстановления контекста Main кратко предложил clear scopedAccount,
затем явно исправил это сообщение и подтвердил исходный approved вариант:
**scopedAccount overwritten из confirmed user/workspace; deviceId cleared;
foreign caller scope discarded.** Именно этот вариант актуален в CHK003 и
проверках выше. Это не mutation operation: метод остаётся GET, без body и
дополнительных запросов. Подтверждённый snapshot обязателен до I/O; source
review должен проверить фактические headers. Промежуточный clear вариант
не является текущим дизайном. Ничего в controller/browser/dialog/owner timer
не принято этой редакционной коррекцией.

**12 checked / 0 unchecked, C0/H0/M0 — ограниченный дизайн одобрен.
Неподтверждённого design C/H пункта после уточнений нет.**
Ни production resolver source correctness, ни native tests, ни UI deadline,
actual network, installed client/launch или end-to-end T119 этим gate не приняты.
Ничего не собиралось/не запускалось: только read-only inspection, узкие
официальные WinHTTP docs и создание/оценка этого checklist. Code/spec/plan/tasks,
GitHub, commit, VM/device/install и чужие dirty work не изменялись.
