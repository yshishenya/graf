# Round268 — REQUIREMENTS: наблюдение места неудачного ожидания

Дата: 2026-10-06. Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty worktree сохранён. Область относится к существующей high-risk-product
T116 / #7444; отдельная новая задача, схема или продуктовая политика не нужны.

## Решение

**SCOPED REQUIREMENTS GO** для предложенного tests-only наблюдения в
`apps/windows/Tests/GrafWindowsContractTests/DesktopUploadRecoveryTests.cpp`.
Scoped analyze: CRITICAL=0, HIGH=0, обязательных неразрешённых уточнений нет.
Это допуск к указанному изменению и его проверке, НЕ SOURCE approval ещё
не написанного кода и НЕ прохождение native validation.

**CURRENT VALIDATION NO-GO/PENDING остаётся:** Release267e FAILED5/6,
DesktopUploadRecoveryTests deadline assertion330. Наблюдение не исправляет
и не аннулирует этот результат. Полная T116 и приложение не приняты.

## Лично прочитанная нормативная область

Использованы полностью прочитанные `speckit-checklist` и `speckit-analyze`.
Проверены root guidance/README, spec-kit-flow, codex-worktrees, tracker-policy,
release-and-validation, применимые product-gates, constitution, active feature
context и текущие spec/plan/tasks/quickstart по затронутой области. Все критерии
десяти действующих нормативных checklist прочитаны; исторические отчёты не
перечитывались как новый набор обязательств. Читать гигантскую validation
историю для этого решения не требуется.

Read-only prerequisites `--json --paths-only`, `--json --template checklist-template`
и `--json --require-tasks --include-tasks` указывают на активную Feature200
в canonical worktree. Они не выполняют тесты или hooks. Checklist рассматривается
как качество требований, а не как доказательство runtime PASS.

| Требование / текущий источник | Связь с предложением |
| --- | --- |
| spec FR-013:494–498 | Recovery/queue truth не меняются; наблюдение не сбрасывает queue и не создаёт пустую замену. |
| spec FR-021:528–532; security CHK017:40; audio CHK022:40 | Только номер строки и длительность. Ни пути, ни identity, ни содержимое, ни exception text не выводятся. |
| spec SC-005:588–590, SC-006:591–593 | Наблюдение помогает расследованию, но не доказывает 100 recovery cycles или security acceptance. |
| constitution VI:401+; release-and-validation:179–200, 434–440 | Сбой функционального assertion остаётся жёстким; scoped факт не заменяет native/full/release evidence. |
| plan:1501–1534, tasks:536–570 | Существующий независимый storage/T116 порядок сохранён; не подключается protected queue или эффект. |
| quickstart:1–43 | Portable результат не объявляется Windows/MF/installed доказательством; main выполняет необходимые проверки отдельно. |

## Принятая конкретная форма

Изменяется только тестовый файл: добавить `<cstdio>`, переименовать helpers
в `waitForAt(int callsite, Predicate)` и `runWorkerAt(int callsite, ...)`.
Локальные variadic macros `waitFor(...)` и `runWorker(...)` передают `__LINE__`.
`runWorkerAt` передаёт свой `callsite` непосредственно в `waitForAt`, а не
номер строки внутри helper. Это важно для отличия разных worker scenarios.

`waitForAt` сохраняет один start на `steady_clock`, deadline=start+3s,
вызов predicate до проверки времени и sleep1ms после успешной проверки.
Внутри прежнего loop один `now` используется для обоих условий:
при now>=deadline вывести ровно
`RECOVERY_WAIT_TIMEOUT callsite=%d elapsed_ms=%lld\n`, выполнить `fflush(stderr)`,
затем прежний `assert(now < deadline)`. Значение elapsed рассчитывается
из того же start через duration_cast<milliseconds>; для `%lld` передаётся
явный `long long`, для `%d` — `int`. Нового ограничения или повышения3s нет.

Macros размещаются после соответствующих определений helpers и до первых
вызовов: они не должны подменять объявления. Все текущие calls используют
эти локальные helpers; variadic форма сохраняет аргументы и lambda bodies.
Никаких новых target/framework/dependency, production API, source_location,
синхронизации, retry, пропуска assertion или нового timeout не требуется.

Сохранено существующее `#undef NDEBUG` перед `<cassert>`: отказ обязан
оставаться активным также в Release. Печать выполняется только на неудачном
пути, без файлового журнала и без ожидания дополнительного worker. `fprintf`
и `fflush` не дают hard wall-time guarantee и не превращают helper в watchdog.

## Source trace и предел наблюдения

Лично прочитаны текущие helpers Tests:327–341 и все места их вызова; текущий
assertion330 сам по себе не различает ожидания. Proposed `__LINE__` различит
direct waits и места `runWorker`, но один callsite внутри loop не определяет
номер итерации. Дополнительные данные для этого gate не нужны.

