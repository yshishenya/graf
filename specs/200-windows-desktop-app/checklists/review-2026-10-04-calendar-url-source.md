# T119 Round234 — bounded URL source review

Дата: 2026-10-04. **Request Changes: C0 / H0 / M1.**
Это оценка только URL validator/facade/build registration/test slice, не
whole Feature200, source resolver re-review, Windows-ready или T119 acceptance.
Единственный reviewer write — этот файл; product code, нормы, tasks, GitHub,
design checklist markers, commits/install/VM не изменялись.

## Снимок и метод

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
свежо проверены branch `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Dirty user/main work сохранён.
Лично полностью прочитаны code-reviewer и ponytail-review SKILL; применён
ограниченный source review внутри существующего high-risk Spec Kit slice.
Applicable AGENTS/guidance/constitution и bounded normative context уже лично
прочитаны при предшествующем design gate и используются без full-task restart.
Design gate принят на SHA256
`b0d2b38f65e520b0df37588bc6f5f9c97fd7f8acdc002b0acbf474ac7b563df0`,
12/0; документированное H1 defect deviation сохраняется, не пересматривается.

Прочитаны текущие восемь файлов, полный shared fixture, scoped working-tree
diffs и текущие тела функций. У CMake diff относительно HEAD есть более ранние
transport/storage OBJECT changes: здесь проверена URL регистрация, прежний
transport/storage review заново не выполнялся. NativeSettingsBridgeTests
прочитан, но findings ограничены changed URL expectations/их потребителями.

Все пути ниже относительно `apps/windows/`:

| Файл | SHA256 текущих прочитанных байтов |
|---|---|
| `RecApp/Shell/CalendarMeetingOpener.h` | `a88702d672cb9f956686fabd7b28e161b2114b03da5b120a2933037e167f46f0` |
| `RecApp/Shell/CalendarMeetingOpener.cpp` | `981ce171d045ce465ba1bcdd9efc539d1d06b56b05e564a7aacf41fe20da5475` |
| `RecApp/Shell/MeetingReminderModel.cpp` | `3b2340150e112c3a626b71db9333dd67e641d85b08b4bdf40017c550d74899bb` |
| `RecApp/GrafWindowsApp.vcxproj` | `8cbd9cd2f86051a78c1f30e7255458821a76f35ba5bc7d4aae3e47c6ed25677a` |
| `CMakeLists.txt` | `7d2e1ce939dd0a2edc78d46e7f41c2eb42dd233f6659ec4611d4846b474f1b18` |
| `Tests/GrafWindowsContractTests/CalendarMeetingUrlTests.cpp` | `2f929fc8e156ce89f8ecba9ab953a67bcfab583b24c85360d8eb908d2caa79d2` |
| `Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp` | `14fd38baa81dc1d22563db808e105e7d73c6864b39c84d0ea5a91247cfd821bd` |
| `Tests/GrafWindowsContractTests/Fixtures/calendar_join_host_policy.json` | `7c6731fe293226eb1033acb2c5acc930897134395e8d67ebc29cca7ba17757d1` |

Test hash уже отличается от первоначально присланного dc07...: лично прочитаны
actual bytes с `winrt/Windows.Foundation.Collections.h` на строке14. Main
подтвердил, что это mechanical definition include для JsonArray.Size/C3779;
не policy/expected change. Семь других хешей совпадают с запросом. Fixture
полностью прочитан, 141 rows и hash совпадают с pinned server blob на
`721b5125d799ea798a4af0b3625e18d3c1109039`; expecteds не правились.

## M1 — dot trimming исправляет невалидный bracket IPv6 вместо отказа

**Medium/P2, blocking source approval до узкого исправления.**
Location: `RecApp/Shell/CalendarMeetingOpener.cpp:90`, caller flow175–214;
`Tests/GrafWindowsContractTests/CalendarMeetingUrlTests.cpp:23–48`.

`normalizeHost(value, ipv6)` вызывает `trimDots(lower(...))` без различения
DNS/IPv6. Проверка InetPton/inet_pton выполняется только позже, на уже изменённом
host (строка213). Например:

```text
https://[.2606:4700::1111]/join
    originalHost = .2606:4700::1111
    normalizeHost(..., true) = 2606:4700::1111
    IPv6 syntax check now passes; resulting address is global
