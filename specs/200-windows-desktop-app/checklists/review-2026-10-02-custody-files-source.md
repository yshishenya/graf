# Независимый source-only review: bounded protected custody files

Дата среза: **2026-10-02 UTC**; локальная дата владельца — уже 3 октября,
Europe/Istanbul. Итог: **Approved source only — 0 blocking findings** для
перечисленных ниже замороженных исходников. Это не завершение T116, не
приёмка всего приложения и не разрешение установки, миграции или выпуска.

Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
Ветка: `codex/200-windows-followup`.
HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`.
Рассмотрены локальные рабочие байты, включая новые untracked файлы, а не
утверждается наличие этих изменений в HEAD. Все шесть SHA-256 совпали с
переданным владельцем freeze. Посторонние рабочие изменения сохранены.

## Объём и нормативная опора

Полностью прочитаны `code-reviewer` и `ponytail-review` SKILL. Сначала
проверены correctness/security и порядок отказов, затем отдельно сложность.
Использованы root AGENTS, guidance index и применимые risk/product/release
правила; underlying lane остаётся **high-risk-product**. Работа reviewer —
исследование исходников и запись только собственного отчёта, без реализации.

Опора — accepted `contracts/windows-protected-local-custody.md` §§2–5 и
`checklists/review-2026-10-02-custody-durable-io-gate.md`. Принятый codec §3
не аудировался повторно: проверены его вызовы и физические границы нового
слоя, а не повторно утверждается его реализация.

Объём: `ProtectedCustodyFiles.h/.cpp`, `ProtectedCustodyFilesTests.cpp`,
публичная экспозиция существующего `validIdentity` в queue header и
регистрации CMake/product vcxproj. Префиксы путей в таблице ниже — от root.

| Проверенный файл | SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.h` | `1a8ba5ad54618b66ccf651b74489b6f03c220f28470e35a14a7d6aaa9cd02aac` |
| `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp` | `a04e33b1261dd9a429ee7612e41713c7eeea5e2c37e9530ffdebd42ff547988a` |
| `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp` | `5df8f9a15df74710ee474f74916cf6c61b639323c79d08c453d6a37d691a934f` |
| `apps/windows/RecApp/Upload/DesktopUploadQueueService.h` | `e975df4077df25c8c021487b88ee8e60c3e51947b319062c2fce2a4600775418` |
| `apps/windows/CMakeLists.txt` | `62d81ae52e0269b81f32b6e2aa78f0093e726256dd96d4354090a799bbab561f` |
| `apps/windows/RecApp/GrafWindowsApp.vcxproj` | `4773b9c1b76fd53ad97a83687574153c32f3b7d81d3730450d6df435499c7dca` |

