# Независимая проверка исходного кода Round252: обе версии метаданных

Дата: 2026-10-06. Владелец: независимый reviewer.
Область: T116, dependency5; только physical metadata pair и readonly
`ProtectedCustodyPackagePair`, включая исправление классификации identity IO.
Полоса: high-risk-product storage; самостоятельная проверка кода после
согласованного requirements gate. Никакие испытания reviewer не запускал.

## Решение

**SOURCE APPROVED / scoped GO — C0/H0/M0/L0.** В сравнении пяти окончательных
файлов с сохранёнными исходными копиями не найдено конкретного нарушения
согласованных требований. Одобрение относится к приведённым ниже SHA-256,
а не к всему dirty HEAD, текущим сборкам или будущей реализации consumers.

Самостоятельная приёмка выполнения тестов отсутствует. Последний переданный
main результат native252 — 5/6, с отказом Files при первой внедрённой ошибке
ReadFile; это **не PASS**. После исправления shared identity требуется итоговый
запуск точных окончательных файлов. Одобрение исходного кода не превращает
старый запуск в успешный и не закрывает T116 либо установку приложения.

## Исходная точка и неизменность требований

Работа велась только в
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Сравнение — `diff -u` с пятью exact copies в
`/tmp/graf-f200-metadata-pair-baseline.BA18fG`, не общий diff относительно HEAD.
Существующие посторонние изменения сохранены и не включены в это одобрение.

Requirements report лично перечитан целиком. Фактический SHA-256
`review-2026-10-06-metadata-pair-gate.md`:
`5d26889dd72a59a16d6fefc5a84d13e12690c6d75890558656ddb3e7d1f9a496`.
Обозначение `report9e464e` из сообщения main не использовано как идентичность
файла: прочитаны фактические байты существующего scoped GO 14/14.
Отчёт требований не изменялся reviewer при этой проверке.

Повторно вычисленные SHA constitution/spec/plan/tasks/data-model/quickstart,
обоих custody contracts и Memory.h/Codec.h совпадают с таблицей requirements
gate. Новый schema, lifecycle, access enum, backend, mutex или критерий
package authorization не введён. `CustodyMetadataIndices` — название того
же согласованного fixed array2 результата, не изменение протокола.

## Проверка кода по согласованным границам

PASS в таблице означает вывод из лично прочитанного исходного кода, не тест.
Номера строк относятся к окончательным файлам из таблицы SHA ниже.