```

То же для trailing dot `[2606:4700::1111.]`/двух крайних точек. Portable path
вернёт реконструированный валидный URL; Windows parser получает уже исправленное
представление, поэтому больше не может подтвердить syntax исходного literal.
Это прямой вывод из source flow, не reviewer-run native reproduction и не
заявленный private-IP bypass: globalAddress по-прежнему отказывает non-global
адресам. Но approved CHK003/008 требуют отказ invalid bracket IPv6, а не
расширение dot-normalization DNS правила на IP literal.

Минимальный запрос: DNS/non-IPv6 trim dots оставить, IPv6 literal не обрезать;
проверять его корректный синтаксис без такого исправления. Добавить negative
leading/trailing-dot global IPv6 cases в existing focused tests и facade;
сохранить valid global/mapped IPv6 positives. Не менять shared corpus/norms.
Не требуется новый parser или framework. Percent-encoded structural IPv6
variants также стоит явно закрепить по approved raw-literal syntax boundary,
не смешивать с допустимым once-decoded DNS host.

## Что подтверждено чтением source

- Header8–11 и cpp175–241: один owned optional result, noexcept/catch отказ
  при исключениях. Нет I/O, DNS, launch, auth, retry, scheme candidates или
  apartment initialization; это не launch authority.
- cpp35–61: explicit bounded UTF-8/UTF-16 conversion с strict flags и checked
  result. Surrogate пары обходятся scalar-complete; одиночные surrogates дают
  отказ. Вычисленный supplementary scalar ограничен10FFFF самой формулой и
  guarded16-bit pair. Cc/Cf через u_charType, без GetStringTypeW, broad category C
  или blanket non-BMP deny. H1 known Foundation false positives не копируются.
- cpp72–108: strict двухhex percent decode original host ровно один раз,
  residual percent/authority delimiters rejected; IdnToAscii0 native-only,
  bounds обоих conversion outputs checked. M1 отдельно ограничивает корректность
  этого общего normalizeHost для bracket literals.
- cpp177–208: raw8192 inclusive, case-insensitive absolute HTTPS, original
  authority/suffix split, userinfo/backslash authority rejection, explicit
  bracket/tail guards и bounded decimal port0..65535. optional port с value0
  не теряется по truthiness; absent/default/explicit port representation сохранён.
- cpp129–168: denied IPv4/IPv6 CIDRs, exceptions и mapped IPv6 → IPv4 policy
  соответствуют закреплённым reference tables/corpus. Ошибка чтения констант
  fail closed. DNS fallback non-IP сохранён (включая256.0.2.1), localhost/sub
  denied; никакого DNS lookup/pinning обещания.
- cpp214–240: native CreateUri с approved flags, S_OK/nonnull checks,
  HasProperty userinfo presence, port и HTTPS scheme проверяются. GetHost BSTR
  освобождается RAII; native result снова проходит normalization и host policy.
  Возврат не original authority и не native AbsoluteUri: canonical host плюс
  original suffix. Raw path/query/fragment bytes не декодируются helper.
- Model1–5/245–273/306–308: facade делегирует, old URL validator/parseIpLiteral
  удалены; normalized helper и owner/workspace/origin matching сохранены.
  Не добавлен parallel legacy policy. Known AppMain raw ShellExecute consumer
  неизменён и остаётся последующей T119 migration, не accepted launcher.
- vcxproj128 регистрирует production cpp; CMake GLOB/common OBJECT включает
  helper и explicit CalendarMeetingUrlTests registration добавлена. Native
  libraries normaliz/urlmon/oleaut32/icu заданы pragma в cpp15–18; ws2_32 уже
  есть у Windows targets. Native fixture JSON reader windowsapp/init_apartment
  только в tests, после cold helper calls; production no COM side effect.

## Tests и ещё неподтверждённые native границы

Reviewer один раз выполнил только:

```text
ctest --test-dir /tmp/graf-f200-calendar-build.gOxKwL \
  -R '^(CalendarMeetingUrlTests|NativeSettingsBridgeTests)$' --output-on-failure
