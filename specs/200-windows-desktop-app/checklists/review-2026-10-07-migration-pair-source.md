# Round273 — независимый SOURCE review MigrationPair и согласованных Files исправлений

## Итог и граница

**SCOPED SOURCE GO — C0 / H0 / M0 / L0** для замороженного Round273:
`ProtectedCustodyMigrationPair` с проверкой BOTH собственных intent-слотов,
их взаимной согласованности и direct immutable Birth, плюс перечисленные ниже
согласованные исправления построения строк/путей и строгой ASCII identity.
Блокирующих дефектов этой границы при чтении исходников, тестов и окончательных
доказательств не выявлено. Это не завершение T116 и не разрешение эффектов.

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
HEAD не является хешем реализации с незакоммиченными изменениями: решение
связано с exact 204-input map и SHA файлов ниже.

Применены полностью прочитанные `code-reviewer` и `ponytail-review`.
Reviewer лично читал production diff относительно сохранённого Round272
`graf-f200-migration-path272.d01Ilk/apps/windows`, итоговый код, native тестовую
матрицу, allocation/read adapters, окончательные Release/Debug журналы,
квитанции и скрипты readback. VM, тесты, приложение и GitHub reviewer не запускал.
Исполнение в Windows и реальные NTFS/EXE readback — действия main; здесь
проверены доступные неизменяемые экспорты и их внутренняя/исходная согласованность.

## Требования и сохранение

Принятый REQUIREMENTS gate:
`review-2026-10-07-migration-pair-gate.md`, SHA
`5435475dfc24d8f3a655c3bf343dfddf762362f9a1265d0cb4e70f338e50ba81`.
Его direct-only ограничения сохранены в публичном комментарии Metadata.h:75–79.
Base custody:155–172,415–434,481–545 и packed custody §6.1:297–347 остаются
источниками BOTH, independent tuple, v1/v2, immutable/sticky facts и Birth.
Stage progression не превращает JSON в доказательство выполненного IO.

До новой записи: 153 Markdown в checklists; все 153 лично сопоставлены с
сохранённым before inventory, расхождений0. SHA sorted
`basename<TAB>SHA256<LF>` inventory:
`d8f1d98123011283c37b969757825005a7bd31ae46926da454ea3a7f658df271`.
10 текущих нормативных checklist имеют 154 checked / 0 open;
143 остальных документа — исторические/исследовательские/review материалы,
не 143 новых нормативных checklist. Старые NO-GO и прошлые ошибки не переписаны.
Этот отчёт содержит 0 checkbox и не меняет markers.

Tasks: 120 / 93 checked / 27 open; SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Lane остаётся high-risk T116 / #7444; новый task не нужен. Свежий OPEN/canon
issue status сообщён main, не выдаётся за самостоятельный GitHub audit.
Constitution, spec, plan, data-model, quickstart, оба custody contracts и
feature/extension identity совпали с хешами принятого gate. before/after
analyze/checklist/implement: каждый зарегистрирован1, enabled0; reviewer
никаких hooks/commits не dispatch-ил. Переиспользованы ранее прочитанные нормы,
обновлена их hash-freshness; гигантская validation-история не подменяла gate.

## Проверка реализации

