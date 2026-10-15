# Round273 — узкий REQUIREMENTS допуск: indexName и два reader path

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing
T116 / #7444. **SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** только для
описанной формы; не SOURCE approval и не успешный runtime matrix.

## Точная область до кода

В `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp`: заменить private
indexName:88 ровно на прежний принятый blockName construction pattern:

```cpp
std::wstring indexName(std::uint32_t slot) {
    std::wstring name(L"index.");
    name += std::to_wstring(slot);
    return std::wstring(name);
}
```

Только в readIndex:493 и внутри прежнего slot loop
readValidatedSnapshotImpl:600 заменить binary index path expression:

```cpp
const auto name = indexName(slot);
std::filesystem::path path(state_->directory);
path /= name;
```

Передать path в прежний State::read, не менять role indexEnvelopeLimit/аргументы,
место read, branches или loop. Не добавлять default path/new helper/normalization.
readIndex slot>1 guard остаётся ДО construction/IO; внутренний loop по-прежнему
читает только slots0/1. indexName сохраняет строку `index.<uint32 decimal>`
для всего диапазона uint32, без нового ограничения helper API.

## Диагностика, прочитанная reviewer

Stand `/Users/yshishenya/Documents/graf-f200-pair-rootpaths273.AaJbow`:
лично прочитаны receipt/script/relevant stderr stack; файлы хешированы без записи.
diagnostic-rootpaths273.json SHA
`29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d`:
temporary-diagnostic-not-acceptance, terminal=true, build_exit0/test_exit3.
stderr SHA `845ec168d5ccfd0e89fb7a5781c5784fc4b92b325f455d92297187e0372db4ee`:
последний PAIR_CUT ordinal138/bytes16; Alloc_proxy → basic_string<wchar_t>
→ std::operator+ → indexName → readValidatedSnapshotImpl → MetadataPair →
MigrationPair. Это actual helper failure; не новый path-operator/ failure
на двух reader expressions. Их замена — явно ограниченная causal аналогия с
уже доказанными и принятыми block/open path gates, а не отдельный runtime PASS.
stdout пустой; reviewer VM не запускал.

source-rootpaths273.json SHA
`7d22bd3c443098fa7ac147813c48c0ef7533d19ebbacc87071989d8c4a1d8c6c`:
204 entries; canonical203 совпали. Snapshot FilesTests
`7a13f91d1610bce0784196fe92527513677af3c3e3cb60e21223ccbaf55956ae`
отличается от canonical `0ca2a265214148995b785a578271a1d8cd46a9d7cbeb7d42eee4686cd9919aa0`.
Скрипт поверх frozen native input подставляет только external diagnostic test
`b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57`,
совпадающий с receipt; map/diagnostic/canonical tests не смешиваются.
Files.cpp до кода canonical/map SHA
`679fb90c167861e758c7c0951905cdfc48bce36163f333f6219357ec1f8ae251`.

## Общие callers / failure boundaries

Лично прочитаны все direct indexName calls: readIndex, publishIndex:525 и
readValidatedSnapshotImpl, оба readers полностью вместе с catches/selection.
Named literal construction/append/explicit copy-prvalue устраняет прежнюю
operator+ return-move форму; потенциально бросающие copy allocations сохраняются
в actual cuts. При C++17 returned copy-prvalue не требует named-return move.
Нет claim, что все внутренние MSVC allocation/move sites теперь безопасны.

readIndex: прежняя native read/openIndex authentication/error propagation и
bad_alloc→allocationFailed. Snapshot: BOTH reads, physical closure validation,
missing-slot distinction, metadata no-singleton, generation/slot selection,
trustedPrefix restrictions и sticky failed сохраняются; caught bad_alloc
по-прежнему sets failed=true + allocationFailed. ACL/reparse/hardlink/exact
size/path check/identity leases State::read не меняются. Нет нового IO/write.

publishIndex получает то же имя через изменённый общий helper и по-прежнему
использует прежние guards/openIndex/rename/readback/catch. Этот helper влияет
на allocations общего caller, поэтому публикационная regression обязательна;
сам publishIndex не редактировать. В частности temporary binary path:523 и
targetPath binary path:530 не входят в допуск. Их native faults ещё не доказаны
этим стеком; режим publication ambiguity/sticky failure не ослаблять.

## Scoped analyze / неизменность

code-reviewer применён к helper и всем callers. Ранее полностью прочитанные
нормы переиспользованы; свежие spec/plan/tasks/quickstart/constitution hashes
совпали с предыдущим open-path gate. Base custody §2 fixed index.0/index.1 и
handle confinement, FR-012/013/014/022, Constitution VI и T116:568 покрывают
этот helper root; нового schema/product choice/task или C/H ambiguity нет.
Минимальное reuse существующего blockName pattern, без generic path framework.

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch codex/200-windows-followup, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.
Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
До отчёта151 markdown: current10 normative154 checked/0 open и141 остальных
historical/context. Старые findings не новые normative checklist obligations.
Inventory sorted basename TAB SHA256 LF
`8b7acfa62b8e616842c3d3392105a961b4e8391bb7786cadebda863796f167d2`.
Все прежние151/markers сохраняются побайтно. YAML parsed: six before/after
implement/analyze/checklist stages each1 registered/0 enabled; dispatched0.

## Что ещё необходимо после правки

Свежий instrument-free Release/Debug source, actual all allocation/cancel cuts,
включая indexName copies и reader path allocations; cleanup/baseline/fresh retry,
retained leases, BOTH-peer failures/selection и readIndex/publish readback
regressions. Без ослабления proxies/cuts/flags/assertions. Exact maps/raw logs/
EXE identity/readback отдельно обязательны для SOURCE решения. Новый следующий
fault root не предрешён. Старый test_exit3 остаётся FAILED evidence.
Нет SOURCE GO/native PASS/full Pair authority/startup/adoption/GC/effects,
T116–T120 closure, H250/AAC/physical-x64/installed/release acceptance.
Единственная reviewer запись — этот новый 0-checkbox report; code/tests/spec/
plan/tasks/старые reports/markers/VM/GitHub/hooks/commit не изменяются.