2/2 PASS; total0.01s
```

CMakeCache/CTest paths проверены: build относится к canonical apps/windows.
Это запуск существующих binaries, не reviewer fresh rebuild. Последний test
include WinRT-only; portable assertions не изменяет. Main portable focused2/2
и MSVC /W4 /WX production compilation — отдельно сообщённые evidence;
full41/native focused/full suite на момент review ещё принадлежат Main и
здесь не выдаются за завершённые. Windows/VM/probe запусков reviewer не делал.

Текущий native test64–111 действительно проверяет IDNA/fullwidth/numeric IPv4,
supplementary Cc/Cf в suffix и percent-host, non-control/known-defect positives,
byte preservation, full141 expecteds и validated-output revalidation. Test
asserts остаются активны в Release через undef NDEBUG. Portable branch прямо
пишет ASCII-only и не притворяется full IDNA/native URI proof.

Нельзя пока подтвердить native141/141 либо cold helper positives только чтением
кода или portable PASS. Особо нужны actual Windows результаты GetHost IPv6
representation (если SDK выдаёт brackets, normalizeHost сейчас их отвергает),
port0/65535, native-return stable parse и Unicode suffix. Это **не отдельный
доказанный GetHost defect/finding**: reviewer не подменяет IUri документацию
.NET Uri.Host и не утверждает native failure без результата. Actual properties
нужно проверить production tests Main; ошибки нельзя обходить ослаблением corpus.
[Microsoft IUri::GetHost](https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/ms775019(v=vs.85))
документирует S_FALSE как отсутствие property, а не success; здесь он отвергается.

Дополнительные минимальные gaps: M1 malformed-dot literals; при дальнейшем
наращивании focused assertions — malformed UTF-8 continuation/overlong/surrogate
encoding и %00/%7F decoded host. Сейчас есть raw ff/NUL/C0/DEL и percent-Cc/Cf,
но не вся эта узкая комбинация. Это рекомендации покрытия, не новые H findings.
IDNA allocation/native failure tests не объявлены выполненными.

## Ponytail-only conclusion

Lean already. Ship.

Здесь это только complexity verdict: лишних framework/dependencies/parser
abstractions для удаления не найдено; security/correctness M1 относится к
code-reviewer, не к Ponytail. Не shipping/launch/runtime approval. Native SDK
reuse, один helper и facade — достаточная форма; сокращать CIDRs/guards/RAII
ради числа строк нельзя. Намеренного нового `ponytail:` shortcut не требуется.

## Терминальный verdict

**C0 / H0 / M1. Request Changes. Source approval пока не дан.**
Доказанный bounded source blocker — M1 invalid IPv6 syntax normalization.
Windows native results pending — отдельная proof boundary, не fake portable
parity и не whole-T119 blocker переоценка. После минимального fix+focused
assertions достаточно повторной проверки M1 на fresh source hashes и квитанции
в этом же отчёте; полный requirements/Feature200 review не нужен.
Launcher/current owner/resolver wiring/bridge/Record/recovery/installed gates
остаются за пределами этого среза. Никаких norms/tasks/GH/code edits reviewer.

## Квитанция M1 recheck — исправление raw bracket IPv6

2026-10-04, тот же Round234; только M1 и минимальные дополнительные assertions.
Исторический Request Changes/C0/H0/M1 выше сохранён без редактирования.
Предшествующий SHA256 отчёта:
`78283de65cc91919c17b6cd8dd75dbde53f7ff24172c1f452a7be80af4c099ab`.
Fresh canonical branch/HEAD вновь проверены:
`codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Code-reviewer и ponytail-review SKILL лично полностью перечитаны;
нового whole-feature/requirements/transport/storage review не было.

### Три изменившихся файла

Пути относительно `apps/windows/`; все три SHA256 совпали с запросом:

| Файл | Fresh SHA256 |
|---|---|
| `RecApp/Shell/CalendarMeetingOpener.cpp` | `1e711ba4c7235a4e5ab651f1639e2ea1e69ef28b7b6a121a7ed2f084bf9ad134` |
| `Tests/GrafWindowsContractTests/CalendarMeetingUrlTests.cpp` | `7fd513ff5de471c9d30286c1301fbc5c3ce33b6db22e2ec0f1283a1381e5298d` |
| `Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp` | `5dd5cd233ed25e2199d25ab314000a7ad0584fe4174dc9cf980395b84bcce07a` |

Пять остальных файлов из исходного восьмифайлового scope — header, Model.cpp,
vcxproj, CMakeLists и fixture — свежо hash-checked и совпадают с таблицей выше.
Нормы/shared corpus expecteds не изменились. Лично прочитаны changed root flow
и добавленные tests, не только описание исправления Main.

### M1 CLOSED: проверка корневой причины и regression coverage

1. cpp90–91: ASCII lowercase сохраняется для обоих типов host; trimDots теперь
   вызывается **только !ipv6**. Второй native IDNA/trim pass103 тоже находится
   внутри !ipv6 branch. Leading/trailing dot bracket literals больше не могут
   стать валидными посредством normalizeHost.
2. cpp210: percent spelling original bracket IPv6 явно отвергается **до**
   decodeHost; корректный once-only DNS host decoding не изменён. Это закрывает
   прежнюю возможность превратить encoded dot/colon/digit literal в допустимый
   адрес и не вводит новый DNS restriction. Scope IDs остаются refused, как
   было определено approved native representation boundary.
3. cpp215: strict readAddress проверяет IPv6 без dot correction. Формы
   `[.2606:4700::1111]`, `[2606:4700::1111.]` и double-edge dot дают отказ
   до CreateUri. Uppercase hexadecimal корректно lowercase, valid IPv6/global/
   mapped policy остаётся прежней; URI suffix/port/globalAddress не переписаны.
4. CalendarMeetingUrlTests33–42: добавлены leading/trailing/both dots,
   percent digit/colon/dots и `%00`/`%7f` DNS host negatives; каждый проверяется
   helper **и facade**. NativeSettingsBridgeTests1032–1033 дополнительно
   закрепляет dot/encoded-colon refusal через existing facade suite.
   Existing valid DNS/global/mapped IPv6 positives сохранены в обоих tests.
5. CalendarMeetingUrlTests65–67: invalid raw UTF-8 cases теперь включают lone
   continuation80, overlongC0AF, encoded surrogateEDA080 и above10FFFF F4908080.
   Assertions не меняют ASCII-only ограничение portable adapter и не выдают его
   за Windows Unicode acceptance proof. Native путь проверяет strict conversion.

M1 исправлен минимально внутри существующего helper, без нового parser/service,
не через ослабление отрицательных expecteds. Дополнительных C/H/M findings
в этом fix slice не обнаружено. Ponytail-only: Lean already. Ship.
Это оценка минимальности, не разрешение release/runtime handoff.

### Разделение source verdict и test receipts

Main сообщил tests-first focused BOTH RED на dot input до fix. Main также
сообщил для **предыдущих** product bytes native focused2/2, corpus141/141 и
full44/44 PASS197.33s. Эти результаты снимают прежнюю неподтверждённость
GetHost representation в том native run, но не являются fresh PASS трёх
изменившихся файлов. Reviewer не запускал Windows/probes или новые test jobs.
Текущие portable41/native44 rebuild/rerun на момент этой квитанции **pending**;
их итог будет отдельным Main evidence. Ранее reviewer portable2/2 также
исторический, не повторный run текущих assertions. Никакого вымышленного GREEN.

**Актуальный bounded SOURCE verdict: Approved; C0 / H0 / M0; M1 CLOSED.**
Code/source blockers после этого узкого recheck отсутствуют; fresh execution
validation ещё не подтверждена. Source approval ограничен текущим URL helper,
facade и указанным fix/test diff с прежними proof fences; он не закрывает
launcher/owner/bridge/installed/T119 и не утверждает whole Windows readiness.
Единственное reviewer изменение — append этой квитанции в тот же report.
Product/norm/tasks/GH/commits/install/build/VM writes не выполнялись.