| Участок | Проверенное свойство |
| --- | --- |
| Metadata.h:75–99; Metadata.cpp:469–555 | Private ctor, const slots/indices/current; ожидания role/own/transaction/subject/directory приходят от caller, не из JSON. Fixed native Files.open без create/scan/repair. No Files/HANDLE/writer exposure. |
| Metadata.cpp:500–535 | Существующий native BOTH validator до выбора; каждый slot положительный ≤65536, один DATA, exact read/open, strict v1/v2 decode по собственной index generation. Ошибка невыбранного slot блокирует весь результат. |
| Metadata.cpp:106–147 | Один sameMigrationIdentity используется Pair и Birth: exact schema/context/tuple/whole anchor/source set, comparison по kind независимо от порядка. Newer stage не меньше older. Уже заполненные destination receipt/packed stamps, barrier и authorization не исчезают и не меняются. |
| Metadata.cpp:525–535 | Каждый non-null barrier обоих slots прочитан exact direct blockVersion/envelope size; существующий Birth validator проверяет cipher SHA, native own authentication и schema/immutable связь. Ни latest-version guessing, ни исторический index g1 не требуются. |
| Metadata.cpp:487–499,511–535,539–555 | Реальный NativeJob и Pin, cancel до/после bounded compound/helper IO, после успешного DPAPI open до parse, после parse/Birth и после shared_ptr materialization. Не заявляется прерывание внутри OS/DPAPI или жёсткая latency. |
| Metadata.cpp:469–481,503–508,521–533,540–554 | Index/proxy throwing moves завершаются до передачи Pin/lease. Raw object и shared controlblock charged; local values/успешно возвращённые parsed/Birth copies wiped, retained values wiped до lease/pin release. Placement/controlblock failure и final cancel корректно раскручивают владение. |

`migrationProgress` вызывается только после строгого per-slot shape, поэтому
поиск kind не разыменовывает end: exact unique kind set уже проверен.
Отдельная stage adjacency не добавлена: same-stage/jump/non-adjacent generation
допустимы как содержательные факты, но не как durable transition authority.
G1 tie остаётся правилом физического BOTH validator, не новой эвристикой.
Lease блокируется только после всех чтений; результат не может снова читать
или писать через неё. Sticky failure и проверка native identity не отключены.

### Согласованные общие исправления Files

Проверены против отдельного разрешения каждого narrow gate, а не как
произвольная перепись Files:

- Files.cpp:48–65,291–304: два обхода компонентов native drive-absolute пути
  через bounded wstring_view вместо faulting path iterator. Сохранены длина,
  drive/ACL, NUL/slash/ADS/dot/trailing rules, порядок ancestor locks и actual
  handle/path comparison. Интерьерные пустые separators не нормализуются
  в доверенный путь: реальный повторный separator по-прежнему отвергается.
- Files.cpp:101–124: два State path copy-ctor и два vector count0 ctor допускают
  throwing Debug proxy allocation. Directory default сохранён лишь для
  DefaultInsertable count0; реальные элементы создаются emplace с validated
  path. Throwing relocation копирует path до передачи Handle; failure приводит
  к уничтожению неопубликованного State, а не повторному использованию его.
- Files.cpp:136–138 и State::inspect: named SDDL/wanted strings без noexcept
  concatenation move, те же SID/ACL bytes и exact comparison, без normalization.
- Files.cpp:305–332: пять openImpl binary path constructions заменены named
  copy + append с теми же role/store/id locations и confinement/lock checks.
- Files.cpp:88–92, readIndex/readValidatedSnapshotImpl: indexName named append
  и forced copy prvalue, два named read paths. Publish/прочие producer paths
  не были автоматически переписаны или признаны fault-safe.
- Files.cpp:278–284,315–317: прежний identity guard плюс независимый explicit
  ASCII [A-Za-z0-9_-] guard до IO. Package widening выполняется только после
  доказанного ASCII; Unicode root остаётся native Unicode. Нет глобальной
  смены legacy validator/кодовой страницы или расширения protected identity.

Предыдущие Round272 blockName/path/SHA corrections сохранены; это не новое
разрешение других shared helper изменений. Экономия пары выражений путём
возврата к прежним default/noexcept move/операторным цепочкам нарушила бы
реально проверенный allocation-failure путь.

## Тестовая и доказательная проверка

Stand: `/Users/yshishenya/Documents/graf-f200-pair-accepted273.nSEy3f`.
Все 204 canonical/frozen input hashes лично пересчитаны: mismatches0.
Обе квитанции содержат ровно тот же map; все 12 PE/hash entries сопоставлены
с readback export: mismatches0, machine34404 = 0x8664.

