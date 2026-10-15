# T116 — независимая проверка времени жизни pressure и конструкции reset343

Решение: SCOPED TEST-ONLY CONSTRUCTION GO для обычного вложенного scope в ProtectedCustodyFilesTests.cpp. Production CustodyBytes менять не требуется. Actual Release RED #9 достаточен как исходный отказ для этой правки; GREEN исправления ещё не получен. Запуск подготовленного harness пока NO-GO: два условия ниже должны быть проверены до копирования в native tree. HTTP control-types343 остаётся отдельным заблокированным срезом, не заменяется reset343.

## Проверенные границы

Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`, branch `codex/200-windows-followup`, HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, до отчёта235 dirty entries. Прочитаны AGENTS/router guidance, активные spec/plan/tasks/quickstart/constitution и применимые custody contracts; использован code-reviewer. Это независимая проверка существующего high-risk-product среза, не понижение его требований до low-risk.

Source342 manifest `/Users/yshishenya/Documents/graf-f200-wipe342.fVaWAY/source.json`: `8f9cbf93de54af8d67eb8e03cba73f12598546da1646dcd822825c798a7fa62a`. Все209 canonical и frozen inputs повторно сверены, расхождений0. Normative9 unchanged относительно таблицы текущего analyze `review-2026-10-10-protected-http-integration-gate.md`, SHA `51af545d0cc8a4dc31c5ea0d65595f08dcb6be2c8a4e2194ee3c3d8da90174e0`.

Повторный скан186 reviewer Markdown:29 с checkbox items,420checked/0unchecked. Новых checkbox items нет; исторические SOURCE/runtime findings и приёмки не переписаны и не объявлены повторно выполненными. T116 открыт; live GitHub в этой проверке не перечитывался и не менялся.

## Причина и минимальная правка

В FilesTests:3452–3458 `pressure.reserve(limit-usedBytes())` занимает оставшийся бюджет при size0. Новый CustodyBytes::operator=(initializer_list) вызывает assign(empty), который не освобождает capacity. В этом случае oldSize0, wipeTail ничего не делает; allocation остаётся честно учтённой. Это объясняет отказ следующего parent reopen. Actual лог доказывает assertion parent.ok(), но не печатает конкретный error повторного reopen; диагноз удержания capacity основан на исходниках, не на несуществующей дополнительной runtime-трассе.

Разрешённая конструкция будущего единственного test delta:

```cpp
{
    CustodyBytes pressure;
    inject(FileFault::none);
    afterRead = [&] { if (reads == lastRead) pressure.reserve(CustodyOwnedMemory::limit-CustodyOwnedMemory::usedBytes()); };
    const auto failed = ProtectedCustodyQueueInput::read(*parent.value, cancelled); afterRead = {};
    assert(!failed.ok() && failed.error == CustodyFileError::allocationFailed && !writes && !renames);
} // pressure и его Debug proxy уничтожены до reopen.
parent.value.reset();
parent = ProtectedCustodyBootstrapPair::read(f.root, cancelled); assert(parent.ok());
assert(ProtectedCustodyQueueInput::read(*parent.value, cancelled).ok());
```

Setup, lastRead, величина reserve, callback trigger, failed/assert и оба reopen assertions остаются прежними. Callback снимается внутри scope до уничтожения pressure; failed уничтожается раньше pressure. Sticky parent не используется повторно: после освобождения давления остаётся прежнее parent.value.reset() и создание нового owner. Никакого нового optional, helper, production API, выделения временного пустого контейнера или Debug proxy под полной квотой не нужно.

CustodyAllocator::deallocate noexcept обнуляет всю retiring allocation по capacity до free и только затем снимает charge. Разрушение контейнера освобождает также существующий Debug proxy, не создавая замену. Обычный scope использует именно этот уже существующий путь. Не допускаются ручное уменьшение счётчика, увеличение64MiB, ослабление assertions или clear() вместо реального release.

Поиск CustodyBytes охватил35 Windows .cpp/.h; проверены кандидаты `={}` и явные способы освобождения. Найденный прямой empty-list reset, от которого ожидается release, — pressure:3457. `indices = {}` в Metadata:1638 имеет тип std::array<CustodyBytes,2>: присваивание массива использует move assignment его элементов, а не их initializer_list operator. STATSTG outputs, callback/counter/context resets — другие типы. Существующие release места используют scope/raw allocator deallocate, optional/shared owner reset, swap либо clear+shrink_to_fit. Их полная безопасность при любом состоянии квоты здесь заново не принимается. Соседний FilesTests:3376 уже освобождает давление scope до такого же fresh-parent retry; аналогичный подход есть Codec:779, Files:4506–4522 и NativeCaptureStorageIntegration:914–920.

MutationBudget Codec:198–255 требует непустого initializer-list присваивания внутри capacity при usedBytes==limit, без смены storage/capacity, с немедленным wipe хвоста. Поэтому удалять initializer-list overload или превращать обычное присваивание в создание временного контейнера нельзя. Empty-list release в общем типе был бы отдельным изменением семантики, не нужным для данного отказа; `shrink_to_fit` не является обязательным освобождением по стандарту. Выбранная RAII-правка сохраняет production in-place assignment, full-quota mutation и noexcept cleanup без новой зависимости от реализации shrink.

Первичные справочные источники: [правила предпочтения initializer_list](https://eel.is/c++draft/over.ics.rank), [vector capacity/shrink_to_fit](https://eel.is/c++draft/vector.capacity), [Microsoft STL vector: destructor/_Tidy/deallocate](https://github.com/microsoft/STL/blob/main/stl/inc/vector). Microsoft main — справочная реализация, не доказательство версии установленного MSVC; фактический Debug GREEN остаётся обязательным.

## Actual RED и подготовленный harness

Прочитан текущий внешний `/Users/yshishenya/Documents/graf-f200-regression342.KzxiQ7/Release-ctest.stdout`: `9/53 Test #9: ProtectedCustodyFilesTests ... Failed 60.27 sec`, `Assertion failed: parent.ok()`, line3458. Codec #3 Passed4.21sec. Наблюдаемый stdout SHA `e5724f05fbb3afb40bd1c259ae670ff2f23d1ce1a18313a1cc81685d8d468071`,8206B, mtime2026-10-10T14:59:30.002Z — снимок незавершённого журнала, не финальная квитанция. При чтении native.json отсутствовал. Session93427 не опрашивалась и не затрагивалась; полный53 Release/Debug PASS, terminal и idle не заявляются.

