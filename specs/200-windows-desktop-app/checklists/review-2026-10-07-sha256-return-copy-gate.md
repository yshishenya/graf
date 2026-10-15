# Round272 — второе REQUIREMENTS-дополнение: hexDigest return copy

Дата: 2026-10-07. Независимый reviewer, high-risk-product, существующая T116.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty preserve.

## Узкое решение до правки

**SCOPED REQUIREMENTS GO; C0 / H0 / M0 / L0** только для строки возврата
общего существующего hexDigest в `apps/windows/RecApp/Storage/Sha256.cpp`:

```cpp
return result;
// заменить на:
return std::string(result);
```

Принятый empty-count constructor `std::string result(std::size_t{0}, char{});`
сохраняется. Никаких иных producer изменений, новых helper/wrapper/backend,
compile flags, схем, targets, лимитов или рефакторинга этот допуск не разрешает.
SOURCE completion приостановлен; это не SOURCE approval или новый runtime PASS.

## Доказательство причины и граница доверия

Reviewer лично прочитал и хешировал внешнюю запись main
`diagnostic272-after-sha-stack.txt`, SHA
`4851d7bf58cf86b75f84ee82e814da85805401df2b21743d683c762c00e5f52f`.
Файл находится в stand `graf-f200-migration-corrected272.MqWbne`.
Это запись фактического main tool5762a2, не raw console dump и не reviewer VM run.
Первый диагностический запуск с пропущенной компиляцией не используется как
доказательство; запись отдельно указывает последующую проверку SHA/timestamp,
реальную компиляцию FilesTests и диагностический результат.

После count constructor schema1/queue Birth cuts1/2 возвращают allocationFailed,
retry0 проходит; cut3 завершается exit3. Стек: operator new → allocator
Container_proxy → Alloc_proxy → basic_string move constructor → hexDigest
named return result → NativeHash::finish → sha256Stream → digest → Birth.
Это следующий доказанный root: необязательное NRVO не произошло, implicit move
вызывает noexcept string move, а его Debug proxy allocation не допускает выхода
bad_alloc к существующему обработчику Birth.

Ранее лично прочитанные corrected native квитанция/raw log показывают
Debug build0/test8, пять из шести тестов PASS, Files FAILED; corrected Release
не запускался. Sha256Tests PASS0.18s подтверждает обычные bytes, не все fault cuts.
Первый root исправлен, но полная native Birth/envelope матрица ещё не принята.

## Семантика C++ и ограниченная стоимость

Лично проверены действующие build settings: CMake CXX_STANDARD17 required,
GrafWindowsApp.vcxproj stdcpp17; общий props default stdcpp20. Все поддерживают
C++17 guaranteed copy elision для prvalue возвращаемого точного std::string.
`result` внутри std::string(result) — lvalue; выбирается потенциально бросающий
copy constructor, не string move. Сконструированный prvalue становится объектом
результата непосредственно, без последующего implicit named-local move в этом
return. Конструктор самого копирования может отказать; bad_alloc должен выйти
на уже существующую границу обработки, без пустого или выдуманного digest.

Копируется ровно64 lowercase hex-символа. Прежние reserve64, hex digits/цикл,
provider, string API, SHA-256 bytes, identity/deletion UUID/reminder keys,
artifact/range hashes и порядок вызывающих операций не меняются.
Стоимость — дополнительная ограниченная копия 64 символов с обычным хранением
терминатора и STL proxy; Debug может иметь отдельные proxy/buffer allocations.
Не заявляется фиксированное число выделений для каждой STL-конфигурации.
Их нельзя исключать из actual all-cuts. Это не безаллокационный formatter и не
новое доказательство общей charged RAM domain защищённого приложения.

Предпочтительный минимум — эта строка. std::move(result) оставил бы доказанный
noexcept move; рассчитывать на NRVO или менять compiler flags нельзя. Новый
wrapper/formatter/hash backend и обход ordinal не нужны и не разрешены.
Это не общий допуск всех остальных return/move внутри shared pipeline.

## Применимые нормы и сохранённые артефакты

Переиспользованы лично полностью прочитанные guidance/constitution, все десять
действующих нормативных checklist и scoped analyze принятого B и первого
SHA-дополнения. Их актуальные hashes/context проверены в предшествующей проверке;
сейчас повторно проверены HEAD/branch/tasks, текущая строка и build settings,
новая диагностика и инвентарь139 прежних файлов. Все Windows SHA public caller
paths прочитаны при первом дополнении; единственная новая семантика здесь —
способ построения того же string result. Большие historical validation не нужны.

T116:568 прямо включает Storage/Sha256.*, FR-012/013/014/022 и SC-005/006;
Constitution VI требует independent gate и реальное failure evidence.
Нового product choice, task, нормативной неоднозначности или противоречия нет.
Migration.v1/v2 shapes/Birth stamps, logical bytes, caps, native DPAPI/CNG и
запрет plaintext/empty fallback остаются прежними. Общие calling paths:
portable identity/reminder/deletion/upload и native stream/file custody/v5/
transport; binary sha256ProtectedStream finish(array) этот hex return не вызывает.

Исходный gate B SHA
`f85821923fd47cbb876d4998804aeefd1c92fff742e89fd3a0889f0f4fb17516`;
первое SHA gate SHA
`6867e324dbcbedcbc45a9af056873eb782cc8663fce5321f6f0f1cbaec8f5497`.
Sha256.cpp до данной строки:
`3c21961487babdf4221a0d57fb0af2a9820dd3f81177ec5a61efc71c49cb1f2e`.
Tasks120 total/93 checked/27 open, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Hooks before/after analyze/checklist/implement сохраняют по1 registered disabled,
0 enabled/0 dispatched; reviewer hooks/commit/GitHub не исполняет.

Baseline139 markdown: десять нормативных154 checked/0 open,129 исторических/
контекстных отчётов. Historical markers не новая обязанность этой строки.
Inventory SHA (sorted basename TAB SHA256 LF):
`c860a033fa8073599367e51d000e148c340ec2eb28bcc0ebff2f88d0ec3851ee`.
Новый файл имеет0 checkbox markers; все прежние139 сохраняются byte-identical.

## Последующий SOURCE gate, пока не выполненный

Сохранить все actual failure ordinals, quota, native Debug proxy allocations,
assertions и warning flags. Удалить временную диагностическую instrumentation
из проверяемого native снимка; canonical tests не менять ради PASS. Новый
frozen map должен включать именно две согласованные строки SHA и принятый B.
Повторить полную Birth/envelope matrix обеих схем/subjects с allocationFailed,
no value, cleanup/quota baseline/retry; fresh native Debug и Release, SHA known
vectors/read errors и portable suite. Лично проверить новые receipts/raw logs,
source identity и EXE readback перед SOURCE решением.

Если следующий ordinal обнаружит другую причину, сначала стек/диагноз, затем
отдельный узкий допуск. Непроверенные blockName/wstring/path не входят сюда.
Старые Debug failures остаются неизменными; legacy AAC RED257/B1, T116–T120,
MigrationPair/queue authority/app adoption/H250/physical x64/installed/release
не закрываются. Reviewer добавляет только данный отчёт, не меняет product/tests/
spec/plan/tasks/old reports/markers и не исполняет VM/сборки/тесты.