| Окончательное исполнение main | Результат | Граница |
| --- | --- | --- |
| Normal native Release/x64 | build0, test0; selected6/6, 66.56s; Files48.09s | Не ALL50. Raw содержит ровно6 Test Passed. |
| Normal native Debug/x64 | build0, test0; selected6/6, 133.60s; Files111.03s | Реальные Debug paths, proxies не отключены; raw ровно6 Test Passed. |
| Portable | raw46/46 Test Passed; main elapsed27.33s | Проверка применимости/общих codecs; Windows DPAPI/Files branch этим не доказан. |
| Main native readback58208 | terminal0; 204 native/frozen, receipts,12 EXE/PE MATCH; ownedprocess0 | Reviewer прочитал script/export, но не выполнял guest readback. |

Лично прочитаны FilesTests:1371–2017, executable-only allocation hooks:40–82,
native fault adapters и Fixture. `NDEBUG` снимается перед assert. Setup synthetic
DPAPI/ACL fixtures происходит вне active failure hook; fault hook не заменяет
реальный allocator успешной заглушкой. `migrationFactory` не выдумывает наличие
lease до её acquisition: actual afterRead observer отдельно удостоверяет
exclusive ID и job во время index/Birth IO.

Матрица включает birth g1; actual g3/g4 без g1 index, version17, BOTH bad peer,
exact tuple/anchor/source/stages/receipts/sticky mutations; source order;
schema1/2 × queue/package; native/semantic Birth tamper; direct missing при
существующем fixture tombstone; empty/ZERO/oversize/multiple-entry refusal.
Удержание lease до последнего shared owner, no writes/rename/search/effects,
Pin32/Job4/owned quota, cleanup baseline и fresh retry проверены отдельно.

Из окончательных raw, для каждой схемы:

- Release: queue228 и package246 actual allocation ordinals; все failure и
  cancel ordinals, direct_birth_reads2, final_alloc_cancel1, retry1.
- Debug: queue503 и package539; те же all-ordinal failure/cancel проверки,
  включая объект/controlblock и Debug proxy allocations. Не package557.
- Birth regressions: Release10/envelope16, Debug20/envelope36, все четыре
  schema/subject fixtures с retry1. Writer cuts Release1/Debug3.
- Root grammar/ASCII regressions: invalid roots/identities до IO, actual
  repeated separators refusal, genuine unique Unicode root, valid ASCII
  native role paths/16-byte identity files, independent wrong store/object.
  Length300 guard tested с invalid root без утверждения NTFS300 creation.
  Locale1251 реально доступна в обоих raw: checked1/witness1/before-open1.

All actual allocation ordinals не означают все возможные thread interleavings
или runtime/device/performance acceptance. Нативные std path/security scratch
имеют прежнюю модель Files и тоже охвачены global-new cuts; отчёт не называет
их новой полностью CustodyAllocator-charged областью. Release proxy SKIP
честно относится к конфигурации без proxy; доказательство Debug не пропущено.
Allocation-free scanner cancel покрытие старого QueueCandidate не расширено
словами «all cuts» нового Pair. Diagnostic DbgHelp/prints/terminate handlers
отсутствуют в canonical/frozen final; временные диагностические прогоны не
подменяют эти normal результаты. Старые compile/runtime failures сохранены.

### Exact SHA-256

