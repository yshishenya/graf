# T119 Round237: независимый SOURCE review strict decoder-only

Дата: 2026-10-05. Reviewer-owned, current canonical dirty bytes.

**Approved для decoder-only source slice: C0 / H0 / M0 / L1.**
Блокирующих C/H/M findings не обнаружено. Один L1 — небольшой конкретный
пробел положительных Unicode compatibility regressions, не дефект реализации
и не условие приёмки будущего host/owner wiring.

## Scope и основание

Repo: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD freshly read: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Точный verdict привязан к четырём SHA-256 ниже, а не утверждению, что dirty
implementation уже входит в HEAD.

Лично полностью прочитаны новые CalendarJoinIntent/declarations,
decodeCalendarJoinIntent и calendarJoinEnvelopePayload, полный новый
CalendarJoinWireTests.cpp и строка CMake регистрации. Перечитаны используемые
JsonReader, calendarString, calendarEventId/accountId и текущий runtime
allowlist, но старые transport/launcher/storage срезы не проверялись заново.
Две новые функции оценены против принятого exact wire/owned-data контракта.
Предыдущие изменения в HEAD diff не выдаются за новый decoder-only diff.

Requirements gate 5/0 и M1 closure прочитаны; его exact SHA-256:
`26dd2627afe57c54a42b53d5e5cfd25e90c4d61222eb408f7724c33a24b1411c`.
Нормативный cap/replay M1 уже CLOSED, но его **реализация** в host не относится
к этому срезу и здесь не требуется/не принимается. Использован ранее прочитанный
неизменный applicable AGENTS/guidance/constitution контекст. Полоса проверки —
bounded source review существующего high-risk T119, не downgrade risk lane.

Полностью прочитаны и применены code-reviewer и ponytail-review. Main analyze,
issue OPEN, TDD и PASS сообщения не подменяют независимое чтение текущего source.

## Проверенный фактический поток

| Граница | Вывод по текущим исходникам |
| --- | --- |
| Exact intent | DesktopApiClient.cpp:597–614 принимает только calendar_join/calendar_join_cancel. Join требует ровно три decoded root поля и action="joinCalendarEvent"; cancel — ровно два eventId/requestId. Недостающие, лишние, неверного типа или неправильного action поля не проходят. Полученный CalendarJoinIntent содержит лишь две owned строки, не URL/Record/launch authority. |
| UUID/null/NUL | calendarString с default allowNul=false и calendarEventId:524–533 дают строгую UUID8-4-4-4-12 hex форму, нормализацию A–F и отдельное разрешение nil calendar UUID. accountId:166–173 по-прежнему запрещает nil для account authority. JSON null/bool/object вместо строки не становятся UUID; decoded NUL не проходит known intent/command fields. |
| Original envelope | Cpp:617–629 читает оригинальный JSON до любой SDK нормализации. Whole64KiB проверяется до reader. Root command обязан совпасть с переданным точным command, payload отдельно проходит exact intent decoder. Функция не проверяет nonce/origin/protocol/auth и прямо документирована как data-only; неполный envelope может пройти lexical stage, но не становится разрешённым запросом. |
| Decoded duplicates/Unicode | Strict mode использует calendarString для каждой строки и decoded object key на всех уровнях. Raw/escaped aliases считаются одним key; nested duplicates и invalid UTF-8/surrogate в ignored fields тоже отвергаются. Valid ignored JSON string может содержать escaped NUL: syntax validation использует allowNul=true, не переносит known-field NUL refusal на metadata. |
| Lifetime | В обеих новых функциях reader — named local. Root decoded key views живут в его owning rootKeys_ до конца extraction; nested keys не сохраняются в возвращённой root map. Intent UUID скопированы в owned strings. Envelope payload копируется в std::string на cpp:629 **до** уничтожения reader/входного буфера; наружу не возвращается string_view/map. |
| Depth/size | Payload reader использует kBridgeMaxPayloadDepth, envelope — +1 и затем отдельный exact payload decode; root не съедает тот же payload бюджет. Accepted intent schema сама плоская, произвольная вложенность в payload не разрешается. Strict reader также bounded при обходе unknown envelope values. Тесты содержат границу nonempty nested unknown values; 65536 bytes включительно, 65537 отвергается. |
| Legacy/default behavior | Новые функции opt-in strict mode; legacy JsonReader defaults остаются maxDepth32/strictStrings=false, существующий accountId contract не изменён. Никакого второго JSON parser/SDK roundtrip/HTTP/URL validation/dispatch в двух функциях нет. |
| Runtime denial | Фактический WebViewBridge.cpp:194–195 allowlist по-прежнему не включает обе calendar команды. CalendarJoinWireTests.cpp:93–94 закрепляет denial. Добавление typed decoder не активирует WebView/host/AppMain путь и не создаёт permissions. |

