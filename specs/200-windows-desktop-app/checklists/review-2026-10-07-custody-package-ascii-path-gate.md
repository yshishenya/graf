# Round273 — узкий REQUIREMENTS допуск: ASCII package path

Дата: 2026-10-07. Reviewer-owned, 0 checkbox. High-risk-product, existing
T116 / #7444. **SCOPED REQUIREMENTS GO — C0 / H0 / M0 / L0** только для
двух изменений openImpl; SOURCE/native acceptance не выданы.

## Разрешённая форма и нормативная причина

`apps/windows/RecApp/Storage/ProtectedCustodyFiles.cpp`: сохранить existing
role/service/access/validIdentity guards:276–280 и добавить ДО localPath:281
и любого native query/IO/State allocation:

```cpp
if (!service && !std::all_of(package.begin(), package.end(), [](unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
        || (c >= '0' && c <= '9') || c == '_' || c == '-';
})) return failure<Result>(CustodyFileError::invalidInput);
```

В существующей `!service` ветке:311 заменить ТОЛЬКО packageName:

```cpp
const std::wstring packageName(package.begin(), package.end());
```

Прежний `path = root; path /= packageName;` и последующие locks неизменны.
Допустима эквивалентная интеграция all_of в прежний guard при том же порядке
раннего отказа; validIdentity обязательно сохраняется, пустота/length<=300
не переопределяются. Predicate только явные ASCII ranges, без isalnum/locale.

Лично прочитан base contract §9:417–430, особенно424: identity1–300 ASCII
`[A-Za-z0-9_-]`, без locale-dependent расширений. Metadata.cpp:22–25 уже
проверяет эту форму. QueueService.cpp:1396–1399 использует isalnum(unsigned char),
следовательно его одного недостаточно для независимого ASCII доказательства.
Менять общий QueueService validator НЕ разрешено. Это уточнение enforcement
действующей нормы protected IDs, не новый schema/product choice.

Каждый допущенный byte <=127 и обозначает тот же ASCII character при расширении
char→wchar_t; нет narrow filesystem code-page conversion или потери Unicode
содержимого, потому что произвольное Unicode package не допускается контрактом.
Signed char вне ASCII всегда отвергается predicate до widening; embedded NUL,
separator, colon, dot и whitespace также не принимаются. Unicode ROOT не
преобразуется/не ограничивается этой проверкой: localPath/native ancestor flow
сохраняется. service-empty/bootstrap/queue и package migration classification
сохраняются. Никакой normalization, fallback, repair, redirect или нового IO.

## Проверенный diagnostic и source identity

Stand `/Users/yshishenya/Documents/graf-f200-pair-index273.m4I1Lr`:
лично прочитаны receipt/script/stdout/relevant stderr stack и хеширована карта.
Receipt diagnostic-index273.json SHA
`29cda31bc7b30eea6fae07092dba33d87bb27c7bb35394b580daf58d735e949d`:
temporary-diagnostic-not-acceptance, terminal=true, build_exit0/test_exit3.
stderr SHA `d8228a3bc61b274873382fc7d4aa280872739850375d465c247ca4d77febb3f1`:
последний PAIR_CUT117/16B: wchar default → _Convert_narrow_to_wide →
path conversion<std::string> → operator/= → openImpl → MigrationPair.
stdout имеет schema1/queue row allocations503/cancel_cuts503/retry1;
эта строка НЕ доказывает PASS остальных schema/subject или всего matrix.
Actual installed filesystem code-page implementation — сообщение main;
reviewer VM/header retrieval не выполнял. Raw stack причинно подтверждает
именно narrow conversion, не произвольный следующий fault site.

source-index273.json SHA
`458fd4a05a3d0557aedee0b26c53d5d1f149d0184348d51e36821a855fae5b88`:
204 entries, canonical203 MATCH; только snapshot FilesTests
`7a13f91d1610bce0784196fe92527513677af3c3e3cb60e21223ccbaf55956ae`
отличается от canonical `0ca2a265214148995b785a578271a1d8cd46a9d7cbeb7d42eee4686cd9919aa0`.
Скрипт подменяет native test отдельным diagnostic
`b29865b8012964ce5e8fdd77fd130614165ce3e769a5d2c8bcbe8d3e99262e57`;
это не instrument-free SOURCE evidence. Files.cpp canonical/map до правки
`71050b705c058e774789d407b6568da6af68cb5ef951eabd516edfcbea59a566`.

## Failure/lifetime и scoped analyze

Лично прочитан openImpl от guards до publication/catches. Для invalid package
отказ происходит ДО localPath/State/security/directory/ID accesses, поэтому
invalidInput/no effects — корректная граница. Valid ASCII сохраняет те же
native path components, user-only ACL, reparse/hardlink/handle confinement,
ancestor/store/object leases и create/access/discover порядок. Wide constructor
и `/=` могут выделять память; их internal faults не объявлены заранее безопасными.
bad_alloc→allocationFailed и filesystem_error→unsafePath не меняются; failure
unwinds неопубликованный State, retry через fresh factory. createNew прежние
namespace effects до поздних отказов не объявлены отсутствующими.

code-reviewer проверил source flow; ранее прочитанные нормы и scoped analyze
переиспользованы с hashes без drift: Constitution VI, spec FR-012/013/014/022,
plan:1510–1522, tasks T116:568 и base contract §2/§9. Нового C/H/M/L конфликта
нет. Прямой all_of + existing iterator string ctor — минимальный reuse без
нового helper/parser/dependency/backend. Pair/effect authority не добавляется.

## Обязательные проверки main после правки, НЕ нынешний PASS

Прямые native regressions: mixed ASCII case/digits/_/-, empty/301 rejection,
300 ASCII input guard acceptance; high bytes (включая0x80/0xFF), UTF-8 bytes,
NUL/separators reject invalidInput до native queries/IO, source/IDs без изменений.
Для300 не требовать successful native directory creation: допустимость identity
не гарантирует допустимость такой длины компонента на файловой системе. Можно
проверить reaching следующего root guard с заведомо invalid root; не сокращать
нормативный cap300 и не маскировать действующий filesystem failure.
Unicode root + допустимый ASCII package regression отдельно обязателен.
Если installed locale доступна, проверить non-ASCII rejection при временной
locale и восстановить её; при unavailable явно SKIP/не claiming locale PASS.

Свежий instrument-free snapshot, Release/Debug ALL actual allocation/cancel
cuts обеих схем/subjects, cleanup/baseline/lease/retry и exact maps/raw/EXE
readback. Не исключать widened-string/proxy/path allocations, не ослаблять
flags/assertions/cuts. Следующий root требует отдельного evidence/gate.
Не менять QueueService/Metadata identity, other path producers, index/publish/
packed helpers, schema, caps, default state, filesystem error classification.
Нет SOURCE GO/fullT116/H250/AAC/physical-x64/installed/adoption/release PASS.

## Freeze / сохранение предыдущих отчётов

Canonical `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
branch codex/200-windows-followup, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`, dirty preserve.
Tasks120/93/27 SHA `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.
До записи152 markdown:10 current normative154 checked/0 open,142 остальных
historical/context. Inventory sorted basename TAB SHA256 LF
`443eb4df831416178348e74b143af586d99069f1ac8f0288a64d18586fde3690`.
Все152 прежних files/markers сохраняются побайтно. Hooks YAML parsed:
each before/after analyze/checklist/implement registered1 disabled;0 dispatch.
Reviewer единственная запись — этот новый 0-checkbox report; code/tests/spec/
plan/tasks/governance/старые reports/VM/GitHub/commit не изменяются.
