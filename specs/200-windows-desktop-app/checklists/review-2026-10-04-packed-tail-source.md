# Независимая проверка исходников: packed short tail / T116

Дата: 2026-10-04. Отметки принадлежат независимому reviewer.
Сигнал source-ready получен только для статического чтения; основным агентом
прямо исключено окончательное принятие до новых native результатов.

## Первоначальный вердикт до terminal native receipts

**Статическая проверка завершена: 8 checked / 1 unchecked (PTS009).
Финальный SOURCE ACCEPTANCE НЕ выдан.** Подтверждённых новых дефектов
CRITICAL/HIGH/MEDIUM в рассмотренном алгоритме или тестовых исходниках
не найдено. PTS009 ожидает доказательства исполнения точного снимка;
это реальная непроверенная граница, а не отрицательный исход native теста.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
Лично сверенный HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Risk lane: independent review внутри high-risk-product; reviewer меняет
только собственный отчёт. Готовность Windows не выводится из этих отметок.

Requirements gate принят только в своей области: 14/0, SHA-256
`eb341afb826a316b9f547e67dfd4e4de30ec521dfbea8cfd1a1a605d87d7c4ce`.
Неизменные нормы и прежние полного чтения материалы сохранены из проверки
этого gate. В текущем проходе прочитаны полностью четыре фактических source
файла; повторно прослежены Guard/Locked IO, codec/format semantics,
admission и CMake test routing. code-reviewer перечитан.

## Reviewer-owned source критерии

- [X] PTS001 Оба public API передают только bytes в один private `commitBlock`; нет caller descriptors, legacy alias или второй write backend. append разрешён для1..262144 при aligned EOF, replacement — только nonempty short tail, complete oldTail..full replacement без implicit shrink.
- [X] PTS002 Арифметика block/count/length/generation/slot сохраняет wire bounds и exact tail. Exact прежняя paired authority и selected slot проверяются до append/head effects; stale proof отказывает без новой публикации.
- [X] PTS003 Прежний Guard/job/Owner/State mutex охватывает весь commit, оба readback этапа, catch и nonallocating return. writeReady проверяет observed fault раньше input/последующей admission; первый exact error/nativeError сохранён. Обычный invalidInput не poison старый reader.
- [X] PTS004 Прочитанные authenticated BASE paths и exact unchanged Ref64 доказывают единственную изменённую позицию для обоих modes. New DATA exact input size, selectors/version/extent/tail, SHA перед decode, ≤1DATA+3NODE/290816B; ZERO splitting не меняет соседние ranges и не разворачивает flat index.
- [X] PTS005 Сохранён полный append-only/flush/independent readback→HEAD attempt/flush→обе exact HEAD→повтор new records/confinement→proof путь. Logical ambiguity не исчезает после physical cell verification; orphan tail не truncate/reuse, writer copies не заменяют чтение диска.
- [X] PTS006 Pin/dirty/owned reservation и charged prospective Tree/control storage остаются до publication; result copy/move nothrow, base lease сохранён при отказе. Не появился allocation после ACK или reliance на optional NRVO; internal DPAPI/MF quota не объявлена доказанной.
- [X] PTS007 Immutable прежний root/length сохраняется у старых short/full pinned snapshots после replacements и вытеснения из HEAD; strong Owner/results удерживают actual custody. Cold verify по-прежнему читает обе HEAD и достижимые closures, не переносит proof через новый epoch.
- [X] PTS008 Тестовые исходники проверяют actual shared worker и новые modes: exact short/same/growing/full→next append, старые bytes, stale/maxgen/64GiB/radix/inlineZERO, admission и native cuts/pressure/sticky-error. Valid unchanged sibling negative проходит real codec/hash/DPAPI и child semantics до structural-diff отказа; CMake не подменяет worker и не дублирует его TU.
- [X] PTS009 Представлены terminal native результаты текущих новых веток и последних дополнительных tests с exact source identity: main finalsync8904 MATCH4of4 / EXIT0 → Releasebuild49047 EXIT0 → Windows Release CTest1577 2of2 PASS190.45s / EXIT0; Debugbuild91346 EXIT0 → Windows Debug CTest23598 2of2 PASS189.22s / EXIT0 на том же final snapshot. Четыре final source SHA и три неизменных baseline SHA лично сверены; native fixtures/assertions включены по прочитанным исходникам и подтверждению main. Portable ограничения и прежние отрицательные результаты сохранены отдельно. Исполнение принадлежит main, не reviewer; extras не приняты заранее.

