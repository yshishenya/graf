# Независимый обзор исходников codec T116

## Решение и область

**Approved source only. Блокирующих находок в проверенном ограниченном codec-шаге: 0.**
Это принятие исходников формата, контекста, границ и проверки целостности,
не результат запуска тестов и не принятие защищённого приложения.

- Root: `/Users/yshishenya/.codex/worktrees/200-windows-followup/crisp`.
- Ветка: `codex/200-windows-followup`.
- Базовый HEAD: `99b00a579c24b50e320465b69d9a296038bc544d`, повторно подтверждён.
- Обзор завершён 2026-10-03 после полуночи Europe/Istanbul; имя отчёта сохраняет заданный владельцем идентификатор среза `2026-10-02`.
- Проверены текущие незакоммиченные `Storage/ProtectedCustodyCodec.h/.cpp`, `Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp`, регистрации `CMakeLists.txt` и `RecApp/GrafWindowsApp.vcxproj`.
- По дополнению владельца включён текущий `NativeHashFailureTests.cpp`, в частности добавление codec-регрессий на строках 89–108.
- `Storage/Sha256.*` прочитан как зависимость реального пути digest, не как отдельный повторный обзор hash-среза. Test `.vcxproj` прочитан только для разграничения способов регистрации.
- Risk lane продукта остаётся `high-risk-product`. Действие reviewer — чтение исходников и единственный документальный отчёт; полный Spec Kit путь не сокращён.

Полностью прочитаны root `AGENTS.md`, `code-reviewer/SKILL.md` и
`ponytail-review/SKILL.md`. Прочитаны guidance index и относящиеся к области
правила worktrees, risk lanes, product gates, validation, constitution,
PRD/current status; актуальные FR-012/013/014 и storage clarification в spec,
завершающий порядок plan, storage tasks и quickstart §12. Нормативная опора:
`contracts/windows-protected-local-custody.md` §§1–4, прежде всего §3,
и текущий `review-2026-10-02-custody-codec-gate.md`. Допуск требований не
подменяет этот обзор реализации. Отдельных вложенных `AGENTS.md` в проверенных
поддеревьях не найдено.

## Проверка реализации

Пути в следующих ссылках на строки — относительно `apps/windows/RecApp/Storage/`, если не указано иное.

