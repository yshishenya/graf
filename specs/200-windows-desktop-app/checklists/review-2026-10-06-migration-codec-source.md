# Round261 — SOURCE: migration.v1 codec

Дата: 2026-10-06. Независимая проверка корректности и безопасности через
`code-reviewer`; отдельно применён `ponytail-review`. Существующий T116,
lane **high-risk-product**, чистая структурная зависимость §8.1.
Рецензент читает исходники и экспортированные результаты основного агента;
не запускает VM, тесты или EXE и не меняет реализацию.

## Решение и границы

**SCOPED SOURCE APPROVED** для добавления `graf.custody.migration.v1` в
`ProtectedCustodyMetadata.h/.cpp` и существующий `ProtectedCustodyPackageTests.cpp`
на финальных SHA ниже. Неразрешённые findings:
**CRITICAL=0 / HIGH=0 / MEDIUM=0 / LOW=0**.
Принятый REQUIREMENTS261 gate не изменён и не расширен.

Это не приёмка полной миграции, bootstrap/queue admission, writer/очереди,
исторического native validator, packed migration.v2, T116/T117/T118,
установленного приложения или выпуска. Legacy RED257/B1 остаются открытыми.
Чистое значение JSON не является proof/permission, даже при успешном чтении.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.

## Findings

| ID | Серьёзность / состояние | Причина и закрытие |
| --- | --- | --- |
| SRC261-1 | MEDIUM, CLOSED | В первоначальной матрице не было отдельных отрицательных случаев полного destination triple с generation0, несовпадающими length и SHA; partial-null и source/anchor mismatch этого не доказывали. Основной агент добавил ровно три assertions, финальный test SHA `bd437f…58269`, строки314–316. Использован валидный switched fixture: остальные поля и source/anchor неизменны; проверяется общий для copied_verified и всех дальнейших stages guard `.cpp:69–70`. Свежие Release261g и Debug261h на этом SHA проходят; rejection count вырос487→490. Production H/CPP не менялись |

Это пробел покрытия, не найденная ошибка production. Mutation execution не
проводился; способность трёх случаев обнаружить снятие соответствующего guard
установлена чтением кода и fixture, не заявлена как отдельный mutation-run.
Старые261b/c/e не считаются финальными доказательствами после test change.

## Проверка исходников и требований

Полностью прочитаны три исходных файла, затем лично перечитаны три новые
assertions и повторно вычислены final hashes. Полностью прочитаны REQUIREMENTS261,
base contract §8.1 и используемые `CustodyBytes`/allocator правила. Сохранён
ранее полностью прочитанный AGENTS/constitution/required guidance и контекст
десяти действующих checklist; их свежие SHA совпадают с принятым gate.

| Проверка | Основание / вывод |
| --- | --- |
| Значение и независимый tuple | `.h:10–62`, `.cpp:43–56`: fixed arrays/optional, нет retained input views. Schema1, own migrationIntent role/store/object, generation≥1, expected transaction/subject/directory сверяются одной shape для reader/writer; queue требует empty expected directory и JSON null, package explicit ASCII identity≤300 |
| Закрытые формы | Root12/mask4095, anchor4/15, source7/127, barrier5/31, authorization6/63. Все ключи обязательны, включая nullable; неизвестные и decoded duplicate keys отвергаются до чтения значения. Overload общего PackageJson, не второй parser/DOM; неизвестные вложенные объекты не пропускаются |
| Границы parser | Full input1..65536, strict EOF/BOM/trailing/comments rejection. Token300, только закрытая ASCII grammar, валидные ASCII escapes, lowercase hex после decoding. Non-ASCII/invalid escapes/surrogates не принимаются; u64 через from_chars, без minus/fraction/exponent/leading zero/overflow. Нет recursive unknown-key descent; known depth≤3/keys≤12/source array≤6 |
| UB/index/overflow | Stage и source enum проверены до table access/shift, sourceCount1..6 до обхода fixed array; bad enum/count отказывает. Generation maxu64 допустима, инкремента и потенциального generation overflow в codec нет |
| Anchor и sources | Anchor ID/gen цельная optional pair, present gen≥1, length≤4MiB. Package требует protected anchor; queue ровно один ledger source с exact anchor length/hash. Package исключает ledger, kinds уникальны. Caps через существующий logicalLimit: ledger4MiB, manifest/recovery64KiB, canonical/media/playback64GiB |
| Destination/stages | Prepared triple весь null; остальные stages весь present, gen≥1, exact source/destination length/hash. Birth g1 только prepared, barrier/auth null. Switched и далее barrier required; cleanup_pending/complete authorization required. Copied_verified/null barrier и early authorization при gen>1 намеренно разрешены структурным gate — не разрешение IO/effect |
| Barrier | Own object exact, historical generation1, version>0, envelope bytes>16 и≤69632 через существующий blockEnvelopeLimit(65536). Не приравнивает version к generation и не принимает structural SHA/size за native envelope proof |
| Authorization | Два точных kind; bounded operation/actor/workspace identity, queue gen≥1. Owner_confirmation operation равен lowercase transaction hex; delete_purge не получает выдуманного ограничения transaction equality. Не проверяет fresh owner/current queue и не выдаёт право cleanup |
| Whole failure | `.cpp:360–366`: parse/shape/cap failure даёт no value + invalidPlaintext. Writer invalid shape даёт invalidInput до allocation. Нет fallback, default success, path/URL, IO, migration controller или native effect |
| Writer/память | `.cpp:368–412`: charged reserve65536 до plaintext, emit ограничен remaining cap, deterministic fields и source order. Quoted только после validated ASCII grammar, 20char to_chars достаточно всему u64. Reader не выделяет heap; output/token wipe и release используют существующие механизмы. bad_alloc/length_error дают typed no-value outcome; нет unwiped growth buffer |