## Прямые статические доказательства

### API, арифметика и отказы

Tree.h:37–46 даёт только `appendBlock`/`replaceTail` и private общий worker.
Tree.cpp:114–120 — два минимальных делегирующих вызова. Поиск всех caller
в apps/windows нашёл только два существующих тестовых файла; активного
`appendFullBlock` alias/caller нет. Historical evidence не переписано.

Tree.cpp:134–143 сначала проверяет `writeReady`, затем input и tail:
empty/oversize, append при unaligned EOF/64GiB, replacement empty/aligned
или input короче старого tail, max generation отказывают до append/HEAD.
Это не автоматически sticky failure для неверного вызова.

Tree.cpp:152–155:

- Private доказанный descriptor имеет length≤68719476736 и точный
  blockCount=ceil(length/262144). При append aligned length<limit означает
  как минимум один полный блок оставшегося представимого диапазона.
  Поэтому input≤262144 даёт новую length≤limit без overflow.
- При replacement tail>0 доказывает nonempty base и blockCount≥1:
  `blockCount−1` не underflow. Индекс максимум262143. Умножение предварительно
  переведено в uint64; `index×262144+input.size()` максимум64GiB.
  Candidate `block+1` равен прежнему count; для append равен old count+1.
- Max uint64 generation исключён до `base+1`; target=(generation−1)%2.
  Node slots вычисляются по прежним strides4096/64/1, не по byte offset
  tail. Short→full не создаёт лишний DATA index, лишь меняет logical EOF.

Это доказательство из closed/private descriptor invariants, не новый публичный
доверенный descriptor input. Нет основания требовать второй arithmetic model.

### Authority, structural diff и ACK

Tree.cpp:124–133 держит base lease и Guard вне try/catch. Exact `heads_`
и selected проверяются в144–154 до записи. Physical Owner/Files/CMake
не изменились относительно принятого round221 снимка.

Tree.cpp:164–198 сохраняет authenticated BASE bodies и все64 child checks;
inline ZERO splitting строит лишь changed path с прежними prefix references.
DATA position — вычисленный append index или last-block index, не caller root.
Tree.cpp:206–237 пишет один DATA и три NODE с hard physical span guard.
DATA body length в repeated validate сравнивается с input.size(), а child
decode принимает лишь exact tail по candidate length. New NODE siblings
в251–260 сравниваются побайтно со старым BASE Ref64, изменённый slot —
с единственным expected new child. Нет full old DATA scan на checkpoint.

Codec `openReferenced` сверяет exact envelope length/SHA до DPAPI, затем
typed header/checksum; DATA length входит в expected address. Format
`decodeChild` ограничивает expected level/base, selector path, generation,
child-before-parent, EMPTY beyond EOF и точную short/full payload length.
Повторное чтение writer BODY не используется как авторизация соседних refs.

Tree.cpp:266–299 сохраняет прежний порядок: first flush/validate,
makeProof до HEAD write, physical publish, release HEAD caller copies,
readHeads обеих ячеек, exact candidate/new pair/exact selected-base peer,
second validate, только затем snapshot/committed. Logical `headStarted`
сохраняет ambiguous boundary даже после clearing physical `headAttempted`.
Guard/owner/job живы в bad_alloc catch; результат shared_ptr/scalars
не выделяет память на копирование/перемещение.

### Тесты и фактическое покрытие исходников

TreeTests:262–355: short3, размеры1/3/262143/full; same-size rewrite с иными
bytes; short→short→full→next append; точные old/new bytes и EOF; pinned g2
после вытеснения из обеих HEAD; stale replacement без роста physical file;
job4/pin32/dirty4 replacement refusal, затем successful replacement.
Все continuous owners освобождаются перед отдельным actual cold reopen.