| ID | Предмет | Вывод и точное основание |
| --- | --- | --- |
| S01 | Один физический validator, прежний API | PASS: Files.cpp:486–508 сохраняет публичный `readValidatedSnapshot()` и направляет его в тот же body с null outputs. Единственная новая ветка body, :572, переносит уже проверенного peer; повторного сканера/выбора нет. |
| S02 | Обе версии и выбор current | PASS: Files.cpp:489–502, :520–574. Новый entry point допускает только manifest..migrationIntent; metadata требует обе исправные candidates. Индексы размещаются по physical slot, current — highest generation, equal g1 — прежняя проверка точного decoded равенства. Неисправный lower slot нельзя спрятать выбором higher. |
| S03 | Прежний audio/trusted-prefix контракт | PASS: при null peer прежние проверки и пути :515–582 неизменны. Canonical/media имеют прежний trusted prefix, playback его не получает. Metadata pair не разрешён audio; audio g1 placement и conflicts не изменены. |
| S04 | Исключение protocol writer | PASS: Metadata.cpp:253–262 получает job/pin до IO и открывает `writeExisting` до проверки pair. Files.cpp:166–177 удерживает data-access identity HANDLE без share-write; `readExisting` по-прежнему не считается frozen. Второй обычный protocol writer получает несовместимое native открытие. Нет новой очереди ожидания. |
| S05 | Actual identities и confinement | PASS: Files.cpp:229–287 использует existing path/ancestor/ACL/no-reparse/hardlink checks, store.id и id.bin. Package wrapper независимо получает own context и directory, разрешает только packageState и закрытый directory grammar (:246). JSON не выбирает собственные trusted IDs/path. |
| S06 | Собственные payloads обоих slots | PASS: Metadata.cpp:269–284 читает каждую ссылку DATA, повторно применяет existing openBlock к точным own context/position/version/length и вызывает `readCustodyPackage` с generation именно этого index. Результат создаётся только после обоих successful parses; fixed values2 и indices2 сохраняются. |
| S07 | Bounds, ZERO/empty и strict parser | PASS: :272 отвергает length0/>65536, entries!=1 и flags!=DATA. Existing Codec проверяет envelope/context/tail/hash и slot placement; existing parser не расширен. Malformed lower payload или несовпавшее own generation не дают partial pair. |
| S08 | Readonly lifetime после возврата | PASS: :285–295 блокирует writes и публикует только shared_ptr<const>. Metadata.h:48–65 не отдаёт Files/HANDLE, constructor private; copy запрещён. Lease/pin — private члены и живут до последней owning reference, а не только до выхода worker. Public const values/indices не дают write capability. |
| S09 | Порядок освобождения ресурсов | PASS: Metadata.h:62–65 и Metadata.cpp:227–238. На обычном destruction fixed values очищаются, затем уничтожаются indices, native lease, pin. В factory job объявлен раньше pin/lease и освобождается после actual synchronous work. При раннем отказе локальные leases закрываются раньше admission. |
| S10 | Debug throwing transfers и allocation failures | PASS: potentially throwing CustodyIndex/CustodyVector moves остаются внутри function-try handlers. Constructor pair завершает indices move до передачи pin/lease (:230–232); при неуспехе caller ещё владеет ими. Placement construction catch освобождает charged raw object (:288–290). Если shared_ptr control-block allocation откажет, штатный shared_ptr pointer/deleter constructor вызывает deleter; object/lease/pin не теряются. Error return содержит disengaged optional, не повторяет allocating index move. |
| S11 | Общие resource limits | PASS: job4/pin32 берутся до open; indices buffers, plaintext CustodyBytes, result object и control block используют общий CustodyAllocator/owned64MiB. Tree pattern сохранён. Мелкие внутренние Files path/security allocations и native DPAPI allocations остаются прежними, не объявляются новой полностью charged моделью. Нет unbounded data growth или UI IO. |
| S12 | Plaintext wipe и отсутствие effects | PASS: returned raw plaintext — CustodyBytes с wiping destructor, including exception transfers; Codec/native DPAPI guards очищают промежуточные buffers. Wrapper WipeValues очищает slots-local values на всех выходах, parsed result очищается после копирования; proof destructor очищает retained fixed values. Ни публикации/CREATE_NEW/rename/flush, ни сети/GC/delete/миграции wrapper не вызывает. Это проверка новых owned buffers/retained values, не обещание очистки всех CPU/register/stack копий прежнего parser. |
| S13 | Cancellation/error classification | PASS: :252, :270, :277, :285 отказывают до IO, после physical pair, после native payload read и перед publication. Уже начатое bounded synchronous чтение завершается, ресурсы сохраняются до него. Codec/native/file error и nativeError сохраняются; allocation/system_error классифицированы. Не возвращается default value или один успешный slot. |
| S14 | Identity root fix | PASS: Files.cpp:170–176 теперь отдельно классифицирует GetFileSizeEx/ReadFile failure как ioFailed с немедленным GetLastError. Неверный размер, successful short read и неверные ID остаются identityMismatch. Share flags и handle adoption не изменены; store/object используют ту же функцию. |

У shared_ptr нет второго скрытого mutable owner capability. `indices()` даёт
const физические values, а не lease; любые дальнейшие mutation того же объекта
требуют отпустить proof, заново открыть объект и перепроверить полномочия.
Это согласованная граница, не новый запрет следующей стадии реализации.

## Разбор native252 и исправления identity

Старое выражение State.identity объединяло native false-return, неправильный
размер/short read и несовпавший ID в identityMismatch без nativeError.
Конкретный старый контрпример: внедрённый ReadFile failure на первой операции
чтения identity с ERROR_READ_FAULT возвращал identityMismatch/0 вместо
ioFailed/ERROR_READ_FAULT. Это root cause общего helper, не повод ослаблять
assert или пропускать injection. Окончательные :171–176 исправляют именно
классификацию; ложная идентичность всё ещё отвергается.

Проверены оба actual callers identity: store.id read и object id.bin read
(Files.cpp:257/:279). Ошибка open/inspection проходит прежним путём;
failed temporary handle закрывается без adoption. Не добавлены repair,
запись ID или допущение short-read успеха.

## Прочитанный тестовый протокол и его ограничения

Новая группа `protectedPackagePairs`, FilesTests.cpp:1319–1425:

- Schema1 и schema2, padded64KiB equal birth g1; сохранение g3/g2 и разных
  собственных member values; subsequent g4 после release.
- Writer не открывается во время proof и после сброса первой ссылки, пока
  живёт copied shared_ptr; после last release открывается снова.
- Artifact equality/no writes/renames/flushes и ограниченная read-only IO.
- Внедрённый ReadFile failure для всех ordinal1..8: два identity reads,
  два index и два physical DATA reads, два wrapper payload reads. Требуется
  exact ioFailed/ERROR_READ_FAULT. Исходный отказ native252 не замаскирован.
- Cancellation cuts6/7/8 соответствуют концу physical pair и двум wrapper
  payload reads; pre-cancel требует opens0.
