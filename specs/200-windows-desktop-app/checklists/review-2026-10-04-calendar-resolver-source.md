# T119: независимый ограниченный source review resolver

Дата: 2026-10-04. Владелец отчёта: независимый reviewer.

**Approved — C0 / H0 / M0. Блокирующих source findings в рассмотренном
resolver/native-request срезе нет. Это НЕ функциональная приёмка T119.**

## Область и основание

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Свежо проверенные branch `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Рассматриваются текущие dirty bytes, а не реализация только из HEAD.

Единственный разрешённый записываемый файл — этот отчёт. Product code,
нормативы, tasks, прежние reviewer reports, GitHub и чужие storage/CMake
изменения не исправлялись. Commit/build/install/VM/device операции reviewer
не выполнял; выполнен только ограниченный запуск существующих portable
тестовых исполняемых файлов, указанный ниже.

Lane: reviewer-owned scoped source review существующего high-risk Spec Kit
среза, не новая реализация и не повтор whole Feature 200 requirements review.
Лично прочитаны code-reviewer и ponytail-review SKILL полностью; применены
correctness/security/error/lifetime/default-caller анализ и отдельная оценка
минимальности. Applicable AGENTS/guidance/constitution, лично прочитанные
на предыдущих этапах этой review, сохранены как контекст. Свежие хеши
AGENTS, constitution и действующих spec/plan/tasks/quickstart/bridge совпали
с approved design snapshot; новое чтение всего Feature 200 не выполнялось.

Approved design: `review-2026-10-04-calendar-resolver-gate.md`, 12/0,
SHA-256 `f127e62487b6bade4fee3982242e831da9145cf5819fd53da1a9bfce1260c8ce`.
В частности, scope **overwritten из confirmed user/workspace**, deviceId
cleared; промежуточное предложение clear scope не является дизайном.
Approved path/response review сохранён без изменений:
`review-2026-10-04-calendar-response-source.md`, SHA-256
`4318f9199a92120841d63c06529fdd86e61719d798824b0cd47c1f2773d9fc8f`.
Fresh decoder/header/ContractFixtures hashes совпали с его последним
M1-closed snapshot; decoder заново не реализовывался и весь corpus не
пересматривался.

## Точные рассмотренные байты

Все шесть SHA-256 ниже вычислены reviewer локально и совпали с сообщением
Main о Windows NTFS GetFileHash. Windows проверку выполнял Main, не reviewer.

| Файл от repo root | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.cpp` | `5b64cfb025268b40419404f0db3effe947669dae95363f678fa1193dcfe547e3` |
| `apps/windows/RecApp/Upload/DesktopHttpTransport.h` | `daf0de7084b1c51de89dda11880cd13cb582cf3e12c3b3cd792654b0582ab12d` |
| `apps/windows/RecApp/Upload/DesktopUploadQueueService.h` | `95e62113e29072efb00ddd681cac29902b3e41461cc10660acfa1367e2e83073` |
| `apps/windows/Tests/GrafWindowsContractTests/CalendarJoinResolverTests.cpp` | `0aa5f7598d79bf047e745af3ce4a3e217ea87cfdd229e57556428d793674bf89` |
| `apps/windows/Tests/GrafWindowsContractTests/NativeCalendarJoinTransportTests.cpp` | `4c4ff484fb7c661107fac6714a1cef8b1deca1b8c2ae216750c6d39200b15621` |
| `apps/windows/CMakeLists.txt` | `3baee91b1e809c824f967a9c4f46f9879daace840794c72a6efb4975a69faceb` |

Прочитаны текущие transport .h/.cpp, оба новых теста и CMake целиком;
прочитаны relevant declaration и existing validServerOrigin implementation.
`DesktopUploadQueueService.cpp` не имеет diff; fresh SHA-256
`08ea8aac504d6f31d03cfed53b65ff4caed05522e57871a0a34ab376a4c12e5b`
совпадает с pre-edit gate. Изменение helper — только public declaration
с комментарием, не переписывание его parser/legacy policy.
Existing custody-tree OBJECT split уже был в pre-resolver design snapshot;
его dirty diff относительно HEAD не приписывается этому resolver и не
расширяет source approval на storage.

## Проверенные свойства потока