TreeTests:410–507: same-highest altered previous pair regression; compact
ZERO base на1/63/64/4095/4096/262143 blocks→short append→full replacement,
bounded growth/old short bytes/full independent verify. Final64GiB отказывает
следующему append. Generation max проверяется и для append, и для replacement.
TreeTests:555–580: короткий tail внутри inline ZERO subtree, filling и
unchanged zero predecessor/old exact length. Giant DATA allocation нет.

OwnerTests:240–400 параметризует тот же реальный worker для full append,
short append3 и replacement5 от short base3. Main вызывает все три варианты
в строках730–732. Baseline измеряет native write/read/flush counts для каждого
варианта; cuts не заимствуют ordinal full-блока для short режима.
HEAD boundary наблюдается actual positioned offset128/16512/count16384 до
возможного WriteFile fault. FAILED/short/zero write, flush, FAILED/changed/
throwing reads и pre/post-head metadata exception имеют explicit outcome,
no snapshot/base lease/first exact native error и no unsafe retry assertions.
Неверный input/другой mode после fault не скрывает latched error.

Prospective pressure в OwnerTests:283–352 переиспользует измеренный последний
pre-HEAD read и minimum owned charge на final validate check; proof allocation
должен отказывать после первого flush, до HEAD, сохраняя custody. Начальная
owned exhaustion проверяется отдельно без native read/write/flush. Поиск
минимума и assertions остаются runnable evidence requirements, не заявлением
о подтверждённом новом native исполнении.

Valid sibling negative в OwnerTests:154–186,252–275 строит существующий
соседний full DATA; new short append version3 или replacement version4
меняет только sibling0 на structurally valid ZERO в новом NODE_L0.
Реальный seal пересчитывает checksum/DPAPI, worker вычисляет actual envelope
SHA; real open/decodeChild подтверждают допустимость ZERO при правильной
candidate length/blockCount. Assertion `siblingDecoded` исключает обычный
hash/framing отказ. Общий worker должен отказать exact BASE comparison до
HEAD, с одним flush, retained lease/sticky error и external writer denial.
Base records не подменяются, новых production fault switches нет.

REAL Files.cpp включён до codec macro, REAL Tree.cpp под точечной codec spy;
open/read checks делегируются настоящему codec. Прежний отдельный Tree OBJECT
в CMake исключён только из WIN32 OwnerTests, где actual Tree TU уже включён;
portable получает обычный object. `/W4 /WX` и Release assertions сохранены.

Этого статического чтения достаточно для PTS001–008, но не для PTS009:
assertions в `_WIN32` не исполняются portable и не становятся PASS по сборке.

## Идентичность текущего снимка и receipts

На первом и повторном чтении Tree.h/Tree.cpp **не совпали** с переданными
source-ready SHA e332c110…/85a8b0a0…. Ни один вывод этого отчёта не привязан к
тем непрочитанным версиям. Тестовые SHA совпали с сообщением основного агента.
Текущие фактические hashes ниже лично сверены дважды; по этому снимку сделаны
статические выводы. Причина изменения двух source SHA здесь не установлена.