| Файл | SHA-256 |
| --- | --- |
| Files.cpp | `57b3db0d930e0f134d7d8d24badcb089f03c2eaef0c993e1ae74cbeb64e2ad5b` |
| Metadata.h | `fa5538d7e8a6e633607bd0e093e0c426afd50f6459df3e1c0ce42b6bd93e9865` |
| Metadata.cpp | `d971dda38d13370d55acab3b1ab474fcbbd349888b53d2c6708a6a3e87580650` |
| FilesTests.cpp | `26687aebdfd2752fe915fcbbb1466dbecb9b49b681f6515bf919197d2ac1ce01` |
| source-accepted273.json | `d87e2fdc5aeeaf461557668391e9fb42283e2c3ca375838dddefb85975d612e8` |
| accepted-native273-release.json | `6d32223966582c13cf87df77ed53e6cf80c5ec580e749509e202b94b08411a1d` |
| accepted-native273-release-test.log | `fdc253ff83de8d092bf5c27b562599b88bbc827c4f5a0f888d365bed1c8cfdb4` |
| accepted-native273-debug.json | `67efb3aedcc13aa0f0a7f3f0e567fbc9d22750fb756be5d57ce7f3caee646394` |
| accepted-native273-debug-test.log | `b2a39b4031ba2bbdf091ece2a58f2a55c3d3888e435faed087926a3920c392db` |
| readback-accepted273.json | `5e9af47d9ba1ebd75398a36f78173e0ac74099a18e906cab032d4b4ea20f4800` |
| portable-accepted273.log | `31414a8c783eb709d61c95da14b9e2b20401bef7f2faa2e013f6e7d9e32e7819` |

UTF8 BOM квитанций удалён только в памяти для JSON.parse; байты экспортов
не переписаны, перечисленные SHA включают их исходный BOM.

## Дополнительная compile-only проверка приложения

Лично разобран `app-accepted273.json`: terminaltrue/build0,
mode build-only-no-install, configuration Release/x64, source204 exact тот
же map. SHA квитанции
`3a4043b355f85099d5b466c8a3d43db427a4343a94c5ea0d9035ef25a3b65cc8`;
EXE `b8563fec0cf3b5599c61a27f67b6965731adc1e82d24b1a63305cf42544d6f97`,
PE0x8664, AEC provenance
`14bff774615f3dfa12188d53dea8fcad1a19fbcf7800f66faa46ce76c549556e`.
WebView2/Windows App SDK и actual pinned AEC commit
`846fe90a289f58b7c9303a635142aa2c7caa93e5` guard — build evidence main.
Прочитан `readback-app-accepted273.ps1`; его реальный terminal0 session51078,
204 source/native-export/EXE/PE MATCH и ownedprocess0 сообщены main. Отдельный
standalone app-readback JSON здесь не заявлен. D9025/external C4100 остаются;
zero-warning/security audit не утверждается. Compile-only не является
установкой, запуском, H250 или приложенческой полномочностью Pair.

## Ponytail и оставшиеся границы

Безопасного удаления/лишней зависимости/нового контроллера или общего framework
не выявлено. Tiny shared immutable comparison переиспользован Birth; physical
BOTH и codecs не продублированы новым сканером. Forced copies/throwing ctors
обоснованы действительными MSVC Debug failures и final all-ordinal retry,
не декоративная гибкость. **Lean already. Ship.** Это результат проверки
формы данного diff, не разрешение выпускать приложение.

SRC273-PRE-1 закрыт исходным post-openBlock cancel и exact final normal evidence.
Остальные narrow REQUIREMENTS допуски реализованы в разрешённых местах;
SOURCE blockers этой границы отсутствуют.

Открыты: standalone verified tombstone и обе конфликтующие копии; полноценный
recovery resolver/GC; matching bootstrap/queue/package intent и destination
full closures/retained roots; account/epoch/currentness/effect-owner,
startup/runtime adoption, typed mutation/transition/cleanup и actual absence.
T116/T117/T118/T119/T120, H250, legacy AAC counterexample/B1, physical Windows
x64, installed UI/audio/auth/upload/release и общая parity-цель не закрыты.
Fresh ALL50 в Round273 не выполнялся; прежний известный49/50 не назван GREEN.

Единственная запись reviewer — этот новый 0-checkbox отчёт. После записи
проверены неизменность всех прежних153 отчётов, tasks и четырёх frozen inputs.
