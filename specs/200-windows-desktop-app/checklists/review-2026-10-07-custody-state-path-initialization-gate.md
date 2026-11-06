# Round273 — узкий REQUIREMENTS-addendum: два path-поля Files::State

Дата: 2026-10-07. Reviewer-owned, 0 checkbox, high-risk-product, existing T116 / #7444.

## Решение

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для исправленного предложения:
`State(const std::filesystem::path& root) : directory(root), trustedRoot(root) {}`,
`std::make_unique<State>(root)` и удаления последующего `state->trustedRoot = root`.
Применение только к `ProtectedCustodyFiles::State` в существующем Files.cpp.
Раннее предложение с несуществующим полем `root` НЕ является принятым API.
Это REQUIREMENTS разрешение до кода, НЕ SOURCE GO, Debug PASS или завершение Pair.

## Лично проверенная диагностика

Stand: `/Users/yshishenya/Documents/graf-f200-pair-iteration273.rkAoZP`.
Полностью прочитаны stderr, `diagnose-iteration273.ps1`, текущий State и его
uses/callers; разобраны receipt и source map. Reviewer не запускал VM/тесты.

Receipt `diagnostic-iteration273.json`: schema1,
`mode=temporary-diagnostic-not-acceptance`, terminal true, build0, test3.
Последний cut2 bytes16: `_Container_proxy_alloc → basic_string<wchar_t>
_Construct_empty/default ctor → filesystem::path default ctor →
ProtectedCustodyFiles::State::State → make_unique<State> → openImpl →
MigrationPair::read`. Cut1 — выделение самого State. Log не является PASS
matrix; завершение процесса и сведения MSVC относятся к actual main execution.

Main дополнительно сообщил personally read installed MSVC14.44 declarations:
filesystem1443–1444 iterator ctor noexcept; xstring708–709 default string ctor
noexcept и copy ctor716 без noexcept. Reviewer не читал VM headers лично;
эти declaration facts атрибутированы main. Они согласуются с прочитанным stack,
а не с предположением о причине в VM. Инициализация lvalue `root` выбирает copy
construction, не default construction с последующим assignment/движением.

Script проверяет frozen inputs, копирует snapshot, подменяет ТОЛЬКО внешнюю
FilesTests копию, обновляет timestamp, строит Debug/x64 и запускает
`--migration-pair`; затем экспортирует receipt/logs. Outer exit0 сам по себе
не PASS: тестовый статус берётся из receipt, здесь test3. Это диагностика,
не окончательная current-source validation и не независимый reviewer NTFS audit.

Source map содержит204 inputs; лично сопоставлены с canonical:203 совпадают,
единственное отличие — текущий worker FilesTests. Files.cpp совпадает.
Не заявляется полное current204 MATCH или applicability старого test snapshot
для окончательной matrix нового теста. Instrumented test отдельно от map.

## Точная трассировка initialization / exposure

| Участок current Files.cpp | Факт и требование |
| --- | --- |
| State:97–111 | Два непосредственных path members: directory, затем trustedRoot; поля root нет. Между ними tokenUser/descriptor/security/directories; порядок объявления не менять |
| openImpl:249–268 | Единственное создание этого State: после role/access/package и localPath guard. Context/writable задаются как прежде; затем initializeSecurity |
| initializeSecurity:113–129 | Работает с token/SID/descriptor/security, не читает directory/trustedRoot и не выполняет content open/create по placeholder |
| openImpl:268–296 | Root/ancestor locks и store identity получают explicit local path; методы inspect/lockDirectory/identity используют свои path arguments, не State::directory |
| openImpl:297–313 | directory безусловно заменён итоговым fixed role path до первого directory use: CreateDirectoryW/lockDirectory/id.bin. Только после identity checks possible success/new ProtectedCustodyFiles |
| Wrapper ctor:235; State users:334–633 | Wrapper принимает готовый unique State; public read/write/index/snapshot methods существуют только после successful factory. Placeholder не возвращается наружу |
| Packed owner:680–703, 873–908 | Friend получает уже успешно открытый Files. check использует trustedRoot для fixed store.id, directory для id.bin/content; ранняя инициализация не меняет эти итоговые пути |

`directory(root)` — лишь private временное значение, не authority или target
для IO. При каждом раннем возврате State уничтожается, не публикуется; destructor
не открывает directory. Нельзя переносить конечный role-path assignment за
первое использование или сохранять placeholder в опубликованном объекте.