| Файл относительно canonical | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `f18dc05dd7eeff40869cdf2522873fd83ce58d6ebeb866a05859633d4f0af582` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `fc32e711076f395854f55deeb25884bd1d2712b6d1f119818d03a76154c9113b` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `169644bfdcda9f4017b6bed07986d20d13db3cb293bade531218f609bbc1837c` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `ffbafaec76c315cdfb5e9d7a8ba099a4d3c420ace11250035bcfcc7624efd5fc` |
| apps/windows/CMakeLists.txt (не изменён с round221) | `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h (не изменён) | `99dee259444c8a552d3e759e91e10a5a301d38991bfa655ebb90e5abb03922ed` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp (не изменён) | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |

Основной агент сообщил, reviewer не исполнял:

- RED35904: Release BUILD0, CTest1of1 FAIL short-append committed assertion
  line268, EXIT8. Сохраняется отрицательным baseline, не PASS новых веток.
- Portable32336 BUILD0; portable11325 CTest39of39 PASS52.69s относится к
  предыдущему TreeTests до дополнительных budget/stale/maxgen/inlineZERO
  cases. Остальные три переданных source SHA, по сообщению main, прежние;
  несовпавший текущий Tree source требует нового identity binding.
- Native77398 transport255 — не доказанный тестовый EXIT255. Read-only29346
  был заявлен проверкой process/log; его terminal conclusion не представлен
  здесь. Native исполнение новых веток не подтверждено, не принято за PASS
  и не объявлено остановленным по transport failure.

Нет новых замечаний, требующих architecture/requirements изменения.
**PTS009 остаётся unchecked; итог перечитан: 8/1.** Следующий шаг — main
terminal native receipts новых режимов/последних тестов с совпадающими
полными SHA, затем отдельная reviewer проверка evidence. Новый source change
требует проверки его точного diff/identity, не переноса старого результата.

Reviewer изменил только этот NEW report. Code/spec/plan/tasks/старые reports/
checklists/Git/GitHub/VM/runtime/install/commit/release не менял и не исполнял.
Не приняты полная T116–T118, adoption, аппаратные/аудио/доступность/installed
и release gates; их открытость не превращена в новые блокеры этого prerequisite.

## Дополнение: окончательные source SHA и новые сообщения main

Main подтвердил, что final product parameter назван `replace` вместо
скрывающего member name имени; это только rename без изменения semantics.
Фактические Tree.h f18dc05…/Tree.cpp fc32e711… совпали с его окончательным
снимком. Лично повторно сверены все четыре полных source SHA в таблице:
совпали; tests169644…/ffbafa… не изменились. Причина initial несовпадения
теперь объяснена сообщением main; непрочитанный прежний снимок не принимается.

Main сообщил terminal portable62464 **BUILD0 / CTest39of39 PASS41.17s /
EXIT0** именно final four-file snapshot. Это заменяет прежний portable11325
как текущий portable receipt, но не native execution: новые `_WIN32` fixtures
исключены на portable. Governance91347 OK, bootstrap doctor frozen OK,
YAML parse PASS, diff check PASS / EXIT0 — отдельные process/docs проверки,
не substitute PTS009. Round222 прочитан только как main metadata receipt,
reviewer его/F200 fragment не менял и результаты не выдаёт за свои.

По последующему terminal сообщению main read-only29346 EXIT0 наблюдал лишь
прежний MSBuild4372, без cmake/ctest/new tests, со старым LastTest RED02:56.
Cmd/version33883 и25317 EXIT0 подтвердили Windows26200.9168. Это прекращает
неопределённость старого transport77398: новых тестовых результатов в том
наблюдении не было. VM availability/cmd version не новый source identity,
build или тестовый PASS. Main начал отдельный final sync/hash/serial native
build+CTest; terminal receipts этого нового запуска здесь ещё не получены.
Ни завершение, ни успех запуска заранее не приняты; reviewer VM не опрашивал.

**Текущий итог неизменен: static source findings C0/H0/M0, 8 checked /
1 unchecked (PTS009), финальный SOURCE ACCEPTANCE НЕ выдан.** Native exact
guest/source identity и исполнение новых режимов/дополнительных tests остаются
неподтверждёнными. Нет основания требовать новую архитектуру или иной scope.
Новых code/normative изменений reviewer не делал; дополнён только свой report.

## Дополнение: native identity/build до terminal CTest

Main сообщил завершённые nativefinalsync8904 **MATCH4of4 / EXIT0** и
target Releasebuild49047 **EXIT0**, обе target test программы и REAL Tree
скомпилированы с сохранённым `/WX`. Лично повторно сверены четыре final
source SHA и три baseline SHA из таблицы: совпали. Guest сравнение и сборку
reviewer не исполнял; это атрибутированные main receipts, не свои проверки.

CTest1577, по сообщению main, начал actual OwnerTests и остаётся pending.
Ни terminal CTest EXIT0, ни результат новых native modes пока не представлены.
**PTS009 остаётся unchecked, счётчики 8 checked / 1 unchecked; финальный
SOURCE ACCEPTANCE не выдан.** Source identity/build не подменяют исполнение.

Сообщённый main Windows binary diff SHA-256:
`aac1cae4835286752b3451d97f7b8b064899c1cbf49565823c982d27374d6877`.
Это идентификатор diff, не hash установленного EXE/пакета и не runtime receipt.
Планируемые Debug/full suite/AppBuild не приняты заранее; установка не
выполнялась. Новых статических замечаний к неизменному снимку нет.
Reviewer изменил только собственный report, перечитал отметки **8/1**;
VM/build/tests/install/source/normative/Git actions не выполнял.

## Окончательный ограниченный вердикт после native1577

**SCOPED SOURCE ACCEPTED: 9 checked / 0 unchecked; C0/H0/M0.**
Приняты только рассмотренные `appendBlock` и `replaceTail` через единый
private `commitBlock`, точные короткие блоки и относящиеся к ним регрессии.
Ранее записанные состояния 8/1 и pending являются историей проверки;
этот terminal receipt закрывает PTS009, но не превращает прежний RED или
transport255 в успешный тест.

Основной агент предоставил terminal Windows Release CTest1577:
**2/2 PASS, 190.45s, EXIT0**; OwnerTests — **77.36s**, TreeTests —
**111.58s**. По сообщению main, новые native fixtures и assertions исполнялись
на текущем final four-file snapshot, включая последние дополнительные cases.
Это согласуется с лично прочитанными маршрутизацией CMake и исходниками
тестов: native ветки включены для Windows, assertions сохранены в Release.
Цепочка main evidence: guestidentity8904 **MATCH4/4, EXIT0** →
target Releasebuild49047 **EXIT0**, оба теста/REAL Tree, `/WX` →
terminal CTest1577 **2/2 PASS, EXIT0**. Тесты, guest identity и сборку
исполнял основной агент; reviewer их повторно не запускал и не приписывает
себе это исполнение.

Перед обновлением отметки лично повторно сверены все семь SHA из таблицы:
четыре изменённых final source файла совпали; три baseline файла остались
неизменны. Requirements gate остаётся 14/0 с SHA-256
`eb341afb826a316b9f547e67dfd4e4de30ec521dfbea8cfd1a1a605d87d7c4ce`.
Вердикт привязан к этим точным исходникам и canonical HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, а не к будущему коммиту.
Изменение исходников требует новой проверки соответствующего diff и evidence.

Debug target build запущен main последовательно после Release; terminal
Debug build/test receipts ещё не представлены. Debug, full suite и AppBuild
остаются отдельными ожидающими проверками и не приняты заранее. Native
Release закрывает execution criterion этого ограниченного prerequisite;
полная T116 не требуется для его принятия и не объявляется выполненной.
Приведённые длительности не доказывают performance, cadence или Stop.

Не приняты произвольный writeAt, SetSize/shrink/ZERO ranges, cursor/Clone,
интеграция, миграция, полные T116–T118, установленное приложение, аудио,
аппаратная матрица, интерфейс/доступность, подпись или публичный выпуск.
Reviewer обновил только собственный checklist/report; код, нормы, задачи,
старые отчёты, Git/GitHub, VM/runtime/install/commit/release не менял и не
исполнял. После обновления отметки итог должен читаться как **9/0**.

## Дополнение: terminal Debug и окончательный readback

Основной агент предоставил завершённые Debugbuild91346 **EXIT0** и
Windows Debug CTest23598 **2/2 PASS, 189.22s, EXIT0**: OwnerTests —
**149.40s**, TreeTests — **34.65s**. По сообщению main, все четыре final
source SHA неизменны и соответствуют guestidentity8904 MATCH4/4.
Лично повторно сверены локальные семь source SHA, requirements gate SHA
и canonical HEAD: все совпадают с записанным снимком. Debug исполнение,
как и Release, принадлежит main; reviewer VM/tests/build не выполнял.

Эта квитанция дополняет уже принятый Release1577, не заменяет его.
Предыдущий абзац о pending Debug описывает состояние до нового сообщения;
теперь Debug build и оба новых native теста имеют terminal evidence.
Ограниченный итог сохраняется: **SCOPED SOURCE ACCEPTED, 9 checked /
0 unchecked, C0/H0/M0**. Отметки PTS001–PTS009 и заключение перечитаны;
подтверждённых дефектов в рассмотренном неизменном снимке не выявлено.

Full Release all-target build, остальные регрессии с исключением уже
проверенных двух тестов и AppBuild/EXE hash, по сообщению main, выполняются
следом. Их завершение и успех не представлены и заранее не принимаются.
EXE hash сам по себе не доказывает установку или пользовательский сценарий.
Область приёмки, ограничения полного T116 и Windows/release gates из
предыдущего заключения остаются неизменны; длительности обоих запусков
не являются performance/cadence/Stop evidence. Дополнён только этот
reviewer-owned report; чужие marks и файлы не изменены.

## Завершение отчёта: дополнительные terminal receipts main

Отчёт перечитан целиком, включая первоначальные отрицательные/pending
состояния и последующие дополнения. code-reviewer перечитан; область
проверки, требования и критерии PTS001–PTS009 не расширены. Ниже только
атрибутированные результаты основного агента, reviewer их не исполнял:

- allRelease CMake build76959 — **EXIT0**.
- CTest32353 с `-E`, исключающим два новых уже проверенных теста, —
  **39/39 PASS, 62.97s, EXIT0**. Вместе с Release1577 **2/2 PASS** это
  покрывает **41 текущий Release case в двух отдельных запусках**,
  а не один monolithic 41-test run. Debug23598 остаётся отдельным 2/2 PASS.
- AppMSBuild20205 `/t:Build`, incremental Release/x64 — **EXIT0**.
  Main подтвердил verifyAEC3 identity
  `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
  Существующее предупреждение D9025 о W1→W4 осталось: это не clean Rebuild
  и не сборка без предупреждений. Эти сведения не меняют ранее прочитанные
  `/WX`/assertion свойства двух native test targets.

