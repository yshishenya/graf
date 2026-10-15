# Round272 — REQUIREMENTS addendum: SHA-256 empty construction

Дата: 2026-10-07. Независимый reviewer; high-risk-product, существующая T116.
Canonical: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty preserve.

## Решение до правки

**SCOPED REQUIREMENTS GO; C0 / H0 / M0 / L0** для единственной строки
в существующем `apps/windows/RecApp/Storage/Sha256.cpp`, `hexDigest`:

```cpp
std::string result;
// заменить на:
std::string result(std::size_t{0}, char{});
```

Это точечное дополнение к принятому gate B
`review-2026-10-07-migration-v2-codec-gate.md`, SHA
`f85821923fd47cbb876d4998804aeefd1c92fff742e89fd3a0889f0f4fb17516`.
Никаких других producer changes, новых helper/backend/flags, рефакторинга,
schema/API/provider/cap или task изменений этим решением не разрешено.
SOURCE approval отсутствует; широкая SOURCE-проверка приостановлена до
исправления и свежих точных повторных испытаний.

## Доказанная причина и происхождение evidence

Лично прочитаны финальные экспортированные квитанции и полные raw test logs
из внешнего generated-only stand `graf-f200-migration-final272.a194Fu`:
Release build0/test0, пять тестов PASS; Debug build0/test8, четыре PASS,
`ProtectedCustodyFilesTests` FAILED. Карты обоих экспортов равны финальной
карте204, лично сопоставленной с canonical и frozen stand до диагностики.
Это не полный native suite или установленное приложение.

Main затем выполнил отдельный Debug `--migration-history`: counted invoke0
успешен, Birth allocation cut1 завершается exit3. Предоставленный main стек
tool e1cc80 записан в `diagnostic272-stack.txt`; reviewer лично прочитал эту
запись и проверил SHA
`baf2bec9736724014fddf8ef1a23c36b57a3b1360cb749256387bea3e0430213`.
Это запись main о фактическом диагностическом запуске, не raw console export
и не исполнение VM reviewer.

Стек: operator new → allocator Container_proxy → Alloc_proxy →
basic_string Construct_empty → default basic_string → hexDigest →
NativeHash::finish → sha256Stream → custody_detail::digest → Birth.
Отказ внутри noexcept default string construction не доходит до имеющегося
Birth catch bad_alloc. Предварительная гипотеза reviewer о streambuf/locale
не подтверждена этим стеком и не является причиной для иных правок.

FilesTests восстановлен, лично SHA-проверен:
`a20226b7e95b2a82676e460044cd85d1aa8968eaca744a3c781be7ea30e561f3`.
Временные DbgHelp/печать не входят в будущую проверяемую реализацию.
Текущий Sha256.cpp до правки:
`84032d4a6b8f6a8c2e52e9bdd194d1cffe70050216cc3b392964ff46798ae76c`.

## Семантика и общие вызывающие пути

Лично прочитаны полный Sha256.cpp/.h, существующий CustodyString count0
construction и все прямые Windows SHA public call sites по rg с контекстом.
Count0/char{} выбирает потенциально бросающий count constructor и создаёт
ту же пустую строку: нулевой символ не добавляется. Прежний reserve64 и цикл
из 32 байтов с lowercase hex остаются; успешный результат ровно64 символа.
Это не освобождение Debug proxy от счёта, не запрет выделений и не обещание
успешного хеширования при нехватке памяти. Требуется корректное распространение
bad_alloc к уже существующей границе обработки, а не пустой/выдуманный digest.

Общий hexDigest используется PortableHash::finish и строковым
NativeHash::finish. Public sha256 сохраняет provider-independent memory route;
sha256Stream/File сохраняют native CNG на Windows, portable route вне Windows,
EOF/read-error поведение и ограниченный 64KiB буфер с wipe. Двоичный
sha256ProtectedStream использует NativeHash::finish(array), не этот hex formatter;
его admission, cancellation, native errors и IStream ownership не меняются.

