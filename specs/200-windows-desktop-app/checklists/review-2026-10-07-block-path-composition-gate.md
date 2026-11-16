# Round272 — четвёртое узкое REQUIREMENTS дополнение: композиция block path

Reviewer-owned, 0 checkbox markers. Дата: 2026-10-07.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserve.

## Решение до кода

**SCOPED REQUIREMENTS GO; C0 / H0 / M0 / L0** только для трёх прямых
blockName callers в `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp`:
readBlock (нынешняя строка323), readMigrationBirthEnvelope (341), writeBlock (362).
В каждом заменить expression `state_->directory / blockName(...)` на:

```cpp
const auto name = blockName(...);
std::filesystem::path path(state_->directory);
path /= name;
```

Передать именованный path в прежний State::read/create, с прежними аргументами.
В readMigrationBirthEnvelope оставить position0; в двух других — position/version.
Сохраняются все ранее принятые SHA256/blockName corrections.
Не разрешены изменения indexName, inspect, других path helpers, scanner,
API, формата, backend, quotas, flags, fault ordinals или assertions.
Это допуск требований к реализации, НЕ SOURCE GO и НЕ итоговая приёмка.

## Подтверждённая причина и статус доказательств

Reviewer лично прочитал и хешировал main record
`/Users/yshishenya/Documents/graf-f200-migration-block272.Y9LFrB/diagnostic272-after-block-stack.txt`:
SHA `675e24d7f7abc30d895fa91e7c9e500d41406c8b471eef0db0cb269ae7f2e41a`.
Это запись main об actual session29793/chunk61a779, не raw console export
и не выполнение VM reviewer. Запись подтверждает реальную Debug-компиляцию:
Birth cuts1..20 проходят классификацию/cleanup/retry; envelope cuts1..6 также;
envelope cut7 завершает процесс exit3. Стек содержит Alloc_proxy →
basic_string<wchar_t> → filesystem::path → readMigrationBirthEnvelope.
Доказан перенос rvalue wide string в path; последующие fault points не доказаны.

Лично прочитаны квитанция block-native272-debug.json и весь raw test log.
Квитанция SHA `8eaf6791e35de4acb961d94b4bbf755dd3abdc6f37a0d7304ccd08ee013b3355`:
terminal=true, configuration=Debug, architecture=x64, build_exit0/test_exit8.
Лог содержит5 PASS и Files FAILED17.58s; общий40.84s — сообщение main.
Release на этом снимке не запускался. Portable46/46 — отдельно по main,
не доказательство исправления Windows Debug fault.
source-block272.json SHA
`6dc05146cb2b609c722e88b38a740cc9fc3caa53048a3f476afb19b492b503c3`:
reviewer лично сопоставил все204 entries с canonical, mismatches0.

Main предоставил actual read-only header evidence chunk870ebb для установленного
MSVC14.44.35207/include/filesystem:641 path(string_type&&) переносит _Source;
648 path(const _Src&) использует _Convert_Source_to_wide;
772 Source operator/= строит path{_Source}, затем вызывает path append.
Reviewer не выполнял VM и не выдаёт эту выдержку за лично прочитанный полный
установленный header. Первое shell quoting failure127 не test result.

## Три вызова, ошибки и границы минимального изменения

Лично прочитаны текущий blockName и все три функции полностью с соседними guards.
Именованный const wstring исключает прежний rvalue string constructor на этих
call sites. Copy construction path из state_->directory и lvalue Source append
используют другую форму, чем прежний operator/ expression. Возвращаемое
blockName copy-prvalue при C++17 строит name напрямую; ручного разделителя нет.
operator/= может создавать временный path и выделять память: отсутствие
временных объектов/аллокаций НЕ заявляется. Потенциально бросающие публичные
перегрузки сами по себе не доказывают безопасность каждого внутреннего MSVC move.
Именно поэтому реальные Debug allocation cuts остаются обязательными SOURCE tests.

Имя остаётся block.<uint64 decimal position>.<uint64 decimal version>;
directory, filename, native path composition и confinement прежние. Имя относительное,
без пользовательского separator/root; path /= не заменяется ручной конкатенацией.
Проверки readBlock limit/exact/version/position/payload (319–322) остаются ДО path/IO.
Birth role/version/exact checks (335–337) также остаются ДО path/IO.
writeBlock writable/failed guard и native envelope validation (357–361) остаются
ДО composition/create. Нет дополнительного IO, reopen, rename, repair или scan.
ACL/reparse/hardlink/handle/share проверки State::read/create не меняются.

Оба reader function-try-block сохраняют bad_alloc → allocationFailed.
writeBlock сохраняет caught bad_alloc → state_->failed=true + allocationFailed;
create failure/readback failure и no-write fence не ослабляются. Новая directory
copy и временные объекты могут добавить allocations; они не исключаются из
quota/fault enumeration и не объявляются бесплатными. Path caps не меняются.
Это не исправление всех path producer и не разрешение расширить catch/flags.

## Scoped analyze и сохранение нормативов

Переиспользованы ранее лично полностью прочитанные guidance/constitution,
десять нормативных checklist, spec/plan/tasks/contracts и gate B с тремя
дополнениями. Свежие constitution/spec/plan/tasks/quickstart hashes совпали
с прочитанным baseline. T116:568 покрывает Storage.*, typed failure и safe
custody; FR-012/013/014/022, SC-005/006 и Constitution VI не изменяются.
Нового product choice, schema rule, uncovered task или C/H blocker нет.
code-reviewer проверяет guards/lifetime/error shape; ponytail-review: Lean already,
нет безопасного сокращения обратно до доказанно падающего expression.
Scoped analyze не переписывает нормативные артефакты; этот отдельный отчёт
разрешён только reviewer-owned write scope пользователя.

Files.cpp до предлагаемой правки SHA
`976ae89979f1227cf39aab21ee64a319d3a3125c80cb602d4f081de645f14e7d`;
Sha256.cpp SHA
`e7d6e8c5690c7bf5f1bc2f99f2b88a9dc9c284985eceb33d93458faec1da63a3`;
FilesTests SHA
`a20226b7e95b2a82676e460044cd85d1aa8968eaca744a3c781be7ea30e561f3`.
Tasks120/93/27, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Свежий YAML read: before/after analyze/checklist/implement по1 registered,
каждый disabled; все6 enabled0, reviewer dispatched0.

До отчёта141 markdown: десять текущих нормативных154 checked/0 open,
131 historical/context reports. Исторические открытые markers не новые criteria.
Inventory SHA sorted basename TAB SHA256 LF:
`04d3b6f21e7f470f0e332cab231deb36a64f891ab8bd4659ab17f176dcd910e2`.
Все прежние141 должны остаться byte-identical; новый отчёт содержит0 checkboxes.

## Что требуется после изменения, не нынешний PASS

Новый instrument-free frozen source: Debug и Release, реальная Birth/envelope
матрица обеих схем/subjects и все фактические allocation cuts, включая envelope7
и добавленные copy/append/proxy allocations. Проверить allocationFailed/no value,
cleanup/baseline/retry и существующие read/write confinement/error/failure fences;
writer после caught allocation failure остаётся failed, не получает unsafe retry.
Нужны новые source maps/receipts/raw logs/EXE identity и независимый readback;
прежние failures сохраняются. Последующий иной root требует отдельного доказательства,
этот допуск его не предрешает. VM/tests/code reviewer не запускает и не меняет.
MigrationPair/authority/app adoption, T116–T120, H250, AAC RED257/B1,
physical x64 и installed/interface acceptance остаются открытыми.
