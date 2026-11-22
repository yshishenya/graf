# Round273 — узкий REQUIREMENTS-addendum: SDDL и inspect wanted

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing T116 / #7444.

## Решение

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** для двух точных replacements
конкатенации в `ProtectedCustodyFiles::State`: named SDDL string с append в
`initializeSecurity` и named wanted string с append в `inspect`. Первый site
подтверждён actual cut12; второй допустим по непосредственно читаемой аналогии,
НЕ отдельному actual inspect stack. Допуск означает право на минимальную правку
и её проверку, не SOURCE GO/Debug PASS/готовность MigrationPair.

## Диагностический снимок и предел доказательства

Лично прочитан весь
`/Users/yshishenya/Documents/graf-f200-pair-vectors273.ltKUm3/diagnostic-vectors273-stderr.log`;
разобраны receipt/source map и сверены diagnostic-test hashes. VM/тесты reviewer
не запускал. Receipt mode temporary-diagnostic-not-acceptance, terminal true,
build0/test3; это failed diagnostic execution main, не зелёная matrix.

Последний cut12 bytes16: `_Container_proxy_alloc → basic_string<wchar_t>
move ctor → std::operator+ → State::initializeSecurity → openImpl →
MigrationPair::read`. Предыдущий cut11 находится в append/reallocation того же
operator+; cuts4/5 показывают `_Construct_n` count-vector constructors.
Main сообщил classified refusal/retry предыдущих cuts, но присутствие их stack
не заменяет полного matrix receipt и не доказывает успех следующих cuts.
Конкретная цепочка, а не VM-гипотеза, обосновывает устранение temporary-return move.

Source map204:203 inputs совпадают с canonical, единственное отличие — current
worker FilesTests; Files.cpp совпадает. Не заявляется whole204 current test
applicability. Diagnostic instrumented cpp отдельный, SHA соответствует receipt.
Installed MSVC default/move proxy facts из предыдущих addenda остаются
атрибутированными main, reviewer самостоятельно VM headers не читает.
Перед финальным решением main сообщил actual installed xstring14.44:1027–1030
move ctor noexcept выполняет `_Alloc_proxy` перед `_Take_contents`, copy ctor716
не noexcept. Это main read-only evidence, согласующееся с cut12, не reviewer run.
Named strings здесь не возвращаются; сохранять все proxy allocation cuts.

## Разрешённая форма / сохранение поведения

### initializeSecurity — прямое доказательство

Заменить только выражение создания SDDL на:

```cpp
std::wstring sddl(L"D:P(A;OICI;FA;;;");
sddl += static_cast<wchar_t*>(text.value);
sddl += L")";
```

Literal constructor и append потенциально throwing; не создавать default string,
не возвращать named string и не использовать concatenation/move вместо append.
Содержимое строго прежнее: тот же prefix, exact native SID text и suffix.
Это не новая ACL: flags OICI, FILE_ALL_ACCESS, protected DACL, SID текущего
пользователя, revision и native conversion APIs не меняются.

ConvertSidToStringSidW остаётся перед сборкой строки, его LocalMemory text
живёт до окончания conversion; ConvertStringSecurityDescriptorToSecurityDescriptorW
получает прежний sddl.c_str()/SDDL_REVISION_1/output pointer. Security descriptor
публикуется в security.lpSecurityDescriptor только после успеха, как прежде.
При исключении освобождаются token handle, SID text и построенная string;
state/resources unwinding и прежний openImpl bad_alloc handler сохраняются.
Не добавлять bool fallback, новый catch, native call, formatter или резервирование.

### inspect — аналогия, не actual failure

Заменить только `std::wstring(prefix) + expected.wstring()` на named
`std::wstring wanted` с ТОЧНО прежним extended-path prefix (четыре native chars:
backslash, backslash, question mark, backslash), named const строку из
`expected.wstring()`, затем `wanted += expectedText`.
Оставить существующую conversion `.wstring()`, не переходить на `.native()`
как иной интерфейс, не canonicalize/normalize и не возвращать/move wanted.

Оба выражения используют тот же std::wstring allocator/temporary-plus механизм;
устранение return move заменой на append минимально и прозрачно по строковым
байтам. Но internal expected.wstring() может иметь собственные runtime allocation
границы — их этот gate не объявляет проверенными и не разрешает дальше менять.

