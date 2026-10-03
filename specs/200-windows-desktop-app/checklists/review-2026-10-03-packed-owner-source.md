# Scoped source review: packed owner / physical IO — 2026-10-03

Актуальное решение: **scoped source APPROVED — C0/H0/M0**, по current-source
recheck2 в конце отчёта. Initial и промежуточные findings сохранены как история
с их собственными hashes. Это НЕ execution PASS и не полная T116 acceptance.

## Решение initial review (последующие rechecks ниже)

**REQUEST CHANGES — C0 / H1 / M3.** H1 блокирует source approval данного
снимка: обработка исключения после HEAD I/O отпускает mutex до фиксации
sticky fault, поэтому другой admitted вызов может изменить outcome.
Предыдущий requirements-quality gate C0/H0 этим не отменяется: найденные
ошибки относятся к реализации согласованных требований.

Рабочее дерево: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Исходники untracked; привязка именно к bytes/SHA-256 ниже, не к одному HEAD.
Хеши четырёх продуктовых файлов повторно проверены: они не изменились во время
review. Тест параллельно расширен с initial smoke сначала до 225, затем до 282
строк; последний прочитанный снимок привязан к SHA-256 ниже. Report не переносит
ранее сообщённые runtime receipts автоматически на эти новые test bytes.

## Область

Навык `code-reviewer` прочитан лично. Переиспользован принятый owner-gate;
проверены непосредственно:

- `ProtectedPackedCustodyOwner.h`: весь physical API и retained read result.
- `ProtectedCustodyFiles.cpp`: owner State/methods:561–904; новые metadata
  Directory/trustedRoot части:99–101,164,240 и связанные вызовы confinement.
- `ProtectedCustodyFiles.h`: friend:89 и используемые typed physical results.
- `ProtectedCustodyMemory.h`: новый CustodyNativeJob:14–30; существующие
  pin/allocator прочитаны как зависимости lifetime/budget.
- `ProtectedPackedCustodyOwnerTests.cpp`: initial smoke и расширенный снимок
  TU-local native faults/admission tests; не доказательство исполнения.

Existing v1 methods прочитаны только для проверки reuse/security/ID/резерва,
не перепроектировались и не редактировались. Codec/format прочитаны как
вызываемые validators, без повторного полного аудита прежнего codec.
Область — physical prerequisite, не полная T116, tree/descriptor semantics,
cold closure, logical ACK, consumer adoption, migration или release.

## H1 / P1 — mutex освобождается до фиксации post-HEAD allocation fault

Место: `ProtectedCustodyFiles.cpp:882–893`, особенно внешний function-try-block
catch:890–893. Связанные окна sticky-fault также есть в read:790 и append:847.

Внутри publishHead mutex держится lock_guard:869. После физической записи,
flush и readback вызывается check:884. Он не allocation-free: paths array:604–605
копирует filesystem paths, а reused inspect:141 строит wanted wstring.
`std::bad_alloc` здесь возникает **после** `headAttempted=true` и возможного
полного изменения HEAD. При выходе из try lock_guard уничтожается прежде
входа в catch. Catch заново захватывает mutex и читает общий headAttempted,
а не зафиксированный outcome конкретного вызова.

Конкретное допустимое межпоточное расписание, не результат запуска:

1. A вызывает publishHead; запись/flush/readback выполнены. В последнем check
   возникает bad_alloc. В state ещё `fault=none`, `headAttempted=true`.
2. При unwinding уничтожаются lock_guard и локальный CustodyNativeJob A;
   sticky fault ещё не установлен. Второй admitted job B может получить mutex
   до входа A в catch — предел4 это допускает. Внешние strong owners сохраняют
   объект; native IO A уже завершено, ранний close здесь не утверждается.
3. B проходит проверку fault и выполняет физический append либо HEAD operation
   на том же owner, хотя A уже не смог подтвердить post-write состояние.
   При успешном publishHead B строка887 сбрасывает общий headAttempted=false.
4. A входит в catch, устанавливает allocationFailed, но строка893 теперь
   возвращает **notPublished**, хотя HEAD A уже физически записана.