Инициализация идёт по порядку объявления: сначала directory copy, после прежних
промежуточных членов trustedRoot copy, затем прежние handles. Если copy бросает,
уже созданные члены очищаются стандартным unwinding; initializeSecurity/native
lock/identity операции ещё не выполнялись. Constructor НЕ noexcept. Не применять
default-path+assignment или rvalue/move вместо явных copies. Остальные member
defaults/order и RAII resources не меняются; возможные их будущие noexcept cuts
этим gate заранее не разрешены и не объявлены безопасными.

## Нормативная граница и анализ

Сохраняются base custody §2:46–65: проверенный user-scoped root, opened-handle
confinement, запрет reparse/UNC/ADS/foreign JSON paths, user-only ACL/идентичность
до effects; создание новых IDs и repair не добавляются. Constitution III/IV/VI,
FR-012/013/014/022, задачи T116:568 / T117:569 / T118:570 покрывают существующий
storage prerequisite. Противоречий текущим spec/plan/contracts и нового product
decision не найдено. Публичного API/schema/dependency/target не добавляется.

Разрешены только constructor с указанными двумя copy initializers, передача
root в sole make_unique и удаление redundant trustedRoot assignment. Constructor
для native fields располагается внутри существующей Windows границы; unsupported
portable path остаётся прежним. Context, writable/failed, ACL, locking, Files
access/discover/create modes, errors/catches и root validators неизменны.

Не разрешены `ProtectedPackedCustodyOwner::State`, его path; Directory::path,
inspect/indexName/root_path/прочие helpers, allocator/quota/flags/cuts/seams.
No proof of queue/bootstrap/account/GC/admission/effects из placeholder/copies.
Нативные ошибки/отказ памяти остаются исходно классифицированными openImpl
catch handlers; отказ нового throwing copy должен быть проверен actual matrix.

## Gate inventory и будущая проверка

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
Существующие145 reports/checklists byte-identical предыдущему inventory:
10 текущих нормативных154 checked/0 open и135 прочих/исторических документов;
не превращать historical findings в новые normative markers.
Sorted basename<TAB>SHA256<LF> inventory145:
`3f38c98f86703632b483424cb9765afca8e3a083a7f71a582b80bc65e02d2f5b`.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Issue ownership T116/#7444 — прежний accepted owner, GitHub reviewer не проверял.
Before/after analyze/checklist/implement: каждый registered1/enabled0,
YAML лично разобран, dispatched0. Read-only prerequisites подтверждают Feature200.
Ранее полностью прочитанные guidance/norms переиспользованы с fresh hashes;
`code-reviewer`, `speckit-analyze` и memory skill прочитаны; анализ read-only.
Пользователь отдельно разрешил единственную запись этого нового report.

Main сохраняет текущий actual failure отдельно, выполняет fresh exact-source
Release/Debug allocation/cancel cuts, baseline cleanup/retry/last-owner lease
checks и старые shared Files/open/discover/packed regressions без weakening.
Portable applicability не доказывает native copy/proxy/ACL поведение. Следующий
actual stack требует отдельного решения, не расширенного скрытого допуска.
Окончательный SOURCE review отдельно после terminal evidence/readback.

## Hashes лично прочитанного снимка

| Файл | SHA-256 |
| --- | --- |
| canonical Files.cpp | `f4faa01d97ac14cf84db12e1447a6abbe9d37c3ac5fe17a8ae756e2f93a967ef` |
| canonical worker FilesTests.cpp | `0ca2a265214148995b785a578271a1d8cd46a9d7cbeb7d42eee4686cd9919aa0` |
| source-iteration273.json | `1c20bc05c3047d3462ce739d4b523ebba04a309fd4564a6ec99725e6a729e397` |
| diagnostic stderr | `da1c5d160288aa8b17fc2e95b9ada924eb443f0206173ad6bb3578c679ffd0a9` |
| diagnostic receipt | `29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d` |
| diagnostic-FilesTests.cpp | `b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57` |
| accepted iterator gate | `d288da14df873e48527ef4f5b0742b39c195d777be84c71c018bfd016d2581a3` |

После записи лично проверено сохранение всех прежних145 reports/markers и
исходных artifact hashes. Reviewer изменил только этот новый0-checkbox report;
code/tests/spec/plan/tasks/GitHub/VM/hooks/commit не изменялись. Full T116–T120,
H250, AAC legacy counterexample, physical x64/installed/app/release и SOURCE273
остаются открыты. Это допуск только двух actual State path initializations.
