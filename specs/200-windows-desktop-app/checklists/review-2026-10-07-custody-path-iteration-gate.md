# Round273 — узкий REQUIREMENTS-addendum: обход native пути без path iterator

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing T116 / #7444.

## Решение

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для устранения двух
`relative_path()` / `path` iteration loops в `ProtectedCustodyFiles.cpp`:
`localPath` и обхода root ancestors в `openImpl`. Допуск относится к точному
предложению ниже, а не ко всем filesystem операциям или готовности MigrationPair.
Это разрешение реализации и последующей проверки, НЕ SOURCE GO/Debug PASS.

## Проверенный исходный отказ

Лично прочитаны полный `diagnostic-pair273-stderr.log`, scalar receipt
`diagnostic-pair273.json`, текущие оба цикла и единственный caller `localPath`.
SHA диагностической копии теста проверен отдельно. Reviewer не запускал VM,
diagnostic executable или тесты; это анализ экспортированного результата main.

Receipt: `mode=temporary-diagnostic-not-acceptance`, `terminal=true`,
`build_exit=0`, `test_exit=3`. Последний cut4, bytes16, даёт цепочку:
`_Container_proxy_alloc → basic_string<wchar_t> default construction → path
default construction → _Path_iterator construction → path::begin → localPath
→ Files::openImpl → MigrationPair::read`. Это соответствует сообщённому main
прекращению процесса в noexcept iterator construction при отказе памяти.
Сам log показывает stack/последний cut, не заменяет исследование declarations
MSVC и не является пройденным failure-matrix тестом.

Cuts1–3 напечатаны раньше; из этого не выводится полный успех последующих cuts.
Release6/6 PASS64.70s и предшествующий Debug Files failure — сведения main,
не свежая reviewer execution и не основание объявить текущий Debug зелёным.
Отказ связан с конкретным iterator flow; гипотеза «это VM» здесь не требуется.

## Разрешённый минимальный diff и обязательная эквивалентность