При удалении только новых migration блоков **в памяти**, без записи файлов,
header и tests восстановили побайтно SHA baseline260:
H `8cbf848fa864bc50298e2d0bb30d6bf7d2225e1c0258cef184959d981ffd3eec`,
Tests `833eab30402e0743bf1c90ffed382c62fca400c7eda2814bd0b3e25852d8571d`.
Для CPP такое побайтное восстановление не заявляется: старые функции/primitives
прочитаны, новая часть использует их без изменения логики, comment shape bounds
обновлён. SDK179 относительно260e имеет ровно три изменённых inputs этой области.

Матрица лично проверена по assertions: пять stages×два subjects, valid roundtrip,
16 destination-null masks; every12/4/7/5/6-key omission/decodedduplicate/type/null,
unknown enums/schema/keys, count/duplicates/order, independent tuple mismatch,
birth/barrier/authorization constraints, role caps, ID/identity/u64 границы,
exact65536/+1, BOM/escape/trailing, reader на занятом shared budget, writer
allocation refusal/no value/release/retry. Release assertions включены через
`#undef NDEBUG` до `<cassert>`. После новых tests исполняются прежние bootstrap
и package v1/v2 assertions; в конце owned count возвращается к начальному.
44/490 — счётчики `check`, не число всех assertions или migration IO сценариев.

## Лично прочитанные доказательства

Каталог `/Users/yshishenya/Documents/graf-f200-calendar-test.UjB7WI`.
Receipt JSON разобран со снятием WinPS UTF8 BOM **только в памяти**;
SHA вычислены по исходным bytes, exports не переписаны. RED/финальные
Release/Debug raw logs прочитаны целиком, не только PASS-строки.

| Исполнение основного агента | Лично прочитанный результат |
| --- | --- |
| RED261a | terminal failed, configure0/build0/test8, один Release PackageTests: assertion migrationDecoded.ok() line211, raw1.94s. Receipt172 map совпадает с RED map. Этот ранний отказ не доказывает выполнение старых assertions после точки остановки |
| Release261g FINAL | terminal passed, configure0/build0/test0, два targeted tests: Package0.08s, Files24.29s. Migration44/490, bootstrap15/173, refusal/retry1. CTest total24.38s сообщён основным агентом; LastTest содержит per-test времена, а не итоговую сумму |
| Debug261h FINAL | terminal passed, configure0/build0/test0, два targeted tests: Package0.30s, Files30.75s; те же44/490 и15/173. Receipt map тот же finalg172 и совпадает с canonical172. CTest total31.06s сообщён основным агентом отдельно от raw per-test времён |
| SDK261i FINAL | terminal passed, restore0/build0, mode full-sdk-app-build-only, exact179. App EXE hash остался прежним при test-only correction: SDK не компилирует данный test target. Это build-only, не launch/install/acceptance |

Все172 canonical hashes лично вычислены и совпали с finalg map и Release/Debug
receipt maps; **172/172 MATCH**. SDK map/receipt/canonical **179/179 MATCH**.
RED→первыйGREEN меняет CPP/test; первыйGREEN→finalg только test.
FilesTests logs содержат прежние generated AAC1s/30s и damaged rejection,
45 normal/privacy и14 degraded rows. Release имеет три SKIP-no-proxy-allocation-fault
сообщения; Debug показывает charged-proxy path. SKIP не выдан за PASS fault case.

