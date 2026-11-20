# T119 Round234: URL policy pre-code gate

**Purpose**: независимая ограниченная оценка окончательного дизайна общего
HTTPS validator до product edits; не source/runtime/launcher приёмка.
**Created**: 2026-10-04.
**Feature**: `../spec.md` FR-002/005/006; `../contracts/windows-native-web-bridge.md`
§10 URL; `../plan.md` T119; `../quickstart.md` §13; tasks T119.
**Lane**: reviewer-owned requirements/design gate существующего high-risk
Active Spec Kit slice. Единственный разрешённый output — этот файл.
**Review Ownership**: только независимый reviewer оценивает markers.
`[x]` означает качество определённых требований/дизайна, не работающий код,
пройденный native test или полный T119. `$speckit-implement` читает состояние
gate и не меняет markers.

## Полнота и ясность требований

- [x] CHK001 Определены ли одна shared validation authority, owned validated result и отсутствие parallel legacy policy/launch/network/auth side effects? [Completeness, Plan T119:1176–1182, bridge §10]
- [x] CHK002 Полностью ли определён отказ invalid UTF-8 и всех Unicode control/format scalars во всём raw URL и once-decoded host, включая supplementary range, без неподтверждённого равенства native classification и Swift? [Security, bridge §10, Gap]
- [x] CHK003 Однозначны ли absolute HTTPS, userinfo/backslash authority/empty host refusal, IPv6 syntax и port0..65535, включая empty/invalid/overflow port? [Clarity, bridge §10:432–438]
- [x] CHK004 Однозначно ли отделены original authority и suffix: strict percent-decode host ровно один раз, refusal decoded delimiters/residual escape ambiguity, сохранение path/query/fragment bytes без общего unescape? [Security, bridge §10, final design]
- [x] CHK005 Определена ли native IDNA normalization без собственного Punycode, иных DNS restrictions или внешних dependencies, с отказом conversion/normalization errors? [Consistency, pinned Mac/corpus, final design]
- [x] CHK006 Задана ли гарантия согласованности проверенного native parsed host/userinfo/port и возвращаемой canonical ASCII authority с original suffix, без возврата непроверенного original host? [Security, bridge §10, final CreateUri design]
- [x] CHK007 Полна ли exact frozen Python3.13 global/non-global policy с exceptions, numeric IPv4 и mapped IPv6, без сокращённой private-only проверки? [Consistency, pinned Mac/corpus141]
- [x] CHK008 Сохранены ли DNS fallback при non-IP и запрет DNS lookup/pinning promises, без произвольного allnumeric/singlelabel/local DNS denylist? [Coverage, pinned Mac addressBytes, bridge §10]
- [x] CHK009 Определены ли raw8192 UTF-8 byte limit, suffix preservation и отсутствие init-apartment/global-setting side effects, с native API/RAII failures fail closed? [Bounds, bridge §10, final design]
- [x] CHK010 Явно ли описаны влияния facade на все existing callers/tests и отделён ли still-legacy AppMain launch от принятого validator среза? [Traceability, Plan T119, current Presenter/AppMain/tests]
- [x] CHK011 Измеримы ли Windows production-path proof на unchanged141 corpus и honest ASCII-only portable coverage, без выдачи адаптера за native IDNA/parser parity? [Measurability, Quickstart §13, pinned corpus]
- [x] CHK012 Явно ли оставлены последующие source review, launcher/owner/bridge/current/installed gates открытыми, без functional handoff/T119 completion? [Coverage, Tasks T119, Constitution VI]

## Notes и снимок

Критерии сгенерированы unchecked по speckit-checklist template; независимая
оценка ниже выполняется по прямому запросу пользователя. Полностью лично
прочитаны speckit-checklist и ponytail-review SKILL, applicable AGENTS/index,
spec-kit-flow и constitution. Before/after checklist hooks содержат только
disabled commit, не исполнялись. Prerequisites указали текущий Feature 200.
Root routing/guidance прочитаны, не исправлялись. Предыдущий transport,
storage, весь task program и исторические reports заново не ревьюились.