- Hash failure, allocation failure, pin32/job4/owned64MiB pressure,
  последующее исправное чтение, wrong own identity/role/directory/null token.
- Authenticated malformed lower JSON, wrong own payload generation,
  missing lower index/DATA и ZERO metadata не дают результата.

Существующий `snapshotChecks` :1426–1584 сохранён: birth pair для всех шести
metadata roles, singleton/missing DATA/conflicting g1, native/hash/allocation
sticky failure, slot entropy и audio prefix/playback. В него добавлена проверка
metadataPair equal birth и запрета playback. Группа нового wrapper подключена
к обычному Windows запуску :1671, portable ветка проверяет unsupportedPlatform
(:1661–1667). Portable PASS **не выполняет Windows pair ветки**.

Лично прочитаны production codec/Memory/Primitives, relevant Files open/read/
snapshot/blockWrites и Tree allocator pattern; сопоставлен changed test hook
afterRead с TU-local native ReadFile substitution. Assertions принудительно
включены независимо от NDEBUG. Нет нового production fault switch.

Тесты не объявляются исчерпывающей новой runtime matrix: точечное исчерпание
памяти на final object/control-block/Debug transfer и работа Windows sharing
оценены здесь по коду, не independently executed fault runs. Прежний
`metadataMoveBudget` относится к прежнему commit result, не считается тестом
нового proof constructor. При source review конкретного небезопасного пути
не обнаружено; новых gates/schema или дополнительных implementation задач
reviewer не создаёт.

Переданные main сообщения, **не reviewer execution**:

| Сообщение | Что можно утверждать |
| --- | --- |
| RED portable b13460, missing class | Main сообщает ранний RED; reviewer не выполнял его. |
| Compile cba86b до последних правок | Не идентифицирует окончательные пять файлов и не принимается за final compile. |
| Native252 terminal1/ab6f57,5/6; Tree PASS22.06s, Files assert | Отказ раннего состояния сохраняется. Полная успешная native приёмка отсутствует. |
| Portable oldcohort46/46,21.44s | Сообщение main о другом/раннем cohort, не исполнение Windows wrapper и не final native PASS. |
| Native252b и final portable rebuild | На момент проверки только запланированы; результатов reviewer не наблюдал. |

## SHA-256: прочитанные окончательные файлы и baseline

| Файл | Окончательный SHA-256 | Baseline SHA-256 |
| --- | --- | --- |
| Files.h | `cb0e4eb64f72c0b2332c9adee8f0d3824cd8063a5ef4e2bed5458293b65fdfa1` | `108f2e989b081812a38a2464a3eda9930fe35c1173a86df0f288851e6aefeced` |
| Files.cpp | `ae784b46f417c503e592410edd7dc71ab8131592f5cfeb04c235e0a96a817b82` | `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882` |
| Metadata.h | `3e1f12fda3e18463c6430921e16173afac5c549aaebfa222efcc9dd24b743478` | `bc5b665d0e28a10ade9b66e4c7966a8255055627746a1d0b5705343e4ed14f05` |
| Metadata.cpp | `c917b43a94d09547be829694b6cf9c44efde0f91d03dce4c931d8534fa68a1f7` | `f8ad4a5ed733f803088e025e8de15a4f427e6f747241929a658dbadb9d646965` |
| FilesTests.cpp | `f6424220ccfb4067ee7204eaec0d05275ff4273a3da981a570f514ada143d08b` | `1a3d6a68addf40d2d38fcb333253c6368730a5cdff1541286be9956ea427d33e` |

Имена Files/Metadata обозначают соответствующие ProtectedCustody* файлы в
`apps/windows/RecApp/Storage`; FilesTests находится в
`apps/windows/Tests/GrafWindowsCoreTests`. Baseline Files/Metadata hashes
совпадают с requirements gate. Окончательные Files.cpp/Tests hashes учитывают
переданное в ходе review исправление shared identity и ordinal1..8/cancel6..8.

## Состояние checklist и scoped analyze

Перед записью нового отчёта перечислены98 существующих Markdown checklist
файлов и зафиксированы их SHA. Физические исторические markers:
410 checked/10 unchecked, не420 уникальных нормативных требований.
Десять действующих нормативных checklists:154/0; tasks120=93closed/27open.
Новый отчёт добавляет0 checkbox markers. Ни один старый marker не изменяется;
исторические unresolved/error-cut и terminal append verdicts сохраняются.

Связь ограниченного компонента с FR-012/013/022 и SC-006, задачей T116 и
планом dependency5 подтверждена; unmapped0, ambiguity0, новых требований0.
Таблица S01–S14 даёт14/14 положительных source выводов в согласованной области,
не14 выполненных runtime тестов. Требования gate 14/14 остаются прежними.