Даже без второго HEAD, один concurrent append после read/append allocation
exception проходит в окне до blockWrites. Допустим вариант с одним writer:
reader A получает bad_alloc в финальной проверке, освобождает lock до:790,
writer B успевает выполнить append до фиксации отказа reader.

Это нарушает serial physical-operation/fault boundary, sticky fail и
обязательный ambiguous outcome после начала HEAD I/O; не зависит от tree ACK.
Новые single-thread fault tests это расписание не воспроизводят.

Минимальное направление исправления: фиксировать failure и outcome под тем
же mutex, без промежуточного unlock; например, inner try/catch внутри lock
scope. Post-HEAD факт конкретного вызова нельзя выводить из флага, который
другой вызов успел сбросить. Аналогично закрыть unwind→blockWrites окна read/
append. Не требуется другой storage backend, async dispatcher или новый API.

Будущая регрессия main: one-shot allocation failure в post-HEAD check плюс
детерминированная синхронизация competing operation; A всегда ambiguous,
следующий writer не совершает IO, owner/results остаются до actual completion.
Отдельно reader-allocation failure при одном concurrent writer.

## M1 / P2 — appendPosition и flush не переводят allocation exception в result

Место: `ProtectedCustodyFiles.cpp:792–807` и `849–860`, вызовы check:800/858.

Эти два public worker methods не имеют catch, хотя тот же check создаёт
filesystem paths/wstrings. В отличие от read/append/publishHead allocation
failure выходит из API исключением вместо CustodyFileResult и не делает owner
sticky failed. Concrete source-level case: при live writable owner следующий
path-copy allocation в check бросает bad_alloc; flush/appendPosition бросает
его caller, fault остаётся none. После восстановления allocation следующий
append разрешён, хотя обработчики остальных методов такую ошибку блокируют.

Особенно важно покрыть финальный check после FlushFileBuffers: flushed disk
fact не должен теряться за исключением worker/future. Здесь не заявляется
logical ACK; ошибка — неполный typed error/sticky contract самого helper.

Исправление: та же общая exception discipline, что H1, с фиксацией failure под
удерживаемым mutex и typed возвратом. Не использовать catch с новым окном
unlock/relock. Regression: throw на pre-check и post-flush path allocations,
typed allocation failure без escaping exception; дальнейшие writes refused.

Дополнение по read/append catches:790/847 и blockWrites:899–902. На healthy
owner allocation exception вызывает blockWrites(), который сохраняет
recoveryRequired, после чего текущий result возвращает allocationFailed.
Конкретный однопоточный случай: исчерпать owned budget, вызвать valid bounded
read, получить allocationFailed, освободить бюджет и повторить read — теперь
result recoveryRequired. Аналогично allocation exception во время append.
Это НЕ снимает write ban и не является отдельным H: оба состояния закрывают
owner. Но first observed cause не сохранена единообразно; диагностическая
причина следующего typed result отличается без нового отказа. Текущий admission
test:171–177 проверяет только !ok(), а не error identity. Этот сопутствующий
недостаток включён в M1, не посчитан отдельным finding: тот же inner-under-lock
обработчик должен сохранять allocationFailed через State::fail и возвращать
сохранённый first error/nativeError. Явный внешний blockWrites() может по-прежнему
означать recoveryRequired; v1 методы изменять для этого не требуется.

Если fault уже установлен другим вызовом, catch не должен выдавать новый
allocationFailed поверх сохранённой первопричины. Межпоточное окно, которое
делает такой случай возможным, отдельно разобрано в H1. Regression для M1:
assert точного allocationFailed и его сохранения при следующих отказах,
плюс preservation уже установленного fault; никаких новых normal effects.

Ещё одна defensive ветка appendPosition:803–805: наблюдённый actual length
меньше appendOffset либо слишком большой для alignment возвращает invalidContent,
но не вызывает State::fail. Следующий вызов поэтому не наследует эту ошибку.
Если такой невозможный размер действительно наблюдён, sticky invalidContent
согласован с physical contract; это не обычный invalidInput caller. Не
утверждается, что допустимый append сам создаёт такой размер либо что требуется
ослабить sharing для воспроизведения. Включено в тот же разбор M1, без нового
H или отдельного finding; проверять fault injection размера может main.

## M2 / P2 — копирующее присваивание CustodyNativeJob нарушает admission count