Нормативные pins: contract
`630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0`;
durable-IO gate
`d118ca80b707ab20846db29e34cd4a05c49e76ff9fc9692ca113d5efbc808cb0`;
root AGENTS
`384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b`;
constitution
`d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.

## Correctness/security: проверенные основания

В этом разделе строки CPP относятся к `ProtectedCustodyFiles.cpp`, строки
тестов — к `ProtectedCustodyFilesTests.cpp` в указанном freeze.

| Граница | Проверка текущих исходников |
| --- | --- |
| Namespace и ancestor lifetime | CPP45–59 отвергает UNC/ADS/relative/dot/trailing-dot-or-space paths и неподходящий volume. CPP128–159 проверяет каждый открытый directory handle, reparse bit и фактический normalized DOS path; CPP237–264 открывает и удерживает всю цепочку предков до уничтожения объекта. `FILE_LIST_DIRECTORY` вместе с share-read-only участвует в share exclusion. Нет отпускания locks ради rename. |
| ACL до первого write | CPP101–126 строит protected DACL с единственным full-access ACE текущего process user SID; отвергает иной SID/type/mask, inherit-only, неприкрытый или отсутствующий DACL. CREATE_NEW получает descriptor при создании; CPP181–182 проверяет ACL/path/link count до CPP187 первого write. Изменения ACL профиля/VM отсутствуют. |
| Identity и lease | CPP161–169 проверяет ровно16B `store.id`/`id.bin` и ожидаемые bytes. CPP228–270 использует fixed enum roles и существующий package validator, не JSON paths. Store ID не генерируется заново; новый role/id только через exclusive create. Writer удерживает writable id handle без share-write/delete, второй writer не получает lease. Это физическая exclusivity, не account/snapshot authority. |
| Immutable blocks | CPP302–326 проверяет codec envelope до IO, использует CREATE_NEW, не перезаписывает collision/orphan, полностью пишет и flush, затем закрывает и повторно открывает, валидирует и сравнивает ciphertext. Ошибка физического write/flush/reopen делает writer failed. Временно decoded block payload очищается через WipePlain. |
| Размеры и чтение | CPP195–213 получает size на защищённом read handle; минимум, role bound и exact block size проверяются до allocation/ReadFile. Каждая операция write/read ограничена256KiB, short write/read продвигает точный offset; zero/overcount отвергается. CPP286–296 проверяет block position/version/payload/exact и codec context; role logical cap проверяется до открытия файла и allocation. Missing/invalid DATA — ошибка, не ZERO/legacy/plaintext fallback. |
| Index publication | CPP343–397 валидирует slot/envelope до temp IO; ciphertext temp создаётся exclusive с opaque RNG suffix, полным write и preflush. Native rename работает на том же защищённом source handle. После rename проверяются actual target path/ACL/links, postflush, close/reopen, codec validation и точное равенство ciphertext. Только весь путь возвращает published. |
| Ошибка и сохранение артефактов | CPP381 ставит failed до native publication attempt; любой ненулевой NT return или IOSB.Status, postinspect/postflush/reopen отказ — ambiguous, writer остаётся failed. До rename ошибка temp write/flush — notPublished, но также failed. Ни temp, ни published slot/orphan не удаляются. CPP399–402 возвращает allocationFailed; после начала публикации сохраняет ambiguous. Открытие и read также ловят bad_alloc типизированно. |

Публичный header28–31 явно ограничивает слой physical worker IO: published
slot **не** logical commit ACK, caller резервирует память и владеет snapshot,
pins и reconciliation обеих slots. API возвращает ciphertext либо typed
отказ, а не выдаёт ledger/upload/delete полномочия. Никакого фундаментального
противоречия с последующим accepted logical design в этом API не найдено.

### Закрытый blocker: реальные locks и native rename

Раннее замечание к metadata-only directory access закрыто: CPP155 теперь
запрашивает `FILE_LIST_DIRECTORY`. По официальному MS-FSA алгоритму
attribute/control-only handle не обеспечивает нужной sharing exclusion;
directory list/read-data access её включает. Тест184–188 прямо требует
ERROR_SHARING_VIOLATION при DELETE и GENERIC_WRITE open самого root, а не
опирается только на отказ переименования предка с открытым потомком.

Тестовый флаг167–168 снимает только FILE_LIST_DIRECTORY через TU-local
wrapper28–31 для ручного RED контроля. Он не является production knob и не
передаётся обычным CTest. По исходникам такой контроль должен провалить
конкретный assert187. Владелец сообщил фактический RED с кодом0xc0000409
на direct-open DELETE/WRITE guard; reviewer запуск и его лог не проверял.

Промежуточные Win32 rename варианты в freeze отсутствуют. CPP79–83 и
351–378 используют типизированный `NTAPI` function pointer, class10,
BOOLEAN/HANDLE/ULONG/WCHAR record и uint64_t-aligned buffer достаточного
размера. Получение адреса только из уже загруженного ntdll, через memcpy
между одинаковыми по размеру function pointers; нет DLL search/load,
новой зависимости или Win32 fallback. Target — фиксированный `index.0/1`,
не пользовательское имя; RootDirectory=nullptr и simple name означают
переименование в том же source directory, не разрешение имени через CWD.

Microsoft прямо документирует user-mode имя NtSetInformationFile,
FileRenameInformation=10 и такую same-directory форму. Документация
IoIsOperationSynchronous указывает SetInformationFile как synchronous API
даже для asynchronous file object. Здесь дополнительно используются только
собственные synchronous CreateFile handles, без OVERLAPPED и без внешних
handle inputs. Поэтому требование отдельного pending/wait пути не является
блокером этого среза. Проверка обоих конечных статусов консервативна; ABI,
время жизни IOSB/buffer и confinement в текущем потоке не дали замечаний.

Официальные источники, прочитанные при review:

- [MS-FSA sharing access algorithm](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/8c0e3f4f-0729-49f4-a14d-7f7add593819).
- [File access rights constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants).
- [NtSetInformationFile](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationfile).
- [FILE_RENAME_INFORMATION](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information).
- [IoIsOperationSynchronous](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ioisoperationsynchronous).

## Тесты и регистрации: source evidence, не runtime PASS

Тесты11–14 undefine NDEBUG до cassert: assertions выполняются и в Release.
Тесты22–84 включают настоящий files.cpp с локальными WriteFile/FlushFileBuffers/
ReadFile/CreateFileW/GetProcAddress wrappers. Windows headers включены до
macro substitution; macros сняты после include. Production исходник не
содержит fault controls. CMake17/58/82–84 исключает второй files object
только из Windows fault-test, сохраняя обычную product-source компиляцию и
non-Windows unsupportedPlatform путь. Реальный codec остаётся подключён.

Проверены содержательные assert и порядок faults: wrong store/object IDs;
path/ADS/UNC; writer lease; block exact size/missing DATA; semantic corruption
до создания файла; collision и sticky writer; сохранение unknown; hardlink
и junction к отдельному synthetic object; unprotected DACL; максимальный
256KiB block и ZERO index для64GiB/262144 entries; oversize отклоняется с
reads==0. Последнее доказывает отсутствие ReadFile в тестовом пути, а
отсутствие преждевременной allocation видно непосредственно в CPP200–203.

Последнее уточнение freeze отдельно перепроверено: CPP287–290 берёт known
role logical cap и отвергает payload за `logical - position*blockBytes`
ещё до CPP292 open/read. Предшествующий position bound и short-circuit
`||` исключают умножение/вычитание для недопустимой позиции; максимальный
known logical cap64GiB делает сложение для ceiling block count безопасным.
При неизвестной роли cap0 и position bound отвергает запрос до вычитания.
Тест280–287 требует typed invalidInput и0reads для4097B manifest request.
Его отсутствие физического open/allocation установлено по порядку кода;
счётчик ReadFile не объявляется самостоятельным allocation profiler.

Wrong process CWD устанавливается только тестом129–134/170–172, отличается
от role directory; assert209 проверяет отсутствие index в CWD. Fixture
нормализует возможный8.3 TEMP alias через GetLongPathName, не ослабляя
production actual-handle comparison. Очистка ограничена созданными
synthetic fixtures после закрытия handles; junction удаляется как link.

Fault loops300–331 проверяют partial/zero/failed write, preflush,
native rename return failure, postflush, IOSB completion failure и reopen
read failure; assert322 различает notPublished/ambiguous, assert323 требует
sticky отказ следующей публикации,324–328 проверяют сохранённые артефакты.
Особенно важно: wrapper53–61 в renameCompletion сначала вызывает **REAL Nt**,
затем подменяет успешный IOSB.Status, а тест требует уже существующий slot
при ambiguous. Это не mock-only имитация публикации. Fault allocation не
инжектируется: её обработка проверена по исходникам, не объявлена runtime
доказательством. Write wrapper проверяет protected single-ACE DACL на каждом
content-write boundary; точные SID/type/mask проверяет production inspect.

`DesktopUploadQueueService.h:391–392` только открывает существующий
validIdentity для reuse, без изменения его реализации. CMake23/58–61/82–94
регистрирует новый тест и объект с строгими warnings; product vcxproj94
включает files.cpp. Runtime lookup не требует ntdll import library.
Включение CPP в проект не означает production storage integration.

Сборки, VM, native/host suites и ручной RED контроль reviewer не запускал.
Владелец сообщил native36/36 PASS29.06s, full VS App solution/Core PASS и
ручной RED для предыдущих шести pins, до последнего readBlock role-bound
уточнения. Финальный native rerun на указанные здесь a04e33…/5df8f9… ещё
выполняется по сообщению владельца. Это отдельные runtime сведения, не лично
проверенная приёмка этого freeze. Финальные результаты и source-mirror pins
остаются в ответственности основного агента; прежние codec35/35 и host34/34
нельзя переносить на этот новый physical IO слой.

## Ponytail — отдельно от correctness/security

**LeanAlready. Lean already. Ship.** Безопасного точного сокращения не найдено;
**net: 0 lines possible** в проверенном объёме. RAII handles, fixed-role
namespace, native argument adapter и test-only fault seams обслуживают
реальные границы безопасности/публикации, не спекулятивную абстракцию.
Повторно используется existing identity validator; новых dependencies нет.
Ponytail не служит основанием удалить locks/ACL/bounds/reopen или уменьшить
high-risk validation lane. Сокращения кода reviewer не выполнял.

## Что остаётся открытым

Whole T116: logical snapshot/generation/slot authority и exact tails,
metadata g1 birth pair и singleton blocking, global64MiB owned reservation,
pins/cache/dirty-group quotas, async UI tickets/worker adoption и все
producer/reader/queue/finalizer/upload/playback/delete adapters. Helper не
подменяет эту authority, поэтому отсутствие этих следующих слоёв не
Request Changes к bounded physical step, но и не их одобрение.

T117 migration/GC, T118 full storage и installed-app acceptance, hardware/
audio/60min/AEC, clock T094–T096, calendar T119 и общие Windows/release gates
не закрываются. Flush/rename/reopen не объявлены доказательством любых
power-loss свойств носителя. Production integration, legacy cleanup,
установка, commits/push/GitHub mutations и публичный выпуск не выполнялись.

Единственная запись reviewer — этот отчёт через apply_patch. Код, spec,
plan, tasks, checklist markers и чужие отчёты не изменены. Одобрение привязано
к шести указанным SHA-256; изменение их байтов требует актуализации review.
