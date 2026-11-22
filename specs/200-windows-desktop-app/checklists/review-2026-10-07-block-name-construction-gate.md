# Round272 — третье REQUIREMENTS-дополнение: blockName construction

Дата: 2026-10-07. Независимый reviewer; high-risk-product, существующая T116.
Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserve.

## Решение до правки

**SCOPED REQUIREMENTS GO; C0 / H0 / M0 / L0** только для тела существующего
TU-local `blockName(uint64_t position, uint64_t version)` в
`apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp`:

```cpp
std::wstring name(L"block.");
name += std::to_wstring(position);
name += L".";
name += std::to_wstring(version);
return std::wstring(name);
```

Это заменяет только цепочку operator+ в прежнем return. Обе принятые SHA-строки
сохраняются. Не разрешены изменения indexName, nextBlockVersion prefix,
filesystem path helpers/inspect, других producer, API, schema, parser, wrapper,
backend, compiler flags, quotas или assertions. SOURCE completion удерживается.

## Причина и ограничения доказательства

Лично прочитана и хеширована запись main `diagnostic272-after-copy-stack.txt`
во внешнем stand `graf-f200-migration-copy272.b0XWqv`, SHA
`dd9b5e557f2cea62a99149e23ae57551fef5b9621d39746e11c67f7acdcd3c74`.
Она фиксирует actual native tool a035f4 после проверки SHA диагностической копии,
обновления её timestamp и реальной компиляции. Это запись main о запуске,
не raw console export и не выполнение VM reviewer.

В первом schema1/queue fixture Birth cuts1..20 классифицированы allocationFailed,
baseline cleanup и retry0 проходят. Envelope cuts1/2 — to_wstring constructions —
также отказ/retry проходят. Envelope cut3 завершился exit3. Стек: operator new →
allocator Container_proxy → Alloc_proxy → basic_string<wchar_t> move constructor →
std::operator+ → blockName → readMigrationBirthEnvelope → invokeEnvelope.
Доказана конкретная noexcept move внутри operator+, не общий дефект всех path.
Диагностика первого subject не является полной обеих схем/subjects матрицей.

Прежний copy-native Debug результат остаётся build0/test8, 5/6 PASS, Files FAILED,
42.14s по main. Reviewer лично прочитал его квитанцию и полный raw log;
source map204 совпал с copy map. Copy Release не запускался. Portable46 PASS
не закрывает Windows-specific fault. Старые failures/exports не переписываются.

## Корректность минимальной формы и вызывающие пути

Лично прочитаны blockName, все три direct call sites и окружающие проверки:
readBlock:319, readMigrationBirthEnvelope:337, writeBlock:358; State::read/create,
block version scanner и no-write/sticky-failure handling также сверены.
Построение начинается потенциально бросающим literal string constructor;
operator+= добавляет исходные значения без цепочки rvalue operator+.
Завершающий std::wstring(name) копирует lvalue потенциально бросающим copy
constructor. При действующих C++17/C++20 settings prvalue строится напрямую
в возвращаемом объекте, не зависит от необязательного NRVO named-local return.
Отказ должен доходить до existing bad_alloc catch, а не terminate в move.

Точное имя прежнее: block.<position decimal>.<version decimal>, без padding,
новых разделителей, signed conversion или ведущих нулей. Используются те же
to_wstring для обоих uint64. Максимум47 wchar units без терминатора при двух
20-digit uint64; это арифметическая граница этой строки, не новый path cap.
Дополнительное копирование имени и Debug proxy allocations ограничены, но
не исключаются из fault ordinals и не объявляются безаллокационными.

Файловый формат, entropy, версии/позиции, exact payload/envelope bounds,
State::directory, ACL/reparse/hardlink/handle/share проверки и path confinement
не меняются. Reader bad_alloc возвращает allocationFailed; writeBlock сохраняет
существующий sticky failed=true при caught bad_alloc. Нет нового write/delete/
rename/scan/repair, изменения IO порядка или разрешения на повтор writer после
failed. Прямого purge caller у TU-local blockName нет: сохранение exact names
не меняет имена, распознаваемые прежним scanner/поздней очисткой. Их алгоритмы
и полномочия этим дополнением не принимаются и не меняются.

## Scoped analyze, нормы и исходные hashes

Переиспользованы лично полностью прочитанные guidance/constitution, десять
нормативных checklist и актуальные spec/plan/tasks/contracts из gate B и двух
SHA-дополнений; исторический аудит не повторялся. Новая source проверка ограничена
подтверждённой причиной и общими direct call sites. T116 прямо покрывает Storage.*,
FR-012/013/014/022, SC-005/006 и typed protected failure; Constitution VI сохраняет
independent gate. Нового product choice, uncovered task или C/H ambiguity нет.
Все migration.v1/v2/Birth и shared budget нормы сохраняются; helper не proof.

До правки Files.cpp SHA
`484e81430bc57e2c15e130179d5a7a740f0a9b821bf6b89801dc3df7442a824c`;
Sha256.cpp с обеими принятыми строками SHA
`e7d6e8c5690c7bf5f1bc2f99f2b88a9dc9c284985eceb33d93458faec1da63a3`.
Tasks120/93/27, SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Прежние B/SHA gates immutable; не расширяются на другие producer автоматически.
Hooks before/after analyze/checklist/implement: по1 registered disabled,
все6 enabled0/dispatched0. GitHub/commit/actions не исполнялись reviewer.

До нового отчёта140 markdown: десять нормативных154 checked/0 open и130
исторических/контекстных отчётов. Historic markers не новые criteria этого fix.
Inventory SHA (sorted basename TAB SHA256 LF):
`a2753deed058357d91e9f1bbda447b2f118e2409df49de542041252a5d2a3904`.
Этот новый отчёт имеет0 checkbox markers; все прежние140 byte-identical.

## Следующая SOURCE-проверка, не нынешний PASS

Все реальные allocation cuts сохраняются, включая прежний envelope cut3,
новые append/copy/proxy allocations; quota/flags/assertions не ослабляются.
На новом instrument-free frozen source повторить полную native Birth/envelope
матрицу обеих схем/subjects, allocationFailed/no value/cleanup/baseline/retry,
Debug и Release; прежние read/write block-byte/name/version/unsafe path/native
failure проверки сохраняются. Нужны exact source maps, receipts/raw logs/EXE
identity/readback и portable regression отдельно. Иное следующее падение требует
actual ordinal/stack и нового узкого согласования, не превентивной правки path.

Code-reviewer: proposed construction сохраняет semantics и failure boundary;
ponytail-review: минимальное тело в прежнем helper, без нового abstraction.
Нет SOURCE GO/full matrix/app acceptance. T116–T120, MigrationPair/authority/
adoption, H250, AAC RED257/B1, physical x64, installed/release остаются открыты.
Reviewer добавляет только этот файл; product/tests/spec/plan/tasks/old reports/
markers/VM/GitHub/profile/build/test не изменяет и не исполняет.