Место: `ProtectedCustodyMemory.h:16–29`, около deleted copy constructor:24.

Copy constructor удалён, но copy assignment не удалён и не реализован.
Неявное присваивание копирует held_ без изменения live_. Текущие production
call sites assignment не используют; это дефект callable RAII token API,
а не утверждение о пяти одновременно работающих jobs нынешнего smoke.

Контрпример по исходникам, не выполненный тест:

```cpp
CustodyNativeJob a, b, c, d; // четыре реально held token
{
    CustodyNativeJob rejected; // held_=false: лимит исчерпан
    rejected = a;             // implicit assignment копирует held_=true
}                             // уменьшает live_ до3, но a/b/c/d ещё живы
CustodyNativeJob fifth;       // принимается: пять живых admitted token
```

При последующем уничтожении возможен unsigned underflow счётчика и постоянный
отказ admission. Минимально удалить copy assignment, как у CustodyDirtySlot;
если move понадобится, он должен явно передавать единственный token. Static
regression на non-copy-assignable/non-move-assignable и отдельный limit4 test.

## M3 / P2 — статические read bounds проверяются после metadata IO

Место: ProtectedCustodyFiles.cpp:779–784, проверка State::read:648–650;
State::check:596–617. Принятая scoped граница owner-gate, пункт3:88–94,
требует checked offset/length/native bounds до IO/allocation.

readCiphertext сначала принимает job/result pin и вызывает check(), который
выполняет ancestor/file metadata queries, ACL/path checks и stream enumeration,
а также создаёт paths/wstrings. Лишь затем State::read отклоняет count=0,
count>266240 либо offset>INT64_MAX-count. Эти три условия полностью известны
без обращения к файловой системе.

Контрпример: на healthy owner readCiphertext(0,0) вызывает native metadata
queries, прежде чем возвращает invalidInput. Если в этот момент stream query
вернёт unknown error, тот же заведомо некорректный запрос вместо invalidInput
получит unsafeFile и оставит owner sticky failed. Если path allocation бросит
bad_alloc, он активирует allocation/recovery failure вместо input refusal.
Это нарушение fail-before-IO preflight, не утверждение о content read beyond
EOF, oversized owned allocation, arbitrary write или полном logical reader.
State::read действительно проверяет numeric bounds до GetFileSizeEx,
CustodyBytes allocation и ReadFile; эту полезную защиту не нужно убирать.

Исправление: выделить allocation-free numeric predicate и проверять его в
public read до check()/result-buffer allocation (и по возможности до
admission); State::read может сохранить defensive duplicate check. Для owner
с прежним sticky fault сохранить явный приоритет прежней ошибки; важно, что
numeric refusal на healthy owner не запускает metadata IO. Dynamic actual-EOF
bound требует same-HANDLE size query и не может быть вычислен заранее: этот
finding не требует обходить confinement ради EOF или менять logical semantics.

Регрессия: count0, count266241 и offset=UINT64_MAX/count1, с отдельным счётчиком
metadata queries/stream calls и allocation attempts, а не только ReadFile/
WriteFile counters. Для этих запросов healthy owner возвращает invalidInput,
не выполняет metadata/content IO, не выделяет ciphertext и остаётся usable.
Предварительно включённый stream fault не должен быть затронут invalid request;
следующий valid read обнаруживает его обычным confinement check.

## Проверенные свойства вне findings

