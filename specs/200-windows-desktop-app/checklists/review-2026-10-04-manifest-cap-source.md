# Независимый source review: T116 manifest-cap prerequisite

Дата: 2026-10-04. Canonical:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD фактически прочитан: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Lane: high-risk-product, ограниченный source review уже принятой нормы.
**Статический итог C0/H0/M0; окончательное source acceptance PENDING.**
Последние native terminal receipts ещё не предоставлены/не записаны в
прочитанном round226. Это не отрицательный результат выполняющегося теста.

## Scope и чтение

Product diff только `ProtectedCustodyCodec.cpp`: manifest перенесён из
4096B в прежнюю группу metadata64KiB. Рассмотрены две новые группы codec
assertions и три cap-related участка FilesTests: metadata limit,
committed-limit Reader Stat/Read и pre-read cap+1 rejection.
Clone charge/reset/reclone hunk в diff относительно HEAD — ранее принятое
round224 изменение; его смысл сверён с неизменным Reader source report,
не приписан новому manifest prerequisite.

Лично заново прочитаны весь Codec.cpp, релевантные CodecTests, новые FilesTests
участки, hooks/counters реального File слоя и существующие metadata commit/
file-read guards. Memory allocator и Codec declarations прочитаны для bounds.
Старое полное reader-test чтение используется как контекст, не заявляю новое
полное чтение всех FilesTests или истории F200. code-reviewer SKILL прочитан.
Root/guidance/constitution из предыдущего полного чтения повторно проверены
по неизменным hashes. Requirements12/0 и текущие local-custody §3/plan/
quickstart нормы не переотмечались.

Reviewer владеет ТОЛЬКО этим новым отчётом. Нет правок code/norms/tasks,
old reports, VM, audio, private inventory, issues, Git state, install/release.
Git diff/show/read-only hashes не выполняют commit/checkout/push. Reviewer
сам не запускал portable/native тесты; execution ниже атрибутировано main.

## Собственные критерии source review

- [x] MCS001 Изменяется только manifest logical limit; все другие role limits, неизвестные роли и пустые/невалидные запросы сохраняют прежние решения.
- [x] MCS002 Manifest65536 остаётся одним256KiB блоком; count/index/envelope arithmetic и guards до subtraction/multiplication/native сохраняют bounds.
- [x] MCS003 Role/store/object/position/version/length/schema/checksum/DPAPI binding, точный payload и отсутствие fallback не ослаблены; wrong role отклоняется.
- [x] MCS004 1/4096/4097/65536 exact DPAPI byte roundtrip,65537 и position1 refusal представлены actual native codec tests; Release assertions активны.
- [x] MCS005 Предельный payload не обходит общий CustodyAllocator budget; real saturation проверяет allocationFailed для seal/open без повышения лимита.
- [x] MCS006 Metadata commit и IStream проверяют committed logicalLength/Stat/полный Read65536 и exact bytes; oversized commit/write и file cap+1/read отказывают до операций.
- [x] MCS007 Старый размер4096 и старые envelope/index форматы сохраняются; generic role/fault/reader regressions не удалены, отдельная semantic v5 validation не выдаётся за codec acceptance.
- [x] MCS008 Scope не включает capture/UI/writer/LocalRecordingPackage parser/T120; prerequisites/readiness/issues и source/runtime/hardware/release acceptance разделены.
- [x] MCS009 Финальные native Release full41 и запланированные Debug Codec/Files результаты, соответствующие сборки и актуальная guest/source identity подтверждены terminal receipts для точных3SHA; финальный readback после них выполнен. Подтверждено финальным readback ниже.

## Доказательства и вывод по коду

1. Codec.cpp113–120 — единственное продуктовое изменение. Media остаются
   64GiB, queue4MiB, остальные metadata64KiB, неизвестная роль0. Новой
   функции/backend/config flag/alias нет.
2. Codec.cpp44–66/123–130: blockRequest ограничивает position до расчёта
   `limit-position*blockBytes`; manifest допускает только position0.
   Для4096 и65536 count=1, прежний indexEnvelopeLimit=4096+16+65536=69648B.
   Общая blockEnvelopeLimit формула `payload+4096` и blockBytes262144
   не меняются. Нужный ciphertext может быть больше прежнего4096 payload,
   но это не увеличение global physical envelope формулы или index ceiling.
3. sealBlock проверяет запрос до digest/plain/nativeTransform, openBlock —
   до unprotect. Header identity/role, entropy и SHA256 exact-payload проверки
   прежние. openIndex повторно проверяет length/count/exact-size/checksum.