Прочитаны, но не исполнены external reset343:

- prepare.mjs SHA `43937fac4bcf1020aa6f4ebd9079731439471916eb64af0a01de1213ea55b2f0`;
- run.mjs SHA `2818c5478e03c1eee7ef689a44479cd34c2e80a00f903397f78eee78e5578517`;
- каталог `/Users/yshishenya/Documents/graf-f200-reset343.bulm6q`.

Reuse validate.ps1342 сохраняет53 tests для Release и Debug, assertions, уникальный regression343 TEMP, source verification, no-kill timeout и последующий RequireIdle. Native preflight выполняет RequireIdle, проверяет прежние209 native inputs по342 и новые canonical/frozen inputs, затем копирует только FilesTests и вызывает VerifySource. Это правильная граница копирования после завершения прежнего запуска.

Два условия допуска, пока не выполненные prepared code:

1. Связать квалифицированный terminal RED с его квитанцией: проверить receipt.source_manifest_sha256 против pinned342, найти completed Release-ctest run/exit8 и сверить SHA Release-ctest.log с его log_sha256. Сейчас prepare проверяет stage/terminal/completed/последний exit8 и текст assertion, но не эти связи. Проверить также строку Failed именно #9/FilesTests в связанном журнале; прочие отказы полного запуска не объявлять устранёнными этой правкой.
2. Проверить точный test diff до native copy. changed.length==1 ограничивает файл, но допускает любые изменения его assertions/quota/fixtures. Нужна либо проверка exact expected scope-only transformation от frozen342, либо независимое принятие фактического diff, привязанное к хешу единственного изменённого FilesTests. Будущего source delta сейчас нет, его приёмка не выдумывается.

Повторный искусственный RED для lifetime-правки не нужен: actual #9 уже проверяет требуемый retry после снятия давления. Он не разрешает произвольную production правку и не является HTTP type-oracle RED. После terminal исходного запуска и actual idle main может внести только одобренный scope delta и получить новую209 manifest binding; source342 тогда становится исторической исходной базой, не текущим GREEN. Требуются фактический Files Release/Debug GREEN и завершение заявленного full53 regression gate на новом источнике; старый wipe342 остаётся историческим доказательством своего ограниченного среза. До этого HTTP343 не редактировать/не запускать.

Reviewer не менял prod/tests/spec/tasks/markers/GitHub/external harness, не запускал VM/jobs/builds/tests/cleanup. Единственная запись — этот новый append-only отчёт. Полный Windows parity, ALL/T116, hardware/installed/release gates остаются открытыми.

## Уточнение по последнему scoped запросу

Итог: GO на ровно описанную scope-only test construction. Existing full Release #9 принимается как уже qualified actual RED; повторно доказывать его или создавать другой RED не требуется. Pressure, callback и failed/assert помещаются во вложенный scope; afterRead снимается внутри, destructor вызывается до прежних parent.reset/reopen assertions. Production initializer-list и mutationBudget остаются без изменений.