Main сообщил, что source/normative/tasks неизменны, четыре final source
hash подтверждены; reviewer не переносит результаты на новый снимок.
Отдельный read `certutil` для EXE hash ещё pending: hash не получен и
бинарная/установленная идентичность по нему не принята. Добавление main
этих receipts в validation остаётся его действием, не действием reviewer.

**Окончательный ограниченный итог отчёта: SCOPED SOURCE ACCEPTED,
9 checked / 0 unchecked, C0/H0/M0.** Дополнительные успешные проверки
поддерживают этот же снимок, не создают новых review gates и не меняют
область ранее выданной приёмки. Отметки принадлежат reviewer; чужие marks,
старые отчёты, код и нормы не изменены. Предыдущие pending extras теперь
имеют перечисленные terminal результаты; pending EXE hash сохранён явно.

T116 остаётся открытой. Установка, аппаратная и пользовательская
функциональная приёмка, macOS/Windows соответствие и публичный выпуск
не приняты этим отчётом. По сообщению main, установка/commit/release
не выполнялись, данные и VM не перезапускались. Reviewer этих действий
также не выполнял. Полная готовность Windows из source acceptance и
дополнительных сборок/тестов не следует.

## Последнее дополнение: built EXE digest и финальное перечитывание

Основной агент сообщил terminal95437 **EXIT0**, SHA-256 построенного
GrafWindowsApp.exe получен через PowerShell `Get-FileHash`. Точный ASCII
digest сопоставлен с main validation-2026-10-02.md, строкой6229:

