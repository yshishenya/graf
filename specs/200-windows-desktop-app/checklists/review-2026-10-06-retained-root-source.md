# Независимая проверка исходников: cold retained-root reader, T116

Дата: 2026-10-06. Владелец: независимый reviewer.
Полоса: high-risk-product storage; read-only source investigation + report.
Область: только новый bounded `verifyRetained → readonly media-root proof`
и его проверки в трёх существующих файлах. Это не package authority,
не завершение T116 и не проверка установленного приложения.

## Решение

**SOURCE APPROVED для окончательного снимка ниже: C0/H0/M0/L0 открытых замечаний.**
Проверены 12 source-критериев, удовлетворены 12, неподтверждённых по source 0.
Это проверка исходников, а не результат исполнения 12 тестов.
Native execution acceptance этим отчётом не выдана.

Requirements prerequisite остаётся прежним:
`review-2026-10-06-package-authority-gate.md`, SHA-256
`5d7d2d8f1652a4f28ba42025f66d3ad710cbe07e51c64f8488c57824201332e0`.
Его bytes и все прежние checklist/evidence markers reviewer не менял.

## Точная база и окончательный снимок

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`; HEAD:
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
HEAD не обозначает текущие незакоммиченные source bytes.

Обычный diff к HEAD включает предыдущие независимые storage-изменения и
не использовался как граница этого review. Исходные копии найдены в локальном
зеркале `/Users/yshishenya/Documents/graf-windows-followup-200` и лично
сверены с предыдущими SHA-256. Прочитан полный incremental diff трёх файлов:
Tree.h +16/-4, Tree.cpp +57/-8, TreeTests.cpp +173/-1.
Ни зеркала, ни Git index reviewer не изменял.

Все пути в таблице относительно canonical, столбцы — SHA-256 файлов.

| Файл | До шага | Окончательный проверенный снимок |
| --- | --- | --- |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.h | `9c28432d20e49726033a1f855bc458b93040c6681d9155a81504dfad4a7a9b87` | `12221fc52c6955c3bd79efa11e37764dc93f7a80dfea25ef01704d8c742dfa6c` |
| apps/windows/RecApp/Storage/ProtectedPackedCustodyTree.cpp | `97f101c34413ac57bbe48ab64b98a6e3ecfdc11ff61ec24681c9a7f9e99a56b3` | `c308ac7159695a5a1e8edc1c65a1332481c576fff4f53b2ab270c99960d97391` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedPackedCustodyTreeTests.cpp | `c3f9e9a62818f05ca1cb904ed9c5d6d1183b55c70455dab771eb611d8e8a6eb3` | `c52782725acf10d1a3faaa9a0815c14177b99380038265b74dede8bd3e6c06b3` |

Исходный hash TreeTests также присутствует в сохранённой reviewer карте
файлов перед requirements review и validation-2026-10-02.md:7040.
Уже одобренные normative spec/plan/tasks/data-model/quickstart, оба custody
contracts и constitution hashes лично пересчитаны: совпадают с immutable
таблицей requirements report. Format.h/.cpp, Owner.h, Reader.cpp, Writer.cpp
также совпадают с той таблицей. История source reports/checklists заново
не перечитывалась и повторная полная parser-проверка не проводилась.

## Проверка новых путей и границ reuse

Лично полностью прочитан incremental diff, новые test groups и затронутые
verify/commit/read пути Tree. Для вызовов переиспользуемых компонентов
проверены Format reference/descriptor/child validators, actual Guard check/
size/read/reject/writeReady, Writer::open и Reader lifetime/length/status.
Эти вспомогательные чтения не являются повторным общим approval их истории.
Прочитан code-reviewer skill; runtime/preflight не выполнялись по явной
границе пользователя. Scoped `git diff --check` трёх файлов завершился exit0.

| ID | Source-критерий | Результат и точный путь |
| --- | --- | --- |
| S01 | Actual owner и expected context | PASS — Tree.cpp:92–109: null owner отвергается, тот же Guard; check до сравнения store/object/role/container и prefix, mismatch sticky. |
| S02 | Обе current heads и обе полные closures | PASS — Tree.cpp:112–123: readHeads/decodeDescriptor actual EOF, selectHeads, walk обоих деревьев до retained проверки. Новый verify повторно использует тот же путь без lazy/highest-only обхода. |
| S03 | Strict typed stamp shape и actual EOF | PASS — Tree.cpp:125–135: encode/decodeReference, g>0 и extent минимум через reference bounds, root kind/payload/version/offset/envelope bounds, length≤64GiB до count arithmetic, exact count, extent≤native size, exact empty g1 birth. Reserved wire bytes не представимы в typed descriptor; parser не заменяется этим API. |
| S04 | Generation/extent согласованы со всей парой | PASS — Tree.cpp:134–139: выше selected highest отказ; при равенстве любой head exact descriptor equality; older extent≤каждой более поздней head, включая lower peer. Older logical length не сравнивается с current length. |
| S05 | Historical full closure под тем же Guard | PASS — Tree.cpp:144–151: walk retained descriptor/root; Format::decodeChild ограничивает каждый ref историческим generation/extent/parent/base/tail, Codec::openReferenced проверяет ожидаемый envelope. Guard остаётся до построения result. |
| S06 | Отдельный неизменяемый retained stamp | PASS — Tree.h:38–42/71–76 и Tree.cpp:14–25/149–150: fixed optional owned descriptor, настоящая current pair не подменена; generation/length/readBlock используют descriptor(). |
| S07 | Отказ любых Tree mutations до content effects | PASS — Tree.cpp:172–195: retained guard.check перед conflict; отказ до dirty admission, readHeads, same-size success, reserve/append/flush/head publication. result notCommitted/без snapshot с actual base lease. |
| S08 | Writer open также не получает право записи | PASS — existing Writer.cpp:204–219 вызывает proof->setSize до установки state.packed. Retained conflict не устанавливает capability; destruction failed-open не отзывает здоровый owner. Tree.cpp:419–426 закрывает checkWrite независимо от physical writable mode. |
| S09 | Permission refusal не стирает first fault | PASS — retained mutation сначала guard.check, затем здоровый conflict без reject/revoke/blockWrites; реальный observed context/hash/structure/IO/owned allocation fault следует существующему sticky Guard::reject. Admission pin/job refusal не выдаёт proof. |
| S10 | Read/lifetime сохраняют реальный owner после здоровых commits | PASS — Tree.cpp:429–497 читает historical descriptor, без требования вечного current-pair equality. Existing proof/pin/shared owner и Reader/Clone сохраняют actual HANDLE; bounded размер Tree≤4096 asserted. Нет нового owner/backend/cache/dispatcher. |
| S11 | Новые регрессии соответствуют scope | PASS по source — tests:1286–1466: cold gap g2 вне g3/g4 во всех трёх ролях, bytes/EOF/readonly/current healthy/Reader Clone/writer release/cancel; 14 context/stamp cases; corrupt historical DATA+3 NODE и обе HEAD cells; birth/shrink EMPTY/64GiB ZERO; pin/job/owned pressure и first fault. Они вызываются в existing native full test; portable ветвь не исполняет native fixtures. |
| S12 | Нет расширения authority/consumer | PASS — new API comments прямо исключают package/upload/delete/GC; private constructor/makeProof, без serialized verified flag. Три файла содержат primitive/tests, не подключение к AppMain/профилю/metadata registry. |

Source scope coverage:12/12. Это не 12 новых checkbox markers и не изменение
формальных checklist totals. Предыдущие 154/0 нормативных markers и исторические
410/10 физические строки этим отчётом не переотмечаются; задачи не закрыты.

## Найденный дефект тестового helper и его исправление

В первоначальном frozen TreeTests SHA-256
`a02647f1f4e5d14067c60627a37c60ba62f1dabd20f416703ea464235e834e76`
найдено **M251-1: тест проверяет не тот объект при media/playback role**.

Конкретный путь: coldRetainedRoots меняет context.object.role и создаёт файл
под соответствующей role directory; Fixture::content всегда возвращал
`canonical/content.packed-v2`. После canonical case media case вызывает
denyExternalWriter для отсутствующего canonical path и требует sharing
violation. Это детерминированный дефект fixture/acceptance, не доказанная
ошибка удержания HANDLE или product lifetime. Reviewer сообщил его main,
не исправлял код и не запускал тест для воспроизведения.

Main сообщил Native251 terminal1 на этой assertion; этот runtime receipt
reviewer не читал и не выдаёт его за лично подтверждённое исполнение.
Failed snapshot/evidence остаётся частью истории, не заменяется новым PASS.

В окончательном `c527827...` content():124–127 assert разрешённых трёх ролей
и выбирает directory по actual fixture context; denyExternalWriter получает
правильный объект. **M251-1 закрыт по source**, native rerun отдельный.
Tree.h/.cpp hashes при этом исправлении не изменились.

## Borrowed input — не новый блокер

verifyRetained синхронно передаёт const context/stamp references в verifyImpl,
не ставит их в очередь и не сохраняет pointers в proof. Caller обязан
сохранять lifetime и не допускать concurrent mutation обычных C++ objects
до возврата синхронного вызова. При таком установленном worker-only потоке
нет конкретного defined-behavior counterexample подмены проверенного stamp.
В result descriptor копируется по значению и хранится const optional.
Текущий контракт не требует новой asynchronous input ownership дисциплины
для этого метода; copied input до IO не объявляется обязательным fix.
Будущая асинхронная постановка будет иметь собственную границу владения,
не разрешается этим source approval.

## Исполнение и терминальная граница

Main сообщил RED4b96e9 terminal2 (нет API), portable ec223f terminal0,
Native251 terminal1 со старым helper, Native251b rerun начат.
Это сообщения main: reviewer не запускал build/tests, не подключался к VM,
не читал runtime/profile и не проверял terminal нового native run.
**Ни running run, ни portable build не означают native all-PASS.**
Для native acceptance main предъявляет отдельные terminal receipts,
source hashes и результаты всех новых groups и прежних регрессий.
Исправление теста требует новых execution receipts, прежний failed receipt
не удалять. Source approval остаётся привязанным к трём final hashes выше.

Нормативный requirements PASS сохранён; открытых source findings нет.
НЕ принято: provenance protected metadata stamps, retainer enumeration,
semantic package admission/полный logical SHA, account rights, GC/upload/
delete, migration/adoption, T116 целиком, H250-1/H250-2, installed/release.
Reviewer создал только этот новый report. Никаких code/spec/plan/tasks/
старых checklist edits, commit/push/merge/GitHub/runtime действий.

### Сообщение main после подготовки source verdict

Main сообщил Native251b/tool f3a662 terminal0: config/build/test0,
Tree full test22.44s и focused6/6 за29.70s; frozen source171 manifest
`b9ee923fe1e497f23541bb7a07b130e54bb4e980b5737dc9df7edd5cc88aa7f6`.
Также сообщил final portable Tree e35b63 terminal0, portable full83088
running и SDK178 starting. Reviewer actual receipts не читал:
**MAIN-REPORTED, independently unverified execution evidence**.
Это сообщение не изменяет source hashes/verdict, не превращает running
проверки в terminal PASS и не снимает отдельные acceptance gates.

## Дополнительная ограниченная проверка DOCS

По отдельному запросу main прочитан только новый appendix quickstart.md
«Холодная проверка исторической версии packed media», строки711–747.
Лично проверенный полный hash документа:
`4ba06328532a417002d126ce1e5b47963f72859155311c477b53aeb344b5034a`.
SHA-256 bytes первых709 строк, включая завершающий newline, равен прежнему
`f88d2931c59420ef74332f51f15952dd4a39f09b59457f1e0a6a9c3c0e060d08`:
прежний документ сохранён целиком; дальше добавлен пустой разделитель и appendix.
Это новая docs identity после source-phase проверки прежнего immutable текста,
не незаметная замена нормативной базы или расширение продуктового scope.

**DOCS APPROVED в этой области: C0/H0/M0/L0; критерии5/5 по тексту.**

| ID | Проверка | Результат |
| --- | --- | --- |
| D01 | Имена build/CTest целей существуют | PASS — шесть точных имён совпадают в build list и anchored CTest regex, все зарегистрированы через GRAF_WINDOWS_TESTS/add_executable/add_test; NativeCustodyProtectionFailureTests добавляется при WIN32. |
| D02 | Порядок, timeout и ошибки | PASS — configure→build→CTest, непосредственный LASTEXITCODE/throw после каждого; CTest -j1/timeout300/output-on-failure, запрещён конкурентный native storage test/build и остановка чужих процессов. Build -j2 — внутренний параллелизм завершённой стадии, не конкурентный test/build. |
| D03 | Текст соответствует новым tests | PASS — cold gap, три роли/context, current+historical closure, corrupt DATA/3 NODE/HEAD, stamps, readonly, Reader/Clone, admission, EMPTY/ZERO перечислены без обещания whole-package proof. |
| D04 | Результат выполнения не подменяется инструкцией | PASS — требуется6/6/terminal0 и exact source/EXE identity; старые parser5/5 и portable PASS явно не засчитываются native cases. Текст не объявляет SDK/native/installed all-PASS. |
| D05 | Provenance, retainers, effects остаются отдельно | PASS — protected stamp provenance, refs обоих metadata slots/barriers, finalized logical SHA, package/account/upload/delete/GC, migration/profile/install/release и T116/T117/T118/T120 не объявлены закрытыми. |

Reviewer команды из appendix не выполнял; `git diff --check` quickstart exit0.
Новых checkbox markers или изменений quickstart reviewer не создавал.

В последнем сообщении main также сообщил final portable full83088/19038f
terminal0,46/46 за5.39s и build7cbbb5/e35b63 exit0. SDK27310 restore0,
build in progress, real AEC identity сообщена только сокращённо.
Это всё ещё **MAIN-REPORTED execution, receipts reviewer не прочитаны**.
SDK terminal PASS не заявляется. Source/DOCS approval не закрывает runtime gates.

### Последующее сообщение и проверка сохранности

Main позднее сообщил SDK f37855 terminal0/restore0/build0; reviewer actual
receipt по-прежнему не прочитан, это MAIN-REPORTED, не независимый SDK PASS.
Сообщённый отказ первого receipt-reader из-за execution policy относится
к запуску helper, не классифицирован reviewer как product test failure.
Reviewer никаких policy/runtime изменений не выполнял.

Лично повторно сверены SHA-256 всех95 исходных checklist/report файлов
из сохранённой карты до requirements review: changed=[]; requirements report
`5d7d2d8f...` и три окончательных source hashes также совпадают.
Полный новый source report и добавленный DOCS раздел лично перечитаны.

## Финальное подтверждение применимости ограниченного review

После сообщения main о final actualreceipt061bc3 reviewer лично повторно
пересчитал hashes: все три source файла совпали с final таблицей выше;
quickstart совпал с `4ba06328532a417002d126ce1e5b47963f72859155311c477b53aeb344b5034a`.
Tasks остался `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
requirements report — `5d7d2d8f1652a4f28ba42025f66d3ad710cbe07e51c64f8488c57824201332e0`.
**SOURCE APPROVED12/12 и DOCS APPROVED5/5 сохраняют применимость;
открытых замечаний C0/H0/M0/L0. Ограниченный source/DOCS review завершён.**
История, старые markers и прежние оценки не переписаны.

Main сообщил actualreceipt061bc3 reread terminal0: native171 configure/build/
test0 и source/все6 EXE hashes match; Tree EXE
`adb3ada4645ceb40df63bd48f5558f0d5b75191d9b30d5db6d2da18d14f48025`.
SDK178 source hashes match/restore0/build0, app EXE
`42cd308684f7fb42d6455eb98715ff3729703ab451fb7b60b88874b1dd672390`;
final portable46/46 за5.39s. Reviewer не открывал эти actual receipts,
не проверял EXE bytes и не исполнял runtime: **MAIN-REPORTED**, не его
независимый native/SDK/portable acceptance. Round251 validation/changelog
не входят в этот узкий review. Все прежние authority/consumer/migration/
installed/release gates остаются отдельно.