| Approved criterion | Независимый source вывод |
| --- | --- |
| CHK001: один transport, прежние defaults | Новый production overload вызывает ровно существующий TU-local request с GET, проверенным calendar path и пустым body. Upload/identity/deletion callers сохраняют default arguments без calendar deadline; второго клиента/service нет. |
| CHK002: pre-I/O identity/token/event | До callback проверены event UUID/path, наличие confirmed identity, оба account UUID, exact matching nonempty workspace и printable bounded token. Нет fallback /auth/me или workspace discovery. Config — copied snapshot; получение именно для того же token остаётся обязательным native-owner precondition, а не доказательством из одного DTO. |
| CHK003: origin/headers/scope | HTTPS-only guard + неизменный validServerOrigin отказывают malformed/control/path/query/userinfo origin до callback. Native request дополнительно использует WinHttpCrackUrl. Retained token/clientVersion bounded ASCII; deviceId очищен; foreign scopedAccount заменён двумя confirmed UUID. Production GET headers проверяются native test; mutation body/idempotency/offset/hash headers не добавляются. Helper не объявляется meeting-URL policy. |
| CHK004: один original deadline | cpp:905 принимает original absolute steady deadline и только уменьшает его до now+15s. Callback получает этот deadline; private request его не обновляет между chunks или фазами. Past deadline прекращает работу до wire. Время до входа должно учитываться переданным original deadline будущего owner. |
| CHK005: phase bounds/failure | cpp:255 phase проверяет active до/после native call, пересчитывает positive remaining timeouts перед фазой и проверяет результат их настройки. Clamp1..15000ms, с прежними per-phase верхними пределами, не допускает infinite0/-1. Send/receive/status/query/read failures и ошибки options/timeouts не дают target; после invalidation следующие native phases не вызываются. Optional absent headers не ошибочно считаются transport failure. |
| CHK006: sole-worker cleanup | cpp:283 три unique_ptr owners принимают handles немедленно после открытия. Обратный порядок destruction request→connection→session покрывает early returns и exception unwind. На normal path reset в том же порядке находится между двумя active checks (cpp:440–444). Нет concurrent close/watchdog, OS wait не объявлен принудительно остановленным на15s. |
| CHK007: whole-body/EOF | Calendar mode держит body≤65536 inclusive, отвергает available>remaining и read failure/overflow. При available0 выполняет scratch1 read для доказательства EOF; trailing byte сверх cap не добавляется в accepted body. HTTP200 valid JSON prefix при ошибке/переполнении не разбирается как success. Legacy2MiB exact-cap refusal сохранён. |
| CHK008: safe typed result | Только complete nonfailed HTTP200 + existing strict matching decoder даёт resolved target.0/408/429/5xx/transport failure→dependencyUnavailable;401→authRequired;403/404/410→eventUnavailable; прочие ответы/invalid JSON→invalidTarget. У каждого nonresolved результата нет target/auth expiry. Нет upload-style «любой2xx success». |
| CHK009: redirects/cookies/metadata | WINHTTP_DISABLE_REDIRECTS\|WINHTTP_DISABLE_COOKIES проверяются до send. Cache URL, logging/body egress, cookie/auth/UI mutation здесь отсутствуют. Только parsed numeric bounded auth-expiry metadata может сопровождать resolved target; применение требует current-consumer проверки следующего этапа. |
| CHK010: late results | stopped до wire, после wire/exception и после decoder отвергает наблюдённые cancel/expiry; late200/401 не превращаются в target или auth authority. Native request проверяет active после cleanup тоже. Cooperative checks не заменяют final current-context fence у будущего consumer и не обещают атомарность return относительно последующей cancellation. |
| CHK011: tests настоящего helper | Portable callback подменяет wire, не resolver decisions. Native TU включает actual transport cpp с локальными WinHTTP wrappers и private now function pointer; настоящим остаётся WinHttpCrackUrl, но реальная сеть не используется. CMake исключает production HTTP OBJECT только для этого native TU, сохраняя его у ordinary targets, без double definitions/warning suppressions. |
| CHK012: граница acceptance | Target остаётся untrusted owned data. Resolver не валидирует разрешение launch, не открывает URL, не создаёт owner timer/lease/controller/bridge/shim. Браузерный handed_off, UI15s и installed T119 не следуют из source approval. |

### Исключения и прежние callers

Новый stdlib ownership закрывает ранее возможную утечку после открытия
session/connection/request при string allocation exception. Текущие native
fixtures вводят bad_alloc на send/receive/headers/available/read через actual
request; exception доходит до existing resolver catch, все три handles
закрываются ровно один раз, возвращается dependencyUnavailable без target.
Это проверка unwind и owners, не обещание полного восстановления процесса
при любом global out-of-memory. Новый public API не объявлен noexcept;
allocations вне wire catch не рассматриваются как безусловно безошибочные.