## L1 — добавить маленькие positive Unicode compatibility assertions

**Не блокирует source approval.** CalendarJoinWireTests.cpp:67–71 покрывает
invalid UTF-8 и lone surrogate в unknown envelope fields, но не содержит
положительного unknown-field случая с valid supplementary Unicode и escaped
NUL. Escaped ASCII keys/action и nil UUID уже проверены отдельно.

Минимальная рекомендация — два assertions на calendarJoinEnvelopePayload с
обычным корректным join и unknown envelope extra `"\uD83D\uDE00"` и
`"\u0000"`: результат должен остаться равным исходному join. Это фиксирует
full-valid-JSON compatibility именно нового lexical envelope entry point,
включая ранее важное различие ignored-string syntax/known-field NUL refusal.
По source текущий reused reader оба случая разрешает правильно; изменения
product parser не требуются. Reviewer тесты/код не редактировал.

## Тесты и Ponytail

Новый test file полностью прочитан: exact join/cancel, неизвестные commands,
escaped known keys/values, UUID case/nil, missing/extra/type/action, raw/decoded
duplicate keys, lone surrogates/NUL/invalid UTF-8, envelope command mismatch,
duplicates/Unicode внутри unknown fields, trailing garbage, owned lifetime,
64KiB inclusive bounds, envelope nesting и runtime denial.

CMakeLists.txt:50 добавляет один portable/common contract executable по
существующей схеме; warning policy и прочие registrations не обходятся.

Сведения main, не собственные прогоны reviewer: compile RED exit2 при отсутствии
новых методов, затем GREEN focused wire1/1 PASS0.41s. Portable/native full suites
на момент оценки ещё выполняются; этот отчёт не называет их PASS. Reviewer
не запускал повторные builds/tests/VM/probes и не проверял issue через GitHub.

Ponytail-review: **Lean already. Ship.** Только в смысле текущего data-only
source slice, не релиза. Две узкие функции переиспользуют существующие reader,
string/UUID helpers и std::string ownership; второго parser/service/factory
нет. Safe schema/lifetime guards и assertion fixtures не считаются лишними.
**net: -0 lines possible.**

## Exact source SHA-256

Пути относительно `apps/windows/`:

| Файл | SHA-256 |
| --- | --- |
| RecApp/Upload/DesktopApiClient.h | `7f8b579f16d0babca351c49930e1786b0f56c7b02cbdc7835e1fe698751ddabc` |
| RecApp/Upload/DesktopApiClient.cpp | `67465129df8eec5aef9502868f7cf3d322d7273145822890c8357e1f6b13f5bd` |
| Tests/GrafWindowsContractTests/CalendarJoinWireTests.cpp | `422129d78ca812a0ef32f10a4951c58d8784aeaa45b9ccc26d4d1647de72ddb3` |
| CMakeLists.txt | `a1631adfeb575b7bec7ead6b5635d4d80be015eff214338da8e32cb223afefc0` |

**Terminal: Approved C0/H0/M0/L1 для strict decoder/raw owned payload ONLY.**
Не приняты runtime allowlist, source/frame/route/nonce/auth proof, consumed
request UUID/cap/replay implementation, host reply/invalidation, HTMX shim,
AppMain oneflight, launcher/dialog physical lifetime или installed/Record.
Они остаются отдельными следующими срезами существующего T119, не blockers
этой изолированной decoder реализации. Нет functional handoff/T119 closeout.

