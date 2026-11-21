# T119: независимый source review минимального path/response

Дата: 2026-10-04. Reviewer-owned результат, без forked history.

**Терминальный вердикт: Approved для ограниченного C/H source gate;
C0 / H0 / M1. Блокирующих Critical/High замечаний нет.** Единственное Medium
ниже — воспроизводимый пробел совместимости неизвестных escaped JSON keys,
не разрешение на запуск и не расширение этого обзора до всего T119.
Полное утверждение «любые дополнительные поля с корректным JSON принимаются»
пока не доказано и имеет этот конкретный контрпример.

## Область и источник

Canonical repository лично проверен read-only:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
Branch: `codex/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Reviewed state — рабочие байты трёх файлов, а не только committed HEAD:

| Файл от корня repo | SHA-256 после NUL fix |
| --- | --- |
| `apps/windows/RecApp/Upload/DesktopApiClient.h` | `af7ded9a6001609fe331b722eb29071a7497a60c59c7a26b3b7c891bae31c9fb` |
| `apps/windows/RecApp/Upload/DesktopApiClient.cpp` | `4f3c8e9896d9b9cc065c634834645c7c90d5004bb64d1da98c08ffece5526a30` |
| `apps/windows/Tests/GrafWindowsCoreTests/ContractFixtures.cpp` | `a2b3cb907361d2a48af9bf8baa97f9c1b485f44bc921c5f4cb48f09a0c12acc5` |

Лично прочитаны local diff, три исходных файла и связанные вызовы изменённых
helpers внутри DesktopApiClient. Применены полностью прочитанные
`code-reviewer` и `ponytail-review` SKILL.md. Сохранён лично прочитанный
нормативный контекст предыдущей requirements review: applicable AGENTS,
guidance index/worktrees/Spec Kit/product gates/validation, constitution,
активные spec/plan/tasks/quickstart/data-model и bridge §10. Risk lane:
bounded source review существующего high-risk Active Spec Kit slice T119;
единственная постоянная запись reviewer — этот новый отчёт.

Ни storage diff, ни остальные исходники Feature 200 здесь не пересматривались.
Их dirty bytes проверяются только хешами для сохранности. Нет изменений кода,
норм, tasks, GitHub, commit, install, VM, устройств или установленного пакета.
Локальная проверка использует существующую временную portable-сборку и
отдельный временный проверочный executable, не добавляет repository helpers.

## Подтверждённые свойства среза

| Свойство | Проверенное основание |
| --- | --- |
| Path не допускает подстановку query/path | cpp:516–522,565–568: ровно UUID36 с hyphens, только ASCII hex; A–F нормализуются; path формируется из проверенного UUID. Неверный вход возвращает пустую строку. |
| Calendar UUID не становится account authority | Nil разрешён локально в calendarEventId, accountId не изменён и всё ещё отвергает nil/uppercase. Это проверено отдельными отрицательными тестами. |
| Только три известных обязательных scalar strings | cpp:570–583: root lookup event_id/provider_family/https_url, calendarString, expected/response UUID equality после нормализации. Missing/type/duplicate/trailing/mismatch дают nullopt. Nested одноимённые поля не замещают root authority. |
| Ограничения размера | До JSON read whole response≤65536 raw bytes. Известные строки имеют raw cap65536, затем family≤64 и URL≤8192 decoded UTF-8 bytes. Escaped URL не ограничивается прежним raw16384; fixture проверяет 8192 decoded ASCII из raw49152. |
| Unicode проверяется и в ignored metadata | JsonReader(json,8,true) проверяет каждый string/key через существующий calendarString. Invalid UTF-8, overlong, surrogate scalar, >U+10FFFF, truncated sequences, lone/malformed surrogate escapes отвергаются; корректные пары декодируются. Unknown values не становятся policy. Исключение совместимости keys — M1 ниже. |
| NUL fix правильно разделяет syntax и known values | cpp:23–24,71–72,507,578: allowNul=false по умолчанию; true только в строгой syntax-проверке JsonReader. Escaped U+0000 в неизвестном значении принимается, в known family/URL — отказ. Literal unescaped NUL остаётся невалидным JSON везде. |
| Legacy defaults не изменены | JsonReader default depth32/strictStrings=false; старые jsonObjectFields/jsonArrayValues используют defaults. CalendarReminder calls сохраняют calendarString raw16384/allowNul=false. Body builders, deletion/upload/auth/transport логика вне добавлений неизменна в diff. Portable regression suite GREEN. |
| Lifetime и ресурсные границы | JsonReader views живут только пока живёт вход decode; возврат CalendarJoinTarget владеет строками. До parsing есть 64KiB cap, recursion bounded8; нет постоянного хранения/кэширования URL, логирования или side effects. Дополнительное Unicode декодирование bounded raw input, без новой библиотеки/parser. |
| Typed data не является разрешением | h:70–76 явно обозначает Untrusted resolver data. Family не выбирает приложение; URL строка не валидируется как разрешённый адрес. Даже "x" принимается как данные — намеренная граница. GET, redirect policy, owner/fences, launcher и Record этим diff не добавлены. |

## Finding M1 — escaped unknown keys отвергают корректный JSON

Severity: **Medium / P2, non-blocking для запрошенного C/H gate**.
Место: `apps/windows/RecApp/Upload/DesktopApiClient.cpp:129`, вызывается
новым decoder на строке574. Это унаследованный запрет JsonReader, который
новая response-функция теперь применяет к будущим неизвестным полям.

В ответе с корректными тремя известными полями добавление
`,"\u0065xtra":0` перед закрывающей `}` приводит к nullopt. Аналогично
extra value `{"\u0061":0}` отвергает весь ответ. Обе формы содержат корректные
JSON strings/Unicode; это не duplicate, не type/size/depth/UUID ошибка.
Прямой ключ `extra` и простой Unicode key принимаются. Причина —
`key.find('\\') != npos`, не проверка корректности Unicode.

Следствие: будущее дополнительное metadata, сериализованное с допустимым
JSON escaping имени, ломает декодирование известных полей. Это противоречит
заявленному намерению игнорировать дополнительные корректные JSON данные,
но не даёт лишних полномочий и не является security C/H. Bridge §10:378–385
закрывает payload; §10:407–415 не вводит запрет новых response fields.

Предлагаемое последующее исправление в Main-owned code: отделить старую
escaped-key policy от строгого response режима, не ослабляя legacy defaults,
known-field lookup и проверку decoded duplicate keys. Требуются RED/GREEN
для неизвестного escaped root key, escaped nested key и alias duplicate
(`extra`/`\u0065xtra`), а не разрешение дубликатов или новая библиотека.
Reviewer код и requirements не менял; M1 остаётся открытым на хешах выше.

## Проверки и их происхождение

Reviewer лично выполнил:

1. `cmake --build /tmp/graf-f200-calendar-build.gOxKwL --target ContractFixtures -j 2`
   — exit0; текущая Release-сборка up-to-date.
2. `ctest --test-dir /tmp/graf-f200-calendar-build.gOxKwL -R '^ContractFixtures$' --output-on-failure`
   — **GREEN 1/1**, exit0, повторено после проверки текущего build target.
3. `ctest --test-dir /tmp/graf-f200-calendar-build.gOxKwL --output-on-failure`
   — **39/39 PASS**, exit0. Это локальное portable regression evidence,
   не независимый review остальных исходников и не runtime acceptance Windows.
4. Отдельная программа из compiler stdin, собранная с текущим
   DesktopApiClient.cpp, существующим Sha256 object и flags
   `-std=c++17 -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -g`
   с явным MacOSX26.5 SDK — **54/54 PASS**, exit0, без ASan/UBSan diagnostics.
   Instrumented именно reviewed decoder/probe; не заявляется sanitization
   всех зависимостей. Дополнительно четыре наблюдения вне PASS counter:
   escaped root/nested key rejected, root+8 empty arrays accepted,
   root+9 empty arrays rejected.
5. Scoped `git diff --check` трёх файлов — exit0.

54 проверки включают unknown escaped/nested NUL, literal controls,
20KiB unknown string, malformed JSON/numbers/literals, максимальный Unicode
scalar/пару, некорректные UTF-8/surrogates/escapes в ignored values и key,
family64/66 UTF-8 bytes, URL8192/8196 UTF-8 bytes из surrogate pairs,
calendar nil path, account nil/uppercase refusal, legacy JSON defaults,
scalar depth8/9. M1 observations не включены в 54 PASS как успешная
совместимость: их фактический отказ явно записан выше.

Первый compile этой вспомогательной программы без явного SDK не нашёл
стандартный `<array>`; исправлена только команда с `-isysroot` существующей
сборки. Это ошибка настройки проверки, не source finding. Никакой установки.

История NUL сохранена: Main обнаружил проблему и добавил fixture;
reviewer лично воспроизвёл pre-fix CTest assertion exit8 на
`withExtra("\"\\u0000\"")`. После allowNul fix независимый GREEN подтверждён.
Первоначальный compile RED exit2 из-за отсутствующей API был сообщён Main,
не воспроизводился reviewer. Его не выдаём за собственное доказательство.

Main отдельно сообщил governance/bootstrap/diffcheck PASS и MSVC19.44
Release/x64 shared-source ContractFixtures build/test1/1 PASS, затем fresh
NTFS build exit0 с тестом в работе. Windows GetFileHash трёх файлов, по
сообщению Main, совпал с текущими canonical hashes. Reviewer не открывал VM,
не читал её build logs и не присваивает этим сообщениям статус лично
проверенной Windows приёмки. В последнем сообщении Main подтвердил также
завершённый fresh NTFS ContractFixtures **1/1 PASS**. Это обновление
сообщённых evidence, не новый запуск или VM-проверка reviewer.

При терминальной фиксации после interruption три исходных хеша, branch и
HEAD повторно прочитаны и совпали с таблицей выше. Код/requirements/тесты
не переоценивались заново; новых Windows или 39-test runs не выполнялось.
Main-owned Round232/F200 notes не являются source writes этого reviewer.

## Недостающие постоянные edge-case tests

Это не дополнительные C/H findings. В ContractFixtures уже есть основные
path/type/duplicate/UUID/byte/depth/Unicode/NUL checks, assert не отключён
Release NDEBUG. Полезно закрепить там обнаруженный M1 и несколько сценариев,
которые пока покрыты только независимой временной программой: nested NUL,
raw metadata string>16384, surrogate/invalid UTF-8 в ignored nested values
и key, многобайтовые decoded limits64/8192, account nil/uppercase unchanged.

Depth использует существующую семантику JsonReader: root object depth0,
каждый вложенный value повышает счётчик. Семь массивов со scalar accepted,
восемь со scalar rejected; восемь массивов с пустым innermost accepted,
девять rejected. Это ограниченное, не бесконечное чтение; «8» не следует
объявлять восемью контейнерами включая root без уточнения соглашения.
В постоянных fixtures отсутствуют empty-object/empty-array граничные пары;
их стоит добавить, сохраняя согласованную семантику existing reader.

## Минимальность и сохранённые требования

Ponytail-review результата формы diff: **Lean already. Ship.** Здесь это
только отсутствие рекомендаций удалять код/добавлять абстракции в трёх
файлах, не разрешение выпускать приложение. Использованы existing
JsonReader/calendarString/accountId; нет нового decoder класса,
зависимости, сети, opener, fallback или speculative registry. Security
validation и тесты не считаются избыточностью.

Fresh hashes нормативного снимка совпали с завершённой requirements review:

| Документ | SHA-256 |
| --- | --- |
| `spec.md` | `0073b6f2ff8e3e9f07389473cf7fc0f5c2eaf146961f08426d140163dd5d4fe2` |
| `plan.md` | `5b5996e9c35a185c470f23b6e9228ebe7d46337513741505ba77ffcfe88928e8` |
| `tasks.md` | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| `quickstart.md` | `3045f730bc59bbc3abdeaf736a7e7e347825bdf6e8878bdaa10a34d293113acc` |
| `data-model.md` | `dc91ac60f180e6221e85917c9a91e510e34008430dfb457e7a7cbeb97162e0a7` |
| `contracts/windows-native-web-bridge.md` | `127356a14df140364ce619554bcc42cab03286262065afa40c1fcdb73ac51ff4` |
| `.specify/memory/constitution.md` (от repo root) | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| `checklists/review-2026-10-04-calendar-join-gate.md` | `d3562fdb494858de208509a721a82c34aa4e4dee4bfd976f908b3946fda37f5d` |
| `checklists/review-2026-10-04-packed-package-gate.md` | `a93a08a1fda433a2a4523161edc39d6d0547eee8ed7cc5d42bc66675a5dc06f2` |

Оба gate фактически перечитаны: по **12 checked / 0 unchecked**;
их C0/H0/M0 — качество требований, не source implementation. M1 здесь
относится к реализации нового decoder, не пересматривает requirements PASS.
Прежние original112/0, tracker #7540 OPEN и canon300PASS не используются
как доказательство нового кода. Новых критериев/markers не добавлено.

**Итог: минимальный path/response C/H gate завершён PASS, C0/H0/M1;
M1 открыт, unrestricted unknown-valid-JSON compatibility не принята.**
Fresh authenticated GET, redirect/status handling, worker deadline/lifetime,
current owner/token/document fences, bridge/shim/reply, URL validator/native
preflight/browser recovery/actual opener, native-only Record и installed
matrix остаются вне этого diff и вне source acceptance. Не заявлены
functional handoff, готовность T119, Feature 200, merge/release или
наблюдаемый запуск Телемоста. Этот отчёт — единственная постоянная запись
reviewer в данном source-review шаге.

## Приложение: повторная оценка M1 и key-view lifetime — 2026-10-04

**Новый терминальный вердикт: Approved для минимального T119 path/response
source slice, C0 / H0 / M0. M1 CLOSED на текущих байтах ниже.** Новых
correctness/security/lifetime findings в этом ограниченном исправлении нет.
Первый C0/H0/M1 verdict и контрпримеры выше сохранены как история, а не
удалены или задним числом объявлены PASS. Новое приложение заменяет только
их актуальный статус для нового снимка, не принимает весь T119.

До добавления приложения исходный отчёт перечитан; его SHA-256:
`0406e3f9602c0d55f69cef69cb922badcc1c8db8363fc21e3539cd47af6f9cf8`.
Запись append-only; прежний текст должен остаться точным префиксом файла.

Canonical repository, branch и HEAD прежние и лично проверены read-only:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`,
`codex/200-windows-followup`,
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Main подтвердил стабильность исправления; reviewer затем сверил хеши:

| Исходный файл от repo root | Текущий SHA-256 |
| --- | --- |
| `apps/windows/RecApp/Upload/DesktopApiClient.cpp` | `05f5eb4bd5e47e5ec2faf184d4bf9154f3625a3d606119b25cce1a388aa1060c` |
| `apps/windows/RecApp/Upload/DesktopApiClient.h` | `af7ded9a6001609fe331b722eb29071a7497a60c59c7a26b3b7c891bae31c9fb` |
| `apps/windows/Tests/GrafWindowsCoreTests/ContractFixtures.cpp` | `3c9f3022e658602952a0154971de6ea91838cff6cd0427d8decdc58a97ac3992` |

### Исправление и владение данными

Лично повторно прочитан diff этих трёх файлов, изменённые object/read/decoder
участки и все JsonReader call sites в DesktopApiClient.cpp. Header неизменён.
Повторно полностью прочитан и применён code-reviewer; проверка минимальности
не требует новой архитектуры или библиотеки. Требования, storage и прочие
части Feature 200 заново не исследовались.

- cpp:130–136: только strictStrings=true декодирует имя через существующий
  calendarString с raw cap входа и allowNul=true. Валидные escaped root/nested
  unknown keys теперь принимаются. Known escaped field распознаётся по
  decoded name; никакие поля не превращаются в launch authority.