У обычного request сохранились30s read-loop deadline, phase timeouts
5000/5000/10000/10000ms и2MiB/equal-cap behavior. Это именно сохранение
defaults/limits, **не** новый hard whole-request30s contract для legacy.
Также замечено ужесточение существующего helper: status-query failure теперь
явно transportFailed, cancellation проверяется в большем числе фаз, cleanup
работает при исключении. Это fail-closed изменения, не скрытое утверждение,
что все error-path raw fields идентичны старым. Identity/deletion не принимают
такие failures; upload получает retryable failure вместо status0 rejection.
Не обнаружено влияния calendar64KiB/15s на default callers или нового
успешного mutation пути. Storage/recovery алгоритмы вне этой границы не
пересматривались.

## Испытания и происхождение evidence

Reviewer самостоятельно выполнил только:

```sh
ctest --test-dir /tmp/graf-f200-calendar-build.gOxKwL --output-on-failure -R '^(CalendarJoinResolverTests|DesktopUploadRecoveryTests|DesktopDeletionProtocolTests)$'
```

Результат: **3/3 PASS, exit0**, соответственно1.67s /0.01s /0.00s;
overall1.69s. Это запуск existing Release portable binaries, без собственной
пересборки и без исполнения _WIN32 request branch на macOS. Build cache
указывает на canonical apps/windows. Scoped git diff --check также exit0.

Отдельно **Main сообщил**, привязав к шести совпавшим хешам выше:
MSVC Release x64 build exit0 и focused3/3 PASS, включая native production
request fault tests; Windows NTFS GetFileHash всех шести файлов совпал.
Reviewer лично проверил source assertions и CMake graph, но не запускал VM
и не приписывает себе Windows build/test. Ранее Main сообщил portable40/40;
на момент этого снимка финальный full portable relink/rerun после RAII ещё
ожидался. Ни прежние40PASS, ни будущий rerun не являются T119 acceptance.

Native assertions охватывают actual GET path/scoped headers/empty body,
redirect/cookie options, cancel/expiry после open/timeouts/connect/request/
option/send/receive/headers/available/read/last_read/EOF, API false failures,
exception cleanup,65535/65536/65537, hidden tail при available0, trickle через
original deadline, sub-ms positive budgets, already expired/no open и legacy
timeouts/body cap. C4459 исправлен именами wirePath/wireVerb/wireHeaders/
wireStatus/wireCursor, не отключением warnings. Assertions включены и при
Release/NDEBUG.

## Findings и остаточные тестовые границы

**Critical0 / High0 / Medium0. Request Changes нет.**
Ниже дополнительные измеримые проверки, не обнаруженные source дефекты и
не блокеры этого bounded approval:

1. Native custom-header fixture пока отвечает «header absent»: успешные
   size-probe/value-read auth-expiry и Retry-After, invalid/oversized metadata
   и interruption именно value-read не выделены в отдельные assertions.
   Portable valid/invalid expiry проверен; native extraction лично прочитан.
2. Portable fixture проверяет неизменность original3s deadline, но не отдельный
   future>15s clamp assertion. Формула min и передача одного deadline видны
   непосредственно в source; будущий operation owner должен доказать original
   start ещё до dispatch.
3. Normal cleanup имеет post-close active check, но fixture не изменяет
   cancellation/clock внутри CloseHandle и не утверждает relative close order
   отдельным журналом. Source порядок и exception owners проверены; каждый
   созданный handle в существующих fixtures закрывается ровно один раз.

Реальные TLS/PAC/network latency, malformed native URL corpus, мгновенное
прерывание synchronous OS wait, runtime owner timer/current fences/busy lease,
browser recovery/opener/Record и installed behavior не проверены здесь и
не являются выполненными пунктами этого отчёта. Ограничения остаются у
соответствующих следующих T119 этапов, не требуют второго HTTP клиента.

## Ponytail и терминальный вердикт

Ponytail-review: **Lean already. Ship.** Это оценка формы данного diff,
не команда release/merge/install. Existing request/UploadResponse/helper,
stdlib unique_ptr и один private clock seam заменяют возможные дубликаты;
generic transport/clock framework, watchdog и новые dependencies отсутствуют.
Security checks и native self-check assertions не предлагаются к удалению.

**SOURCE Approved, C0/H0/M0, bounded source blockers0** для шести точных
хешей. Approved requirements gate не заменён, его markers не менялись.
Следующий controller/bridge/URL/launch срез потребует собственного review;
whole T119, runtime handoff, issue closure и release этим verdict не приняты.

## Приложение: только механический MSVC portability diff T116