| Проверяемое свойство | Основание в исходниках и вывод |
| --- | --- |
| Wire headers 16/104/112 B | `ProtectedCustodyCodec.cpp:19`, `:25`, `:33`, `:147`, `:188`, `:216`: явные little-endian unsigned поля по фиксированным смещениям. `memcpy` копирует только восемь magic bytes, не C++ struct/GUID/padding. Порядок полей блока и индекса совпадает с contract §3. |
| Недоверенный outer envelope | `:153–161`: короткий/слишком большой buffer, magic, schema, kind и точная длина ciphertext проверяются до вызова DPAPI. Лишний хвост и усечённый ciphertext не проходят. Поля header не используются для выделения памяти. |
| Identity и role | `:39–44`, `:49–58`, `:165–173`, `:202–205`, `:238–244`: неизвестная role даёт limit=0 и отказ; после unprotect повторно проверяются schema, role, оба 16-byte ID и header size. Block position/version/exact payload length совпадают с аргументами вызывающего reader. ID не превращается в account authority. |
| Native context / user DPAPI | `:113–131`: ASCII prefix без NUL, IDs, role/kind, selector/version имеют договорный порядок и ширину. У block selector=position, version=entry version; у index selector=slot, version=0. Только `CRYPTPROTECT_UI_FORBIDDEN`, без `LOCAL_MACHINE`, prompt, description, отдельного ключа или plaintext-пути. |
| Integer/end bounds | `:46–58`, `:175–199`, `:214–216`, `:240–244`: count вычисляется без `length + blockBytes - 1`. Проверка position предшествует умножению, известная role ограничивает length до 64 GiB/count до 262144; generation>0 предшествует вычитанию. `payload.size()` ограничен до u32 cast; count ограничен до size_t multiplication/reserve. Все размеры вызовов DPAPI заведомо помещаются в DWORD. |
| Tail и role caps | `:60–72`: размер каждого DATA envelope ограничен полным block либо точным последним tail. Manifest ≤4096 B, queue ≤4 MiB, recovery/package-state/bootstrap/migration-intent ≤64 KiB; canonical/media/playback ≤64 GiB. `openBlock` проверяет exact decoded size, а не только верхний предел. Сопоставление physical file size с entry и замена версии расширяемого tail принадлежат будущему logical IO. |
| Slot/generation | `:55–58`, `:230–244`: только slot0/1; generation0 запрещена; g1 кодируется независимо для обоих slots, дальнейшие generations соответствуют `(generation-1)%2`. Чтение UINT64_MAX как существующей версии не делает следующий increment допустимым: codec не выполняет increment/reset и не выбирает победивший snapshot. |
| DATA/ZERO/reserved | `:60–72`, `:204`, `:238`: DATA требует version>0 и envelope size>16 в точном payload bound; ZERO требует version=0/size=0; другие flags отвергаются. Block reserved u32 и index reserved u64 проверяются на ноль. Никакого восстановления отсутствующего DATA через ZERO нет. Происхождение явного ZERO от SetSize/seek проверяет будущий writer, а не формат. |
| Digest и hash failure | `:89–97`, `:186–187`, `:206–209`, `:224–226`, `:245–250`: Windows digest идёт через существующий `sha256Stream`/CNG, не через portable `sha256`. Block hash охватывает payload; index hash охватывает весь decoded index с обнулёнными bytes80–111. Ошибка hash даёт `hashFailed` без value; mismatch — `invalidPlaintext`. |
| Bounds before allocation | `:133–135`: native output проверяется до копирования в vector. Seal проверяет вход до plaintext allocation; open проверяет role-wide physical bound до DPAPI, decoded length/count и count-specific physical bound после DPAPI, checksum до `entries.reserve`. Максимальный index count не может увеличить allocation сверх договорного предела. Сам native allocator DPAPI не управляется codec; исходный envelope уже передан вызывающим кодом как vector. File-size check до его чтения/выделения остаётся обязанностью будущего IO caller через exported limit helpers. |
| Native output zero / failure exact | `:123–135`: RAII guard вызывает `SecureZeroMemory` перед `LocalFree`, включая native FALSE, пустой/oversized output и выход через исключение при копировании. `GetLastError()` сохраняется в typed result непосредственно после FALSE, до cleanup. `WipeBytes` на `:99–108`, `:188`, `:201`, `:216`, `:237` очищает собственный decoded/plaintext vector при выходе. Успешно возвращённый payload остаётся памятью caller, не обещанием очистки всей памяти Windows. |
| No authority / no fallback | `:22–24`, `:132–138`, `ProtectedCustodyCodec.h:36–43`: штатные отказные ветви возвращают nullopt с typed error; не-Windows путь — `unsupportedPlatform`, не открытая копия. Codec не имеет file IO, legacy parser, commit ACK, выбора index pair, разрешения upload/delete или автосоздания ledger. Успешный decoded index с length0 — только значение, не доказательство пустой восстановленной очереди. |

Умножение count×16 безопасно не благодаря расширенному типу само по себе,
а благодаря предшествующему `indexRequest` и равенству count=blockCount(length)
с коротким замыканием `||`. Аналогично `position * blockBytes` выполняется
только после проверки позиции. Не обнаружено обхода через UINT64_MAX,
последний block, пустую длину, неизвестную schema/role либо неверный slot.

## Тесты: что действительно проверяется

Тесты **не запускались**; ниже проверена причинная связь исходников assertions
с реальными ветвями. Это не выполненное mutation testing и не native PASS.