Tests:939–954 содержит `PausedWork`: release wait948 исполняется в worker.
Владелец до release981 выполняет disk.load979/enqueue980, а до release1015 —
markQuarantined1014. Поэтому будущая строка позволяет различить worker release
wait от owner entered/drain/start waits. Это возможный путь задержки по source,
НЕ установление причины267e и НЕ доказательство deadlock.

Scheduler:28–68 prepare предшествует startAsync и началу runWorker wait;
execute:71–86 публикует done release, drain:115–138 читает acquire.
Drain может выполнять синхронные queue mutations. Пока predicate выполняется,
helper не проверяет deadline. Если predicate затем возвращает true, deadline
вообще не проверяется — именно это прежнее поведение сохраняется. Поэтому
elapsed не устанавливает, где потрачено время, и не прерывает зависший predicate.
Наблюдение не добавляет вывода о VM, ОС, диске или production scheduler race.

## Инвентарь требований и сохранность

До записи:133 `.md` файла, из них10 текущих нормативных и123 исторических/
контекстных отчёта. SHA-256 инвентаря строк `sha256  relative-path\n`, пути
отсортированы: `4db3f99fac8f12d6bfcbc829a21e71549015c4fcdb8aa384a19590bc209f2dd9`.

| Действующий checklist | Подтверждено | Открыто |
| --- | ---: | ---: |
| requirements | 22 | 0 |
| security | 27 | 0 |
| ux | 25 | 0 |
| audio-capture | 24 | 0 |
| advanced-routing | 14 | 0 |
| calendar-launcher | 5 | 0 |
| calendar-operation | 8 | 0 |
| calendar-wire | 5 | 0 |
| packed-writer | 12 | 0 |
| privacy-pause | 12 | 0 |
| Итого нормативных | 154 | 0 |

В остальных123 файлах отдельно256 checked/10 historical unchecked. Эти10
не стали новыми нормативными пунктами и не закрываются этим gate. Tasks120:
93 closed/27 open; T116 остаётся открытой. Связь #7444 берётся из активной
tasks.md и сообщения main, reviewer не делал нового live GitHub запроса.

В `.specify/extensions.yml` все6 before/after implement/analyze/checklist
стадии имеют по1 зарегистрированному git.commit hook, enabled=false.
Итого enabled0/dispatch0; «before absent» не утверждается. Код, нормативные
маркеры и все133 прежних файла не меняются; добавляется только этот report.

## SHA-256 базового состояния

| Артефакт | SHA-256 |
| --- | --- |
| DesktopUploadRecoveryTests.cpp | `480e8fd4a744188215e019c3feb9e351de325a512fffc00c60f7ba1032aeac42` |
| DesktopUploadRecoveryScheduler.cpp | `e4fdac0709bf03c7b3f18d2629651ebded4f895d24fd3f026cc8bee066d6bf3c` |
| DesktopUploadRecoveryScheduler.h | `fd27723045442bf0d0b8ba8359db1da76faa3d4254e695defd61efe6f2886862` |
| spec.md | `b411bfb620e9d571422f9c423b0ae193ed70e87303d08e84a4b9844e32f81658` |
| plan.md | `527e660d9e1682e7a0f0a79118ea4bab38d4c174542b49c0113f571528a5b89c` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart.md | `fc225d2ec40cc26a7fad0bc6d7adcb22d7f4d676fcdf70b2e645dbbdb06ddb8e` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| extensions.yml | `ad728fdff37fe1783903777fbdf792fc44752f2818d1765c76a7e1bea9dabb6c` |
| Prior267 path correction report | `c3717fb2a15177b82dcfb28b3e5fef129eaa3971bf16ddd8b5c602aec6848912` |

## Следующий шаг main и непредоставленные полномочия

После этого REQUIREMENTS GO main может реализовать точную tests-only форму,
проверить fresh source diff/сборку и выполнить focused recovery validation
в уже установленном безопасном состоянии VM. Reviewer не запускал VM,
tests или EXE; gate не удостоверяет guest liveness или исход Debug267f.

По сообщению main a/e Recovery EXE побайтно одинаковы; это не доказательство
VM cause. Старый267e FAILED5/6 остаётся отдельным результатом; успешный retry
его не переписывает. Не требуются ослабление3s, отключение теста или автоматическое
повторение всей suite вместо установления failed callsite.

Принят только допуск к наблюдению. Protected semantic/account/epoch/shared
budget/admission, actual queue/writer adoption, T116–T120, H250, legacy AAC/B1,
installed/UX/hardware/merge/release остаются вне GO. Исторический native49/50
не становится GREEN; никакого global goal blocked/complete перехода нет.