Canonical repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`;
branch `codex/200-windows-followup`; свежо проверенный HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Лично прочитаны текущий bridge §10, relevant spec/plan/quickstart/tasks,
safeMeetingUrl/parseIpLiteral и все найденные production/test callers;
AppMain indirect raw-URL consumer также прочитан. Frozen Git objects читались
через git show, без checkout/fetch/server edits.

| Опорный файл | SHA-256 |
| --- | --- |
| pinned `apps/macos/RecApp/Sources/Calendar/CalendarMeetingOpener.swift` | `05eef2ba53c10913747b314d3eca0aff8a29303c055189c58d2083c677e08652` |
| pinned `apps/server/tests/fixtures/calendar_join_host_policy.json` | `7c6731fe293226eb1033acb2c5acc930897134395e8d67ebc29cca7ba17757d1` |
| pinned `apps/server/src/twobrain_rec_server/calendar/conference_links.py` | `916010cbf242ea328afb40e27a881b7fe69cb181d98f5ef2abe030a7125ba093` |
| pinned `apps/macos/Shared/Tests/CalendarMeetingOpenerTests.swift` | `6ac834407c9a09af8068eb39b555cffdabed10030b57c66dc1298934b8955169` |
| current `apps/windows/RecApp/Shell/MeetingReminderModel.cpp` | `ad053893499165c639ce41c4a23115ff17a5bb3d775ec568ae311e8f8d4529b7` |
| current `apps/windows/RecApp/Shell/MeetingReminderModel.h` | `a0deb749442dafb7c2b9c17a5a2f48e4ef5f858d66d633bffe7cc072d95c437c` |
| current `apps/windows/RecApp/Shell/MeetingReminderPresenter.cpp` | `dd0bc9dee51329582e227fb164000cf6d4ba7188abd985985998f8dff5a33d56` |
| current `apps/windows/RecApp/AppMain.cpp` | `f534c2ef8944120ed535a9a09fbc681b49f391ee6cb68a06fab8d83935391dbd` |
| current `apps/windows/Tests/GrafWindowsContractTests/NativeSettingsBridgeTests.cpp` | `6e6653da1d3d0a3fd01cd005861be2d558e4bb042e0b8f611381af3523c282f7` |
| current `contracts/windows-native-web-bridge.md` | `127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4` |

Pinned revision для всех четырёх reference objects:
`721b5125d799ea798a4af0b3625e18d3c1109039`. Corpus полностью лично прочитан;
read-only count —141 cases, hash совпал с присланным. Main сообщил Swift
reference141/141 PASS и cold CreateUri S_OK без apartment; reviewer не
повторял native/Swift probes, builds или tests. Не использовались private URLs.

## Оценка только окончательного дизайна

Старые queued варианты Windows.Foundation.Uri, return AbsoluteUri и
allnumeric refusal — история уточнения, **не новые параллельные review rounds**.
Актуален Win32 SDK CreateUri с canonical host reassembly и unchanged suffix.

| Критерий | Решение и основание |
| --- | --- |
| CHK001 | PASS: один `Shell/CalendarMeetingOpener::validatedHTTPS(string_view)->optional<string>`; bool facade делегирует, старый validator/parseIpLiteral удаляются. Returned string owned; network/launch/auth отсутствуют. |
| CHK002 | OPEN H1: MB_ERR_INVALID_CHARS задаёт strict UTF-8, но GetStringTypeW(C1_CNTRL) и приведённый BMP probe не устанавливают full control/format scalar coverage. См. finding ниже. |
| CHK003 | PASS: common absolute HTTPS authority guards, userinfo/backslash/empty host refusal, bracket IPv6 actual syntax, decimal port0..65535. No scheme/EXE fallback. Port0 не смешивать с отсутствием порта через truthiness. |
| CHK004 | PASS: только original authority host once strict percent-decode; decoded delimiters запрещены. Не применять Uri.UnescapeComponent к native Host, не decode suffix; `%25` не становится второй decoding pass. После normalization host должен оставаться single component без `%`, authority delimiters или пустоты; это часть заявленной canonical ASCII authority, не дополнительный DNS allowlist. |
| CHK005 | PASS: native IdnToAscii0, strict conversion, trim dots/lowercase; не устанавливать unassigned/raw-puny/STD3 restrictions, не писать Punycode или второй parser framework. Link normaliz/urlmon/oleaut32 — системные SDK libraries, не внешняя библиотека. |
| CHK006 | PASS design: CreateUri CANONICALIZE\|NO_PRE_PROCESS_HTML_URI\|NO_DECODE_EXTRA_INFO\|NO_IE_SETTINGS; проверяются HRESULT/Host, userinfo presence через HasProperty, port. OS canonical host, в том числе inet_aton forms, повторно IDNA-normalized при необходимости и проверен той же policy. Returned canonical ASCII host берётся из этого проверенного native результата; port сохранён из валидированного port field, suffix оригинальный. Требуется повторная stable parse проверка возвращаемого значения при source tests, не доверие исходному тексту. |
| CHK007 | PASS: frozen Mac содержит полные IPv4/IPv6 denied CIDRs и global exceptions, mapped-v6 делегирует IPv4 policy. Corpus включает boundaries, shared address space, documentation ranges, public exceptions и numeric variants. Не заменять эту таблицу только RFC1918/loopback denylist. |
| CHK008 | PASS: frozen Mac addressBytes failure явно DNSallow; frozen server также допускает fallback после ip_address/inet_aton failures. `256.0.2.1` не добавлять в новый denylist. Single-label conference/meeting.local допускаются; localhost/sub.localhost запрещены. Bracket invalid IPv6 — syntax refusal, не DNS fallback. DNS не выполняется; public scoped IPv6, непредставимый native parser, означает OS representation refusal, не новую is_global policy. |
| CHK009 | PASS design: bound8192 определён для raw UTF-8 input, как в Mac validator/bridge target; suffix byte-preserved без native AbsoluteUri expansion/extra-info decoding. Helper не init/uninit COM apartment и не изменяет registry/IE settings. ComPtr/BSTR RAII, explicit length/HRESULT checks, отсутствие host property не success. Bound исходника не выдавать за автоматически доказанный bound любого IDNA-expanded output; source review должен проверить bounded allocation/returned value. |
| CHK010 | PASS scope: Presenter112/172 использует bool только как projection/action eligibility; AppMain3663–3664 ещё передаёт event.meetingUrl в ShellExecuteW. Его migration/fresh resolver/current owner/launcher НЕ приняты здесь. Tests893–899 и1030–1050 имеют старые policy expectations, подлежащие синхронизации, не сохранению parallel legacy validator. |
| CHK011 | PASS design: full unchanged141 cases должны пройти Windows production path; portable только ASCII/native inet_aton/inet_pton. IDN/Windows URI proof не выводится из portable PASS. Future guards/controls/bytes/return value checks описаны ниже как proof fences, не выполненные tests. |
| CHK012 | PASS: новый validator не получает launch authority. Source delivery review, resolver integration/current owner/lease/timer, bridge, candidates/recovery/Record и exact installed gates остаются впереди. Нормативный предыдущий12/0 не заменяется и не редактируется. |

## H1 — supplementary Unicode control/format coverage не установлена

**High, блокирует CHK002 и полный pre-code PASS. Это finding полноты дизайна,
не объявленная выполненная exploit/Windows implementation проверка.**

Pinned Mac отказывает по raw unicodeScalars через CharacterSet.controlCharacters.
Окончательный Windows дизайн обещает полный raw/decoded-host control refusal,
но его единственный классификатор — GetStringTypeW(C1_CNTRL). Присланный probe
U+0085/00AD/200B/200E/202E/2060/FEFF и U+2028 полезен, но весь набор относится
к BMP и не определяет поведение supplementary Cf, например U+E0001/U+E0020
в path/query/fragment. Strict UTF-8 conversion отсекает malformed encoding,
но сама по себе не запрещает эти valid Unicode scalars. IdnToAscii занимается
host, не whole suffix; NO_PRE_PROCESS_HTML_URI не является control rejection.

Microsoft прямо предупреждает, что GetStringTypeW может иметь неполные/
устаревшие сведения, особенно для supplementary characters:
[GetStringTypeW documentation](https://learn.microsoft.com/en-us/windows/win32/api/stringapiset/nf-stringapiset-getstringtypew).
Поэтому из этого API и BMP samples нельзя вывести заявленную full Unicode
control parity. Reviewer не запускал ещё один native probe и не утверждает,
что конкретный test уже показал acceptance этих scalars.

Нужно одно узкое design решение до кода: определить scalar-complete control/
format rejection, согласованное с pinned Mac, включая supplementary range.
Допустимо минимально дополнить native classification явной, закреплённой
coverage недостающих ranges/другим уже допустимым native property механизмом;
не требуется новый Unicode framework или blanket rejection всех non-BMP
символов. Последнее запретило бы обычные допустимые символы без основания.
Future native assertions должны включать control в suffix и once-decoded
host, плюс допустимый supplementary non-control. Нельзя закрыть H1 только
новым общим заявлением «C1_CNTRL совпадает со Swift» без покрытия этой границы.

## Узкие design решения и conditional implementation proof fences

1. Единственная normal form: validated original host → once decode → native
   IDNA → CreateUri → validated OS host/port/no-userinfo → canonical ASCII
   authority + **original** path/query/fragment suffix. Не возвращать исходный
   authority, native decoded query, DisplayUri или whole canonical path вместо
   исходного suffix. Returned value при повторном parsing должен иметь тот же
   allowed host/port, HTTPS и отсутствие userinfo. Reconstructed host снова
   должен быть nonempty single component; residual percent/delimiter ambiguity
   не игнорировать. Это гарантия данного SDK path, не всех сторонних browsers.
2. GetHost S_FALSE/empty, failed HasProperty/GetPort/normalization, embedded NUL
   или length mismatch — refusal; пустое userinfo тоже нельзя разрешать только
   проверкой непустого username/password. Preserve absent vs explicit0/443/
   nondefault port согласно original request, не смешивать с SDK default port.
   Link/CMake/native test compilation требуют будущего source evidence.
3. Shared fixture **не менять**. Existing tests должны перестать требовать
   запрет fragment и permit documentation IP: `2001:db8::/32`, `192.0.2.0/24`
   и mapped documentation IPv4 запрещены actual global policy. Для проверки
   syntax использовать global allowed addresses, оставляя invalid bracket
   cases negative. `256.0.2.1` переносится в DNS-allowed expectations по pinned
   reference; старое arbitrary numeric refusal не является нормой.
4. Windows native tests: unchanged141, percent-host/fullwidth host, once-decode
   `%25`/malformed hex/decoded delimiters, IDNA failures, port0/65535/65536,
   userinfo presence/empty userinfo, invalid UTF-8, H1 boundary,8192/8193 input,
   reserved query/fragment escapes (`%2B/%26/%23/%25`), stable returned authority
   и preserved suffix. Это **не выполненные** испытания. Portable ASCII subset
   явно отделён от full native test, без conditional weakening corpus expected.
5. Facade — projection compatibility, не permission to launch stored URL.
   Existing AppMain raw ShellExecute остаётся известным не принятым T119 путём;
   здесь его не исправлять и не выдавать за migrated opener. Следующий launcher
   обязан потреблять свежий resolver target и returned validated URL с current
   fences, а не boolean validation плюс original raw string.

Выбранные SDK flags имеют описанные ограничения, в частности no-extra-info
decode и no-HTML-preprocess; canonicalization может менять host/path, поэтому
отдельное suffix preservation и проверки returned representation обязательны:
[CreateUri documentation](https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/ms775098(v=vs.85)).
Native IDNA API и его flags не заменяются новым encoder:
[IdnToAscii documentation](https://learn.microsoft.com/en-us/windows/win32/api/winnls/nf-winnls-idntoascii).

Ponytail: proposed single helper + delegating facade + SDK parser/RAII —
минимальная разумная форма. Старые parseIpLiteral/URL validator удаляются;
existing normalized helper сохраняется: строки256–257/273 используют его
для owner/workspace/origin и snapshot matching, не только для URL. Не нужен второй
HTTP client, DNS service, generic launcher или свой Punycode. Экономия кода
не отменяет H1 и native proof fences.

## Терминальный результат

**C0 / H1 / M0. 11 supported / 1 unsupported criterion (CHK002).**
Полный URL pre-code gate **не PASS** до узкого уточнения scalar control coverage.
Остальной окончательный дизайн разумен при перечисленных implementation
proof fences; никакой новой product policy/whole Feature 200 review не требуется.
Отчёт не закрывает T119/launcher/owner/bridge/installed/source gates. Reviewer
не менял code/spec/plan/tasks/старые markers/GitHub, не запускал build/tests,
native probe/launch/network, не трогал dirty storage или пользовательскую работу.

## Квитанция H1: native ICU и документированное отклонение от дефекта эталона

2026-10-04, тот же Round234, только H1/CHK002. Предыдущие H1 OPEN и итог
11/1 выше сохраняются как история; эта квитанция задаёт актуальный результат.
Предшествующий SHA256 этого отчёта:
`734d408c5f918279fdb505671909934f9b622b42478166771b2e6eb341e7f3aa`.
Свежо проверены canonical branch `codex/200-windows-followup` и HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; product edits не выполнялись.
Другие 11 решений и markers не изменены и заново целиком не ревьюились.

### Принятое исправление классификатора

GetStringTypeW полностью исключается из предложенного дизайна. Windows path
использует только системный ICU C API через Windows SDK `<icu.h>`/`icu.lib`.
Combined `icu.dll`/import library доступны с Windows10 1903; их использование
не требует CoInitializeEx. Текущий FR-001 начинается с Windows10 22H2
build19045 и supported Windows11, поэтому pre1903 fallback не нужен:
[Microsoft native ICU](https://learn.microsoft.com/en-us/windows/win32/intl/international-components-for-unicode--icu-).
Никаких download/bundled ICU, внешнего framework или supplementary classifier.

Весь raw URL и original host после единственного strict percent-decode проходят
строгий UTF-8 → UTF-16 через MultiByteToWideChar(MB_ERR_INVALID_CHARS) с explicit
length, checked conversion result/размером, без остановки на embedded NUL.
Обход — по полным scalars, не по отдельным wchar_t: U16_NEXT либо минимальный
paired-surrogate decode с проверенными границами. Значение вне0..10FFFF,
непарный surrogate или невозможная длина/пара дают отказ, не U+FFFD replacement.
U16_NEXT сам по себе может вернуть unpaired surrogate, поэтому guard обязателен:
[ICU UTF-16 iteration](https://unicode-org.github.io/icu-docs/apidoc/released/icu4c/utf16_8h.html).

Для каждого допустимого UChar32 отказ точно при
`u_charType(scalar) == U_CONTROL_CHAR || ... == U_FORMAT_CHAR` (Cc/Cf).
Это scalar-based C API, stable с ICU2.0:
[ICU u_charType](https://unicode-org.github.io/icu-docs/apidoc/released/icu4c/uchar_8h.html).
Не заменять его u_iscntrl-only, blanket non-BMP refusal, общей категорией C
или GetStringTypeW supplement. Non-control scalar сам по себе не является
причиной отказа; остальные syntax/IDNA/native URI/security guards сохраняются.
Bounds raw8192, checked native output, оригинальный suffix и final URI/host
consistency остаются прежними. Отсутствие COM init здесь относится к combined
ICU; прежние CreateUri proof fences также сохраняются.

### Новое контрдоказательство: полного Swift classifier parity нет

Main сообщил full-scalar scan: native ICU с Unicode15.1 —235 Cc/Cf scalars,
23ranges; Swift CharacterSet.controlCharacters —24970 scalars,533ranges.
Первые23ranges совпали, но Swift дополнительно возвращает true для множества
Plane14 non-controls. Эти полные counts — evidence Main, reviewer scan не
повторял, Windows probe не запускал. Ранее сообщённое совпадение девяти samples
остаётся верным, но **не доказывает** равенство полных множеств235/24970.

Reviewer лично выполнил только focused read-only Swift/Foundation проверку:

| Scalar | Swift generalCategory | CharacterSet.controlCharacters |
|---|---|---|
| U+E0100 | nonspacingMark | false |
| U+E0101 | nonspacingMark | true |
| U+EFF01 | unassigned | true |

Apple определяет controlCharacters через Cc/Cf:
[Apple Foundation API contract](https://developer.apple.com/documentation/Foundation/NSCharacterSet/controlCharacters).
Следовательно, наблюдаемое дополнительное membership Mn/Cn не является
основанием расширять Windows control policy. Здесь документирован дефект
наблюдаемого reference/API поведения, **не установлена его внутренняя причина**
и не объявлен универсальный результат для всех версий Foundation.

### Правомерность узкого отклонения и будущие доказательства

Лично прочитаны product-gates `UX Reference Fidelity` и constitution §VII:
они требуют документированного отклонения, если буквальное воспроизведение
копировало бы известный дефект. Bridge §10 требует HTTPS без controls, не
закрепляет дополнительный Plane14 bitmap с ложными Mn/Cn отказами.
Поэтому принимается **явное known-reference-defect deviation**: Windows
отказывает Cc/Cf через native ICU, но не воспроизводит ложные отказы Swift
для supplementary non-controls. Это не silent parity claim и не ослабление
userinfo/host/IP/UTF-8/length/current-owner fences. В пределах этого решения
отдельное новое product-owner approval guidance не требует; прямой запрос
пользователя определяет рассматриваемый вариант. Оно не разрешает другие
отклонения от политики или изменение Mac/server/shared expected corpus.

Future production-path tests должны показать отказ U+E0001/E0020/E007F/
13430/1BCA0/1D173 в suffix и once-decoded host; ordinary valid suffix positives
U+1F600/E0100/13440 проверяют отсутствие blanket supplementary denial.
Добавить различающий false-positive regression U+E0101 в valid suffix
(U+E0120 — ещё один Main sample): classifier не должен копировать Swift true.
Из этого не следует обязательная IDNA-пригодность emoji или любого Cn host.
Не менять unchanged141 shared corpus; сохранить Windows full production-path
proof и честно ограниченный portable ASCII adapter. Нативные tests должны
фиксировать ОС/SDK/system ICU в supported matrix: текущая upstream ICU reference
не доказывает установленную Unicode version на каждой поддерживаемой ОС.
Main cold ICU /W4 /WX probe и совпавшие девять Swift outcomes — полезные
diagnostic evidence, не готовые tests ещё не написанного product helper.

Guidance SHA256: product-gates
`e5c39fb473dcf785f417b9785b0d6ba17fe23026906eedc08c0620c7a6f5d097`;
constitution
`d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.
Current spec SHA256 unchanged:
`0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2`.

**Актуальный terminal verdict: C0 / H0 / M0; H1 CLOSED; 12 checked / 0 unchecked.**
URL pre-code design gate **PASS**, с явным defect deviation и перечисленными
будущими implementation proof fences. Изменён только CHK002 marker и добавлена
эта квитанция в тот же reviewer-owned файл. Не source approval и не functional
T119/launcher/owner/bridge/installed приёмка. Ни code/norm/tasks/GitHub edits,
ни новые product test/build/Windows probe jobs reviewer не выполнял.