- `ProtectedCustodyCodecTests.cpp:7–10` и `NativeHashFailureTests.cpp:4–7` отключают `NDEBUG` до `<cassert>`: Release не превращает проверки и вызовы внутри assert в пустые выражения.
- `ProtectedCustodyCodecTests.cpp:87–103` проверяет invalid input, zero/oversized payload, generation/slot, UINT64_MAX length, DATA/ZERO сочетания и слишком короткие outer buffers. `:105–135` содержит actual DPAPI roundtrip payload1/4096/65536/262144, wrong IDs/role/position/version/length, outer mutations и truncation/tail.
- `:132–134` использует независимо защищённые DPAPI bytes с повреждённым decoded block header/payload. Отказ не сводится к неподходящей entropy или повреждённому ciphertext: product unprotect получает корректно защищённый malformed record. Отсутствие header/digest проверки сделало бы соответствующие `!ok()` assertions ложными.
- `:137–148` проходит все девять roles, length0/count0, wrong slot и максимальный role length/count через ZERO entries. `:150–168` проверяет DATA index и повреждения decoded index. В `:164–168` checksum пересчитан независимым portable SHA перед DPAPI wrap: unknown flags, reserved, count=0xffffffff, DATA size0, wrong block_size и generation0 не могут отвергаться только из-за старого checksum.
- `NativeHashFailureTests.cpp:19–53` подменяет Open/Create/Update/Finish только в translation unit теста, включая настоящий `Sha256.cpp`; wrappers вне выбранной ошибки вызывают настоящую CNG. Codec компилируется отдельно и разрешает тот же `sha256Stream` symbol. Подмены не добавляют production knobs.
- Добавление `:89–108` сначала создаёт настоящие block/index с отключённой ошибкой, затем перед каждым seal/open block/index сбрасывает счётчики и вводит каждую из четырёх CNG failures. Сравнение именно с `hashFailed` отвергает также ранний wrong-envelope/native failure вместо достижения hash. Замена Windows digest на portable SHA или fallback после CNG failure сделала бы эти assertions ложными. Payload65537 B обеспечивает вторую 64-KiB порцию; `:107–108` проверяет Update failure на ней, не первый вызов.

Границы доказанного тестами: не выполнены live assertions, наблюдение zeroing
и искусственный oversized/zero native output. Новые CNG assertions проверяют
error, а отсутствие value установлено чтением общего `failure()`; отдельной
проверки nullopt в них нет. Первый mutation loop index `:159–161` сохраняет
старый checksum: для части header полей он проверяет общий отказ, но не
изолирует отдельный structural guard. Rechecksummed loop покрывает перечисленные
поля, не все допустимые/недопустимые identity/schema/tail комбинации.
Нет отдельной регрессии расширения tail с новой версией и полного двухслотового
metadata birth/authority: это последующие IO сценарии, не реализованное
поведение этого codec. Эти ограничения не скрываются под заявлением полного
покрытия и не являются обнаруженным дефектом данного исходного среза.

## Регистрация и сложность

`apps/windows/CMakeLists.txt:12–16` включает codec в existing common objects;
`:21` и `:59–60` регистрируют codec tests и Windows-only hash fault tests;
`:69–86` создают отдельные executables/CTest entries и связывают `bcrypt/crypt32`.
Для `NativeHashFailureTests` обычный hash object исключён на `:73–75`, поэтому
нет второй definition, обходящей TU-local wrappers. У остальных tests остаётся
обычный hash object. `GrafWindowsApp.vcxproj:93`, `:147` включает codec и
`crypt32.lib` с сохранением `bcrypt.lib`. Это статическая регистрация, не
доказательство успешного compiler/linker run. Existing core-test `.vcxproj`
собирает `ContractFixtures`, а не новые отдельные test mains; их путь — CMake/CTest.

**Ponytail: Lean already.** Существующий incremental hash переиспользован через
малый borrowed streambuf, DPAPI/native cleanup штатные, новых зависимостей,
crypto switches, файловой подсистемы, scanner/lifecycle или общего framework
не добавлено. Безопасного обязательного сокращения не найдено; не предлагать
убрать bounds, второй identity check, RAII zeroing или fault regression.

