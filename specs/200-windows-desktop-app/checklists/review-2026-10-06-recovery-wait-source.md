# Round269 — SOURCE: наблюдение места неудачного ожидания

Дата: 2026-10-06. Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Dirty preserved. Reviewer пишет только этот новый report. Existing T116 / #7444,
high-risk-product; ни новый task, ни изменение требований не вводятся.

## Два независимых решения

**SCOPED SOURCE correctness GO**, CRITICAL=0/HIGH=0: прочитанный tests-only
diff соответствует принятому Round268 gate. Номер вызывающей строки,
типобезопасный вывод двух чисел, прежний deadline и активный assertion сохранены.
Выполненная main portable/harness проверка описана отдельно ниже; Windows
validation этим SOURCE решением не утверждается.

**PORTABLE проверка выполнена; NATIVE VALIDATION PENDING.** Main сообщает baseline
configure/build0 focused2/2, Recovery2.93s; затем post-change build0 и serial
portable46/46 PASS32.92s, session71648/chunk5aae6a. Reviewer лично прочитал текущий
CTest raw и сверил46 test entries/46 passed/0 failed; это не собственный запуск.
Native Round269 не запускался: по main Windows password expired требует входа
владельца. Reviewer не проверял пароль/guest состояние и не действует в VM.

Release267e FAILED5/6, прежний deadline330 остаётся отдельным неуспешным
результатом. Новый SOURCE GO его не заменяет. Native/goal/application/merge/
release GO не предоставляется; T116 и остальные полные приёмки остаются открыты.

## Метод независимой проверки

Лично полностью прочитаны skills `code-reviewer` и `ponytail-review`.
Optional preflight не запускался: scope ограничен чтением кода и одним report.
Лично полностью прочитан собственный accepted gate и сверены его SHA, текущие
helpers, вызовы, `#undef NDEBUG`, CMake C++17, существующий worker/cancel поток.
Применимая guidance и нормативный контекст сохранены из Round268; свежая
проверка active feature/branch/HEAD/tasks/CMake и инвентаря выполнена.

Полный `git diff` RecoveryTests относительно HEAD содержит также более ранние
изменения synthetic native/portable AAC fixture. Они не считаются Round269 diff
и не удалялись. Для точного отделения scope reviewer **в памяти** заменил только
блок `waitForAt`/`runWorkerAt`/двух macros на прежние helpers и убрал новый
`#include <cstdio>`. Полученный SHA-256 совпал с accepted baseline:
`480e8fd4a744188215e019c3feb9e351de325a512fffc00c60f7ba1032aeac42`.
Файл не переписывался. Так подтверждено отсутствие иных изменений regression
bodies/asserts/callers в этом source slice, а не только визуальная похожесть diff.

`git diff --check` по RecoveryTests прошёл. Это source проверка, не компиляция.

## Конкретные проверки кода

| Место в текущем RecoveryTests.cpp | Вывод |
| --- | --- |
| 6–9 | `NDEBUG` снимается перед `<cassert>`; assertion не исчезает в Release. Scope не меняет этот прежний порядок. |
| 11 | Единственный добавленный include `<cstdio>` предоставляет `std::fprintf`/`std::fflush`. |
| 328–332 | `callsite` имеет тип int; один steady-clock start, deadline=start+3s; predicate вызывается первым; затем один now. |
| 333–338 | Печать только при now>=deadline. Статическая строка, `%d` получает int, `%lld` — явный `static_cast<long long>(elapsed)`. Elapsed — duration_cast<milliseconds>(now-start). |
| 339–340 | Assertion использует тот же now и ту же3s границу. На неуспехе log/flush предшествуют assertion; sleep1ms остаётся после успешной проверки. |
| 343 | Variadic `waitFor` macro определён после helper и до callers. Передаёт `__LINE__`, не меняет predicate body. |
| 345–353 | `runWorkerAt` сохраняет startAsync assertion и handled/drain/busy поток; явно `waitForAt(callsite, ...)`, не внутренний `__LINE__`. Macro определён после function body. |
| 397+, 831+, 959+, 1229+ | Существующие runWorker/direct wait calls остаются без изменения; macro применяется и внутри внешних assertions/lambdas. |

`__LINE__` указывает место invocation в данном frozen source, а не стабильный
идентификатор навсегда. Для multiline вызова возможный номер должен сверяться
с этим source/compiler, не с прежними267e строками. Передача int корректна;
нет повторного исполнения predicate или worker из-за этих macros.

В worker `PausedWork` direct wait959 получает собственную строку. Owner entered/
drain/start waits983/994/1004/1009/1011/1016/1024/1027/1037/1048/1051 получают
свои места. `runWorkerAt` forwarding350 отделяет разные вызывающие scenarios,
а не сводит все ошибки к строке350. Один вызов внутри matrix loop всё ещё не
обозначает конкретную итерацию — gate не требовал такого вывода.

Внешние тестовые аргументы/queue identity/paths/token/exception не передаются
в fprintf. Только статическая метка, два числа и newline; никакой новой
production диагностики, файла, parser/schema, framework, dependency или target.

## Сохранённые ограничения и наблюдение отказа