1. `localPath` сохраняет исходный guard **до** доступа к prefix/components:
   длина4..30000 native code units, ASCII буква drive, `:` и `\` в positions1/2;
   NUL, `/`, дополнительный `:` и завершающий `\` отвергаются. UNC/device,
   relative и root-only формы не становятся допустимыми.
2. После guard scan только `std::wstring_view` существующего `path.native()`,
   начиная с offset3. Не выделяется список компонентов; каждый проход продвигает
   cursor, верхняя граница — уже проверенная длина. Interior пустые separator
   runs пропускаются, как компоненты исходного filesystem iteration. Каждый
   непустой slice по-прежнему отвергается при `.`/`..`/suffix `.`/suffix space.
   Нельзя добавлять ASCII-only правило для имён: native UTF-16 сохраняется.
3. Drive argument — локальный `wchar_t drive[4] = {text[0], L':', L'\\', 0}`.
   Сохраняются обе проверки `GetDriveTypeW == DRIVE_FIXED` и
   `GetVolumeInformationW` / `FILE_PERSISTENT_ACLS`. Это замена временного
   `root_path().wstring()`, не новая проверка тома и не новый native доступ.
4. В `openImpl` остаётся начальный `root.root_path()` и его первый directory
   lock. Второй короткий view scan использует валидированный `root.native()`
   offset3; на каждый непустой slice создаётся **named const**
   `std::filesystem::path part(name)`, затем существующий accumulator `path /= part`.
   Не применять rvalue path iterator/operator-return цепочку или ручную
   конкатенацию separators. Source native string живёт весь scan; accumulator
   отдельный и не инвалидирует view.
5. Сохраняется `lockDirectory(path, path == root, false)` для каждого ancestor
   в прежнем порядке. Не заменять `path == root` текстовым сравнением и не
   пропускать промежуточные каталоги. Все последующие `.custody-v1`, role/store/
   object ID, handle inspection, ACL/confinement/hardlink/reparse и retained
   locks остаются исходными, включая различие private и ancestor ACL.
6. Access/create/discover modes, sticky failure, errors/catches, pin/job/budget,
   cancellation, DPAPI и metadata selection не меняются. No repair/fallback,
   schema/path policy/cap widening, owner registry или новая dependency.
7. Допустим прямой include `<string_view>`, если он нужен для самостоятельной
   компиляции. Два коротких ограниченных scan sites не требуют общего parser,
   нового класса или helper framework; это минимальное устранение механизма.

**Не разрешены** изменения `State` default path, `inspect`, `indexName`, других
path/helper producers, wrappers/backend/flags и ослабление allocation cuts.
Сам факт, что следующий cut может обнаружить иной noexcept constructor,
не даёт предварительного допуска к его исправлению. `root.root_path()` и
named path construction/append должны быть проверены новой actual matrix;
этот gate не обещает отсутствие всех следующих Debug proxy failures.

## Нормативная трассируемость / scoped analyze

| Норма / source | Что сохраняется |
| --- | --- |
| Base custody §2:46–50 | Проверенный user-scoped root; запрет reparse/ADS/UNC; actual opened-handle confinement; user-only ACL, без изменения всего профиля |
| Base custody §2:52–65 | Fixed store/object identity и внутренние имена; не JSON-путь или внешний root |
| Constitution III/IV/VI; FR-012/013/014/022 | Защита данных, честный отказ, отсутствие новых эффектов и independent high-risk review |
| T116:568, T117:569, T118:570 | Исправление shared storage prerequisite; full pipeline/recovery/acceptance не закрываются |
| Files.cpp:48–62, 249–307 | Только два iterator sites и drive temporary; actual native lock/identity flow неизменён |
| Accepted Round273 MigrationPair gate | Direct-only own-intent scope сохраняется; tombstone/conflict resolver и effect authority не реализованы |

Проверено соответствие текущих spec/plan/tasks и принятых contracts; новой
schema, продуктового решения, непокрытой нормы этой границы или C/H ambiguity
не найдено. Это узкий analyze, не повторный whole-application acceptance.
Использованы ранее полностью прочитанные guidance/constitution/checklists
с актуальной проверкой hashes; `speckit-analyze` полностью перечитан.
Read-only prerequisites подтвердили активную Feature200; инструмент поддерживает
`--require-tasks --include-tasks`, но не `--require-spec` из инструкции навыка.
Сам анализ read-only; отдельная запись этого report явно разрешена пользователем.

## Что требуется перед SOURCE approval

Main сохраняет failed receipts и diagnostic copy отдельно; canonical без
DbgHelp/temporary instrumentation. Новый exact-source native Release/Debug
должен сохранить все actual allocation/cancellation ordinals, cleanup/retry,
retained lease assertions и старые regression tests. Не исключать proxy cuts.
Проверить path equivalence в существующем target/fixture: drive register,
Unicode components, interior repeated separators, invalid root/relative/UNC/
device/slash/NUL/ADS/`.`/`..`/trailing dot/space/separator и cap boundaries;
сопоставить ancestor lock order, final private-root check и native confinement.
Заявлять только реально исполненные cases; source ordering proof не runtime PASS.
Portable checks не принимают native iterator/ACL/DPAPI поведение.

## Identity, inventory и неизменность

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
`codex/200-windows-followup`; HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`;
dirty сохранён. До report144 files: 10 текущих нормативных, 134 прочих/
исторических. Normative154 checked / 0 open; historical findings не новые norms.
Sorted basename<TAB>SHA256<LF> inventory144:
`1cdfb7abbdf0b9d4d8aa65f810556921b99f695e4d1f63a9547b46761f2988c5`.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
#7444 OPEN — свежая проверка main, не личный reviewer GitHub audit.
Все шесть before/after analyze/checklist/implement hooks: registered1, enabled0;
YAML лично разобран, dispatched0. Никакого commit/hook execution.

| Снимок | SHA-256 |
| --- | --- |
| Files.cpp перед разрешённой правкой | `c62a6bcd879a678178ff3b5da311b5434b2d618dc61648d1bb3b7ba769a6384c` |
| external diagnostic stderr | `9c0af0e225c243fcc56443212ed888e3a5789b21da30d4e324ccf00d088d9f21` |
| external diagnostic-FilesTests.cpp | `b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57` |
| prior Round273 requirements gate | `5435475dfc24d8f3a655c3bf343dfddf762362f9a1265d0cb4e70f338e50ba81` |
| base custody contract | `ec93d11c474cb970d57c2324518d541cd9fb3e7bb7f2f807d63d612ad878624a` |
| packed custody contract | `a1dedd9d5b7ce02e4a6c200a300b0423bcada82192217e2a79f9773428c4a7b5` |

После записи лично проверена неизменность всех предыдущих144 reports/markers;
единственный добавленный report — этот, без checkbox. Code/tests/spec/plan/tasks,
GitHub/VM/profile/audio/commit не изменялись reviewer. SOURCE273, full T116–T120,
H250, legacy AAC counterexample, physical x64 и installed/product/release
acceptance остаются открыты. Этот GO позволяет только описанную iterator правку.
