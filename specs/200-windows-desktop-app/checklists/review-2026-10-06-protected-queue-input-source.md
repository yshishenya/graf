# Round266 — SOURCE: ProtectedCustodyQueueInput

Дата: 2026-10-06. Canonical
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserved.
Lane: high-risk-product, существующий T116/#7444. Независимый SOURCE reviewer
не выполнял VM/tests/hooks/GitHub/app/profile/commit и не менял исходники.
Единственная запись — этот новый отчёт; прежние reports/markers/tasks immutable.

## Текущее решение

**SOURCE NO-GO / REQUEST CHANGES: C0/H1/M0/L0.**
Блокер SRC266-1 ниже относится к определённости повторного входа, а не к
логическому parser или будущему подключению приложения. Даже полученный
Release266f 4/4 PASS не снимает нарушение предусловия стандартной библиотеки.
Финальная приёмка после исправления требует свежих frozen inputs и доказательств.
Текущие Releasef/Debugg executions и portable applicability лично прочитаны,
но не снимают SRC266-1; SDK/readback кандидата здесь ещё не принимаются.
Нет whole-application GO или закрытия T116.

Лично прочитаны `code-reviewer` и `ponytail-review`, canonical AGENTS/guidance
index/spec-kit-flow/product-gates, относящиеся release/evidence guidance,
полный REQUIREMENTS266 gate SHA
`bdd99d7bcf602f463b2521f13a41ac9fe83719d772efb6067244aab136736c78`.
Его уже прочитанные normative artifacts/constitution/active T116 основания
переиспользованы; SOURCE не меняет требований или отметок чеклистов.
Проверены actual Metadata header/BootstrapPair/QueueInput flow, Files discovery,
identity/ancestor handles, compound BOTH validator/readBlock/writer guards,
Codec/Files/Memory types и native fixture/новая матрица FilesTests.

## SRC266-1 — HIGH: повторный try_lock собственного std::mutex

Точки: `ProtectedCustodyMetadata.h:122`, `ProtectedCustodyMetadata.cpp:638–639`,
`ProtectedCustodyFilesTests.cpp:1590–1596`.

`afterRead` выполняется синхронно внутри текущего вызова Files read. В тесте
он снова вызывает QueueInput::read с тем же parent, в том же потоке, пока
внешний `unique_lock<std::mutex>` владеет `queueRead_`. Внутренний
`try_lock` поэтому нарушает предусловие для нерекурсивного std::mutex:
вызывающий поток не должен уже владеть mutex. Гарантированного false/ERROR_BUSY
в этом случае стандарт не даёт. Успех конкретного MSVC исполнения не доказывает
определённую безопасность повторного входа; исполненная тестовая ветвь сама
содержит нарушение предусловия.