- Duplicate detection работает по owning std::string после декодирования:
  `extra`/`\u0065xtra`, `a`/`\u0061`, known `event_id`/`\u0065vent_id`
  отвергаются. Проверены также обратный порядок alias и Unicode/NUL aliases.
  Дубликаты определяются внутри одного объекта; разные вложенные объекты
  могут иметь одинаковые имена. Это не новый запрет неизвестных полей.
- cpp:133,152: root keys принадлежат member rootKeys_; std::set insertion
  не инвалидирует существующие элементы, их строки не меняются и не стираются.
  string_view в fields_ указывает на owning set element, не на временную
  decoded optional или локальную строку. Это верно и для коротких строк,
  и для длинных heap-backed key names.
- Nested decodedKeys принадлежит одному вызову object(depth). Nested key
  views не сохраняются в root fields_, поскольку emplace разрешён только
  depth==0. Set живёт до окончания разбора объекта, включая рекурсивный value;
  при выходе из object наружу не возвращаются views его локальных ключей.
- cpp:584–594: strict reader имеет имя и живёт до окончания извлечения
  всех known values/проверок/создания результата. fields — отдельная копия
  карты borrowed views, не владелец root keys; она уничтожается раньше reader.
  CalendarJoinTarget возвращает owning strings, не reader views. Замена
  named reader временным `JsonReader(...).read()` здесь была бы ошибкой,
  но текущий код её не содержит.