Добавлено по отдельному прямому запросу пользователя после T119 review.
Не повторный storage review и не расширение resolver approval. Единственная
новая область чтения — строка1132 и её непосредственный контекст в
`apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp`,
плюс declaration величины blockBytes в `ProtectedCustodyCodec.h:92`.
Исходники и тесты reviewer не менял.

Main сообщил diagnostic full Windows testbuild compile RED:
MSVC C3493 и последующие ошибки на lambda[] с local constexpr blockBytes.
Это отдельный T116 finding, **full Windows build не PASS**. Выше приведённое
MSVC exit0/3PASS относится к focused T119 targets, не всем Windows targets.
На момент приложения повторный full Windows build ещё ожидается.

Точная рассмотренная замена:

```diff
-            const auto full = tree->appendBlock(CustodyBytes(blockBytes, 0x37));
+            const auto full = tree->appendBlock(CustodyBytes(ProtectedCustodyCodec::blockBytes, 0x37));
```

Before SHA-256, сообщённый Main:
`454febc71de0c1d1ef787f699afe79a8b1d612543dda8be7594c0b6824e66c23`.
Current after SHA-256, самостоятельно вычисленный reviewer:
`ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`.
Reviewer read-only заменил только выражение строки1132 обратно в stdout
и вычислил SHA-256 полученного потока; он **точно совпал с before hash**.
Файл на диске не менялся. Поэтому относительно присланного before snapshot
подтверждена именно эта одна строка, без прочих скрытых изменений.

Лично установлено: local `constexpr ULONG blockBytes` на1127 и static
`constexpr std::uint32_t ProtectedCustodyCodec::blockBytes` означают одну
величину256*1024. Constructor CustodyBytes получает прежнюю длину и прежний
fill byte0x37; tail `{1,3,5}`, assertions и дальнейшие uses local blockBytes
не меняются. Прямое qualified static constexpr expression не требует захвата
local variable в lambda[], не добавляет состояние/lifetime dependency,
literal block size или production изменение. Warning/error suppression нет.

**Bounded portability source Approved: C0/H0/M0, source blockers0.**
Ponytail: одна qualified constant вместо изменения capture или workaround
framework. Свежий MSVC compile/run этого исправленного T116 target пока
не подтверждён reviewer; full Windows completion остаётся отдельно открытым.
Текущие шесть T119 hashes/verdict не изменяются, whole storage/T116
correctness, runtime и acceptance этим приложением не рассматриваются.

### Последующее сообщение Main и закрытие bounded review

После приложения Main сообщил fresh portable full40/40 PASS после RAII
(21.19s), portable focused owner-test1/1 PASS после механической строки
(0.43s), Windows GetFileHash owner-test=`ca4e041...` matching canonical,
full Windows build exit0 и owner native test Passed173.12s. Windows CTest43
на момент сообщения ещё выполнялся; итог43/43 **не объявляется PASS**.
Это последующая информация Main, не повторные испытания reviewer и не
расширение source scope. Исторический pre-fix full-build RED выше сохранён.

One-line portability appendix завершён: before/after привязка доказана,
семантика constant/bytes не изменена, C0/H0/M0 и bounded blockers0.
T119 source verdict остаётся Approved C0/H0/M0 на шести указанных хешах;
новых T119 product edits Main не заявляет. Больше проверок/изменений для
этого ограниченного reviewer задания не требуется. Никакого whole T119,
storage acceptance, runtime handoff, установки или release утверждения нет.

### Терминальная фиксация после прерывания

Reviewer лично свежо перечитал canonical строку1132, её local constexpr
initializer и existing static constexpr declaration; повторно вычисленный
file SHA-256 — `ca4e041ca15b978e6573e3473fe8ac003b166ac313bbc46c54a643bfbcef3205`.
**One-line portability verdict: Approved, C0/H0/M0, blockers0.**
Замена local blockBytes на existing ProtectedCustodyCodec::blockBytes
сохраняет256*1024 и fill0x37, устраняет необходимость захвата local variable
в lambda[], не меняет production или storage semantics. Ранее доказанная
однострочная before-hash привязка остаётся действующей.

Main теперь сообщил final current full Windows CMake build exit0 и
CTest43/43 PASS227.81s; portable after-RAII40/40 PASS и mechanical-only
focused1/1 PASS. Это итоговое сообщение Main, не собственный Windows run
reviewer. Предыдущее «CTest ещё выполнялся» выше — исторический снимок,
а не актуальный незавершённый тест. Новый test job не запускался.

Bounded review окончательно завершён. T119 source Approved C0/H0/M0
остаётся привязанным к исходным шести неизменным хешам; функциональная
приёмка T119, installed handoff, storage review и release не заявляются.