| Требование | Прочитанное основание |
| --- | --- |
| Private same-HANDLE | Owner.h:15–39 не выдаёт HANDLE/cursor и произвольный writeAt; CPP745–747 открывает один RW HANDLE, FILE_SHARE_READ, без FILE_FLAG_OVERLAPPED/DELETE_ON_CLOSE; confined security имеет bInheritHandle=FALSE. |
| Actual identity и non-inheritance | CPP579–581 сравнивает VolumeSerialNumber и все128bits FileId; check608–616 повторяет inspect/GetHandleInformation/FileIdInfo до/после stream query и сверяет исходные identities. Acquisition сохраняет их, subsequent checks не переустанавливают. |
| Stream/confinement | CPP598–602 повторяет path/reparse/ACL проверку удержанных ancestor handles. CPP583–594 делает bounded First+Next: для файла только unnamed default stream и terminal ERROR_HANDLE_EOF; любой ADS/unknown error отказ. Для directory отсутствие streams допускается только по ERROR_HANDLE_EOF, любой найденный stream rejected. |
| Store-ID upgrade | CPP733–739 приобретает новый GENERIC_READ/shareRead store.id HANDLE до packed content effects, затем закрывает прежний более permissive handle через move и заново проверяет size16/exact16/expected ID с offset0. CPP749 сохраняет FileID strict handle. Unknown/native отказ не становится новым store ID. |
| Typed immutable append | CPP820–837 проверяет actual EOF/alignment/address/size и openReferenced typed context/version/body до IO; digest построен от входного envelope, не объявлен parent proof. CPP838–844 reserve, zero padding и append не перезаписывают старый/orphan tail; success означает written, не durable logical ACK. |
| IO chunks | CPP628–644 проверяет signed-offset bound, формирует fresh OVERLAPPED offsets для каждого chunk≤262144B; любой short/zero/error блокирует owner. Разбиение позволяет ciphertext266240B, не уменьшает payload cap. |
| Empty descriptor | CPP666–671 zero body128 с generation1/length0/extent32896/block262144/count0/radix64/depth3/flags0/EMPTY ref/reserved0 соответствует exact empty descriptor. Два seal вызова имеют свои slot contexts. CPP683–697 write/flush, освобождение writer ciphertext copies, prefix readback, independently decoded heads expectedGeneration1 и exact body comparison; не просто BOOL DPAPI. |
| Cold-open boundary | CPP753–760 проверяет minimum size и exact prefix/native checks, но не считает heads/closure доказанными. Owner.h:16–18 явно оставляет это tree layer. Новое приобретение не возвращает прежний epoch/proof. |
| Pins/retained results | State:562/572 и Owner.h:9–12 имеют обратный destructor order: content/files закрываются до owner pin; read bytes уничтожаются до owner и result pin. read:779–788 передаёт strong owner в результат; revoke:896–901 не закрывает HANDLE и не сбрасывает fault. |
| Jobs/epoch/budget | CPP716–726 принимает job до State allocation, pin проверяется до file work; epoch monotonic CAS отказывает при max и не возвращает использованные значения. Public jobs удерживают owner и резервируются до mutex wait. Cipher/readback/State/shared ownership allocations используют existing allocator; pin32/job4 application boundaries не доказывают весь будущий process memory PASS. |
| HEAD non-atomic outcome | CPP875–880 валидирует full HEAD cell и выделяет readback до первой записи; CPP882–886 устанавливает ambiguous до transfer и сохраняет его при native/check/cipher mismatch. Single-thread bad_alloc catch после write сохраняет ambiguous, но concurrent исключение покрыто H1. |

## Native API: первичные документы, не execution evidence

Повторно прочитаны официальные Microsoft документы:

- [ReadFile — Synchronization and File Position](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile): synchronous HANDLE допускает non-null OVERLAPPED с явными offsets и возвратом после завершения. CPP локальный OVERLAPPED и mutex соответствуют этой форме; async pending protocol не требуется для открытого без FILE_FLAG_OVERLAPPED handle.
- [WriteFile — Synchronization and File Position](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-writefile): та же synchronous positioned форма. File pointer может изменяться системой, но caller его не получает и каждое IO задаёт offset заново.
- [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew): sharing действует до close; отсутствие FILE_SHARE_WRITE отвергает existing write handle/write mapping. Attribute/extended-attribute access не охвачен sharing, поэтому rechecks не заменены обещанием абсолютной неизменяемости. Existing-file security descriptor не исправляет ACL сам по себе: CPP inspect обязателен.
- [FindFirstStreamW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findfirststreamw) и [FindNextStreamW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-findnextstreamw): default unnamed stream первый у файла; directory не имеет unnamed DATA; terminal EOF отличается от unsupported/unknown. Это поддерживает ветвления583–594, но не доказывает runtime sharing/filesystem matrix.

## Прочитанные тесты и остающиеся проверки

Тест:246–280 покрывает physical empty creation/prefix и HEAD codec decode,
append/read bytes, external writer denial, revoke с continued reads, retained
result HANDLE lifetime, new epoch после release/reacquire и explicit blockWrites.
Не-Windows ветка проверяет unsupportedPlatform.