Сохраняется порядок inspect: type/info/reparse/directory/hardlink checks,
GetFinalPathNameByHandleW с прежними FILE_NAME_NORMALIZED|VOLUME_NAME_DOS и
buffer32768, затем сборка expected string и прежняя проверка count/size.
CompareStringOrdinal использует прежние lengths и case-insensitive TRUE;
privateAcl вызывается по прежнему short-circuit условию. Нельзя разрешать
normalized-handle/raw-wanted mismatch, включая repeated-separator paths.
Append/conversion failure не превращается в успешный inspect. RAII и typed
отказы существующих callers сохраняются; этой правкой exception coverage иных
callers не переписывается и не считается доказанной whole-matrix проверкой.

## Трассировка и нормативный анализ

Source anchors current Files.cpp:116–130 initializeSecurity (sole caller269
в openImpl); 143–155 inspect; 160/173/202/530 native open/ancestor lock/create/
publish consumers; 684/693 packed owner repeated checks. Inspect не noexcept;
оно не получает новых прав/состояния. Existing callers и catches прочитаны по
релевантному flow; не создаётся второй ACL/path backend или общий string helper.

Base custody §2:46–65 требует confinement opened handles, запрета reparse/ADS/
UNC/foreign JSON paths, user-only ACL до content writes. Прежние native проверки
остаются неизменными, поэтому FR-012/013/014/022, Constitution III/IV/VI и
T116:568 покрывают этот storage prerequisite без нового product decision/schema.
Противоречий current spec/plan/contracts, C/H ambiguity этой границы не найдено.

**Вне допуска:** indexName, другие string/path producers, State layout/constructors,
Directory/packed-owner изменения, нормализация/сравнение путей, SID/ACL/policy,
quotas/allocators/flags, tests/cuts/ordinal exemptions и новая authority.
Будущий actual fault stack требует отдельного решения.

Main сохраняет failure artifacts и выполняет fresh exact-source Release/Debug
allocation/cancel cuts, baseline cleanup/retry/retained leases и shared Files/
ACL/inspect regressions. Проверить прежние private/ancestor ACL результаты и
raw expected-path equivalence; не ослаблять assertions. Различать runtime cuts
и source ordering proof. Portable PASS не является native SID/ACL/Debug proof.

## Identity / inventory / неизменность

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
ветка `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; dirty сохранён.
До report147 files:10 current normative154 checked/0 open и137 прочих/
исторических; их markers не изменены, historical findings не новые norms.
Sorted basename<TAB>SHA256<LF> inventory147:
`e5e2d5745547e6aad085f48270c8c953154ead2dd236600ccc28866a2a2e8f6a`.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Hooks before/after analyze/checklist/implement: registered1/enabled0 каждый,
YAML лично разобран, dispatched0. Read-only prerequisites подтверждают Feature200.
Ранее лично прочитанные guidance/norms переиспользованы с fresh hashes;
`code-reviewer` и `speckit-analyze` полностью перечитаны. Analyze read-only;
пользователь отдельно разрешил единственный новый reviewer report.

| Файл | SHA-256 |
| --- | --- |
| Files.cpp до proposed string fix | `366fb2430e513bec1ba932913ae73034b90347cc233bc3ed6420abe8cd1ad7a8` |
| source-vectors273.json | `871a63ca145fb64c6365bc5b1c2905ae02187690f92542a81cb5720bbeed0831` |
| diagnostic-vectors273-stderr.log | `af9897c6cc7a2aeb47780b4d92d5f9055c16550a9e1fa69c488d59001c66163a` |
| diagnostic-vectors273.json | `29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d` |
| diagnostic-FilesTests.cpp | `b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57` |
| prior State vector gate | `caced56f932be84925815cf39d4a50e28486ee1fae1efde08840d7b2a14bfbb7` |

После записи лично проверены сохранение всех previous147 reports/markers и
source/normative artifact hashes. Единственная запись — этот0-checkbox report;
code/tests/spec/plan/tasks/VM/GitHub/hooks/commit reviewer не менял.
SOURCE273/full T116–T120/H250/legacy AAC/physical x64/installed/app/release
остаются открыты. Это допуск только двух названных string construction sites.