Повторно прочитанный prepare343 уже содержит PRIOR_RED_IDENTITY и PRIOR_RED_LOG_CHANGED: pinned source342/harness342 и receipt log_sha256 проверяются. Соответствующее первое замечание выше снято; исходное описание этих отсутствующих проверок не относится к этой прочитанной версии. SHA prepare/run при повторной фиксации: `43937fac4bcf1020aa6f4ebd9079731439471916eb64af0a01de1213ea55b2f0` / `2818c5478e03c1eee7ef689a44479cd34c2e80a00f903397f78eee78e5578517`.

Единственное оставшееся условие перед native copy: фактический FilesTests diff должен быть именно приведённым scope-only изменением с неизменными assertions/quota. Source всё ещё содержит pressure={}; поэтому этот ещё не внесённый diff не принят как SOURCE/GREEN. Prepare проверяет имя единственного изменённого файла, но не точный diff: main должен отдельно сверить его с одобренной конструкцией либо добавить exact-delta guard. Это не blocker конструкции RAII, а граница её допуска: произвольный FilesTests delta данным GO не покрывается. RequireIdle перед native copy и source209 checks в prepare/run сохранены. Новых аудитов specs/reports, записей source и VM действий в этом уточнении нет.

## SOURCE/construction follow-up после freeze343

SCOPED SOURCE/CONSTRUCTION GO343: блокирующих замечаний по фактическому scope-only diff и подготовленному harness нет. Это не runtime GREEN и не приёмка полного53/T116/HTTP control-types.

Повторно сверены manifest keys и все209 canonical/frozen343 inputs: exact, расхождений0. От frozen342 отличается только `apps/windows/Tests/GrafWindowsCoreTests/ProtectedCustodyFilesTests.cpp`; остальные208 inputs, включая production и Codec mutationBudget, неизменны. Manifest343 SHA `07f4f8cb1135e93ad0c42a01a79a79405332fb07c836f2f084d46fda30c08d42`. FilesTests343 SHA `f057448609d3513f27d72de431f20dfcbb4ed62ffb6a7c098f22c7ba607d2df9`.

Прочитан единственный diff: обычные braces вокруг pressure/inject/callback/read/failed assertion; pressure={} удалён, parent.value.reset() остаётся сразу после scope. Величина reserve, reads==lastRead, снятие afterRead, исходный allocationFailed/!writes/!renames assert и оба reopen assertions сохранены. Независимое сравнение всего файла с oldText.replace(before,after) подтвердило ровно этот delta и единственность old block. Все строки assert во всём FilesTests неизменны, за исключением отступа. Pressure destructor срабатывает после quota-assert, но до reset/reopen; production initializer-list/mutationBudget не затронуты.

Прочитаны актуальные prepare/run и frozen validate343. Exact guard ONLY_REVIEWED_SCOPE_DELTA_ALLOWED выполняется до freeze/copy и проверяет весь FilesTests против единственной разрешённой замены. Квалификация RED использует `/9\/53 Test\s+#9: ProtectedCustodyFilesTests[^\n]*Failed/`: два пробела CTest корректно допускаются. Проверки source342/harness342, receipt/log SHA сохранены. Прежнее условие точного diff теперь выполнено и снято.

Generated validate343 diff относительно validate342 содержит только native preflight idle/old209/new209/single-file copy/VerifySource, prior RED receipt/scope fields и уникальный TEMP regression343. Цикл Release/Debug,53 tests, требования build/ctest exit0 и full53 PASS, source/idle checks и no-kill timeout unchanged. SHA prepare `c4a8d6aea4d954fbc3688d5912b5434e1b9bb4335a3a800b3ad594f81c49c00b`, run `2818c5478e03c1eee7ef689a44479cd34c2e80a00f903397f78eee78e5578517`, validate `3bf4e61f82dfbca1ba3353d3e59ec1c6297fd6d46c0f5b2828a103a53683664c`.

Original342 native.json прочитан: SHA `2cb11cd4bc351591f7db2acd3e545c154973a7b87ff6a9aaedce1dfde49d9d5d`, terminal=true/native_completed=false/stage=test-Release; completed Release-build exit0, Release-ctest exit8. Связанный по receipt SHA журнал подтверждает52/53 и единственный FAIL #9 FilesTests с parent.ok()/line3458. Сохранённый original Release-last-test.log SHA `26f04586cc40bf596c4bf56dd70e325f891c0a911cdf5ab9d280a034b960df7b` также сверён. Это qualified исходный RED, не GREEN343. Предоставленный main terminal/idle preflight — историческая граница перед запуском343; текущий idle здесь не заявляется.

Native343 уже запущен main; reviewer его не опрашивал, не запускал и не менял. Runtime GREEN343 ещё не проверен. Запись ограничена этим append-only дополнением, source и другие reports не редактировались. Никакого повторного полного аудита specs/reports или переноса старого runtime acceptance на343 не выполнялось.