Единственная запись reviewer — этот новый отчёт. Product source, требования,
checklist markers, tasks, Git/GitHub и чужая dirty работа не изменялись.

## L1 closure — ограниченный test-only recheck 2026-10-05

**Актуальный source verdict: Approved C0/H0/M0/L0; L1 CLOSED.**
Прежний C0/H0/M0/L1 и initial test hash выше сохранены как история.
Перечитаны только добавленные CalendarJoinWireTests.cpp:76–79 assertions:
ignored envelope extra `"\uD83D\uDE00"` и `"\u0000"` должны оба вернуть
исходный join payload. Проверяется именно новый envelope entry point;
условия положительные и точные, не маскируют invalid Unicode/known-field
NUL refusal. Это полностью закрывает ранее названный regression coverage gap.

Текущий test SHA-256:
`cea168a1ef28fff6420520600bc3f915cda10fe56c7b440bfcec96d1bca54085`.
Три остальных hashes независимо сняты заново и совпали:

- DesktopApiClient.h: `7f8b579f16d0babca351c49930e1786b0f56c7b02cbdc7835e1fe698751ddabc`.
- DesktopApiClient.cpp: `67465129df8eec5aef9502868f7cf3d322d7273145822890c8357e1f6b13f5bd`.
- CMakeLists.txt: `a1631adfeb575b7bec7ead6b5635d4d80be015eff214338da8e32cb223afefc0`.

Main сообщил portable44/44 PASS21.20s **до** двух assertions. Финальный portable
rerun ещё выполняется. Предыдущий native48 receipt не получен; исчезнувшая
session50581 не считается PASS. Main запустил fresh native48 на старом test
и планирует final-test rebuild/rerun после него, без параллельной custody
проверки. Эти сведения — статус от main, не самостоятельная validation
reviewer; native/final portable PASS этим appendix не заявляется.

Перепроверка ограничена L1/test bytes и неизменностью трёх остальных файлов;
нового широкого source review или test job нет. Единственная запись — этот
appendix; product/нормы/markers/tasks/Git/GitHub не менялись. Approval остаётся
только strict decoder/raw owned payload, не runtime host/owner/installed T119.

## Compiler-fixture receipt — две строки, 2026-10-05

Лично перечитаны текущие CalendarJoinWireTests.cpp:77,79. Два raw literals
заменены обычными C++ строками с escaped quotes и doubled backslashes:
runtime JSON по-прежнему содержит `,"extra":"\uD83D\uDE00"` и
`,"extra":"\u0000"`, не C++ surrogate UCN или встроенный NUL. Оба assertions
по-прежнему требуют исходный join payload. Изменение только записи fixture
сохраняет L1 CLOSED; **Approved C0/H0/M0/L0** для прежнего decoder-only scope.

Новый exact test SHA-256:
`7c31c8924904ec511b19157829d103e037d3cdd08a0f05b0fe0abdf410d0d481`.
DesktopApiClient.h/.cpp и CMake хеши повторно совпали с таблицей первоначального
review; product и warning/компиляционные flags не изменены в этом исправлении.

Квитанции main, не самостоятельные reviewer прогоны:

- Native **pre-L1** full48/48 PASS, receipt6984 exit0, 240.45s теперь получен.
- С raw-literal L1 bytes Clang portable44/44 PASS8.46s; MSVC native build
  получил fixture-only C3850 на строке77. Этот build failure сохранён как
  исторический факт, не переименован в PASS и не доказывает decoder defect.
- После двух escaped-string правок main повторяет обе full suites. Финальные
  build/test PASS на текущем test hash этим appendix ещё не заявляются.

Повторный review ограничен двумя строками, новым test hash и unchanged product
hashes. Другие findings/gates не открывались заново. Единственная reviewer
запись — этот appendix; source/нормы/tasks/markers/Git/GitHub не изменялись.