- Legacy jsonObjectFields/jsonArrayValues остаются на strictStrings=false:
  старые raw-key views/escaped refusal сохранены на строке137. Поведение
  accountId, known NUL refusal, bounds/depth/path и URL-as-untrusted-data
  этим исправлением не изменено. Новые owning keys ограничены прежним
  whole response cap64KiB; без неограниченного ввода или нового parser.

### Проверки исправления

Main сообщил семь RED assertions, первое падение valid escaped root key
CTest exit8, затем исправление и GREEN1/1. Reviewer не воспроизводил этот
исторический RED; лично прочитал все семь новых assertions на строках221–230
и выполнил focused CTest текущего ContractFixtures — **GREEN1/1, exit0**.
Scoped git diff --check трёх исходных файлов — exit0.

Отдельная независимая программа из compiler stdin с текущим
DesktopApiClient.cpp, прежним Sha256 object и ASan/UBSan, C++17,
Wall/Wextra/Wpedantic/Werror, явным MacOSX26.5 SDK — **24/24 PASS, exit0**,
без sanitizer diagnostics. Проверены root/nested escaped keys, decoded
duplicates в обоих порядках, escaped known lookup, legacy refusal,
NUL/invalid surrogate/Unicode/slash aliases, quote/backslash/empty key,
одинаковые decoded names в разных объектах. Отдельно вставлены 500 длинных
escaped root keys с вложенными объектами после escaped known field:
known lookup и returned owning strings корректны, в том числе после
перезаписи исходного buffer. Эти результаты дополняют source lifetime
analysis, а не заменяют его.

M1 regression scenarios теперь закреплены в постоянных ContractFixtures.
Оставшиеся рекомендации из первого отчёта о дополнительных многобайтовых,
empty-depth и stress тестах не являются открытыми C/H/M findings;
500-key stress/обратный порядок aliases проверены независимой программой,
но не добавлялись reviewer в repository tests.

39-test suite, Windows, governance/bootstrap или требования в этой повторной
оценке не запускались/не пересматривались. Обновлённые full portable и
Windows NTFS rebuild/hash checks на момент сообщения Main ещё выполнялись;
они не присвоены этому приложению как лично проверенное evidence.

**Итог повторной bounded source review: PASS / Approved, C0/H0/M0;
M1 закрыт, key-view lifetime подтверждён, source blockers отсутствуют.**
Не расширяет первый review scope до GET/HTTP/redirect/current fences/URL
policy/launch/Record и не подтверждает functional handoff, T119 completion,
installed acceptance или release. Reviewer только добавил это приложение
в собственный отчёт; код, нормы, tasks, GitHub и чужие dirty файлы не менял.