## Привязка байтов

SHA-256 относится к текущим локальным bytes, не только к базовому HEAD.
Codec, обычный test и registrations совпали при начальном и повторном чтении.
Hash-fault файл зафиксирован после дополнения владельца и повторно сверён.

| Файл относительно root | SHA-256 |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.h | `41f14876953475997fac960bc6a466c10887646ade952890affc3af15fe35633` |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp | `0680f09b8f58f3c074a97e8881657a6c1bcd6712b2eea1b7ababb9be4d9ff107` |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | `da8cc416ecf33526249c458e279caf63fc456d738ed5cbda6613334ed217a491` |
| apps/windows/Tests/GrafWindowsCoreTests/NativeHashFailureTests.cpp | `813bc9c32a14a1189a67c61593545ca6094c1c02e477fa69dc3c5fff7f46efb0` |
| apps/windows/CMakeLists.txt | `5d9e84c3c4a81751f07c9441c3e9b83d8a379ec8a2c289c5099fcc9c44c15c40` |
| apps/windows/RecApp/GrafWindowsApp.vcxproj | `2f99db451738cd961df7abcaea51ab231bf26ae9c297f5ff76d7fe2537837c64` |
| apps/windows/Tests/GrafWindowsCoreTests/GrafWindowsCoreTests.vcxproj | `c53d070bbb0bae3f4262a875e593a56c3ff28847c5dec19e176d87d3e20d5df4` |
| apps/windows/RecApp/Storage/Sha256.h | `e51b352aa346036708ad30867fed412b67000434b87d88aeb02c45549c43cc60` |
| apps/windows/RecApp/Storage/Sha256.cpp | `cfad493c54a1b6f0db19bdc0aa80858e18e8396c8605b58b2a91ebea33e01ca2` |
| specs/200-windows-desktop-app/contracts/windows-protected-local-custody.md | `630b85b2a077788a90d23d5763561dce320e317aeddabe8ae5fe8810853bdba0` |
| specs/200-windows-desktop-app/checklists/review-2026-10-02-custody-codec-gate.md | `ca14a08aa09d1472778395130b228a33fcb28d157cabe7d69069595cfa021b28` |
| specs/200-windows-desktop-app/spec.md | `d778aa44725911288331beeddc5a2293333bf2fb39ab93e2087a471cdb4f1c0f` |
| specs/200-windows-desktop-app/plan.md | `34e64befcd775c85ee524a8d0e097d7d08805545cec92966bfdbf98d446f71cc` |
| specs/200-windows-desktop-app/tasks.md | `76c91845c3ce5da964351cca95b027562190bbc0fcb9f76b7159d0d021261287` |
| specs/200-windows-desktop-app/quickstart.md | `9946be5c60a192c2fcb92d7c8db1419827ff757fea8c13d40b9023b949ce1d59` |
| AGENTS.md | `384c41c0b1674a3daf75d0e57646379198295c3f8452012c8101fc6332bec58b` |
| .specify/memory/constitution.md | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |

## Что не принято и что изменено

T116/#7444 остаётся открытым: durable logical IO, confinement/ACL до content
write, flush/publish/reopen, metadata pair authority, leases/pins/GC и все
producer/reader/queue/finalizer/upload/playback/delete подключения ещё не
доказаны этим обзором. T117 migration и T118 full-pipeline acceptance не
закрыты. Clock, physical x64/60min/AEC, hardware, installed MSIX/EXE,
Home/Pro/N, actual key-loss/power-loss, update/rollback и release остаются
отдельными открытыми условиями. Отсутствие этих частей не выдано за дефект
разрешённого bounded codec-шага и не выдано за готовое приложение.

Reviewer не запускал runtime tests, сборку, VM, устройства или повторную CI;
эту проверку выполняет main. Не менялись код, договор, spec/plan/tasks,
checklist markers, GitHub, branch/commit или чужие изменения. Единственный
записанный reviewer путь — этот отчёт через `apply_patch`.