Основание лично проверено в первичном проекте стандарта C++, раздел
[thread.mutex.requirements.mutex.general, try_lock precondition](https://eel.is/c++draft/thread.mutex.requirements#mutex.general).
Это конкретное уточнение SOURCE к R09 REQUIREMENTS gate: межпоточная
сериализация допустима, но выбранный std::mutex нельзя использовать как
гарантированный same-thread reentry detector.

Минимальная рекомендуемая коррекция: закрытый parent `atomic_flag`, одна
попытка `test_and_set` с acquire и RAII `clear` с release. Без spin/wait,
нового registry, публичного unblock или изменения Files validator. Удерживать
parent/job до освобождения guard; busy по-прежнему conflict/ERROR_BUSY до IO.
Такой guard определённо отвергает и same-thread reentry, и другого worker.
Простая замена на recursive_mutex непригодна: она разрешит повторный вход
в общий изменяемый Files state. Удаление теста также не докажет обещанный
отказ при повторном входе.

Для закрытия: повторный вызов получает conflict/ERROR_BUSY и не увеличивает
число чтений; отдельный worker при удерживаемом guard также получает отказ
до IO; после освобождения успешный retry. Межпоточный тест не должен сам
создавать гонку на TU-global counters/afterRead. Исправление и тесты — main,
не reviewer. Нужны свежие результаты на исправленных исходниках.

## Остальной проверенный поток

| Область | SOURCE наблюдение |
| --- | --- |
| Настоящий источник | Private constructor, genuine discover-created parent, null cancel/parent и known-context parent без queueLease отвергаются. Context берётся из проверенного bootstrap и независимо обнаруженного fixed queue ID. Нет reopen/root redirect. |
| Discovery root fix | Files.cpp:298 ставит только writable=false ПОСЛЕ прежних identity locks. GENERIC_READ/WRITE object handle, FILE_SHARE_READ, immutable store и ancestor exclusion не меняются. Удалён только redundant queue blockWrites. |
| Sticky failure | blockWrites по-прежнему failed=true; writeBlock/nextBlockVersion/checkWriteReserve/publishIndex отвергают readonly или failed до write/scan. Ошибка compound validator не очищается ради retry. |
| BOTH | Один existing readValidatedMetadataPair; оба indices и все DATA refs проверяются до selection. Current-only/singleton/empty reservation не становятся допустимой очередью. |
| Bounds | До создания двух полноразмерных буферов проверены ОБЕ positive logicalLength<=4MiB, exact entry count и DATA-only. После cap arithmetic/casts ограничены; count<=256KiB, offset покрывает exact length. |
| Владение | Object/control block и vector buffers используют CustodyAllocator. Результат const; borrowed views требуют retained owner. Parent удерживает bootstrap/queue/store/ancestors, extra pin удерживается результатом. |
| Ошибки конструкции | indices/payloads переносятся до pin/parent transfer. Возможный throwing Debug proxy оставляет caller-held parent и admission. Constructor failure deallocates raw; shared_ptr control failure вызывает deleter; CustodyBytes освобождается с wipe. |
| Последний владелец | Member destruction: payloads -> indices -> parent -> pin. В read: result/scratch/pair -> guard unlock -> held parent -> job; native работа не переживает job, mutex не уничтожается до unlock. Отказ до admitted job не выдаёт result. |
| Отмена | До IO, после bounded compound helper, перед/после каждого consumer readBlock/openBlock, до строительства и после control block. Нет fake inner interrupt/hard latency; mid-helper cancel допускает завершение helper, но не публикацию результата. |
| Память/отказы | Shared jobs4/pins32/owned64MiB сохраняются. Две byte copies до8MiB не выдаются за бесплатный cache или полный native-memory proof. Native/hash/allocation typed errors сохраняются; DPAPI failure не переименован в semantic invalidContent. |
| Нет полномочий | Byte input не logical v3/read-v2 candidate, matching intent/account/epoch, mutation ACK, admission/effect или готовое приложение. Public Files/writer не раскрыт; parser/schema/targets/dependencies не добавлены. |

Других конкретных блокирующих дефектов проверенного нового потока на этой
версии не найдено. Это не утверждение о безопасности всех старых consumers.

## Доказательства, лично прочитанные reviewer

Внешний stand:
`/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
JSON с WinPS UTF-8 BOM разбирался после удаления BOM только из памяти;
файлы/их bytes и hashes не переписывались. Reviewer читал exports на Mac,
не запускал native EXE и не выполнял независимый NTFS readback.

| Export | SHA-256 / факт |
| --- | --- |
| source-protected-queue-input-round266f-release.json | `43688e53c38ade6f44f79bf312bf91f4b9b45a5cb9bfc3285f491f280bf6e8e2`; 172 inputs лично rehashed canonical, mismatch0; receipt source_hashes равен map. |
| graf-f200-protected-queue-input-round266f-release.json | `c03fa7acdd28af90d7a7cac72316f18db22f4bc5d97a5284c3fabaf5a0831b8b`; terminal passed, configure/build/test0. |
| graf-f200-protected-queue-input-round266f-release-test.log | `f533c774107ce437140adaf36a97265b0653b67509030ccd28b1b6fe0e9b5a0e`; четыре actual Release commands/PASS, Files26.23s. Total28.18s сообщён main, raw LastTest log не содержит aggregate CTest total. |
| graf-f200-protected-queue-input-round266g-debug.json / raw | `5ad34ab609b76a414e19b1ee1ff6d3cbba67fa5790aa0ece251f418e37e8ebe4` / `5230b6f144f05113f702bef98224427b4970069b1cd5c27a55dffb14a9d69a47`; terminal configure/build/test0, source172 равен f map, raw четыре Debug commands/PASS, Files35.52s. Total38.67s сообщён main. Accidental RELEASE в stdout flag не использован для определения config. Debug proxy16 и существующие move-budget paths actual executed, не отдельный fault-proof каждой новой QueueInput transfer. |
| graf-f200-protected-queue-input-round266p-portable.json / raw | `749686e1e65b52b815cc8161934a8265402396c4b927ea687599d79c3951df7c` / `b1b8f4e8c61b5b8bfe2d2f337abd946efc99bd4d16bf88d8f6c2bc68efab355e`; terminal build/test0,46/46,8.16s в receipt, source172 равен f map. Applicability only: Windows QueueInput/DPAPI native branch не исполняется. |
| graf-f200-protected-queue-input-round266r-red.json | `90e41f82723e41d4eea06e5389d94888a2ac0386cc4978ddea1a29fa01190a49`; terminal failed, configure/build0, test8. |
| graf-f200-protected-queue-input-round266r-red-test.log | `d287953815b69ecaee7dd89de1847b27ce1c9248b41076d0e70ca34cf9f297da`; actual Release Files command, writerFailed9/native0, input.ok assert1528,0.13s. Genuine native RED, не compile-only. |
| graf-f200-protected-queue-input-round266b-release.json / raw | `3426fe2404c8ccadec38e084f383b9f69d9e75d60b9ac302a6bdcdd1ba954293` / `cc9c569ca167b797027abeb3980f1e4896cfc52462d3c85b34554ab44cee1e60`; failed test8/assert1619, неправильное ожидание invalidContent для native DPAPI failure. |
| graf-f200-protected-queue-input-round266c-release.json / raw | `b4be1cec7d64d2ab4a49a4346c9af2fafc54c556ab9489427b8293c67611b86d` / `34e540e42b8cdb35853882b27721edc355c9715779522a9e60f20ec2472a3ae1`; failed test8/assert1650, счётчик hook не сброшен. Historical failed, не final proof. |

Сверка c map ранее дала один ожидаемый mismatch FilesTests после исправления
счётчика; поэтому c не принят как current. f map совпал целиком. Готовый
Debug/SDK script или map без запуска не принят за execution. Releasea до
extra matrix и portableb до test correction не заменяют финальные результаты.

Actual delta f/previous265g172: только Metadata.h/.cpp, Files.cpp, FilesTests.cpp.

| Текущий source input | SHA-256 |
| --- | --- |
| Metadata.h | `524a040b07a3264369406d7bdbcd9e9bcb90417b471f4f3455ced9109f02b615` |
| Metadata.cpp | `6b9566e55edb24e6880d971777cb0d2b852e04cafb28831530395c161dcefba1` |
| Files.cpp | `484e81430bc57e2c15e130179d5a7a740f0a9b821bf6b89801dc3df7442a824c` |
| FilesTests.cpp | `f3731f4a60c36dba248c9af5243486b4066df4e3cc57a632086fd88613bb602d` |

Матрица лично прочитана: real g1 BOTH, g2 old3bytes/current multi-block и
exact4MiB, producer refusal+1; missing g1 indices/block и corrupt g2 lower/
higher indices/blocks; reservation/empty/ZERO; null/pre/mid read cancellation;
job/pin/global pressure, native IO/hash/allocation, partial last-read pressure,
fresh-owner retry, retained child/exclusive identity lifetime, writer counters0.
Missing-g2 отдельная новая строка отсутствует; +1 — producer guard, не
QueueInput-read oversized fixture. Поздняя pressure включается внутри
readBlock после ReadFile, не адресует отдельно raw object/control allocation.
Final post-construction cancel и каждый Debug transfer failure по отдельности
не инъецированы. Они проверены SOURCE ordering, не объявляются отдельными
native PASS. Same-thread busy ветвь не является валидным доказательством из-за
SRC266-1; реальный межпоточный busy случай пока не показан.

## Ponytail: только сложность

Private retained result необходим для владения двумя charged payloads и parent,
не speculative controller. Existing discovery/validator/allocator/native codec
переиспользованы; безопасного удаления, новой зависимости или второго parser
не найдено. Замена небезопасного synchronization primitive относится к обычному
correctness review, не разрешению упрощать guarantees.
Итог отдельного complexity review, НЕ SOURCE/release approval:
**Lean already. Ship.**

## Inventory и открытые границы

До этого отчёта128 checklist/report .md:10 normative154 checked/0 open;
отдельно118 historical/context. Все markers неизменны. Исторические10 open
не превращены в новые normative obligations. Tasks SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
120/93checked/27open. REQUIREMENTS266 GO не закрывает текущий SOURCE finding.
В registry before/after implement/analyze/checklist по одному disabled git.commit,
enabled0; reviewer ничего не dispatch.

После записи лично сверены все128 прежних hashes: changed0, только один
added report129. Финальный SOURCE GO сейчас не выдан. T116–T120, protected
semantic parser/shared projection/intent/current account/epoch/typed writer/
startup/adoption, H250, B1/legacyAAC/whole application остаются OPEN.
Известный full265k49/50 — NOT GREEN; это не новая регрессия Round266 и не
обоснование пропустить SRC266-1.