Расширение:110–149 проверяет семь HEAD cuts (write/short/zero/flush/read/changed
read/bad_alloc в readback после записи), sticky ambiguous при повторе, три
second-chunk cuts max-size DATA с сохранением orphan tail и fail-unknown stream
enumeration. Admission:151–178 проверяет job4, owner+31 result pins=32, отказ
до IO при exhausted owned64MiB и sticky allocation fault после освобождения
бюджета. Test TU включает real ProtectedCustodyFiles.cpp:54 с локальной заменой
native вызовов, а не новую product fault-injection поверхность. Последующее
расширение confinement:179–218 содержит retained writable mapping/view,
hardlink acquisition refusal и actual named ADS refusal. Publication:219–235
содержит успешную physical HEAD/readback, max DATA append/read с двумя chunks
и отказ overwrite старого DATA. По последнему сообщению main эти test-only
добавления confinement()/publication() ещё не скопированы/собраны в native
окружении. Это прочитанные assertions, не мои execution результаты и не
покрытые baseline receipt 40/40 ниже.

Эти проверки однопоточные. Они не покрывают interleaving H1 между unwind и
catch/blockWrites; throwingRead подтверждает лишь single-thread ambiguous.
Проверка owned allocator exhaustion не заменяет std::filesystem path/wstring
allocation exceptions в appendPosition/flush (M1). Limit4 не проверяет implicit
token assignment (M2) или preflight до metadata IO (M3). H1/M1/M2/M3 требуют
focused regressions до повторного
source acceptance.

Actual FileID mismatch, ACL/reparse faults и exact empty descriptor body с
независимым fixture остаются отдельными native acceptance проверками; их
отсутствие в текущем тесте само по себе не новое finding об уже обещанной
полной suite. Metadata/state-path bookkeeping
унаследованного backend не принимается как полная pipelineOwned/account-budget
реализация этим scoped review.

Сообщённые main receipts: initial product build exit0 /W4/WX, smoke1/1 PASS
0.21s; расширенный native test1/1 PASS0.53s и portable38/38 PASS24.58s.
Последний baseline: full native CMake build + CTest 40/40 PASS34.64s,
session33321 exit0. Main прямо отделил этот baseline от ещё не собранных
confinement()/publication() test-only additions; runtime PASS не переносится
на весь текущий test hash. Следующий сообщённый main receipt: последние
confinement()/publication() additions compiled /W4/WX, native1/1 PASS0.69s,
session19554 exit0. Это отдельный последующий scoped run, не повтор полного
40/40 на новом test snapshot. Product sources по сообщению main не изменены,
что совпадает с повторной локальной сверкой четырёх SHA-256.
CMake special-link exclusion сообщён main; его отдельный source audit не входил
в область. Это результаты main, не reviewer execution evidence. Reviewer не
запускал тесты/компилятор/VM, не проверял runtime receipts и не объявляет
execution PASS. Финальные запуски текущих test bytes и docs выполняет main.
Предыдущая .NET sharing диагностика не принимает эту owner implementation.
Tree proof/cold closure/logical ACK/adoption/full T116/T117/T118 по этому
source review не принимаются. Пять normative checklists/112 markers не менялись.

## SHA-256 прочитанного снимка

Пути относительно repo root. SHA целого CPP фиксирует файл, но scope review
ограничен новыми owner/State integration частями; полного v1 source approval нет.

| Файл | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `d13e7aeb8263c7ba055c1394343d65abfec6ca9f93f875f360b53ccdc66c2d56` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `589879eafe0b7faf233748c7483a92bc478a6fbe302697e2d0c2678ecdc12022` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `10441f19a21bd1bb8dc5d60cdc6178c01784aacf1127e4ab2708fe25ba26c17f` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `ef5c3b1c2100dcf530b77dc2acdfddc13cc65cbb122c65c2bcd27580663c5414` |
| specs/200-windows-desktop-app/checklists/review-2026-10-03-packed-owner-gate.md | `51623b6046d422d14f730a8ced5f2111d796cafa18fda299000dfa556e4046ba` |