Ponytail-review: **Lean already.** Использован existing validator, Files lease,
parser и allocator pattern. Constructor catch нужен для throwing Debug moves;
private retained lease/pin и wipe guards нельзя удалить без потери требований.
Безопасного удаления или новой лишней абстракции в этом incremental diff
не найдено. Оценка возможного сокращения: net0 lines.

## Терминальная граница

**Scoped SOURCE GO только для readonly обе-slot payload provenance primitive.**
Actual member roots/closures/logical hashes/manifest/trusted-prefix/positive
short predicate, cross-record phase transitions, account/admission и
upload/playback/delete/GC остаются следующими зависимостями. Generic physical
pair сам по себе не делает readExisting frozen. Нельзя заявить полную package
authority, завершение T116/T117/T118/T120, migration/bootstrap/intent recovery,
installed parity, working-profile acceptance или release; H250-1/H250-2
не сняты. Повторные испытания окончательной ревизии остаются работой main.

Reviewer изменяет только этот новый source report и прекращает работу после
его передачи. Исходный код, spec/plan/tasks, существующие reports/markers,
runtime/profile/Windows/GitHub/commit/push/PR/merge/install/audio не менялись
и не запускались reviewer.

После записи отчёт лично перечитан; SHA и markers всех прежних98 checklist
файлов повторно проверены: совпадение98/98. Пять окончательных source hashes
также совпали с таблицей. Единственный новый файл — этот отчёт, markers0/0.

## Дополнение: ограниченная проверка quickstart после SOURCE GO

Дата: 2026-10-06. **DOCS APPROVED / scoped GO — C0/H0/M0/L0.**
Проверен только последний раздел quickstart.md:749–789
«Обе защищённые версии описания пакета», относительно принятого выше SOURCE
GO. Новых требований, критериев, задач или расширения области приёмки нет.
Это проверка документации узкого readonly pair, не готовности приложения.

Неизменность прежнего quickstart подтверждена побайтно через SHA-256:
его первые65624 bytes дают исходный
`4ba06328532a417002d126ce1e5b47963f72859155311c477b53aeb344b5034a`.
После них добавлены один разделительный LF и новый appendix; заголовок
начинается с byte offset65625 (нумерация с0). Текущий полный quickstart SHA:
`5ff63ffb0519448fbe853ef7aefd573355b4f6a400d90be9162035c2847197a3`;
appendix от заголовка до EOF:
`177ee268268597f4203d58cedcb1e532f1f6f582fa6f1502b2991628ebe0f657`.
Quickstart reviewer не редактировал. Пять source SHA повторно вычислены и
совпали с таблицей SOURCE GO; новое source review не открывалось.

Описание обеих физических версий и собственных payloads, no lower-slot
fallback, собственных generations/schema1/2/64KiB, удержанной identity lease
до last shared reference соответствует SOURCE S01–S08. Описанные восемь
ReadFile failures, cancellation после physical pair/каждого payload,
pin32/job4/owned64MiB и отсутствие write/rename/flush соответствуют лично
прочитанному test protocol, S09–S14; identity IO fix не смешан с поддельным ID.
Нет заявления, что generic physical pair сам приобретает frozen ownership.

Release-ссылка ведёт к непосредственно предыдущему разделу с шестью полными
наборами, -j1/timeout300 и проверкой exit0. Добавленная Debug-команда собирает
тот же полный ProtectedCustodyFilesTests и запускает только его, с проверками
exit после build/test. Последовательность, source/EXE matching и actual
terminal completion не заменены одной строкой PASS. Ограничение Debug
coverage сформулировано точно: все allocation cuts нового constructor/control
block не выдаются за выполненные тесты; отдельный анализ исходников сохранён.

Граница authority явно сохранена: member roots/hashes/manifest, account,
переход данных и upload/discard/delete/GC не принимаются. Consumer должен
освободить proof перед metadata mutation и заново проверить полномочия;
const views после last release использовать нельзя. T116/T117/T118/T120 и
установленное приложение новым appendix не закрываются.

Main сообщил independent reread876bb8/terminal0: native252b source171 и
all6 EXE match; Debug252 source171/Files EXE match,1/1 PASS8.51s;
SDK252 source178/app EXE match,SDKBuild0; все перечисленные завершились.
Это сообщения main, не независимо прочитанные reviewer runtime receipts и
не reviewer execution. Nativefull50 на момент запроса выполняется: его
успех здесь **не заявлен**. Исторические statements SOURCE выше, включая
native2525/6 и прежние pending-состояния на дату их проверки, не переписаны.
Новые actual runtime evidence main ведёт append-only отдельно.

Единственная запись reviewer в этом задании — данный append section.
Прежние разделы/markers не редактируются; новые markers0, criteria0, tasks0.
Runtime, сборки, тесты, Windows/profile/GitHub не запускались и не менялись.
После DOCS verdict ограниченное задание завершено.