| Export | SHA-256 исходных bytes |
| --- | --- |
| source-migration-round261a-red.json | 766ca6c5a035f5a503efef40ca7f993a519c1442c1ab452957316a2bb3ac6721 |
| graf-f200-migration-round261a-red.json | 72532292bc277066bb1c07fb08f586734958ce091ac5504a36670ef47e61511a |
| graf-f200-migration-round261a-red-test.log | 3adb9a5f386d23a7eb362669b1752c2b3bd4c6c7b240a7b59d2832088f0003b4 |
| source-migration-round261g-final.json | 68e4f9e9c9c9a282010251bd316858ac36674badcd5a81e412292f653592e6dc |
| graf-f200-migration-round261g-final.json | ed0135905d98c8bf726664179a9cc4ccf9d545ff9de4793fcc10bc9b07ad3bc1 |
| graf-f200-migration-round261g-final-test.log | 7210b3910e3f878ee747d10bb6ed82e025b9f67fbb414428c407e8ff2936e141 |
| graf-f200-migration-round261h-debug.json | 121dc0fa2feeec96b46508c7c894674834418c3b1fe9a42a6300ef9382a6f426 |
| graf-f200-migration-round261h-debug-test.log | c4d6b5c587b79d033ba5946759bc47f0171f14c6142fcd13ecf08659ece671ab |
| source-sdk-round261i.json | e4f6e447929d71ae4f8dcff8afdc738da4b33aeee304d5767fa07c04dc4256f6 |
| graf-f200-sdk-live-round261i.json | 4882490f742839bca2b874300cbb33087c8ecb598cfd94bd453354eddc1d3f50 |

EXE SHA **из прочитанных receipts**, не собственный VM/NTFS reread рецензента:

- RED Package `a505e4756f10eb53eeabaab7f3e10751461ba6a2f7e26280cb23fee8ac0f3f41`.
- Final Release Package `378d4dc11bf1a4b6c649081722febb78548b9cbe070f1ab5cc2b1a7d75ce8fb0`;
  Files `3b5be67226d9ff187a8c3e5deff5cb884cb57393aff1525496dd5231e88c676b`.
- Final Debug Package `ef43e573b879cc3f82a3f7a667cab661ab2d3293e4e4edae12507e9095054360`;
  Files `86456fb3c071c644044e582135eccc247d8103f6db34ed425d6d7363060722c1`.
- SDK app `8828568e5fe641b7f3f4461b1a5ef72200c5ee6a2ecc5babdf3a5d68485431ff`.

Portable FINAL46/46 PASS5.37s сообщён основным агентом; здесь не исполнялся
и отдельный portable raw log не читался. Не заявляется fullnative50/50,
исправление legacy RED, новая native историческая/IO/migration проверка,
hardware, live audio, current account authority или приложение в целом.

## Ponytail и сохранность

`Lean already. Ship.` — вывод только о форме данного codec, не release GO.
Reuse существующих parser/allocator/writer patterns, fixed shape вместо DOM,
один existing test target; новый framework/dependency/controller не появился.
Безопасных сокращений без ослабления grammar, bounds или evidence не найдено.

Final source SHA:

- H `910b8d5d20a1b5ecac18a563058c483c7aeefbbc65bead08ccd58251ea032004`.
- CPP `1b261f470885988c1ef77ac64bd77d90897f55afbb91bfea3e942864db4fff74`.
- Tests `bd437f417c9ea07d03d182a471e53fef4885a620c9aa137bf61f250eb6c58269`.
- REQUIREMENTS261 `7581fc7af886dad0c6a1e1569b1d7debe2eb2bf192c52c59eaf13f58f998bf35`.
- Tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`:
  120 total /93 checked /27 open, неизменены.

Перед созданием этого отчёта117 старых `.md` checklist/report файлов;
inventory SHA (sorted basename + space + file SHA + LF):
`af2743917d2143e3539f6626334297fafa9911c9258bbd40cd4cba90d4f0bf2d`.
10 действующих normative checklist154 checked/0 open, отдельно107 historical/context
с прежними256 historical checked/10 historical open. Никаких новых нормативных
обязанностей из старых unchecked не выведено; старые markers не изменены.

Рецензент записал только этот новый reviewer-owned SOURCE report. Production,
tests, spec/plan/tasks, старые reviews, GitHub, VM, profile, commits и release
не менялись им. Полный goal и следующие реальные ownership/IO/adoption gates
остаются вне данного узкого одобрения.