После исправлений требуются новый source snapshot и scoped повторная проверка
H1/M1/M2/M3; approval старых bytes не переносится на compiler fixes/test expansion.
Reviewer создал только этот отдельный отчёт. Исходники, v1 methods, markers,
spec/plan/tasks/constitution, GitHub/commits и пользовательские файлы не менял;
чужие изменения не откатывал.

## Initial review closed / current-source recheck checkpoint

Initial source review завершён: REQUEST CHANGES, C0/H1/M3. Findings выше
привязаны к продуктовым bytes в таблице, тестовые line references — к
прочитанному test snapshot ef5c3b1c2100dcf530b77dc2acdfddc13cc65cbb122c65c2bcd27580663c5414.
После сообщения main о tests-first fixes повторная read-only сверка показала:
все четыре product hashes ещё совпадают с initial snapshot; test уже изменён
на a1b5edbfceb0672be45ddbe6d6aede13488b2b897ca76d010b9b74d52a73a27c.
Этот промежуточный test hash зафиксирован как observed, не как выполненный
или полностью принятый reviewer snapshot; прежние test-coverage conclusions
не переносятся на новые assertions автоматически.

Main сообщил, что изменит только Files.cpp и tests для exception/bounds/error
preservation и observed-invalid-size handling. Reviewer не вносит competing
product edits. Current-source acceptance recheck pending готового снимка:
после готовности новых bytes добавить сюда отдельные hashes, проверку H1/M1/
M2/M3 и остаточные findings. Пока product patch ещё отсутствует, старые findings
не сняты. Снятие M1/M3 не означает автоматически снятие H1 mutex-unwind окна
или M2 CustodyNativeJob assignment; Memory.h не входит в заявленные main edits.
Последний native1/1 PASS0.69s относится к сообщённому main предыдущему прогону,
не к tests-first snapshot a1b5edbf или будущим product fixes.

## Current-source recheck 1 — exception/bounds patch, до nested-catch перестройки

Снимок Files.cpp SHA-256:
52c05f5dfdc01f7af2b6c190236880d0676e48af13f21b6f17db5848fba94b00.
Tests SHA-256: a1b5edbfceb0672be45ddbe6d6aede13488b2b897ca76d010b9b74d52a73a27c.
Memory.h SHA-256: 10441f19a21bd1bb8dc5d60cdc6178c01784aacf1127e4ab2708fe25ba26c17f.
Прочитаны текущие пять public methods:775–915 и новые test wrapper/admission/
boundsAndAllocation assertions:48–64,178–220. Не является execution review.

Результат этого промежуточного source recheck: REQUEST CHANGES, C0/H1/M1.
Оставшийся M — исходный finding M2, не новая нумерация findings.

- M1: отсутствие typed catch и расхождение allocationFailed/recoveryRequired
  устранены в source: catches793–797/817–821/860–864/878–882 сохраняют первый
  fault и nativeError. Invalid actual size position810–813 теперь sticky.
  Однопоточные причины M1 исправлены; mutex-unwind окно учитывается отдельно H1.
- M3: исправлен source preflight779–781 до guard/job/pin/check/native calls.
  Defensive State::read numeric guard сохранён. Invalid request возвращает
  invalidInput даже на уже failed owner; ни fault, ни authority не сбрасываются,
  valid request по-прежнему получает сохранённый fault. Нового нормального
  content effect от такого input refusal нет; отдельное новое finding не нужно.
- H1: НЕ устранён этим patch. Lock в function body уничтожается до catches,
  которые повторно берут mutex. Это теперь видно также в position/flush.
  publishHead903–914 всё ещё читает общий headAttempted после unlock/relock.
  Изменение enum ошибки не закрывает competing-operation окно.
- M2: НЕ устранён; Memory.h не изменён, implicit assignment по-прежнему callable.

Tests: throwingMetadata через TU-local FindFirstStreamW делает четыре operation
exceptions, проверяет exact allocationFailed и следующий sticky отказ;
bounds requests идут при включённой metadata exception, после отключения
owner остаётся usable. Это полезные focused assertions. Они не являются
concurrent regression H1, post-flush metadata exception test или assignment
regression M2. Main сообщил behavioural RED на старом source: session81597,
CTest8 assertion OwnerTests:185 repeated error != allocationFailed; reviewer
не запускал и не верифицировал receipt. New focused build/run session62744
по сообщению main running; terminal результат пока не принят.