Затронутые общие вызывающие пути: custody_detail::digest и Birth/block integrity;
LocalRecordingPackage artifact inspection; V5 writer prefix/finalize;
DesktopHttpTransport manifest/file/part integrity; WindowsTargetDetector
certificate identity; MeetingReminderModel preference/receipt/context keys;
DesktopApiClient deletion operation identity. Private DesktopApiClient::sha256
является отдельным noexcept predicate, не hash producer; не менять его.
Успешные bytes/IDs/keys/ranges и порядок действий этих callers не меняются.
Нового UI/IO/network, auth, migration или effect authority нет.

## Scoped analyze и неизменные нормы

Применён speckit-analyze; его полная инструкция прочитана. Полностью прочитанный
контекст AGENTS/guidance/constitution и десяти нормативных checklist из gate B
переиспользован с текущей сверкой артефактов и инвентаря; релевантные callers,
T116 и требования к отказам проверены заново. Не повторялся исторический аудит.
Constitution VI, FR-012/013/014/022, SC-005/006, plan protected-storage и T116
прямо покрывают shared hashing/error boundary. T116 явно включает Storage/Sha256.*.
Нет новой неоднозначности, противоречия нормам или uncovered task для этой строки.
Прежний migration.v1/v2 gate, tuple, Birth/stamp/cap правила не ослабляются.

Spec/plan/tasks/constitution/models/quickstart/base/packed hashes совпали с
таблицей gate B. Tasks SHA
`80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`,
120 total /93 checked /27 open. Prerequisite вернул правильный FEATURE_DIR.
Hooks before/after analyze/checklist/implement: по1 registered disabled hook,
все6 этапов enabled0/dispatched0. GitHub ownership #7444 — сообщённое main
состояние; reviewer не выполнял новый live GitHub audit.

До этого отчёта138 markdown: десять нормативных checklist154 checked/0 open;
128 исторических/контекстных отчётов, исторические markers не новые обязательства.
Baseline inventory SHA (sorted basename + TAB + SHA256 + LF):
`0e41b531c6dc2f6d7302af642073197c6df5f57fe7b1bd3f64aeac80a33f023a`.
Этот отчёт имеет0 checkbox markers; прежние138 файлов не изменяются.

## Условия следующей SOURCE-проверки, не нынешний PASS

Сохранить все actual allocation ordinals, quota, assertions и compiler flags.
Не исключать cut1 или Debug proxies, не прогревать helper ради обхода отказа.
Повторить полный предусмотренный Birth/envelope allocation-cut matrix для обеих
схем/subjects, typed allocationFailed/no value, cleanup/quota restoration/retry,
native Release и Debug на новом frozen source. Сохранить SHA-256 known vectors,
binary/empty/current cursor/chunk/read-error регрессии и portable suite; shared
caller compilation соответствует действительно затронутому scope.

Нужны новые source maps/receipts/raw logs и EXE identity; старый Debug4/5 FAIL
остаётся неизменным историческим evidence, не превращается в PASS. Если следующий
ordinal обнаружит иную причину, сначала доказать её и отдельно согласовать scope;
blockName/wstring/path сейчас только непроверенные гипотезы, не разрешённые правки.
Legacy NativeHashFailure AAC RED257/B1 не закрыт и не должен быть скрыт этим fix.

Review формы: code-reviewer — сохранение semantics/error contract;
ponytail-review — однострочный существующий count pattern достаточен, нового
helper или backend не требуется. Нет безопасного основания расширять diff.

Итог: main может выполнить именно эту строку и свежие проверки. T116–T120,
MigrationPair/queue admission/app adoption, H250, physical x64 и выпуск остаются
открыты. Reviewer не менял product/test/spec/plan/tasks/old reports/markers,
не запускал VM/сборки/тесты, не делал commit/GitHub/install/profile actions.