4. CodecTests387–390/417–438: не просто новый cap assert. Для каждого
   размера1/4096/4097/65536 создаётся различающийся payload `i%251`, seal/open
   проходит реальный Windows DPAPI и сравнивает все bytes.65537, position1 и
   expected65537 отказывают; роль recovery не открывает manifest envelope,
   несмотря на тот же logical cap. Generic index-atLimit/limit+1 loop всех
   ролей сохранён. Оба test TU делают undef NDEBUG до include assert.
5. При65536 тест реально резервирует остаток process-wide64MiB через
   CustodyBytes allocator и проверяет allocationFailed seal/open, сохраняя
   usedBytes==limit. Memory.h bounds не изменены; это тест owned-memory,
   не доказательство полного native DPAPI/job/RSS профиля приложения.
6. FilesTests823–842: protectedMetadata loop для manifest и служебных ролей
   отклоняет65537 с writes0; затем commits65536 через реальный metadata path,
   открывает Reader, проверяет Stat exact length и Read S_OK/got==limit/
   full-byte equality. Commit-state=committed после существующей публикации
   индексов и validated reopen, не после одного write.
7. FilesTests1672–1679 использует существующий interposed REAL File layer:
   readBlock(0,1,65537,65537+4096) возвращает invalidInput и native reads0.
   Files.cpp286–300 делает logical role guard до state_->read. Metadata.cpp
   input guard делает cap check до pin/staging/open/publication. Для codec
   отсутствие native операции на invalid input подтверждено чтением guard,
   не выдуманным счётчиком CryptProtectData в новом тесте.
8. DPAPI wire/schema/entropy не изменены: ранее допустимый manifest4096
   удовлетворяет тем же guards и roundtrip теперь явно сохранён. Это не
   отдельная execution-проверка сохранённого старой сборкой ciphertext;
   не выдаю её за проведённую. Перенос роли не меняет interpretation bytes.

В рассмотренном source/test flow не найдено C/H/M-дефектов или необходимого
изменения архитектуры. Весь v5 parser остаётся отдельным строгим consumer
gate T116/T120: `LocalRecordingPackage`4096/exact regex здесь НЕ исправлен
и НЕ принят. Fixture из произвольных bytes проверяет custody primitive,
не bytes-compatible логическую модель ProductPrivacySegment.

## Снимок и точные SHA-256

| Source/test | SHA-256, лично проверен повторно |
| --- | --- |
| apps/windows/RecApp/Storage/ProtectedCustodyCodec.cpp | 5737c34d50bf8a765173a9284054fac90fe0c8ca6ef6d20cdfc3eb2ea9b4b2d3 |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyCodecTests.cpp | b3007b9eafe11ebd7f7e286a64c5de68db4f58d72c306bd4b917b16fbfbf320c |
| apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp | 1a3d6a68addf40d2d38fcb333253c6368730a5cdff1541286be9956ea427d33e |

Прочитанные зависимости: Memory.h
`a5a67fb3448f07d4232cf8dee893e60e65c3eea5687a0908f4469226be2000ad`,
Codec.h `a5152a136c102b285e5e34cc926a9c6da7f6c3c43a5acca5707069a757e3dcde`,
Files.cpp `c7ddc8367c205a9f6e2177ff54b9a46ccc7e8b7a039079dba863378e67b11882`,
Metadata.cpp `739b40a5670227530554a9fc3c92a41a86c2b2577a1d9ac92c3ee118581dab74`,
CMake `34512b061361516a997c0581b6a693d9535d3d5e6893cb2b017a2a061b96e295`.

Current requirements checklist hash
`5e1c0a89ebb33f47876fafd345972e3e627e6597504d6b6a5dc4c8ac1ab10eec`, design
report `9098ed5afd52a956b24020db32b827d579ebbc9b8bf0ff1f8412c95598a6a75e`.
Local-custody contract
`090f4511fb9f3e1aa9fc27caf8ba922f39fc1a5d1d778e7b29a3ae946ec65402`, plan
`91f6b4c5e2bfd29a795a21ce79650395bbfe811ec49d6faf9c462fcd87069828`, quickstart
`c6619ad9ad5fe5e27cced14dd9cbc3d1a708315884559cfb1508d33753804cee`.

## Execution evidence — main, не reviewer

Лично прочитан только новый round226 в validation-2026-10-02.md:

- RED на старом Codec SHA5372538…: portable build0/test134; native Release
  build0/test3 на manifest64KiB assertion, old guest hash подтверждён main.
  Исторические FAIL не переименованы в PASS.