Предикат может сам выполнять синхронную IO или долго не возвращаться. Deadline
проверяется только после false; если predicate вернул true, проверка времени
не выполняется. Это прежний порядок, не новый hard watchdog. `fprintf`/`fflush`
тоже не дают гарантии wall-time и не изменяют выбранный outcome при now>=deadline.
Отсутствие строки не доказывает отсутствие задержки внутри predicate.

После предварительного source review main исполнил внешний harness на том же
source SHA. Reviewer лично прочитал `/tmp/graf-f200-round269.xj4etH/recovery-wait-negative.cpp`:
он переименовывает только original main при include **actual current файла**, затем
в своём main вызывает true predicate либо, после `#line 700`, false predicate.
Repo source не копирует/не подменяет helper. По main compile0 с `-DNDEBUG
-Wall -Wextra -Wpedantic -Werror`, existing CMake link objects; session71877/
chunk130390: true exit0/no stderr, false ожидаемый SIGABRT, строка
`RECOVERY_WAIT_TIMEOUT callsite=700 elapsed_ms=3001`, assertion сохранён.
Это фактическое main execution, не reviewer execution. Отдельный immutable
stderr/compile receipt reviewer не получал; точный текст исхода атрибутирован main.

Так проверены прямой macro callsite, metadata и fail-after-log при `-DNDEBUG`.
Это НЕ отдельный runtime тест forwarding через `runWorkerAt`: его корректность
подтверждена source строкой350, forwarding-negative harness не заявляется PASS.
Для scope при явной прямой передаче int отдельный synthetic scheduler test
не является blocking finding. Нет утверждения обо всех возможных waits/races.

Reviewer не создавал/не исполнял harness. Увеличения timeout, отключения assertion,
production edits или private/device/network данных нет. Результат harness не
исправляет native267e и не заменяет native сборку текущего test source.

Лично прочитанный portable CTest raw находится в `/tmp/graf-f200-round269.xj4etH/
Testing/Temporary/LastTest.log`:46 последовательных entries,46 `Test Passed.`,
0 `Test Failed.`; Recovery entry27 PASS3.63s. Это текущий raw build tree, не
неизменяемый external receipt; SHA ниже фиксирует прочитанные байты. Main total
32.92s относится ко всей suite, baseline Recovery2.93s — к предыдущему focused run.

Причина267e по-прежнему не установлена. Совпадение a/e Recovery EXE не доказывает
VM cause. Здесь нет исправления production race/deadlock/IO или разрешения
подменить native проверку portable результатом.

## Ponytail

`Lean already. Ship.` Только оценка простоты этого diff, НЕ разрешение выпуска.
Переиспользован прежний helper и stdlib; C++17 не требует новой source_location
или logger. Два локальных macros нужны для номера caller без массовой правки
вызовов. Безопасных cuts, сохраняющих accepted observation, не найдено.

## Точные source anchors

| Артефакт | SHA-256 |
| --- | --- |
| RecoveryTests.cpp current | `fe55921e06e473be3c32e5e4d39a8c79cbce8f7d77d444c566e97925b6dc4ef8` |
| RecoveryTests.cpp accepted baseline / reconstructed in memory | `480e8fd4a744188215e019c3feb9e351de325a512fffc00c60f7ba1032aeac42` |
| RecoveryScheduler.cpp unchanged | `e4fdac0709bf03c7b3f18d2629651ebded4f895d24fd3f026cc8bee066d6bf3c` |
| RecoveryScheduler.h unchanged | `fd27723045442bf0d0b8ba8359db1da76faa3d4254e695defd61efe6f2886862` |
| CMakeLists.txt unchanged | `b0c2f16b2047d71f8e94395266e1c9b721b2f046ba7581ee5a893ac10d5aec8e` |
| tasks.md unchanged | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| Round268 gate unchanged | `a8f852c0f6a4594c9c0d5ac945b2d5187cb47e597a729970e1ab54678c7ad4e3` |
| Read portable LastTest.log | `b82bb50d4e1de6085fae0f07dab655dc44d29b9024b25413b60f23da65983f0d` |
| Read external harness source | `70a67822bb1bc8892dd6d54e1f81f3e3876dc02adb9cdd9482c01e2d24becb4e` |
| External harness executable, read/hash only | `f26ffcd5c0ca8d048a94b97a0085b7e3cc00773d9d2fa4a9018af8247c127636` |
| Portable Recovery EXE, read/hash only | `85092ba23b48991b62c71644cfe8c3fc7ac8fe801617a603adc60708c3a18678` |

## Инвентарь и границы

До reviewer write134 прежних `.md` файла. SHA-256 sorted строк
`sha256  relative-path\n`: `aef890063fbc1a6192f97bc808c60f6ffeb621bc41cc34684e2b7c364f3f679a`.
Десять действующих normative checklist154/0; остальные124 context/history
256 checked/10 historical open, не новые обязательства и не closures.
Tasks120/93/27 сохранены. После добавления только этого report —135 файлов;
предыдущие134 hashes и markers сохраняются.

Reviewer не менял исходники, tests, документы main, старые reports, GitHub,
hooks, VM, password/profile, install или commits. Full T116–T120, protected
semantic/admission/owner/epoch/budgets/writer adoption, H250 и AAC/B1,
installed/UX/hardware/merge/release вне данного SOURCE GO. Нет native/goal PASS
и нет изменения global goal status. Последующий terminal evidence остаётся
самостоятельной проверкой, не предположением из source correctness.
