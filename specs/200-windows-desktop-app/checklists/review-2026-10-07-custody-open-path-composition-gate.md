# Round273 — узкий REQUIREMENTS допуск: пять путей openImpl

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product,
действующая T116 / #7444; отдельная проверка требований, не SOURCE approval.

**SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** только для пяти binary `/`
expressions в `apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp`:
openImpl:296,299,303,310,317 на проверенном снимке.

## Точная разрешённая форма

На прежних местах, без перестановки окружающих операций:

```cpp
path = root;
path /= L".custody-v1";
```

После прежнего успешного lockDirectory и ДО прежнего store identity call:

```cpp
std::filesystem::path storePath(path);
storePath /= L"store.id";
```

Передать storePath вместо binary-expression в неизменный identity call.
В существующей ветке `!service`, перед её прежним lockDirectory:

```cpp
path = root;
const std::string packageName(package);
path /= packageName;
```

На прежнем месте вычисления role directory, ДО CreateDirectory/lockDirectory:

```cpp
state->directory = path;
state->directory /= roleName(context.role);
```

После прежнего успешного role lock и ДО object create/identity:

```cpp
std::filesystem::path idPath(state->directory);
idPath /= L"id.bin";
```

storePath/idPath намеренно MUTABLE, packageName const. Не вводить default path
constructor или возвращаемый path helper. Корневой ancestor walk/root_path,
уже существующий package `.custody-v1` append и остальные operations неизменны.

## Лично проверенная причина / предел доказательств

Прочитаны receipt, stderr, script и source map из
`/Users/yshishenya/Documents/graf-f200-pair-directory273.I5j6X1`.
Receipt `diagnostic-directory273.json` SHA
`29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d`:
terminal=true, build_exit=0, test_exit=3, temporary-diagnostic-not-acceptance.
stderr SHA `c2c55c6356eb9c64e097f99c6d9392424347b4e73caecaa1277e523efc41c090`:
последний PAIR_CUT ordinal100/bytes16; Alloc_proxy → basic_string wchar default
→ filesystem::path default → filesystem::operator/ → openImpl → MigrationPair.
Диагностика дошла до cut100 после прежних Directory relocation cuts; это НЕ
полный успешный allocation matrix. stdout пустой. Reviewer VM не выполнял.

source-directory273.json SHA
`14a4561ad48c2d9f4486888b0f4187fc104e8416a1bc8974b9f063115caa0ac6`:
204 entries; canonical203 совпадают, единственное отличие — snapshot FilesTests
`7a13f91d1610bce0784196fe92527513677af3c3e3cb60e21223ccbaf55956ae`
против canonical `0ca2a265214148995b785a578271a1d8cd46a9d7cbeb7d42eee4686cd9919aa0`.
Скрипт отдельно подменяет только native test на diagnostic-FilesTests.cpp
`b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57`,
совпадающий с receipt; эти три test snapshots не смешиваются.
Files.cpp snapshot/canonical/map совпали:
`5b51f63d148da1ae9c66dccb0959d1d103c23c95fafcd00d441668a6c37f6f22`.
Main сообщает установленный MSVC operator/ fastpath с default _Tmp; лично
доступный raw stack подтверждает именно этот causal path, не все internal sites.

## Сохранение семантики и scoped analyze

Лично прочитан openImpl целиком: guards role/package/access/localPath остаются
до State/IO; lock порядок drive/ancestors/root → root custody → store identity →
optional package/package custody → role → object identity неизменен.
Строки компонентов фиксированы либо уже прошли existing validIdentity; это
те же relative components. Native append `/=` вместо binary `/`, без ручного
separator/normalization/root redirect. Discover observed IDs/exclusive handles,
readonly transition, createNew branches, ACL/reparse/hardlink/inspect и exact16
identity validation не меняются. Published Files только после всех проверок.
bad_alloc по-прежнему allocationFailed; filesystem_error — unsafePath. Любой
отказ composition разрушает неопубликованный unique State/handles перед catch;
частично изменённый State не используется повторно. Прежние createNew directory
effects могут существовать до отказа: zero namespace effects не заявляется.

Переиспользованы ранее прочитанные нормы; свежие relevant anchors:
Constitution VI:401–421; base custody contract §2:45–81; spec FR-012/013/014/022;
plan:1510–1522; tasks T116:568. Пять форм не меняют data format/authority/quotas,
не требуют нового product decision/task/schema. code-reviewer проверил guards,
ownership и catches; scoped analyze не выявил C/H/M/L конфликтов предложения.
Не требуется новый path framework: именованные locals — минимальная замена.

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch `codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.
Tasks120/93/27, SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
Current10 normative154 checked/0 open; до отчёта150 markdown (140 остальных
historical/context), не150 нормативных checklist. Inventory sorted basename TAB
SHA256 LF: `e023142eea08ad249d0ea2d2bbbe0762b3eb7713637f699fbc65ffc06b613f81`.
Все прежние150/markers сохраняются побайтно. YAML лично parsed: before/after
implement/analyze/checklist EACH registered1 disabled; enabled0, dispatched0.

## Обязательная последующая проверка / что НЕ разрешено

Именованные copy/append могут выделять память и иметь внутренние временные
объекты; отсутствие всех noexcept faults не доказано этим REQUIREMENTS GO.
Нужен свежий instrument-free snapshot, реальные Release/Debug allocation/cancel
cuts (включая новый путь cut100 и новые ordinals), cleanup/lease/baseline/retry,
service/package/create/discover/root rejection regressions и exact source/log/
EXE readback. Cuts/proxies/asserts/flags не исключать и не ослаблять.
Другой root после правки требует собственного доказательства/допуска.
indexName/readIndex/packed operations, другие helpers/default paths вне scope.
Нет SOURCE GO, native PASS, Pair/effect/admission/GC authority, app adoption,
H250/AAC/installed/release acceptance или закрытия T116–T120.
Reviewer единственная запись — этот новый отчёт; code/tests/spec/plan/tasks/
старые reports/markers/VM/GitHub/hooks/commit не изменяются.