- Main сообщает mirror/native guest3hash MATCH для current source snapshot;
  reviewer независимо подтвердил canonical3SHA, не подключался к VM.
- Portable51033: terminal build/CTest EXIT0,39/39 PASS41.68s по main doc.
  `_WIN32` DPAPI/File fixtures этим portable результатом не принимаются.
- Native Release88235: ещё RUNNING в прочитанном последнем append.
  Native Debug: pending. Ни один не засчитан как PASS.
- `git diff --check` scoped3files пройден reviewer; тесты не запускались.
  Governance/doctor после норм описаны main как PASS, это не native receipt.

## Конечный статус этого чтения

**8 checked / 1 unchecked. Статически C0/H0/M0. Source acceptance PENDING
только MCS009, без требования новых кодовых правок.** Для закрытия нужен
terminal execution packet точного3SHA и независимый readback этого отчёта;
RUNNING или portable PASS не заменяет native доказательства.

**cap codec ≠ new v5 parser ≠ T120 pause.** Полная protected consumer/writer
integration T116 и capture T120 остаются открытыми. #7444 OPEN и T120 owner
pending — сведения main, не новое live issue чтение reviewer. Ни аппаратная,
ни установленная, ни release acceptance не выданы. Собственный итоговый
report SHA сообщается отдельно, не включается в хэшируемое содержимое.

## Финальный terminal readback — 2026-10-04

Этот раздел заменяет первоначальный pending-вердикт выше только в отношении
MCS009. Предыдущие RUNNING/PENDING и8/1 записи сохранены как история первого
чтения; они не являются текущим итогом. Старый RED также сохранён.

Reviewer лично перечитал полный текущий source report, новый main append
`Round226 — terminal native packet` в validation-2026-10-02.md и повторно
проверил canonical3SHA. Они точно совпадают с таблицей снимка выше:

- Codec.cpp `5737c34d50bf8a765173a9284054fac90fe0c8ca6ef6d20cdfc3eb2ea9b4b2d3`.
- CodecTests.cpp `b3007b9eafe11ebd7f7e286a64c5de68db4f58d72c306bd4b917b16fbfbf320c`.
- FilesTests.cpp `1a3d6a68addf40d2d38fcb333253c6368730a5cdff1541286be9956ea427d33e`.

Terminal выполнение атрибутировано main, не reviewer:

| Receipt | Подтверждённый результат | Объём |
| --- | --- | --- |
| Release88235 | full build EXIT0; CTest41/41 PASS185.47s; RELEASE_EXIT0 и command EXIT0 | Все текущие Release cases; реальные Codec/File DPAPI/metadata/reader/pressure regressions включены. Codec12.23s, Files7.28s. |
| Debug79049, после завершения Release | build Codec/Files targets EXIT0; CTest2/2 PASS10.72s; DEBUG_EXIT0 и command EXIT0 | Только Codec2.91s и Files7.69s; не full Debug41. MSVC Debug allocator/iterator проверки не отключались, budgets не повышались. |
| Portable51033 | full build EXIT0; CTest39/39 PASS41.68s; EXIT0 | Portable regressions; Windows DPAPI/File cases отдельно подтверждены native результатами выше. |
| Identity | canonical/mirror cmp3 EXIT0; guest GetFileHash3 MATCH перед Release build; canonical3SHA неизменны после Debug | Связь с ровно этим source snapshot; reviewer проверил canonical, guest/cmp сведения прочитал в main append. |
| Governance82001 | PASS/EXIT0, F200/extensions Ruby YAML PASS, diff-check PASS | Дополнительное доказательство main; не замена native execution. |

Данных достаточно для MCS009: новый cap и новые native ветки проверены в
Release и Debug, exact source binding сохранён; широких новых исследований,
новых методов приёмки или повторного выполнения тестов reviewer не требовал.
После добавления сводки reviewer перечитывает отчёт и подсчитывает markers.

**Конечный bounded source verdict: ACCEPTED,9 checked/0 unchecked,
CRITICAL0/HIGH0/MEDIUM0 — только T116 manifest-cap prerequisite.**

Приняты codec logical cap и рассмотренные native primitive/regression cases,
не v5 semantic parser и не подключение protected consumers. Полная T116,
T120 Pause/Resume, UI/writer, установленный MSIX, physical x64/hardware/AEC/
60min/accessibility/install/update/signature и выпуск остаются за границей.
**cap codec ≠ new v5 parser ≠ T120 pause.** Текущий LocalRecordingPackage
validator не принят новым лимитом. Никаких иных файлов, code/norms/tasks,
old reports, Git/VM/issues/runtime/install/release reviewer не менял.