После этого main сообщил о перестройке всех пяти операций: inner catch внутри
retained/job/lock scope, без повторного mutex acquire. Это заявленное исправление
H1, но на данном промежуточном hash его ещё нет. Следующий recheck должен
проверить ordering по готовому source и отдельному hash, не принять план за код.
Native operation в исходном counterexample уже завершена; раннее уничтожение
job здесь не заявлено как отдельный доказанный native-IO lifetime H. Удержание
guard/admission до classification устраняет спорное окно в той же H1 причине.

## Current-source recheck 2 — nested catches и nonassignable job

**Scoped source APPROVED — C0/H0/M0.** Initial H1/M1/M2/M3 закрыты по
прочитанным source bytes ниже. Независимый reviewer не запускал тесты,
компилятор или VM; runtime evidence остаётся отдельным main gate.
Ветка codex/200-windows-followup, HEAD99b00a579c24b50e320465b69d9a296038bc544d
не изменились. Files.cpp и Memory.h повторно сверены после чтения.

| Current source | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyOwner.h | `d13e7aeb8263c7ba055c1394343d65abfec6ca9f93f875f360b53ccdc66c2d56` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp | `fe81d4d3bc6cb7a2a076f9f9bddfdbd533ef418a8753e45739b3f52252a83476` |
| apps/windows/RecApp/Storage/ProtectedCustodyFiles.h | `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced` |
| apps/windows/RecApp/Storage/ProtectedCustodyMemory.h | `a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyOwnerTests.cpp | `476f86fd6d154a0e74fac0f0b58426b1b7b24e5ef68d6be9d2a49a4fc3c0391e` |
| apps/windows/CMakeLists.txt (build provenance only, not source-audited) | `8d00272d945d5f0880cd3bc1b91753931bf05d2abb84450c7d6511de07764e52` |

H1 ordering проверен в каждой из пяти операций, не только publishHead:

| Operation | Guard/job outside try | Mutex outside try | Inner try/catch |
| --- | --- | --- | --- |
| readCiphertext | 784–786 | 789 | 790–807 |
| appendPosition | 815–816 | 819 | 820–838 |
| append | 848–849 | 852 | 853–906 |
| flush | 914–915 | 918 | 919–930 |
| publishHead | 940–941 | 944 | 945–977 |

При bad_alloc уничтожаются лишь locals внутри inner try. Retained shared owner,
CustodyNativeJob и lock_guard продолжают жить в enclosing scope. Catch НЕ
захватывает mutex повторно: он классифицирует отказ/сохраняет first fault и
создаёт typed return под исходным lock. Лишь после создания return result
уничтожается lock_guard, затем operation locals/job/guard. Соседний admitted
writer не может пройти fault check между обнаруженным exception и sticky fault.
При успешном read strong guard переносится в result.owner:800 и возвращаемый
result сохраняет его; освобождение локального guard не закрывает HANDLE.

HEAD: readback allocation:960 остаётся до первой попытки write. headAttempted
устанавливается:962 и не сбрасывается ни native-failure веткой:963–965, ни
catch:972–977. Mutex остаётся held при чтении этого флага в catch; competing
HEAD не может его сбросить. Только подтверждённый exact readback и check
приводят к reset:970 и physical published:971. Initial H1 counterexample
теперь невозможен по этой структуре. Не требуется общий произвольный writeAt.

M1: catches read803–807, position834–838, append902–906, flush926–930
сохраняют allocationFailed лишь при fault=none и возвращают сохранённые
fault/nativeError. allocationFailed больше не преобразуется в recoveryRequired
через blockWrites. Уже установленная первопричина не заменяется. Observed
invalid actual size в position828–831 устанавливает sticky invalidContent.
Explicit blockWrites985–988 сохраняет прежнее значение либо recoveryRequired;
это отдельный явный запрет, не implicit allocation handler.

M2: Memory.h:24–25 удаляет copy constructor И copy assignment. Объявленные
copy/destructor подавляют implicit move; присвоить held_ из другого token
через public API теперь нельзя. Initial counterexample rejected=a не компилируется
по языковым правилам. Runtime limit4/admission test сохранён. В последующем
test snapshot476f86 добавлены static_assert !is_copy_assignable и
!is_move_assignable:17–18. Это source regression, не утверждение о выполненном
compiler test reviewer.

M3: numeric read bounds781–783 проверяются до shared/job/pin/lock/check,
без filesystem metadata IO или owned allocation. count>266240 проверяется
до signed limit subtraction; count0/overflow дают invalidInput. State::read
сохраняет defensive bounds и same-HANDLE dynamic EOF bound. Typed invalidInput
не снимает уже существующий fault и не разрешает normal content effects.

Текущие test assertions: boundsAndAllocation215–252 проверяют numeric отказ
при включённом throwingMetadata и exact sticky allocationFailed в четырёх
операциях. Admission185–214 проверяет exact повторный allocationFailed после
возврата owned budget. ThrowingRead HEAD cut по-прежнему проверяет ambiguous
после write. Test source расширен параллельно с review: MetadataAllocationFailure
destructor:26–32 пробует job admission при завершении exception handling;
postEffectAllocation253–304 добавляет post-flush/post-HEAD metadata allocation
cuts, sticky impossible size, retained job probe и competing flush с event
rendezvous. Проверены эти новые assertions; product hashes при этом не изменились.
Event writerReady выставляется до входа competing flush, поэтому сам event не
доказывает, что второй job уже admitted/queued при throw; статическое закрытие
H1 следует из enclosing lock, а не из обещания исчерпывающей scheduling matrix.
Exception destructor probe имеет иную границу: три временных job принимаются,
четвёртый отвергается, когда faulting operation ещё удерживает один admission.
На старой outer-catch структуре operation job уже разрушен до classification/
exception destruction и все четыре probe могли быть приняты. Этот probe
структурно различает retained admission и прежний unwind; не является claim
детерминированного старого behavioural RED для competing-writer H1.
Reviewer не выполнял ни concurrency regression, ни новые cuts/compiler assertions.
Отсутствие execution receipts не подменено source PASS.

### Final freeze и сообщённые main execution receipts

Main сообщил final source freeze с точными Files.cpp/Memory.h/Tests/CMake hashes
из таблицы; reviewer повторно проверил совпадение на диске. CMake hash добавлен
для provenance сборок, не как утверждение о независимом аудите CMake linkage.
Source disposition: H1 CLOSED, M1 CLOSED, M2 CLOSED, M3 CLOSED;
remaining C0/H0/M0, scoped source APPROVED.

| Run, сообщённый main | Результат | Session |
| --- | --- | --- |
| Final focused native | compile/run, CTest1/1 PASS0.61s | 56562 |
| Full native | build exit0, CTest40/40 PASS34.93s | 14900 |
| Portable | build exit0, CTest38/38 PASS23.83s | 62872 |
| Full Visual Studio build | main-reported terminal exit0: full solution Release/x64 build0, CoreTests.exe0; AEC3 guard846fe90… verified, D9025 warning retained; built NOT installed App SHA-256 cb7fcb0796ae21967de4fed53120afcb01a4e3f4a50a0c56d197f85ec319a869 | 34357 |

Reviewer не запускал эти sessions и не верифицировал их logs; это явно
атрибутированные main receipts, а не reviewer execution PASS. Ранее
сообщённые pending56562/running62744 были промежуточными и не являются
текущим статусом final focused run. Behavioural RED session81597 доказывал
только exact sticky-error failure на старом source (OwnerTests:185), не
детерминированное воспроизведение H1 mutex race. Старые GREEN receipts
сохранены выше как история и не смешаны с финальными frozen bytes. Docs и
оставшийся VS execution gate ведёт main.

Принято только scoped physical prerequisite: continuous owner, confined native
identity/lifetime, bounded positioned typed immutable append, limited empty
birth и full-cell physical HEAD publication. Не приняты paired logical ACK,
cold descriptor/tree closure, structural-diff proof, reader/finalizer adoption,
полный pipelineOwned/account-budget gate, migration/release или полный T116.
Нормативные112 markers не менялись; requirements checked112/unchecked0 не
являются implementation PASS. Reviewer изменил только этот report и не
вносил/откатывал product edits main.