`1afa20f7d5febab82cbdfe7c858c0347a41b74f9c3681036d62983593c8ceed4`

Он совпадает с сообщённой uppercase ASCII формой. Вариант первого сообщения
с не-ASCII буквой не использован. Reviewer не читал EXE и не исполнял
`Get-FileHash`; сопоставление относится к main receipt и его записи в документе.
Ранее pending получение digest теперь завершено этим отдельным результатом.

Прежний direct `certutil` вернул transport255
`PrlJob_GetResult: Invalid argument`, без digest. Это не hash результат,
не ошибка EXE и не исход теста. Main явно записал: EXE не запускался,
package не собирался/устанавливался; HEAD, code и normative hashes неизменны.
Полученный digest идентифицирует построенный файл, не установленный пакет,
не runtime и не функциональную приёмку.

Финальные отметки и дополнение перечитаны: **9 checked / 0 unchecked;
SCOPED SOURCE ACCEPTED; C0/H0/M0**. Новые gates/criteria не добавлены,
область приёмки не расширена. T116 остаётся открытой; установка, аппаратная
и полная пользовательская приёмка Windows, commit/release не закрыты.
Reviewer изменил только этот report, без code/normative/Git/GitHub/VM/
runtime действий. Исторические отрицательные и pending записи сохранены
с последующими явно атрибутированными terminal дополнениями.
