# T103 — независимый requirements/analyze gate native Phase2, 2026-10-22

## Решение и точная область

**GO, CRITICAL 0 / HIGH 0 — только tests-first synthetic native reset/API и
положительные controls полезной GET-истории.** Это не SOURCE GO ещё не
написанного adapter, не допуск полной интеграции WebView2Host и не runtime PASS.
Риск: существующий high-risk-product F200; T103/#7280, T088/#7231 остаются
открытыми. HEAD `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1` проверен read-only;
рабочее дерево содержит чужую текущую работу, её изменения не присваиваются.

Сначала допустим небольшой тест механизма в существующих
WebView2AuthNativeTests.cpp, WebView2AuthLoopback.py и native PowerShell runner:
принятие синтетического документа настоящими production handlers/latch →
actual CDP reset → проверочный native snapshot → обычная полезная GET-история.
Он может предшествовать полной интеграции, чтобы проверить выбранный API на
целевом runtime. SOURCE review Phase1 policy остаётся обязательным перед её
включением в native host. Написанный новый fixture также требует отдельного
SOURCE review до freeze/build/run; этот отчёт их не выполняет и не разрешает
изменять нормы при несовпадении API с выбранными условиями.

## Прочитанные основания

Применены code-reviewer и speckit-analyze к ограниченному native срезу:
spec.md:397–434,586–590,661–694; выбранный plan.md:3100–3173;
data-model.md:709–722; contracts/windows-native-web-bridge.md:565–574;
quickstart.md:1297–1316; research.md:3309–3376 и tasks T103:447/T088:390.
Прежний same-URL candidate исторический: research:3347 явно выбирает более
строгий ALL-entries GET guard. Постановка и зависимость фаз согласованы.
Конституция 7.1.0 прочитана; противоречий применимым III/VI/VII нет,
capture/Stop, deletion и выпуск не изменяются. Extensions before/after_analyze
commit hooks disabled; hooks не исполнялись. Штатный prerequisite вызван один
раз: active FEATURE_DIR F200, требуемые artifacts присутствуют.

## Checklist reuse с новой native семантикой

Независимо прочитаны байты и пересчитан inventory: **198 файлов, 31 файл с
checkbox, 477 checked / 0 unchecked**. SHA-256 sorted строк
`SHA256  relative-to-checklists-filename\n`:
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Это точное совпадение инвентаря Hooke, а не новая приёмка 477 runtime условий.
Отметки не менялись. Свежая семантика native части проверена по requirements
CHK001/002/004–007/013/019–022, security CHK001–003/007–011/017–018/022,
UX CHK001/002/019/020: origin/routes, source/session ownership, nonce, отказ,
приватность synthetic evidence и явно документированное защитное отличие Mac.
Остальные неизменные критерии переиспользованы в прежней области; устройство,
установка, accessibility и реальный кабинет этим gate не принимаются.

## Coverage и минимальные native oracles

| Группа | Доказательство, необходимое в соответствующем тесте | Покрытие |
|---|---|---|
| Принятый GET | Только actual final response GET + ordinary cabinet completion latch; snapshot/DOM/CDP ACK не заменяют это принятие | FR-003/005/006, T103/T088 |
| Reset механизма | Запомнить принятые ID/точный URL/generation/context; reset ACK недостаточен. Новый snapshot содержит ровно прежний current ID/URL, тот же документ; другой ID не получает старый GET proof | FR-005/006, T103 |
| Безопасность reset interval | От принятого GET через reset до проверки нет допущенного BF/new document; mutation/new ID/session change/stale result/error не разблокируют историю | FR-005/006, T103/T088 |
| Полезная история | После reset новые обычные GET создают историю, actual CDP Back и Forward восстанавливают выбранные GET через production latch; отсутствие нового POST не заменяет current ID/DOM/authority proof | FR-002/005/006, SC-002 partial, T103 |
| Quarantine и recovery | POST/unknown anywhere, включая forwardList/другой URL, запрещает BF; fresh list и один безопасный fresh forward — отдельный путь, не старый POST ID; ошибки/чужой переход/session отзывают цель | FR-002/005/006, T103/T088 |
| Lifetime/отказы | Cancel до replacement сохраняет документ; actual replacement проходит штатный lifecycle. Logout/expiry/account/workspace/recreate и rename race не оживляют старый proof/nonce/intent | FR-005/006, T103/T088 |

Все шесть групп имеют existing ownership; 4 scoped FR и partial SC-002
прослеживаются к T103/T088, непокрытых scoped требований нет. В tasks.md
120 task строк, duplicate IDs 0; обе задачи `[ ]`. Новые задачи не требуются;
live GitHub состояние не проверялось и не менялось. Ambiguity/duplication/
constitution conflicts CRITICAL/HIGH в этом tests-first допуске: 0.

## Рекомендуемая последовательность, без расширения GO

1. Сначала один механизм reset через настоящий host: подготовить несколько
   синтетических entries, принять fresh trusted list GET ordinary latch,
   reset и проверить прежний singleton ID/URL/generation. Отдельно подтвердить
   сохранность текущего документа/bridge без ручной установки nonce/ready.
2. На этом же очищенном browser-owned основании добавить обычные GET и
   проверить actual selected-entry Back/Forward, правильный документ и
   штатное принятие ответа. Always-deny/always-reset не проходят этот control.
3. Ошибка/unsupported reset, другой ID, неполный snapshot, неподтверждённый
   response, timeout или наблюдательная ошибка остаются RED/INCONCLUSIVE с
   ненулевым runner result. Не придумывать GET proof и не ослаблять same-ID
   условие. Если нужны изменения проекта из-за результата — обратно в plan.
4. Тестовый interception допустим для изоляции опыта, но его отмены НЕ
   доказывают наличие production pending/reset fences. Реальные host fences,
   terminal selectedID до новой authority, fallback/singleForward и session
   wiring проверяются следующими tests-first integration slices после
   SOURCE review policy и механизма. Полный Phase2/host GO здесь НЕ выдан.

Не удалять default23; stage9/race negative-only evidence не превращается в
PASS. Прежние source/PE hashes, GUID profiles, synthetic HTTPS loopback,
deadline20s/close10s/case35s и owned-child cleanup сохраняются. В evidence
только синтетические ID/markers/счётчики; никаких реальных URL, cookies,
токенов, nonce, ответов кабинета или содержимого встреч. Вопрос о пригодности
reset API технический, не вопрос продуктового выбора пользователю.

## Exact snapshot

| Артефакт | SHA-256 |
|---|---|
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| spec.md | `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92` |
| plan.md | `7b84e844149a1630b8564e43d832efd2595241d9822399a3b1c42c80c860a050` |
| data-model.md | `338653d8c905eb5db07e33394bbf441978df5b49899cb88a0203047017a885a7` |
| bridge contract | `2d31f0f9bd1548ca592561062788aa87a521cf8f9661bf320a7c9177cb456dc5` |
| quickstart.md | `e94e94fdf40af09f71b1de9f0a7a47d0a6d86a010e2cf6da4a2c986c501f0cbb` |
| research.md | `af208357cb36658a629e1daf1c0af9b82339fba45a9cafe57bec8c871e5f890e` |
| tasks.md | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| WebView2Host.cpp | `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6` |

Единственная запись reviewer — этот собственный отчёт. Нормы/checklists/code,
чужие отчёты, Git/GitHub не менялись. VM/device/build/tests не запускались.
T103/T088/T097/full F200, installed/E2E/hardware/release acceptance открыты.

## SOURCE review frozen native fixture — 2026-10-22

**REQUEST CHANGES: CRITICAL 0 / HIGH 1. SOURCE GO пока не выдан даже для
изолированного опыта.** Requirements GO выше не отменяется; препятствие —
устранимый ложный RED в новом диагностическом сценарии, не дефект reset API
и не наблюдение runtime. Применён code-reviewer, без сборки или исполнения.

Проверены новые диапазоны и окружающий поток трёх actual файлов против
сохранённой базы history9, включая фазовые переходы, final response observer,
snapshot/ACK, bridge dispatch, счётчики сервера, deadline и owned cleanup.
Текущие SHA-256 повторно совпали с объявленным freeze:

| Файл | Текущие байты | База history9 |
|---|---|---|
| WebView2AuthNativeTests.cpp | `ae7d2e791ee55c31aaf7b3ffdedee7f8006721f3635c4ab2e8b1092fa842bb00` | `ec3af695c1393afab7ce2f5ba835f6131f65b4c39e86b698fa861d81e15931b1` |
| WebView2AuthLoopback.py | `f4f8a6ab865d87003eb126d801241c7cf9d6d45d485cb1ba81aa60a590d8b097` | `80d68c8b4401172d8c2907149569d844111f97fe0205d3aee5b0594ba8fc88c1` |
| RunWebView2AuthNativeTests.ps1 | `8600fa0e13e967818286b584a190d73adc518a20fdd7de6c0996bbae4ccd9c6d` | `aabfa7165e379f1f84c9b5826ced3f771aa863edf8a7172f24fe8f28a24e76ec` |

### H1 — ready/bootstrap не упорядочивают завершение native cookie read

`WebView2AuthNativeTests.cpp:717` сразу завершает reset case ошибкой при
`authCallbacks != phase + 1`, хотя остальные условия принятого документа уже
выполнены. Это не гарантированно стабильное условие на данном шаге:

- `WebView2Host.cpp:2251` выставляет ready до чтения cookie;
- `:2282–2305` запускает `GetCookiesAsync`, а затем отдельно ставит его
  completion в dispatcher; только этот путь вызывает
  `reconcileAuthSessionForDocument` → fixture auth handler (`:1167–1168`);
- `WebView2Host.cpp:2442–2463` независимо запускает bootstrap, затем
  `native_ready`; он не ждёт cookie completion. Следовательно, ready и оба
  DOM-признака могут быть видны, пока ожидаемый auth callback ещё не пришёл.

Допустимый контрпример: phase 0, документ/ответ/DOM уже приняты,
`authCallbacks == 0`, cookie completion ещё ожидает; диагностический callback
достигает строки 717 и выдаёт `reset-final-response-or-latch`. При последующем
cookie callback все доказательства могли бы стать корректными, но case уже
terminal FAIL. То же возможно на следующем GET/BF, не только перед reset.
Это SOURCE-доказанная возможность неправильного отказа, не доказательство
того, что такое расписание уже наблюдалось в Windows.

Минимально требуемая правка автора, без изменения host и критериев успеха:
после остальных обязательных проверок и до `checkHistoryEntry`/snapshot/
`startHistoryReset` отдельно проверить count: меньше ожидаемого — вернуть
управление и ждать следующего штатного tick в прежнем общем 20s deadline;
больше — FAIL; равенство — единственный путь дальше. Не переносить ожидание
за capture reset baseline и не продлевать deadline. Существующая ветка
`:729–732` уже применяет такой порядок для control/race. Сохранить все
generation/navigation/phase fences повторного наблюдения. После исправления
нужны новые frozen bytes и повторный ограниченный SOURCE review.

### Остальная конструкция и границы проверки

Других C/H в просмотренном diff не выявлено. Подготовка требует actual
A/POST-B/C/fresh GET-list, native final method/destination/mode/tag/status;
GET на B не подменяет POST. Reset ACK `{}` не заменяет второй snapshot:
требуются singleton, прежний ID/URL и неизменные generation/nav/auth/ready.
Затем проверяются новая C и обе выбранные actual GET entries, DOM и реальный
bridge callback в каждой фазе. Отсутствие лишнего POST само по себе не PASS.
`request_app_update` действительно доставляется существующим bootstrap:
`WebView2Host.cpp:328–341` не требует updateAvailable для dispatch нового
синтетического button, а `:2182–2184` вызывает только подключённый harmless
handler; отсутствующий `setAppUpdateAvailable(true)` здесь не finding.

`history-reset` opt-in; default23 не расширен. Серверный диапазон GET 4–6
с POST ровно 1 дополняет, а не заменяет native oracle. Общие сроки
20s/close10s/case35s и очистка только owned children сохранены. ALL-navigation
fence тестовый; `PRODUCTION_FENCES_PROVEN=0` исключает трактовку результата
как проверки production reset/session/fallback/singleForward guards.

Внешний history10 runner/manifest не квалифицирован этим SOURCE review;
подготовка bundle остаётся отдельной проверкой main. Runtime пригодность CDP
API, полезная история и установленное приложение не принимались. Host hash
повторно равен `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.
Единственная запись — это дополнение собственного отчёта; код/нормы/
checklists/чужие отчёты/Git/network state не менялись, VM/device/build/tests
не запускались. T103/T088 остаются открытыми; production GO отсутствует.

## Повторный bounded SOURCE review H1 — 2026-10-22

**C0 / H0, SOURCE GO только для изолированного synthetic native mechanism
test `history-reset` и прежних controls. H1 устранён.** Это не runtime PASS,
не квалификация внешнего bundle и не GO production/full host integration.

Проверена только исправляющая delta `WebView2AuthNativeTests.cpp:717–726`
с окружающими callback fences и дальнейшим переходом к snapshot. В исходном
property guard теперь `authCallbacks > phase + 1` по-прежнему даёт FAIL;
после него `< phase + 1` возвращает управление без перехода к snapshot или
capture reset owner. Следовательно, продолжение возможно только при точном
равенстве. Иные обязательные свойства guard сохранены. Повторный callback
сохраняет generation/phase/navigation checks; существующий общий deadline
не меняется. Отсутствующий callback не превращается в PASS и не продлевает
срок. Комментарий соответствует ранее проверенному actual host ordering.

Чтобы не заменять bounded review новым аудитом, точность delta дополнительно
проверена обратным преобразованием только в stdout: возврат `>` в `!=` и
удаление трёх добавленных строк восстановили прежний полный SHA-256
`ae7d2e791ee55c31aaf7b3ffdedee7f8006721f3635c4ab2e8b1092fa842bb00`.
Файл при этом не переписывался. Остальной ранее проверенный cpp byte-identical.

Текущие три SHA-256 для последующего freeze:

| Файл | SHA-256 |
|---|---|
| WebView2AuthNativeTests.cpp | `73a9c0414287af6085b5774acb7bb734dceebc73751bb07403b9341472a0ff34` |
| WebView2AuthLoopback.py | `f4f8a6ab865d87003eb126d801241c7cf9d6d45d485cb1ba81aa60a590d8b097` |
| RunWebView2AuthNativeTests.ps1 | `8600fa0e13e967818286b584a190d73adc518a20fdd7de6c0996bbae4ccd9c6d` |

PY/PS и проверенный host hash не изменились относительно предыдущего review.
Известная неизменная конструкция/default23 переиспользованы без полного
повторного аудита. `PRODUCTION_FENCES_PROVEN=0` и прежние ограничения GO
сохраняются. Main отдельно квалифицирует/freeze внешний bundle перед любым
исполнением. Применён code-reviewer; единственная запись reviewer — это
дополнение своего отчёта. Код/нормы/checklists/чужие файлы/Git не менялись;
VM/device/build/tests не запускались. T103/T088 не закрываются.

## Production host integration — scoped pre-code gate, 2026-10-22

**Requirements/checklist/analyze: C0 / H0, условный GO для следующего
tests-first Phase2 среза по выбранному plan.md:3100–3173.** Старый
research-only допуск не используется как ограничение этого плана. Это не
SOURCE GO ещё не написанного host diff и не разрешение считать runtime
механизма подтверждённым. Перед включением интеграции обязательны actual
stage10 runtime proof reset/API с полезными GET controls и независимый SOURCE
review actual diff; предусмотренный планом source gate Phase1 policy также
сохраняется. Если API proof RED/INCONCLUSIVE — host integration не допускается
путём ослабления singleton/method/authority условий. Stage10 сейчас не PASS;
сообщённый main source216 hash не выдаётся за самостоятельно проверенный bundle.

Прочитаны selected plan, spec Session 2026-10-22:661–694,
data-model:709–722, bridge contract:565–574, quickstart:1297–1316 и именно
окончательное research decision:3347–3376, не отвергнутый same-URL candidate.
Применены speckit-analyze и действующие requirements/security/UX checklist
критерии к native integration, не ко всему F200. Active prerequisite подтвердил
F200/tasks; before/after_analyze hooks disabled, никаких hooks с эффектом не
исполнялось. Конституция 7.1.0 не конфликтует с этим срезом: capture/Stop и
данные не меняются, evidence synthetic, source/session/nonce остаются native,
tests-first и документированное Windows security deviation сохранены.

Checklist inventory независимо пересчитан: 198 файлов, 31 checkbox file,
477 checked / 0 unchecked; hash sorted относительных SHA256-строк опять
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Отметки не менялись; это reuse byte-identical требований с новой scoped
семантикой, не runtime-приёмка 477 условий. Применимы requirements
CHK001/002/004–007/013/019–022, security CHK001–003/007–011/017–018/022 и
UX CHK001/002/019/020. Hash восьми нормативных артефактов из Exact snapshot
выше совпал. Unresolved scoped ambiguity/duplication/constitution C/H: 0.
4 scoped FR (002/003/005/006), partial SC-002 покрыты существующими
T103/T088; обе задачи открыты, новых задач/owner не требуется. Это не
перепроверка покрытия остальных требований или текущего состояния GitHub.

### Минимальные обязательные tests-first сценарии и их oracle

1. **Полезная actual all-GET история.** A→B→C, Back/Forward выбирают
   ближайший отличный URL в реальном порядке; из detail/review/share/report
   Back соблюдает meeting-history filter. Проверить выбранный ID, документ и
   рабочий bridge через production latch. Ожидаемые события собственного BF
   должны довести операцию до terminal proof, а не обнулить intent как чужую
   мутацию: always-cancel/always-reset не проходят положительный контроль.
2. **Pending до первого async snapshot.** Вставить конкурирующие BF, GET,
   form POST и второе native действие до ответа snapshot и после него.
   До снимка всё отменяется до begin; после него допускается не более одного
   выбранного BF, без исключения для конкурирующего non-BF того же URL.
   Отмена до replacement сохраняет текущие generation/nonce/bridge; timeout,
   API error и stale callback завершают pending без допуска старого результата.
3. **Terminal до потребления latch/nonce.** Не тот actual selected ID при
   том же URL либо другая session/generation/revision не получает новую
   authority, cookie/auth reconciliation или bootstrap. Main-response и
   completion в обоих порядках; terminal snapshot также приходит позже обоих.
   Без его успеха latch не потребляется необратимо и nonce не публикуется;
   успешный выбранный GET затем принимается штатно, без fake finish.
4. **GET proof не выводится из URL/snapshot.** Actual correlated final GET
   + successful cabinet latch + свежий same-document current-ID snapshot
   необходимы совместно. POST/unknown любого URL, включая forwardList,
   запрещает BF; fresh GET того же URL не реабилитирует прежний POST ID.
   Wrong/missing method/tag/destination/mode/status/response binding,
   incomplete snapshot и late metadata не создают proof. Реальный retained
   bootstrap callback подтверждает authority, одних DOM bits недостаточно.
5. **Replacement/mutation/session.** Cancel before begin сохраняет proof;
   actual replacement прежнего current entry отзывает его до возможного
   наследования. Same-document replaceState/pushState, смена URL/new ID,
   исчезнувший entry, включая POST-U→safe S, не переносят GET proof. Logout,
   401/expiry, account/workspace reselection и recreate очищают proofs/snapshot/
   singleForward и отзывают pending; старый async completion ничего не оживляет.
6. **Полезный fallback, не обход POST.** В карантине Back из individually
   confirmed GET detail делает fresh list; после успешного reset доступен
   один fresh-GET Forward к допустимому detail той же сессии, не old entry ID.
   Повтор/ошибка/посторонний переход/session boundary не оставляют скрытую
   старую цель. Проверить обе стороны и отсутствие повторной отправки формы;
   при отказе остаются безопасные «Встречи»/повтор, не тупик и не raw GoBack.
7. **Reset integration, а не fixture fence.** Accepted trusted GET list/home
   при quarantine/new session → ACK `{}` → fresh same-ID/URL singleton при
   прежних document/session/generation; ВСЕ BF/new-document отменяются
   production-кодом на всём участке, включая первую async границу после
   acceptance. Mutation/new ID/session/replacement/error/malformed или
   mismatched snapshot сохраняют quarantine, не переносят proof и не дают
   singleForward. Затем новые обычные GET снова образуют полезную actual BF
   историю; reset не запускается на каждом GET. Fixture ALL-nav fence не
   может быть причиной успеха интеграционного сценария.

Это обязательства из уже выбранных требований, не новые нормы/архитектура.
Технически критичны места установки pending/reset fence и проверки terminal
до nativeFinishDocument authority, но actual host mapping делает отдельный
reviewer: здесь их существование в коде не утверждается. H1 wait сохраняется:
ready/bootstrap не заменяют завершённое native cookie observation; ожидание
ограничено прежним deadline до захвата owner baseline.

Scope lane high-risk-product / existing active slice; независимый отчёт —
единственная запись. Нормы/код/checklists/чужие отчёты/Git/network state не
менялись; VM/device/build/tests не запускались. Default23 и source/PE/GUID/
deadline/owned-cleanup evidence сохраняются отдельно. Native integration
PASS, MSIX/UI/keyboard/accessibility, T103/T088/T097/full F200 и release не
принимаются этим условным pre-code gate.

## Stage10 — квалификация сохранённого результата и exact-PE replay

**Сохранённый результат квалифицирован как BUILD PASS / startup failure
до fixture launch / 0 из 4 native cases исполнено; API NOT PASS и НЕ API RED.**
Прочитаны внешний stage10 `result.json`, `run.log`, `run.err`, frozen runner и
`Check-Terminal.ps1`, без обращения к VM. Receipt terminal, run_exit=1,
preflight/staged/postflight=216, owned_processes=0, elapsed_ms=256245.
Журнал содержит BUILD=PASS и PE SHA-256
`83904f43fd87b65a5af35a2e0645392e66f0b1e3d2840f2d3d41513f9df732d4`.
Первый case — history-entry-same-url; run.err указывает
`SYNTHETIC_SERVER_NOT_READY`, case elapsed 2412ms, passed=0/requested=4.
По actual runner ready-проверка предшествует Start-Process fixture, поэтому
этот отказ не измерял reset/GET/BF API и не выполнял прежние три controls.

Независимо совпали hash source216 manifest
`c62757572f0ecbe4f8a6e33f4e85c14589d9b09b065351f0859a39745ff91002`,
216/216 current source files, 6/6 staged source files, prior manifest hash и
все пять сохранённых input hashes receipt (scripts/run.cmd/synthetic TLS).
Runtime DLL hashes записаны в receipt и wrapper проверяет их до/после.
Guest PE и фактический guest process state заново не читались: их дополнительная
квалификация Check-Terminal сообщена main. В stage есть исходник helper, но
нет отдельного сохранённого вывода его исполнения; исходник не выдаётся за
такой вывод. Пустые server.err/out и отсутствие ready/final-counts/fixture logs
также сообщены main; это согласуется с сохранённым failure, но не устанавливает
причину и не доказывает, что сервер вообще никогда не мог стать ready позднее.

**Минимальный external replay без rebuild допустим по конструкции, условно
после SOURCE review самого replay wrapper.** Не перезапускать использованный
Run-History.ps1: он защищён STAGE_ALREADY_USED и вызывает сборочный runner.
Не менять его, stage10 evidence или checked-in runner. Новый внешний wrapper
может переиспользовать сохранённый PE и те же три DLL, но обязан:

- Проверить exact PE, source216, server script, DLL и synthetic inputs перед
  запуском и после него; новые runner inputs заморозить отдельным manifest.
  Проверять DLL рядом с исполняемым PE, не только исходный runtime directory.
- Создать новые run/case GUID directories и свежий profile; не использовать
  прежние ready/stop/final-counts, cookies или уже завершённый receipt.
- Сохранить те же четыре scenarios, arguments и actual native/server oracle,
  readiness 15×100ms, fixture wait min(32000, remaining35s), native20s,
  close10s, server drain min(3000, remaining35s), итоговый case35s. Отсутствие
  rebuild не разрешает увеличение readiness или обход server readiness.
- Сохранить exit/status/counts/stderr/terminal-source checks, отсутствие
  параллельного активного probe/build/capture, owned-child cleanup и отдельный
  terminal receipt с числом реально запущенных cases. Не запускать установленный
  GRAF и не приписывать повтору новую BUILD PASS — reused exact PE.
- Зафиксировать фактический Python executable/version и WebView runtime;
  source/PE/DLL equality не доказывает неизменность внешнего интерпретатора
  или Evergreen runtime. Ранее не записанное значение не считать равным задним
  числом. Все synthetic evidence и ненулевой результат отказа сохраняются.

Отдельный один bounded diagnostic server startup может измерить время до ready
с теми же interpreter/script/args в отдельном каталоге, без fixture. Наблюдение
после acceptance readiness deadline допустимо только как диагностика, не PASS
прежнего case и не основание автоматически продлить его сроки. Пустые логи не
определяют причину; source root-cause review остаётся у Hooke.

Production integration conditional gate не разблокирован: reset API/runtime
proof отсутствует. Это saved-result/replay construction assessment, не SOURCE
GO ещё не написанного replay wrapper и не разрешение запуска от reviewer.
Записано только это дополнение своего отчёта; VM/build/test/device/Git/network
операций и изменений чужих файлов не было.

## Stage11 external replay — bounded SOURCE review до исполнения

**C0 / H1, REQUEST CHANGES для exact-input qualification; SOURCE GO пока
не выдан.** Прочитаны external Replay-Native.ps1, Run-History.ps1,
Invoke-Runner.ps1 и run.cmd из `t103-history11.8C5mRb`; ничего не исполнялось.
Это не новый дефект продукта/CDP и не изменение квалификации stage10.

Независимое побайтовое сравнение подтвердило: prefix до заменённого build
block и весь suffix от `foreach ($scenario in $Scenarios)` до EOF идентичны
repo runner SHA `8600fa0e13e967818286b584a190d73adc518a20fdd7de6c0996bbae4ccd9c6d`.
Default23, actual case body/oracles, readiness15×100ms, native20s/close10s,
case35s, PE hash after cases и owned cleanup не ослаблены. Новый GUID out
содержит собственные копии; удаление retained stage10 отсутствует. Wrapper
больше не копирует исходники в guest; до/после проверяет source216 и свои семь
inputs, runtime source directory, terminal owned0; outer600s сохранён. Invoke
выбирает только четыре заявленных cases, вызывает replay, не compile runner.

### H1 — exact DLL proof проверяет источники, но не запускаемые копии

Replay-Native.ps1:41–44 проверяет frozen DLL hashes в `$retained` и равенство
исходному RuntimeDllDirectory, затем копирует их в новый `$out`. В :46
проверяется только скопированный PE. DLL в `$out`, рядом с фактически
запускаемым PE и передаваемая bootstrap DLL (:66), не хешируются ни до запуска,
ни после него. Wrapper :28–31/:43 повторно проверяет другой каталог —
`$base\apps\windows\out\x64\Release`. Успешный replay удаляет свой `$out`
(:143–148), поэтому отсутствие проверки уже нельзя восполнить после PASS.

Конкретный непринятый путь: изменение DLL в fresh `$out` после Copy-Item
не затрагивает retained/runtime-source/input hashes или PE hash; при успешном
поведении fixture и правильных counts весь runner всё ещё может вернуть PASS,
не доказав заявленную точную тройку исполняемых DLL. Это пробел доказательства
exact replay, не утверждение о случившемся повреждении или его вероятности.
Предыдущий assessment явно требовал проверять DLL рядом с запускаемым PE.

Минимальная обязательная правка только внешних replay assertions: сравнить
все четыре destination files с frozen hashes до первого case и повторить
проверку actual destination DLL/PE после завершения cases, до success cleanup.
Mismatch/missing/read error должны делать результат ненулевым и сохранять
диагностику. Case body/readiness/deadlines/oracle и retained stage10 не менять;
проверка перед удалением может стоять вне case body. Затем новые frozen hashes
и ограниченный повторный SOURCE review этой delta.

Прочих C/H в просмотренном bounded diff не выявлено. Source manifest и server
hash совпали с предыдущим freeze. Текущие reviewed external hashes:

| Файл | SHA-256 |
|---|---|
| Replay-Native.ps1 | `3b06687f6538e8484d930f3f4cc2cf2f9143995e55f9e4c3a329fc33bed2b312` |
| Run-History.ps1 | `e86c506f74a03d42e42d17a0ca7812b92a1b5b690525810d3dfe1409dcc47cfd` |
| Invoke-Runner.ps1 | `e0421ce7304a25f0f5251f5a2563b94a160ca2e1761ce685ef5fa669ff92e2e1` |
| run.cmd | `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856` |

CheckPy imports exit0/306ms и Check-Terminal guest PE/source216/owned0 exit0
сообщены main, не повторялись reviewer. Они не дают reset API PASS и не
устанавливают причину stage10 cold startup. Runtime NOT PASS, production gate
не разблокирован. Применён code-reviewer; только append собственного отчёта,
никаких VM/build/tests/Git/source/norm/чужих файлов или external-state writes.

## Stage11 H1 re-review — exact destination комплект

**C0 / H0, SOURCE GO для bounded external exact-PE replay11. H1 устранён.**
Применён code-reviewer; проверена только исправляющая delta с контекстом
catch/finally и свежие хеши. Runtime/production GO этим не выдаётся.

Replay-Native.ps1:36–52 теперь содержит PE и три DLL в runtimeExpected;
Assert-Destination хеширует именно четыре actual `$out` files до первого case.
Повторный вызов :144 стоит после cases, до catch/finally/success cleanup.
Mismatch/missing/read error прерывают путь PASS: throw → runFailure →
DIAGNOSTICS_PRESERVED, затем ненулевой итог. Если case уже бросил исключение,
post-assert не выполняется, но результат и так отказной с сохранённым out;
это не обход проверки на успешном пути. Retained stage10 не удаляется.

Обратное преобразование только этой delta в памяти восстановило прежний
полный external hash `3b06687f6538e8484d930f3f4cc2cf2f9143995e55f9e4c3a329fc33bed2b312`.
Тем самым прочие байты, включая case body/deadlines/cleanup, не изменились.
Новый final Replay-Native.ps1 SHA-256:
`a382c44293e94d912c301ece38bd8fff5e55f808bbe8d057d99c67ddcfb413f4`.
Run-History.ps1/Invoke-Runner.ps1/run.cmd/source216/server hashes совпали с
предыдущим review; повторный полный аудит неизменного среза не выполнялся.

Допуск относится к этому exact replay и прежним четырём cases без rebuild;
stage10 startup failure не становится PASS. Требуются отдельные terminal
receipts/runtime qualification после исполнения; reset API ещё NOT PASS,
production integration условие остаётся закрытым до соответствующего proof.
Standalone policy test PE `bd11c064e5ab6767c4245213e99a784bcb67fd627d4ce0308da73089072ceb65`
и временная cleanup lock сообщены main, reviewer их не проверял/не очищал и
не использовал вместо native evidence. Записано только это дополнение своего
отчёта; VM/build/tests/cleanup/Git/чужие файлы/нормы не затрагивались.

## Stage11 — независимая saved-runtime квалификация

**C0 / H0, mechanism/API-only GO для следующего production tests-first
среза.** Полностью прочитаны все 223 строки сохранённого run.log, пустой
run.err и terminal result.json в `t103-history11.8C5mRb`. Четыре заявленных
cases действительно исполнены и завершены PASS, не только сборка/запуск.
Это снимает прежнее NOT PASS только для проверенного механизма runtime,
не принимает host fix, production fences или всю T103.

Receipt: terminal=true, run_exit=0, elapsed_ms=12371, owned_processes=0,
preflight/staged/postflight=216, build=false/reused_stage10=true. Source216
manifest `c62757572f0ecbe4f8a6e33f4e85c14589d9b09b065351f0859a39745ff91002`
независимо совпал; 216/216 current source hashes и 7/7 receipt input hashes
также совпали. Replay hash по-прежнему
`a382c44293e94d912c301ece38bd8fff5e55f808bbe8d057d99c67ddcfb413f4`.
В журнале reused PE
`83904f43fd87b65a5af35a2e0645392e66f0b1e3d2840f2d3d41513f9df732d4`,
NO_BUILD=1. Три runtime DLL hashes receipt совпали с reviewed frozen values;
успешный путь неизменного reviewed replay включает destination PE+DLL asserts
до/после cases и лишь затем cleanup. Заново guest файлы/процессы reviewer не
читал; это квалификация сохранённого исполнения, не второй live run.

| Case | Native/server exit | Final counts | Case elapsed ms |
|---|---|---|---|
| history-entry-same-url | 0 / 0 | `4 0 0 0 0 1` | 2586 |
| cancel-history-host | 0 / 0 | `3 0 0 0 0 1` | 2001 |
| history-same-document | 0 / 0 | `3 0 0 0 0 1` | 2524 |
| history-reset | 0 / 0 | `6 0 0 0 0 1` | 2472 |

Все четыре имеют exact profile match до навигации и BrowserExited PASS.
Cancellation control показывает отменённый nav с error14, retained current
и последующий успешный документ. Same-document control показывает retained
состояния и следующий документ. Ни один из этих controls сам по себе не
доказывает production history policy или полноту default23.

Reset case наблюдает actual GET A → POST B → GET C → fresh GET list,
generation-tag match, final methods и successful ordinary completion. После
ACK `{}` — exactly same current singleton ID/URL/generation/navigation/auth,
не создание нового GET proof из ACK. Далее новый GET C, selected actual Back
к reset list и Forward к новой C; все три имеют final GET metadata, правильные
entries/DOM и действующий bridge. Всего 7 starts/completions/current cookie
reads, auth invalidations=0, четыре реальных bridge dispatch в фазах 3–6.
Журнал явно содержит FIXTURE_BLOCK_ALL=1 / PRODUCTION_FENCES_PROVEN=0:
runtime доказал reset API и сохранение/возобновление полезной GET-истории в
изолированном опыте, а не реализацию ALL-nav guard в production.

Финал журнала: TEMP_CLEANUP=PASS, CASES_PASSED=4 REQUESTED=4, CASES=PASS;
own fresh GUID cleanup успешен. Reviewed cleanup не затрагивает retained
stage10; его прежний startup failure остаётся отдельным результатом,
причина этим повтором не установлена. Artifact hashes:

- run.log: `8a32c903a521152e9e2dcd78ddb85a14dfa82ca39540e5de92efe98932b328f9`;
- run.err: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- result.json: `6d77a95d2ff67601f3b71b6b3e43fdbe002673c90bb10c873b009c778d792cb9`.

Следующий шаг допускается по прежнему scoped pre-code gate: tests-first
production integration с обязательными отрицательными сценариями и отдельным
SOURCE review actual host diff. Existing latch/nonce/method/session/selectedID
барьеры и все семь групп выше не снимаются. T103/T088/T097, default23/full
regression, MSIX/UI/keyboard/accessibility/E2E/hardware/release остаются открыты.
Code-reviewer применён к квалификации evidence; единственная запись — это
дополнение своего отчёта. VM/device/build/tests/Git/нормы/код/чужие файлы не
затрагивались, никаких повторов или cleanup reviewer не выполнял.

## SafeHistory::allGet — bounded pure extraction SOURCE review

**C0 / H0, SOURCE GO только для выделения allGet(policy) перед native use.**
По code-reviewer прочитан полный diff ровно policy.h/cpp/policytests против
сохранённых stage10 байтов, плюс actual SafeHistory state transitions и
target caller. Baseline hashes независимо совпали:
header `fb5c46379a940b251084b9438f1b5ad2727fc06fd5d02d92db16703b5a3f10a3`,
cpp `2f2de7dc0f6d686d1ead5363d4a21c608953d9d0521c2ff2ab27a032543a9ced`,
tests `4cb2d26bc6861ae0140387c42d6329f85ff29a2f301aced5ef801feb3a6b1305`.

Новый cpp:493–497 — чистый const predicate, без нового state/owner/side effect.
`fresh && all(confirmedGet && allowed)` логически точно эквивалентен прежнему
отказу target `!fresh || any(!confirmedGet || !allowed)`. Порядок обхода и
короткое замыкание сохраняются; остальная nearest-distinct/meeting-filter
часть target не менялась. Внешний API позволяет отличить безопасный singleton
без Back/Forward цели от quarantine, но не выбирает цель и не даёт authority.

Пустая history не становится all-GET из-за математического empty all_of:
изначально/после clear fresh=false, а acceptSnapshot устанавливает fresh=true
только после проверки непустого полного snapshot/current index. Unknown,
forbidden route и invalidation сохраняют отказ; helper не восстанавливает
revision/proof. Native caller по-прежнему обязан обеспечить lifecycle/session/
response ownership и свежесть snapshot; allGet не заменяет terminal ID fence.

Четыре новые assert проверки покрывают empty=false, confirmed singleton=true
при отсутствии target, unknown=false и invalidated=false. Existing positive
BF/nearest/filter/POST/rename/stale tests не удалены. NDEBUG локально снимается
до cassert, поэтому исходник не выключает assertions в optimized test build.
Reported main RED/optimized/ASan results reviewer не запускал/не квалифицировал.

Reviewed current SHA-256:

| Файл | SHA-256 |
|---|---|
| WebViewRoutePolicy.h | `e1d6f64e9ac7fc8633294d6a097285b17060381cb96ed98ab6644b7a3100259f` |
| WebViewRoutePolicy.cpp | `56dfefd4b197f1e40cae563e0cc80b6030cbae53f9049386e7738f72c6d1242a` |
| WebViewRoutePolicyTests.cpp | `e7471cc8e99164f943e1606a19d3bcbdc002714307840741db2f7c54adb9992b` |

Host cpp hash по-прежнему `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`;
host integration/native new tests не рассмотрены этим pure extraction gate.
T103/T088 и оставшиеся gates не закрываются. Записано только дополнение этого
отчёта, код/нормы/чужие файлы/Git не менялись; VM/build/tests не запускались.

## T103 Phase2 — повторная проверка migration H1, 2026-10-22

**C0 / H0; migration H1 снят только на уровне требований и плана проверок.**
По speckit-analyze рассмотрены только новые plan.md:3175–3201 и
quickstart.md:1318–1337, в сопоставлении с прежним выбранным ALL-entries
планом, spec Session 2026-10-22, SafeHistory data model и native-only contract.
Это scoped requirements/checklist/analyze GO для продолжения согласованного
tests-first среза, не SOURCE GO ещё не рассмотренных тестов/host diff и не
разрешение пропустить meaningful old-host RED перед изменением host.

Default runner действительно содержит 23 ID: 14 auth/transport/TLS,
cancel-before-start и восемь history cases. Новая матрица покрывает все эти
ID без удаления, skip/xfail или исключения из production guard. Полезный
actual all-GET Back/Forward остаётся положительным требованием history-get
и opt-in history-host-get: постоянный запрет/reset не может заменить его.
history-post/history-host-same-url проверяют fresh list/reset/один fresh GET
Forward, а не восстановление старого POST/GET ID. history-entry и
history-entry-same-url становятся production-negative: команда действительно
отправлена, отмена принадлежит host до begin/replacement, fixture не Cancel,
текущие ID/DOM/generation/bridge сохраняются. Положительный selected-entry
сценарий не теряется, а проверяется отдельно на all-GET истории.

cancel-history-host сохраняет именно раннюю отмену допустимого native BF
благодаря all-GET A→B→C подготовке; отмена fresh-list fallback не подменяет
эту проверку. cancel-history-script остаётся fixture lifecycle control, а не
доказательством production fence. Same-document сохраняет документ/authority,
но не подтверждает GET proof изменённой записи. Для 14 остальных случаев и
cancel-before-start прежние требования сохранены, будущий PASS на новом
host требуется заново. Counts должны выводиться из конкретных новых
последовательностей; расширение допустимых counts ради GREEN не разрешено.

Все семь прежних integration групп, pending/session/mutation/reset fences и
terminal selected-ID до latch/nonce сохраняются: два новых opt-in случая их
не заменяют. Конфликтов с неизменными spec/data-model/contract/tasks и
constitution в этом дополнении не найдено; новой задачи, продуктового выбора
или ослабления норм для этой миграции не требуется. Проверка actual test diff
должна подтвердить перечисленные наблюдаемые признаки и точные counts до run.

Независимо подтверждены append-only префиксы: первые 3173 строки plan имеют
SHA-256 `7b84e844149a1630b8564e43d832efd2595241d9822399a3b1c42c80c860a050`,
первые 1316 строк quickstart —
`e94e94fdf40af09f71b1de9f0a7a47d0a6d86a010e2cf6da4a2c986c501f0cbb`.
Полные текущие SHA-256:

- plan: `6d7e8144ec00d670936dd3ff63354ac2d45215d264218db75cfe3f0a913ccdfd`;
- quickstart: `1a33e2adbab99031bb72d4b10dd16bc287a520068a01bd9b027f4c00333972d5`.

Checklist inventory повторно совпал byte-for-byte: 198 файлов, 31 с checklist
items, 477 checked / 0 unchecked; canonical inventory SHA-256
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Это повторное применение прежних требований к новой матрице, не новый полный
аудит 477 пунктов; markers reviewer не менял. Spec/data-model/contract/research/
tasks/constitution hashes совпали с предыдущим gate; host cpp остаётся
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.

Prerequisite checker не поддерживает предписанный skill флаг --require-spec;
использован штатный --json --require-tasks --include-tasks с отдельной проверкой
наличия/чтением spec. Before/after analyze hooks отключены, YAML разобран.
Записано только это дополнение своего отчёта. Новые opt-in исходники здесь
не ревьюились; VM/device/build/tests/Git/network mutations не выполнялись.
Stage11 остаётся mechanism/API-only evidence с PRODUCTION_FENCES_PROVEN=0;
T103/T088/T097, production regression и release gates остаются открытыми.

## SOURCE review — initial production opt-in tests, 2026-10-22

**C0 / H0; SOURCE GO только для двух native tests до initial old-host RED.**
Применён code-reviewer. Независимо сверены три заявленных текущих hash и
прочитан diff против frozen stage10 источников (их hashes совпали с ранее
reviewed 73a9c041… / f4f8a6ab… / 8600fa0e…). Рассмотрены production helpers
cpp:412–616, dispatcher:1230, update callback:1421–1425, ContentLoading:1457,
native final response:1469–1498, POST observation:1508–1513,
NavigationStarting:1527–1537, регистрация:1656–1657; прочитаны существующие
requestHistoryResetBridge, lifecycle/deadline и реальные host callers.

| Файл | Reviewed SHA-256 |
|---|---|
| WebView2AuthNativeTests.cpp | `2043fd133fde9f1802643d47b73869398438e2881fe6222a359d3c2ffab9ce46` |
| WebView2AuthLoopback.py | `580df871b32e1eb1609f8f10e27d3c14cadf08d8e456742f39a40065bd69c17e` |
| RunWebView2AuthNativeTests.ps1 | `9b6d1270ba1e68841a423e26f37bf7a1fc32e51bd723c284029c4cf7f2c09d6d` |

Новые opt-in history-host-get/history-host-quarantine не входят в default23;
старый default список и тела прежних сценариев сохранены. Shared observers
расширены условиями только этих двух scenario predicates; старый reset branch
сохраняет прежний путь. Согласованная migration matrix остаётся следующим
обязательным изменением старых oracles при production integration, а не уже
выполненной миграцией или разрешением старого unsafe поведения на новом host.

GET случай проверяет A→B→C→host Back B→host Forward C с сохранением исходных
трёх actual entry IDs/порядка/URL/currentIndex. Quarantine случай проверяет
A→реальный POST-B→C→host fresh list→fresh Forward C→полезные host BF list/C.
Back/Forward вызывают только публичные host buttons; CDP в новых ветках
используется только для getNavigationHistory. Нет fixture reset, ALL-nav
permit/cancellation или ручного latch/nonce. Прежняя origin-isolation fence
не заменяет навигационную политику; same-origin новые переходы она не отменяет.

На каждой фазе обязательны success/status200, совпадающие navigation IDs и
generation с новым документом, реальные final request method/dest/mode/
generation tag, одна main response, точный URL, DOM marker и native_ready.
POST разрешён ровно в фазе1 quarantine и проверяется также request observer;
cached POST restore не становится допустимым из-за отсутствия повторного POST
на сервере. Независимо проверяется actual current entry ID, снятый наблюдением
ContentLoading, и терминальный полный порядок. Каждая фаза завершается
реальным bootstrap request_app_update; attached handler только считает вызовы
и проверяет владельца, не запускает installer. Прямой подстановки nonce нет.

Ожидание async reset ограничено ровно прежними A/POST-B/C плюс новой list
entry на индексе3, с точными IDs/URL и новым list ID. До singleton не выполняются
bridge/action. После reset требуется тот же committed list ID/URL и
canGoForward; новый Forward C не совпадает с прежними тремя IDs или list ID.
Последующие BF сохраняют новую пару IDs. Несостоявшийся reset/bridge/cookie
completion не превращается в PASS: общий 20s native deadline не изменён.
Низкий auth count ожидается, равенство обязательно перед продолжением;
избыточный count не проходит owner check. Async callbacks проверяют phase/
generation/current owner; malformed snapshots/missing observations дают
явный FAIL либо deadline, не более слабый резервный PASS.

Runner добавляет только opt-in регистрацию и отдельные counts: GET 3–5 с
нулём POST, quarantine 4–6 GET и ровно один POST, остальные пять/четыре
счётчика соответственно нулевые. Это три/четыре обязательные сетевые GET и
до двух восстановлений BF; эти диапазоны не распространяются на старые case
oracles. Ready1.5s/native20s/close10s/case35s, PE hashcheck, GUID isolation и
owned cleanup не изменены. Server выдаёт GET-B в all-GET, но не quarantine;
случайная загрузка GET по POST-B адресу не маскируется успешной страницей.

Старый host cpp остаётся a68f2ec8… с raw core.GoBack/GoForward. Поэтому
history-host-get может быть control PASS уже на нём; требуемый meaningful RED
для quarantine — после подтверждённых фаз0–2 host Back выдаёт BF к POST-B
вместо fresh list (unexpected-start), либо доказуемо не даёт требуемого пути.
Startup/build/profile/ранний response failure этим функциональным RED не
считается. Фактический исход и stage12 bundle этим SOURCE review не проверены.

Это только два initial positive integration oracles, не доказательство reset
ACK/ALL-nav fence/terminal-ID-before-authority внутри host и не все семь групп.
Production source review, отрицательные race/session/mutation проверки,
migration default23, runtime/installed/UI и T103/T088/T097 gates открыты.
Изменён только этот собственный отчёт; VM/build/tests/код/нормы/checklist
markers/чужие файлы и Git/network state reviewer не менял.

## Stage12 — независимая квалификация сохранённого old-host RED

**C0 / H0 по квалификации evidence; meaningful old-host RED gate пройден.**
Прочитаны все 150 строк сохранённого run.log, terminal result.json, frozen
Invoke-Runner/Run-History/run.cmd, Check-Terminal и релевантные frozen test
ветки в `t103-history12.SOPyRw`. Использовались только stage12 источники,
не текущие тесты, которые другой автор уже мигрирует. VM/build/tests и
повтор после отказа reviewer не запускал.

Manifest SHA-256 независимо совпал:
`5f8cc949767870eec2d20a2efb8acfbdfafb1ffe713dc64a06ac05a1f3fd9fcc`.
Оба manifests имеют 216 строк; diff prior→source содержит ровно шесть ранее
reviewed файлов: pure allGet policy h/cpp/tests и три native fixture файла.
Все шесть сохранённых файлов независимо совпали с manifest и SOURCE review.
Запись host cpp в manifest осталась
`a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6`.
Пять actual stage inputs hashes совпали с receipt; wrapper проверяет runtime
и inputs после child exit, source до staging/после staging/после child.
Receipt: terminal=true, preflight/staged/postflight=216, owned_processes=0,
elapsed_ms=109951, run_exit=1, failure=NATIVE_RUN_FAILED. Эти поля согласованы
с двумя реально исполненными случаями, а не startup/build failure.

BUILD=PASS и PE SHA из журнала:
`53d070fa42cfa812c73bba5acb04b17b12988f6dd2dfa7c6f2ef128270068cea`.
GET control: пять успешных фаз, selected IDs 5/6/8/6/8, GET method во всех
фазах, generation-tag match, REAL_BRIDGE=1…5; starts/completions=5/5,
cookie reads/signed-out=5/5, invalidations=0. Native/runner PASS, fixture exit0,
server exit0, counts `5 0 0 0 0 0`.

Quarantine: A→POST-B→C успешно завершили фазы0–2 с IDs5/6/8, native methods
GET/POST/GET, тремя real bridge dispatch и неизменённым auth lifecycle.
Затем настоящий host->back() вызвал четвёртый NavigationStarting, и combined
guard дал FAIL `host-history-unexpected-start`: starts=4, completions=3,
fixture exit1. Новый scenario branch не вызывает fixture Cancel; это
неподходящий фактический return start вместо требуемого fresh-list пути,
а не отсутствие API, ошибка сборки или неготовый сервер. Server drain exit0,
counts `2 0 0 0 0 1`; неполные для полного успешного quarantine counts
закономерны при остановке на первой проверке возврата. Итог 1/2 PASS и
общий run_exit1 сохраняются как RED, не переименовываются в suite PASS.

Граница наблюдения: combined Starting guard не печатает отдельно URI/kind/
redirected. Поэтому непосредственно доказан unexpected start после Back,
но не отдельно измеренные URI=POST-B и kind=BF. Объяснение raw GoBack к
предшествующей POST-B записи выводится из frozen host a68 и подтверждённого
порядка A/POST-B/C; это inference, не новый прямой runtime факт. Такой
диагностической детализации достаточно для initial functional RED gate,
но она не доказывает commit/restore POST или нарушение будущего fence.

Main отдельно сообщил Check-Terminal12 exit0: actual guest source216,
actual retained PE hash=53d070… и owned0. Reviewer проверил содержание и hash
самого Check-Terminal:
`42b5960a15e370e4889e9824d29b79285493e24240c621cc01923fe8f8466aaf`;
его выполнение в guest не повторял. Прямое guest readback — evidence main,
не собственная повторная VM проверка reviewer.

Сохранённые artifact SHA-256 независимо проверены:

- run.log: `4ec653cb4d81e765e8b19af8702d3a8f6e292056f7fd180e00095e85ef78d50f`;
- result.json: `115460ea8b444ad102865449267b1c9fe75d9bf9374de9aa8cdd63018422573a`;
- run.err: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes).

Допускается следующий согласованный tests-first production slice с отдельным
SOURCE review миграции default23 и actual host diff. Этот вывод не принимает
ещё меняемые migration tests, не подтверждает production quarantine/reset/
race/session fences и не закрывает T103/T088/T097 или выпуск. Stage11
mechanism/API PASS остаётся отдельным доказательством. Записано только это
дополнение своего отчёта; код/нормы/чеклисты/чужие файлы/Git не менялись.

## Preparation: карта пробелов семи native integration групп

**Только read-only coverage map; НЕ GO host/migration source или runtime.**
Основание: выбранный plan:3100–3173 и migration matrix:3175–3201;
spec Session 2026-10-22:661–694; data-model SafeHistory:709–722;
bridge contract:565–574; quickstart:1297–1337. Точные семь групп — уже
перечисленные выше в этом отчёте:262–308. Не следует путать их с шестью
первоначальными mechanism/API группами:49–58. Новых требований эта карта
не вводит. Code-reviewer применён для сопоставления требований с реальными
исполняемыми ветками, не для принятия незавершённого diff.

Evidence tiers: два initial opt-in имеют SOURCE review; stage12 дал только
old-host GET control PASS и quarantine functional RED. Migration default23
сейчас WIP: ниже отмечены видимые ветки/назначение, НЕ их SOURCE GO или PASS.
Текущие определения productionHistoryScenario включают history-get/post/
host-same-url; history-entry variants отправляют actual unsolicited CDP с
EXPECT_PRODUCTION_CANCEL/FIXTURE_CANCEL=0; cancel-host готовит all-GET.
Это preliminary coverage inventory для будущего frozen review, не фиксация
хеша/принятие меняемых файлов. Production host автора здесь не анализировался.

### 1. Полезная actual all-GET история

Уже есть executable positive: history-host-get и мигрируемый history-get
через host buttons, exact selected IDs/order/URL/DOM/GET/bridge. Stage12
проверил только прежний host. Quarantine positive после reset добавляет BF
новой пары list/C, а не обязательный reset каждого обычного GET.
Остаётся targeted native выбор среди повторов одного URL (nearest distinct)
и history с безопасной, но неподходящей meeting Back целью: detail/review/
share/report должны пропустить non-meeting запись. Проверять actual selected
ID/документ/bridge, а не только конечный URL; always-deny/always-fresh не PASS.
Чистые policy tests этих правил не доказывают их подключение к host.

### 2. Pending ДО первого async snapshot

Целенаправленного production pending-race oracle в новых2/default23 не видно.
history-entry negative не содержит native intent; cancel-before-start и
cancel-history-host отменяет fixture. Старые race-native/script-first имеют
fixture permit/second Cancel и negative-only outcome, не production proof.
Нужен existing-fixture сценарий с удержанной async границей snapshot: actual
BF, новый GET, form POST (включая совпадающий URL) и второе native действие
до snapshot и после all-GET допуска. До принятия snapshot — production Cancel
до begin, нет ContentLoading, generation/old bridge/cookie counters неизменны;
после — не более одного разрешённого выбранного BF, non-BF не допущены.
Отдельно timeout/API error/stale snapshot: pending снимается, старый callback
не запускает переход, следующие обычное и native действия снова работают.
Недоставленный конкурент не считается успешной проверкой гонки.

### 3. Terminal ДО consumption latch/nonce

Новые positives проверяют согласованность terminal ID/response/bridge ПОСЛЕ
приёма; это не доказательство, что nonce/cookie reconciliation не вышли раньше.
Нужен отдельный native тест: response+completion уже доставлены, terminal
continuation ещё удержана; bootstrap/update/auth side effects до подтверждения
отсутствуют. Wrong selected ID при том же URL, stale session/generation/revision
или ошибочный terminal result никогда не дают authority. Проверить оба порядка
response/completion, поздний terminal и следующий правильный GET через ordinary
latch. Конкурирующий same-URL GET-entry должен отличаться actual ID, не методом,
выведенным из URL; prewire NavigationId от CDP не предполагается.

### 4. GET proof не выводится из URL/snapshot

Есть positive actual final method/dest/mode/tag/status binding в новых2;
миграция history-entry/entry-same-url добавляет production denial через
историю с POST, retained ID/generation/bridge и следующий GET. Same-URL
fallback показывает fresh IDs, но не весь ANYWHERE guard.
Нужны host negatives: unknown/POST в другом URL и в forwardList; новый GET
того же URL не реабилитирует old POST ID; некорректный/отсутствующий method/
generation tag/dest/mode/status/binding и неполный snapshot не создают proof.
Ожидать отказ BF/безопасный fallback, без restore POST и новой authority;
POST count=1 сам по себе не исключает cached restore. Existing auth/5xx
controls не проверяют повторное использование history proof после таких ошибок.

### 5. Replacement / mutation / session

Частично есть retained authority после cancel-before-start, all-GET cancel-host,
fixture cancel-script и production denial entry variants; same-document
replaceState/hash сохраняет документ/bridge и допускает следующий документ.
Это ещё не proof ledger invalidation: нужен actual current-entry replacement,
URL mutation/новый pushState ID/исчезнувший entry и POST-U→safe-S rename,
после которых native BF не наследует прежнее GET подтверждение.
401/reselect/default auth cases проверяют recovery без заранее накопленной
history/pending/singleForward. Нужна подготовленная history перед logout,
expiry/401, bind нового account/workspace и recreate: старые snapshot/proof/
singleForward/intent отозваны; отпущенный старый async callback не выдаёт nonce,
auth callback или traversal в новой сессии. Проверять actual host hooks,
не один pure policy clear и не ручную установку epoch в fixture.

### 6. Полезный fallback, не обход POST

Positive executable — history-host-quarantine + мигрируемые history-post/
host-same-url: real POST, fresh list/reset, fresh C, затем actual BF. В stage12
это пока expected RED, не принятый production путь.
Нужны отрицательные ветки singleForward: исходный detail не individually
confirmed GET — цель не создаётся; ошибка fresh list/forward либо посторонний
переход/session boundary отзывает старую цель. Повторный клик не создаёт
второй synthetic fresh grant; после успешного свежего Forward обычный BF
новой пары остаётся полезным (не запрет всех последующих Forward).
Reset failure не открывает singleForward, безопасные «Встречи»/повтор остаются
доступны; ни raw GoBack, ни GET по старому POST URL не являются recovery.

### 7. Reset integration, НЕ fixture fence

Новый quarantine positive наблюдает host-only удаление старых entries и
same committed ID singleton, затем canForward и полезный BF. Он не вызывает
reset сам, но не посылает конкурентов и не наблюдает отдельно host reset ACK.
Stage11 history-reset доказал механизм/API под fixture ALL-nav fence — не
production interval. Нужен production reset-interval тест: BF и новые document
GET/POST после accepted GET, до ACK и между ACK и singleton verification
отменены production до begin; fixture только наблюдает, не Cancel.
Отдельные faults: error/malformed ACK, timeout, неверный/неполный snapshot,
другой current ID/URL, mutation/new ID/session/replacement во время reset.
Ни один не переносит proof и не открывает Forward; stale continuation не
снимает quarantine. Успех требует ACK + того же ID/URL/document/session/
generation singleton; затем обычные GET не запускают reset постоянно.

### Что это означает для следующего frozen review

Default23 migration сохраняет важное покрытие, но не закрывает автоматически
семь групп. Наиболее отсутствующие целевые production проверки — группы2/3,
ошибки/конкуренты группы7 и подготовленные history/session negatives группы5.
Группы1/4/6 имеют реальные positive/negative ветки, но перечисленные детали
нужно добавить/проверить отдельно. Один bounded existing native fixture и
opt-in варианты достаточны; новый generic framework/owner не требуется.
Одинаковые probes можно использовать для нескольких групп, но результаты
разделять: retained old bridge до replacement против запрета новой authority
после неверного terminal, mechanism reset против production cancellation.

Это не finding о ещё не прочитанной реализации Sagan и не требование изменить
нормы/задачи. Actual frozen migration/host review должен подтвердить свойства
и отметить остающиеся executable gaps; успешные 23+2 не означают полное T103.
Добавлен только свой отчёт; тесты/host/нормы/чеклисты/чужие файлы/Git не менялись,
VM/build/runtime повторов не было.

## SOURCE review — default23 migration против frozen Stage12

**C0 / H0; SOURCE GO только для трёх test migration файлов.**
Code-reviewer: прочитан полный delta cpp/PY/PS против сохранённых Stage12
`t103-history12.SOPyRw/apps/windows/Tests/GrafWindowsContractTests`, actual
callers/observers/retention helpers и утверждённая plan matrix:3175–3201.
Baseline три hashes независимо совпали с reviewed Stage12
2043fd13… / 580df871… / 9b6d1270…. Текущие exact SOURCE hashes:

| Файл | SHA-256 |
|---|---|
| WebView2AuthNativeTests.cpp | `7f23757e914a2fa92ddae2f4387a5785d569e468efdfe3d37648676d0a03da0d` |
| WebView2AuthLoopback.py | `e1b00f80972c1389d96e968c865d1c1910044412418329f17bbdf627dfa572fa` |
| RunWebView2AuthNativeTests.ps1 | `43f6d96089fea374b649dacae14c5ce2f20673853231d29fa6d7bf0b07081bd9` |

Default список по-прежнему содержит те же23 IDs и исполняется прежним foreach;
новых skip/xfail/filtered success нет. 14 auth/transport/TLS bodies и
cancel-before-start не ослаблены. Existing opt-in host-get/quarantine остаются;
shared production helpers расширены только нужными scenario predicates.
History-reset и старые race mechanism/negative-only ветки не выданы за
production fence, а семь интеграционных групп не объявлены пройденными.

history-get теперь идёт через настоящий host: A/B/C/B/A/B/C, семь фаз с
selectedIndex=page-1, полным порядком трёх исходных IDs/URL, native final GET,
generation/latch/DOM и real bridge на каждой фазе. history-post и
history-host-same-url используют семь quarantine фаз A/POST-B/C/fresh-list/
fresh-C/list/C, а не старые unsafe BF. Same-URL URL helper различает page marker
и actual entry ID: POST-B может иметь URL=A, но fresh list/C не совпадают с
прежними IDs. Exact pre-reset четыре entries допускают только ожидание;
singleton сохраняет committed list ID. Forward свежий, затем actual BF новой
пары. Нет fixture reset/CDP steering/regrant в этих production ветках.

history-entry/entry-same-url после A/POST-B/C отправляют одну actual CDP
команду к GET-A через POST-containing историю. Должны наблюдаться `{}` ACK,
один BF Starting и OperationCanceled completion с тем же cancelled nav ID;
отсутствие события/ACK не может пройти. Fixture Starting observer лишь
запоминает событие, не вызывает Cancel; ContentLoading в интервале сразу FAIL.
Ранняя production отмена обязана сохранить ready/generation/auth count,
current source/DOM, current C ID/index/count и рабочий прежний bootstrap nonce
(проверяется реальным update callback). Промежуточная потеря ready sticky FAIL.
Следующий ordinary GET-list должен создать новое поколение, одну связанную
native GET response с dest/mode/tag/status200, ContentLoading, новый current ID
не из старых A/B/C и один новый auth observation. Ручного finish/latch/nonce
или выдачи authority из fixture нет. Это проверка сохранения старого документа
и следующего нового, не разрешение unsolicited traversal в production.

cancel-history-host готовит именно all-GET A/B/C: убраны POST submit и POST-only
server route для этого case. Затем fixture отменяет допустимый host BF к B
до product, сохраняет C/bridge и проверяет следующий GET-A. Это прежний BF
lifecycle control, не отмена fresh-list fallback. cancel-script и same-document
сохраняют свои отдельные прежние сценарии и не доказывают GET proof mutation.

Counts разделены по конкретной последовательности, не расширены общим
диапазоном: entry variants = три обязательных GET (A/C/новый A) + максимум
один provisional GET, ровно один POST; cancel-host = четыре обязательных
GET (A/B/C/новый A) + максимум один provisional B, POST=0. GET seven-phase
case сохраняет 3–7 GET и POST=0; quarantine seven-phase = четыре обязательных
GET (A/C/fresh list/fresh C) + до двух BF GET, ровно один POST. Остальные
счётчики нулевые. Server не превращает ошибочный GET POST-only B в success;
для cancel-host GET-B стал явно допустим по новой all-GET подготовке.

Native deadline20s/close10s/case35s, ожидание cookie до exact equality,
phase/generation/navigation guards, GUID/profile isolation, server drain,
PE hashcheck и owned cleanup не ослаблены; missing/extra/неверные наблюдения
дают FAIL/deadline, не резервный PASS. Сохраняемый Stage12 functional RED
не заменяется результатом этой проверки исходников.

Это не SOURCE GO WIP WebView2Host, не runtime GREEN новой миграции и не
закрытие gap map групп1–7, T103/T088/T097 или release. После отдельного host
SOURCE gate нужен frozen build/run с реальными oracles, не исключения ради
старых тестов. Reviewer добавил только этот собственный отчёт; код/нормы/
чеклисты/чужие файлы/Git не менялись, VM/build/tests не запускались.

## Requirements/checklist/analyze — controlled continuation initial negatives

**C0 / H0; GO только на tests-first подготовку pending-read-fence и
terminal-held по новому техническому дополнению.** Это не SOURCE GO seam,
тестов или WIP host и не разрешение runtime до отдельного frozen review.
По speckit-analyze полностью прочитаны новые plan:3203–3240 и
quickstart:1339–1353, сопоставлены с выбранным plan Phase2, spec Session
2026-10-22, SafeHistory data model/bridge contract и прежними семью группами.
Lane прежний high-risk-product; FR-005/006, parity FR-002/003 и SC-002 partial
остаются в T103/T088. Обе задачи открыты; unmapped scoped work/new tasks нет.
Новых продуктовых вопросов/изменения shared contract здесь не требуется.

Один SDK-only friend declaration и определение только в existing native test
не добавляют public API/runtime switch/persistent owner. Допустим только
декоратор настоящего production adapter callable: original операция исполняется,
её неизменённый result/ACK удерживается и однократно доставляется original
continuation на прежнем UI dispatcher. Выбор real selecting/accepting/resetting
stage вместо ordinal call исключает зависимость от числа служебных CDP calls.
Нет fixture writes stage/revision/session/proof/nonce, fake finish,
сфабрикованного snapshot/ACK/header или fixture Cancel. Activation wrapper
немедленно вызывает original и наблюдает ошибочную раннюю активацию, а не
подавляет её вместо продукта. Host lifetime и удержанные closures ограничены
owned teardown; destroy host с ещё недоставленным его callback не допускается.

| Initial scenario | Необходимый наблюдаемый результат |
|---|---|
| pending-read-fence | Настоящий host Back достиг selecting result, который удержан. Реальные BF/GET/form POST конкуренты дают каждый собственные Starting и OperationCanceled ID без ContentLoading; current ID/generation/auth/retained bridge не изменены. Повторное native действие не создаёт второй intent. После original result delivery выбранный BF проходит обычный production путь. Недоставленный конкурент не PASS. |
| terminal-held | Настоящий selected BF уже имеет response/completion; accepting snapshot result удержан. До delivery нет latch consumption/нового nonce/auth/cookie/bootstrap/activation, действительная попытка bridge button не вызывает native handler. После original delivery обычный finalizer принимает выбранный GET, и реальный bridge callback работает. Fixture не активирует документ. |

Эта конструкция проверяет именно отсутствие ранних side effects, а не только
правильное конечное состояние. Будущий SOURCE review должен проследить, что
hold действительно достигнут, попытка конкурента/button исполнена до release,
wrapper не маскирует активацию, delivery однократна, очередь/teardown безопасны,
а missing/duplicate/stale observations не дают резервный PASS. Это выводы из
написанных oracles/one-shot/lifetime ограничений, не новое продуктовое правило.

Первый сценарий не принимает группу2 после all-GET допуска и её timeout/error
ветки; terminal-held не принимает wrong-ID и оба response delivery порядка.
Reset ACK/readback fences/errors, prepared stale-account/session/mutation и
остальная gap map остаются открытыми. Упоминание групп2/3/5/7 как возможных
пользователей одного seam не расширяет первый срез за пределы двух opt-in.
Default23/initial2, native20s/close10s/case35s, source/PE/GUID/owned0 и
synthetic/no-account/no-device evidence bounds не ослаблены. В логах нельзя
публиковать настоящие nonce/cookies/response contents; допустимы synthetic
markers и счётчики прежней модели evidence.

Противоречий constitution/requirements/data model/contract в этой delta нет;
ambiguity/duplication/inconsistency CRITICAL/HIGH=0. Прежние требования
requirements/security/UX применены к observation-only seam и двум oracles,
не к ещё написанному host. Checklist inventory повторно byte-identical:
198 файлов / 31 checkbox file / 477 checked / 0 unchecked; canonical hash
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Markers не менялись; это requirements reuse, не runtime acceptance.

Independently verified append-only: первые3201 строки plan сохранили SHA
`6d7e8144ec00d670936dd3ff63354ac2d45215d264218db75cfe3f0a913ccdfd`,
первые1337 строк quickstart —
`1a33e2adbab99031bb72d4b10dd16bc287a520068a01bd9b027f4c00333972d5`.
Reviewed полные текущие SHA-256:

- plan: `92eea9047baa9121cfed7a6fdd897e42efc5ac39c32fd908768cf9600dc51d42`;
- quickstart: `698b3f4424614ff53c69040da09d284696dc10e9157ed335189a8f6b9a9acf01`.

Spec/data-model/contract/research/tasks/constitution hashes прежние. Штатный
prerequisite с поддерживаемыми --json --require-tasks --include-tasks подтвердил
F200 и artifacts; spec отдельно прочитан. YAML разобран, before/after_analyze
hooks disabled. Проверка строго scoped, не полный повтор аудита F200/checklists.
Изменён только этот собственный отчёт. Code/host/test/нормы/чеклисты/чужие файлы/
Git/network state не менялись; VM/device/build/runtime не запускались.
Следующий gate — SOURCE review exact seam/test/host bytes, не этот pre-code GO.
T103/T088/T097 и release остаются открытыми.

## Final actual host SOURCE: два файла, допуск к frozen25, 2026-10-22

**CRITICAL 0 / HIGH 0 — SOURCE GO только к первому отдельно квалифицированному
frozen25 functional/debug build/run.** Это не compilation/runtime PASS, не
принятие полного host/T103 и не закрытие семи групп отрицательных проверок.
Применён code-reviewer; проверен полный ограниченный diff двух файлов против
предъявленного baseline, затем реальные окружающие callers/latch/policy.
Автор сообщил STOP; SHA независимо совпали в начале и конце чтения.

| Файл | Baseline SHA-256 | Final SHA-256 |
|---|---|---|
| WebView2Host.h | `354ef351a519bce05af0aa60bf480b84434061d331000df856ad5471ec0d0cd1` | `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927` |
| WebView2Host.cpp | `a68f2ec8a2696204e25167a2d90261f41d3e839794453bed2a6e28b659d7b2e6` | `8590fcfd38f95d6448fd1f7bf492a4479ea60bb5410f3f9f73afcf91d21f6e83` |

Baseline: `/tmp/graf-t103-host-review.tYHVxA`; candidate:
`/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup/apps/windows/RecApp/Web/`.
Последняя header delta — один SDK-only friend WebView2HistoryNativeFixture:360;
он не добавляет web/public intent или runtime bypass. Shared response guard
cpp:2252–2264 дополнительно требует browser Sec-Fetch-Mode navigate; метод и
destination берутся из настоящего request, не из DOM/fixture.

Прослеженные защитные границы, SOURCE evidence (cpp, если не оговорено):

- Pending выставлен до первого async snapshot:1107–1115. Результат связан с
  operation/session/generation/revision/source. Selection использует SafeHistory
  target/allGet (WebViewRoutePolicy.cpp:451–518): неизвестная/POST запись в любой
  части actual snapshot запрещает native BF; raw GoBack/GoForward удалены.
  Starting:1987–2015 отменяет pending/чужой BF до begin, без сброса response,
  generation/nonce. Repeated Back/Forward/reload/navigate не открывают второй intent.
- Fresh GET создаётся native CreateWebResourceRequest:2068–2073 с новым native
  marker; Starting RequestHeaders сверяет его до begin:1995–2008. Это не GET на
  основании одного URL. WebResourceRequested:2213–2245 требует actual GET для
  fresh/traversal, снимает marker до сети и отвечает отказом при несоответствии;
  catch также пытается закрыть запрос, а не пропускает POST. Page не выдаёт permit.
- Terminal snapshot:1165–1191 проверяет actual selected current ID/URL и весь
  allGET набор; замещённый прежний current ID теряет proof. Native finalizer:
  2844–2883 проверяет navigation owner, command ACK и свежий terminal revision
  ДО tryFinishDocumentNavigation, который потребляет response/completion latch.
  Новый nonce/cookie/bootstrap возможен только через nativeActivateDocument:
  2559–2637 после этого пути, а не по CDP ACK/DOM/snapshot в отдельности.
- Proof ставится confirmCurrent:1200 только после ordinary cabinet latch,
  из navigationMethod, обновлённого correlated actual response:731–760,
  2247–2266. Reset:1201–1228 не придумывает новый GET: требуется подтверждённый
  list current; resetting удерживается через ACK и отдельный singleton snapshot
  с теми же ID/URL/session/generation. CurrentIsGet проверен повторно. Весь этот
  участок fenced до новой activation; ACK не вызывает fake completion.
- Полезный путь: actual nearest eligible allGET target; без него meeting Back
  даёт fresh list и одну fresh Forward цель лишь из currentIsGet:1124–1145.
  Reset не вызывается на каждом обычном allGET. Чужая ordinary navigation,
  ошибка, mutation и session clear отзывают singleForward; отмена до begin не
  уничтожает уходящий GET proof. Это source trace, не доказательство native UX.
- SourceChanged:2168–2200 отзывает proof same-document mutation, accepting/reset
  mutation завершается отказом; HistoryChanged:2202–2209 отзывает revision и
  pending selection/permit. В navigating событие не отменяет ожидаемый переход,
  а вынуждает свежую terminal проверку. Ошибка read/reset/timeout не даёт authority.

Actual AppMain прочитан read-only, не изменён:1222–1235 cookie handler передаёт
token в NativeCapture и при смене authGeneration вызывает bind empty;1903–1912
и tick:3439–3451 связывают уже подтверждённый account. NativeCapture.h:443–465
не меняет generation при том же token/signedOutObserved. В host:446–475 смена
origin/user/workspace/token/authGeneration очищает старый session proof, а
подтверждённый bind на готовом list запускает новый fresh GET штатным путём,
не переносит proof старого epoch. Поэтому безусловного повторяющегося bind loop
при неизменных входных данных в source нет; реальная последовательность async
account/cookie callbacks всё ещё требует отдельного integration evidence.
Cookie смена:540–562, authRequired/closed:565–567, реальный process failure:
1042–1061 и close очищают историю; callbacks имеют stale/lifetime guards.

Границы знания перед запуском, не доказанные findings и не повод ослаблять guard:

1. RemoveHeader в resource callback не доказывает, что runtime не сохранил
   native marker в browser entry extraHeaders. Fresh fallback → Forward → actual
   BF полезной новой GET пары должен пройти 7-phase native positive; stale marker
   при Starting сейчас консервативно отменит переход. До наблюдения — гипотеза.
2. Ожидаемый HistoryChanged во время navigating не стирает intent, но позднее
   событие относительно accepting/reset ACK/readback может дать stale revision
   и fail-closed либо отозвать уже свежую историю. SOURCE не доказывает порядок
   доставки; functional/debug positive должен подтвердить отсутствие ложного
   отказа. Нельзя автоматически игнорировать событие ради зелёного результата.
3. Новый RequestHeaders вызов/SDK projection и native async continuations не
   содержат обнаруженного compile-level противоречия при чтении, но сборка здесь
   НЕ выполнялась. SDK compile, actual final-method/dest/mode correlation и обе
   response/completion очередности остаются самостоятельными runtime gates.

Все семь negative integration groups прежней gap map открыты, включая after-permit
race, wrong ID, terminal-held, stale session/mutation и reset errors/fences.
Frozen25 не заменяет их даже при 25/25. Новые controlled-continuation opt-in ещё
требуют собственного exact-source допуска. Старые stage11/12 доказательства не
переносятся на эти два SHA. T103/T088/T097/full app/release не закрыты.
Lane high-risk-product не понижен; следующий шаг — freeze host2 + ранее reviewed
migration3 с собственным manifest, build/functional/debug receipts и owned cleanup.
Изменён только этот append собственного отчёта; code/tests/нормы/checklist markers/
чужие отчёты/Git/network не менялись, VM/device/build/tests не запускались.

## Отдельный tiny host compile fix SOURCE, 2026-10-22

**C0/H0 — scoped SOURCE GO к повторному frozen25 build/functional/debug run.**
Этот допуск не относится к новым двум continuation tests и не является runtime
приёмкой. Сообщённый main stage13 compile failure до cases не трактуется как
результат API/25 сценариев; его receipts здесь независимо не квалифицировались.

Независимо проверены baseline stage13 WebView2Host.cpp SHA
`8590fcfd38f95d6448fd1f7bf492a4479ea60bb5410f3f9f73afcf91d21f6e83`
и final candidate
`24eb7c594026cd570abcdea92a0a45e351fee1010c411d349f55a50f62de4810`.
Header прежний:
`f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`.
Baseline взят из t103-history13.y66VAs/apps/windows/RecApp/Web/.
Полный diff — ровно две замены cpp:2093–2094: range-for/JsonValue.GetObject
заменены bounded uint32_t index и JsonArray.GetObjectAt(index).

Это устраняет token GetObject, конфликтующий с Windows GetObjectW macro,
без undef/изменения платформенных заголовков. Прежние проверки entries size
1..128, integral currentIndex, ID range/integrality, URL length, UTF-8 parsing,
policy snapshot validation и exception-to-nullopt сохранены. Порядок массива,
currentIndex и session/revision/latch/reset gates не изменились. Невалидный
element type по-прежнему даёт exception и отказ, не fabricated proof. Переполнение
индекса невозможно при прежнем max128. Обнаруженных C/H source дефектов:0.

Stage14 path/source216 manifest сообщён main, но весь wrapper/manifest не был
предметом этого tiny review: это допуск указанных host bytes, не утверждение
независимой квалификации внешнего bundle. Main отдельно замораживает unchanged
migration3/host2. Сборка и новые runtime receipts обязательны; предыдущий SOURCE
не оказался compilation PASS и не заменяет его. Семь negative groups открыты.
Изменён только собственный report append; VM/build/tests/Git/код не запускались
и не менялись. Test-only2 SOURCE решение будет отдельным разделом.

## Test-only2 actual SOURCE: controlled continuations, 2026-10-22

**C0/H0 — SOURCE GO только на отдельный frozen dedicated2 build/run:
history-pending-read-fence и history-terminal-held.** Это не runtime PASS,
не закрытие групп2/3 и не допуск полной acceptance T103. Code-reviewer прочитан
полностью; проверен весь bounded diff трёх owned файлов к точным frozen stage13
копиям, а не к общему dirty HEAD. Требования initial negatives из report:993
и plan:3203–3240 применены без изменения норм/checklist markers.

Baseline directory:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history13.y66VAs/apps/windows/Tests/GrafWindowsContractTests/`.
Все три baseline SHA независимо совпали с одобренной migration3 report:920:

| Файл | Baseline SHA-256 | Final SHA-256 |
|---|---|---|
| WebView2AuthNativeTests.cpp | `7f23757e914a2fa92ddae2f4387a5785d569e468efdfe3d37648676d0a03da0d` | `0e968ade6e7e14a90589b7112b6ec45bcd3ad92f4618ab713798c5780e609f68` |
| WebView2AuthLoopback.py | `e1b00f80972c1389d96e968c865d1c1910044412418329f17bbdf627dfa572fa` | `9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e` |
| RunWebView2AuthNativeTests.ps1 | `43f6d96089fea374b649dacae14c5ce2f20673853231d29fa6d7bf0b07081bd9` | `8831610834eb7bba5e2b99b996e308fd3cf508c2df7c1bb2fabbb966b3aa10fb` |

Final SHA проверены в начале и после чтения. Plan/quickstart остаются
`92eea9047baa9121cfed7a6fdd897e42efc5ac39c32fd908768cf9600dc51d42` /
`698b3f4424614ff53c69040da09d284696dc10e9157ed335189a8f6b9a9acf01`.

### Реальный continuation и наблюдаемость

- Native fixture cpp:26–96 определён только в тесте; использует approved SDK
  friend. Декоратор сохраняет originalRead/Activate. Original read выполняется;
  capture выбирается по actual selecting/accepting stage после подготовки A/B/C,
  не по номеру CDP request. Настоящий non-null result удерживается без изменения
  содержимого, pending хранит исходную continuation. Нет writes host stage,
  revision/session/GET proof/nonce, fake response/ACK/finish или fixture Cancel.
- deliver проверяет original UI thread, held/pending/нулевой deliveries,
  извлекает closure через exchange и вызывает её один раз. Wrong thread,
  повтор capture, null result или повтор delivery выставляют unexpected, который
  исключает PASS. Activate wrapper считает вызовы и немедленно вызывает original:
  раннюю activation он не маскирует. install после phase2:676–682 обеспечивает,
  что подготовительные genuine GET/bridge уже приняты до удержания.
- Pending owner:496–511 удерживает source/current C, generation, ready и прежние
  accepted starts/completions/auth/cookie/signed-out counters. Повтор native
  Back/Forward:576–582 не должен создать второй read. Три JS команды:587–601
  подтверждают issuer C и инициируют настоящий BF, location GET и form POST.
  Script success сам по себе не PASS:603–609 ждёт actual ID/completion.
- Starting observer:1851–1864 требует отдельный неповторяющийся nonzero ID,
  правильный URL/kind и не вызывает Cancel. Отдельные per-ID completion records:
  1740–1749 требуют HTTP0, успех=false и OperationCanceled; duplicate/unmatched
  completion — отказ. ContentLoading при hold немедленно FAIL:1770–1774.
  Следующий конкурент не запускается до подтверждённой отмены предыдущего.
  Missing event остаётся nonzero по прежнему deadline, не превращается в PASS.
- После всех отмен read-only DOM + native CDP snapshot:532–570 требуют C,
  прежние ordered A/B/C IDs и currentIndex2; retained real bootstrap button
  должен дать ровно один дополнительный update callback. Production handler
  :1719–1728 проверяет его прежнюю authority, а не выдаёт новую.
- Terminal owner:507–511 и fixture accepting требуют настоящий selected B,
  response GET/not POST, one response/ContentLoading/completion/HTTP200,
  новый document generation, непринятый latch, false terminalValidated и пустой
  documentNonce. На hold activations/auth/cookie/update counters неизменны.
  Read-only snapshot требует actual прежний B ID/index1 и DOM history-b.
  Настоящий bridge-button click исполняется при hold; native update не допускается.
  Только после script ACK и повторной owner проверки вызывается original delivery
  :614–633, без ручного finalizer/nonce/ready. Обычный production acceptance далее
  обязан сам дать реальные bridge callbacks на B и последующем Forward C.
- Final phase:667–671 требует один capture/delivery, отсутствие held/unexpected,
  два настоящих activation, состоявшиеся DOM/button/ACK observations. Подготовка
  и конечные фазы сохраняют existing actual ID/order/final-method/bridge oracle.

### Сохранность прежних сценариев и завершение

Полный PS/PY diff только добавляет opt-in имена, прежнюю synthetic GET page
выдачу для двух имён и два отдельных count bounds. Default23 список не изменён,
прежние branches/counts/initial2 IDs не удалены и не ослаблены. Общие C++ guards
добавляют heldRetainedDispatches, равный0 во всех прежних сценариях; остальные
новые ветки ограничены controlledHistoryScenario. Старые сценарии не получают
friend injection, fixture Cancel или дополнительный PASS/fallback.

Pending counts3..7 = A/B/C + до двух useful BF reads + до двух provisional GET
конкурентов; terminal counts3..5 = A/B/C + до двух BF reads. В обоих остальных
пяти счётчиках0, включая non-GET: POST reaching server отвергается. Counts не
подменяют native per-ID cancellation/selected document checks. PY do_POST
и счётчик non-GET прежние, новая POST preparation на сервере не разрешена.

Native20s/close10s, server ready1.5s/case35s и runner exit/hash/GUID/process
cleanup сохранены. finish:250–268 восстанавливает adapters и доставляет held
original continuation до host.close, пока host/fixture ещё живы; UI dispatcher
остаётся до browser exit. Fail-path release может запустить настоящее завершение
на живом host перед немедленным close, но уже terminal FAIL не становится PASS.
Ошибки restore/close делают process exit nonzero. Поздние original adapters
сохраняют production alive guards; fixture member живёт вместе с Application.
Missing async callback/failed queue delivery не разрешает успех, а доходит до
существующего deadline. Исключения parsing/script/ownership закрываются FAIL.

Доказанных C/H дефектов этого test delta не найдено. Это допускает сборку и
наблюдение, а не утверждает runtime устойчивость timing/SDK. Actual host compile
fix24eb имеет отдельный SOURCE gate выше; stage13 по сообщению main остановился
до cases и не доказал 25 runtime сценариев. Dedicated2 bundle ещё требует своих
frozen source/PE/DLL/runner hashes и saved terminal qualification. Ни stage13,
ни подготовленный stage14 frozen25 не считаются выполнением новых двух tests.
Все семь integration groups остаются открытыми как полные группы; after-permit
race/wrong-ID/metadata order/reset/session faults этим срезом не закрываются.
Изменён только собственный append; VM/device/build/tests/Git/нормы/checklists/
код/чужие файлы не менялись. Lane high-risk-product, T103/T088/T097/release open.

## Candidate assessment: убрать eager GET из account bind, 2026-10-22

**C0/H0 для минимального design candidate: удалить только eager reload block
cpp:463–475, сохранить clearHistorySession и остальные проверки.** Кандидат
согласуется с действующим spec/plan; новый product clarify или ослабление норм
не нужны. Это pre-edit assessment, не SOURCE GO ещё не предъявленного diff и
не runtime PASS. Прочитан current host24eb, spec Session:661–694, plan:3100–3173,
data-model:709–722, bridge:565–574, quickstart:1297–1316 и реальные bind callers.

Источник второго перехода конкретен: initial200 native fixture cookie handler
cpp:1692–1694 вызывает bindUserTimeAccount при первом cookie read. В host:452–459
это changed; блок:466–474 вызывает nativeFreshHistory независимо пользовательской
навигации. Получается второй настоящий GET/Starting/completion/cookie read.
Сообщённые main starts2/completions2/current_reads2/counts2 согласуются с этим
путём; live stage14 logs/terminal здесь не читались и не квалифицированы.
Прежнее expected1 не следует менять ради нового незапрошенного reload.

Точное различие условий: plan:3148–3158 требует reset ПОСЛЕ ordinary accepted
GET list/home в новой сессии/карантине; он не требует, чтобы account bind сам
создавал такой HTTP request. Data-model требует proof после actual final GET
и cabinet latch ТЕКУЩЕЙ сессии. Уже принятый до bind документ не является новым
GET нового epoch, и reset сам по себе не может это исправить/выдать proof.
Поэтому немедленно переподтвердить старый current как GET либо сохранить его
proof было бы ошибкой; оставить документ живым, а history quarantined — допустимо.
Ранее в SOURCE разделе описан существовавший eager path, не нормативное
требование его сохранить и не доказательство необходимости второго запроса.

После удаления блока unchanged clearHistorySession:1093–1098 продолжит менять
session/operation/revision, очищать entries/proofs/singleForward, ставить
historyNeedsReset и отзывать pending intent. Ни current URL/документ/nonce,
ни пользовательские cookies/данные этим удалением не подменяются. Native BF
не получает permit: target требует полный fresh allGET; unsolicited BF в idle
по-прежнему отменяется до begin. Stale result не проходит session/operation guards.

Полезный путь не исчезает: ordinary navigation остаётся доступной; из detail/
review/share/deletion-report canGoBack допускает existing fresh-list fallback
даже без snapshot/proof. Новый snapshot не реабилитирует старые entries. Только
следующий действительно принятый GET получает собственный new-session proof;
принятый list при сохранённом quarantine проходит обычный reset/ACK/same singleton.
SingleForward можно сохранить лишь из current, подтверждённого уже после boundary;
из старого до-bind документа его отсутствие ожидаемо, не повод копировать proof.
На текущем list сразу после bind нет истории прежней сессии, поэтому временно
недоступные BF не означают вечное отключение истории или navigation dead end.

Security/functional blocker, вызванный именно удалением eager блока, не найден.
Не требуется сохранять второй GET ради reset и не следует добавлять fake
snapshot/confirmCurrent/activation в bind. Контроль: unchanged initial200 должен
сохранить один реальный load/cookie read и все свои bridge/user-time assertions;
следующие navigation/fallback/reset и session/stale-result cases остаются отдельными
native gates. Неполные session/mutation группы этим assessment не принимаются.
После авторской правки нужен bounded exact-diff/hash SOURCE re-review и новые
frozen runtime receipts. Stage14 ещё не terminal; никаких общих PASS/FAIL25 нет.
Изменён только этот own report append. Code/tests/spec/plan/checklists/Git/VM/
build/runtime не менялись и не запускались; T103/T088/T097/release остаются open.

## Exact SOURCE: удаление eager GET и отдельный observer, 2026-10-22

**(a) C0/H0, scoped SOURCE GO для сборки/повтора unchanged initial200 с
host cpp439460a57f1bbc40e2601c27b361f53c9ac3e005cea7fda6a857e2f8e95da7e2.**
Сравнение полных файлов с frozen stage15.xDSxo9 cpp
24eb7c594026cd570abcdea92a0a45e351fee1010c411d349f55a50f62de4810
даёт ровно один hunk в bindUserTimeAccount: удалён eager fresh-list GET блок
из13 строк, добавлен один комментарий об отзыве proofs. Остальные байты host
не изменены; header остаётся f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927.
Unchanged clearHistorySession отзывает session/operation, snapshot/proofs,
singleForward и pending intent, оставляет historyNeedsReset. Bind не выдаёт
нового GET proof, не активирует старый entry и не меняет nonce/latch/reset guards.
Accepted current page сохраняется; последующий настоящий accepted GET новой
сессии и штатный fallback/reset остаются путём восстановления полезной истории.
Это точный diff ранее оценённого кандидата, согласованный с plan:3148–3158;
ни второй HTTP load при bind, ни немедленный reset старого документа нормой
не требуются. initial200 expected1/bridge/cookie assertions ослаблять нельзя.
Допуск не доказывает runtime исправление и не распространяется на оставшиеся
quarantine phase5 отказы или все семь integration groups.

**(b) Независимо C0/H0, scoped SOURCE GO для diagnostic-only quarantine run
с НЕИЗМЕНЁННЫМ host24eb и test cpp
f926b4443b51a097f802ed1ada907992ecb39cb9fcd10af863c4f69c14c8bd4e.**
Полный diff против frozen stage15 test cpp
0e968ade6e7e14a90589b7112b6ec45bcd3ad92f4618ab713798c5780e609f68
содержит только3 добавленные строки printf: phase, NavigationId, NavigationKind
и bool RequestHeaders().Contains(X-GRAF-History-Intent) в существующем
productionHistoryScenario NavigationStarting observer перед прежними guards.
Синхронное чтение использует тот же API, который читает actual host subscriber;
не добавляет Cancel/permit/headers mutation, stage/proof/session/nonce writes,
новые callback/lifetime либо pass path. Нет URL, значений заголовков или secrets.
Формат %u/%llu/%d соответствует прежнему historyPhase и явным casts.
Прежние guards/counts/deadlines не изменены. Наличие marker на фазе5 будет
конкретным наблюдением RequestHeaders в Starting, но не самостоятельным
доказательством механизма хранения extraHeaders или полного causal fix.
Не смешивать этот опыт с host4394: для сопоставимости причины оставлен24eb.

Оба допуска — SOURCE-only для разных frozen bundles, не runtime/full host GO.
Saved stage14/15 qualification остаётся отдельной следующей работой; сообщённые
main terminal/guest rechecks здесь не переименованы в независимо проверенные.
Lane high-risk-product; T103/T088/T097/release открыты. Изменён только этот
append; VM/build/tests/Git/код/нормы/checklists/чужие файлы не менялись.

## Independent saved-runtime qualification: stage14 + stage15, 2026-10-22

**C0/H0 по достоверности и ограниченному смыслу сохранённых результатов.**
Stage14 — qualified functional RED: BUILD PASS, 21/25 PASS, четыре реальных
отказа; НЕ общий runtime GO. Stage15 — qualified 2/2 PASS только для двух
controlled-continuation scenarios. НЕ full host GO, НЕ закрытие T103 или семи
integration groups. Stage16/17 и последующие исправления здесь не оценивались.

Прочитаны полностью result.json, run.log (886/177 строк), пустые run.err,
Run-History/Invoke-Runner/run.cmd, frozen native runner, Check-Binary14 и
Check-Terminal15. Прямой diff wrappers14→15 меняет только source/prior hashes
и явный набор25→2; run.cmd прежний. Прочитаны реальные held adapters,
per-ID completion/ContentLoading observers, final-response/bridge/owner guards,
initial200 oracle и finish/BrowserProcessExited/deadline/cleanup paths.
Read-only Ruby разбор сопоставил ВСЕ requested IDs, scenario starts, native
results, runner results в точном порядке, проверил уникальность case GUID,
контрольные суммы пяти inputs и всех пяти retained source files каждого набора.
Это анализ сохранённых данных, не запуск native tests/runner/VM.

### Frozen identity и receipts

Папки относительно /Users/yshishenya/Documents/graf-f200-public458.po8CtB:
t103-history14.AzUBxE и t103-history15.xDSxo9. Все SHA-256 ниже вычислены
непосредственно по сохранённым файлам, кроме PE hashes, напечатанных runner:

| Артефакт | stage14 | stage15 |
|---|---|---|
| source216 | 9400d831eca6b8907f88ef09d8988d4f9004a53a501a824163c94bad37810d23 | 0633337a2a3d610a01d591634b749b6b234c21de898f1520cee11866fa2a2cb6 |
| prior216 | 8c921717d2001120ecdc000b5ce36a95cad7b12ec82905f16f5789b947bcab61 | 9400d831eca6b8907f88ef09d8988d4f9004a53a501a824163c94bad37810d23 |
| result.json | 30e6408ccfb52dc3e313140dd6094cc1d97e720a371c330dc91f241dc203b037 | 603ed9a27923f62992c3352d7d89273284c47dfd69ec73529070b6c6c0afcb9f |
| run.log | 6513f9083e9d02a106b9d325e7c6c1d3928593e25125f795f65ce79e2382f21e | 88d3b44f413bb6cd0f9023fa0e0defceca4665b657359624b1dea193c953560c |
| Run-History.ps1 | 8cc766fada29cc9bdd911f66855c36628dc72684c87f85bee44e52d9be4703bc | c4b9a0190193c4e221078b7629a140a26f004dcc6a4606b30c2d62d40df5b187 |
| Invoke-Runner.ps1 | 117d6768392db9dd2d37495f5abc0b6f12d0f0d3779a0df0fece4dbd3a544c05 | 5aaf7391383f5612a92f25a9681b7187d8924ea7999d3ccf9a52e4e5755e0940 |
| PE (run.log) | a519217d261dc8d418be6eb9cf47cd0ca097c39b38692396d47a7069d6600149 | e5e9f2692d5d3d8afe297600c5c2f065373d9423a0afbc560625a1ef837368a6 |

run.err обоих — 0 bytes, SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
run.cmd обоих — 0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856.
Manifest paths216 уникальны, множества prior/source одинаковы. Stage14 меняет
к prior только cpp host (индексированный JSON compile fix); stage15 — только
тестовые C++/PY/PS. Source14 побайтно равен prior15. Retained5 каждого набора
совпадают с manifest: host cpp24eb7c594026cd570abcdea92a0a45e351fee1010c411d349f55a50f62de4810,
header f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927;
test3 stage14 = cpp7f23757e914a2fa92ddae2f4387a5785d569e468efdfe3d37648676d0a03da0d,
PY e1b00f80972c1389d96e968c865d1c1910044412418329f17bbdf627dfa572fa,
PS43f6d96089fea374b649dacae14c5ce2f20673853231d29fa6d7bf0b07081bd9;
test3 stage15 = cpp0e968ade6e7e14a90589b7112b6ec45bcd3ad92f4618ab713798c5780e609f68,
PY9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e,
PS8831610834eb7bba5e2b99b996e308fd3cf508c2df7c1bb2fabbb966b3aa10fb.

Оба receipt: terminal=true, pre/staged/post216, inputs5 match, runtime3,
owned_processes=0; device_started/real_account/installed=false, loopback-synthetic.
Stage14 exit1/NATIVE_RUN_FAILED/217923ms, stage15 exit0/no failure/84150ms.
Runtime DLL hashes обоих: Bootstrap44752d799b8d7cead99d6a20cb9a46009a9a2dfaa9701176a573e50a30ab089c;
Core6eeb1e4091eef101fca4d3c6ec43e4fe183a0188eed624bf8a8ff11a1a24b326;
Loadera9a09232c25805323d4cfb3fc8f545a190a9c8a99c93262ea99d0b88df99ec90.
Wrapper проверяет source216 до/после staging и после child exit, runtime3 и
inputs5 до/после, затем nonzero exit превращает в NATIVE_RUN_FAILED. Поэтому
stage14 функциональные FAIL не маскируются пустым stderr или cleanup PASS.

### Stage14: все25, без ослабления initial200 и без смешения cancel sources

| FAIL | Фактическое наблюдение | Граница вывода |
|---|---|---|
| initial200 | nav2 и3 оба 200/success1; starts2/completions2/current_reads2, counts2 0 0 0 0 0; deadline | Два настоящих load/read вместо одного, не отсутствие SDK/API |
| history-post | phases0..4 IDs5/6/8/10/12; затем nav7 status0/error14 | Не пройден useful Back после fresh pair |
| history-host-same-url | те же IDs/порядок; phase5 nav7 error14 | Same-URL вариант тоже RED |
| history-host-quarantine | те же IDs/порядок; phase5 nav7 error14 | Новый opt-in тоже RED |

В трёх history FAIL phase1 — actual response POST, остальные принятые phases —
GET, generation-tag match, ContentLoading IDs и реальные bridge1..5. Phase3
имеет same committed-ID singleton, FIXTURE_RESET=0/FIXTURE_ALL_NAV_FENCE=0;
phase4 — свежий C id12. Phase5 имеет Starting, cancellation14 и остаётся state2,
но не новый ContentLoading/response/bridge. Frozen flow и Starting kind/URL
guards требуют actual host Back; FAIL не unexpected-start. Однако журнал14 не
печатает marker presence/точный branch Cancel: retained-header cause здесь
остаётся гипотезой, не доказательством storage extraHeaders или POST restore.
Counts4 0 0 0 0 1 и fixture exit1 подтверждены во всех трёх.

Initial200 frozen oracle явно требует currentCookieReads==1, signedOut0,
invalidations0, updatePhase6/updateCallbacks1, localDurationPhase5/inventoryPhase5;
runner ожидает ровно1 GET. Cookie handler реально вызывает account bind;
frozen host имеет eager fresh GET block. Второй load в журнале согласуется с
этим конкретным code path. Нельзя поднять expected count до2, убрать cookie/
bridge/inventory проверки или назвать deadline инфраструктурным успехом.

Остальные21 PASS проверены по полному журналу: login400/email503/cabinet401/
cabinet503/login429/email429/email-json503/reselect/billing401/meeting401/
transport-reset/tls-failure/login-post400 (13); history-get, history-entry,
history-entry-same-url, cancel-before-start, cancel-history-host,
cancel-history-script, history-same-document, history-host-get (8).
History-get actual allGET IDs5/6/8/6/5/6/8, realbridge1..7; host-get IDs5/6/8/6/8,
realbridge1..5, method/generation/owner checks. Entry negatives: unsolicited BF
nav5 production-cancel14, FIXTURE_CANCEL=0, actual C id8/count3 сохранён, затем
настоящий fresh GET с authority. Это не fixture Cancel. Напротив cancel-host
(allGET preparation), cancel-script и cancel-before-start явно fixture-cancel
и доказывают сохранение accepted document/authority после такого cancel,
а не защиту production pending fence. Same-document retained IDs8→10/hash
и следующий документ приняты. Auth/status/transport/certificate сценарии
сохраняют свои отдельные noBridge/recovery/count guards и ожидаемые статусы.

### Stage15: два настоящих held результата и полезное продолжение

Pending-read-fence: accepted A/B/C IDs5/6/8, bridge1..3. Original native snapshot
удержан в selecting: terminal0. Три разных nav5/6/7 (script BF, GET, POST) реально
начались и каждый завершился success0/error14, FIXTURE_CANCEL=0; per-ID guards
запрещают ContentLoading. Actual DOM/history всё ещё C/id8, прежняя generation,
cookie/auth counts и ready сохранены; повторные native Back/Forward не начинают
новый read. Настоящая harmless bridge кнопка C даёт один retained callback.
До delivery activations0. Затем original result/continuation доставлен ровно
один раз на UI thread: useful Back nav8/id6, Forward nav9/id8, realbridge5/6
(добавочный retained callback объясняет отличие от обычных1..5), final activations2.
Counts5 0 0 0 0 0, starts/completions5 полезных переходов; три отменённых
competitors намеренно считаются отдельно по ID, а не исчезают из проверки.

Terminal-held: Back nav5 уже имеет finalGET/tag/ContentLoading id6/completion200,
но original accepting snapshot удержан terminal1. Actual DOM B и currentID6
проверены; stage accepting, response+completion present, terminalValidated=false,
nonce empty, runtime не ready, activations0; auth/cookie/bridge не опережают latch.
Нажатие настоящей bridge кнопки не доставляет native callback. После one-shot
delivery production самостоятельно становится ready/принимает bridge4; затем
обычный host Forward nav6/id8 с bridge5 успешен. Это не доказательство ещё
одного Back после release: именно принятие удержанного Back и последующий
Forward наблюдались. Counts5 0 0 0 0 0, starts/completions5. Ни один тест не
выдумывает native result, метод, finish/latch/nonce или authority. Print HOLD_PROVEN
поддержан actual guards, не заменяет их; окончательный PASS требует captures1,
deliveries1, activations2, held=false и независимый реальный bridge каждой фазы.

### Сроки, cleanup и предел независимой проверки

Frozen bounds прежние: server readiness1.5s, native20s, close10s, case35s,
outer600s. Case14 min1791/max21098ms, case15 3402/2433ms; все внутри35s.
Все25+2 профиля environment/exact-match, browser exit PASS, server exit0,
case GUID уникальны. Final counts читаются только после server join/exit;
runner перечитывает SHA PE перед результатом каждого case. Cleanup ошибок нет.
Stage14 сохраняет свой GUID diagnostic directory после FAIL — это ожидаемая
сохранность evidence, НЕ temp-cleanup PASS. Процессов owned0. Stage15 выводит
T103_TEMP_CLEANUP=PASS после удаления только своего GUID, CASES_PASSED=2 и
CASES=PASS; не сохраняет полный PE/зависимости после успешной проверки.

Check-Binary14 hash321935960fb34ad20d00c24c3ba146c94e85c0f9821cf52f8240b2f604fedc31
читает exact retained PE и сравнивает a519...; main сообщил actual readback PASS.
Check-Terminal15 hash9d6375c5bbf3585c9d067d0ad1064b3ac2c6edf923e8e6c8ad6ea9e6025c776b
проверяет actual guest216/input5/runtime3/owned0; main сообщил postterminal PASS.
Я проверил сохранённый код этих scripts, но не запускал их и не получил нового
guest readback: их execution PASS — сообщение main, не мой независимый замер.
Сам Check-Terminal15 не хеширует уже очищенный PE. Exact PE identity15 следует
из build log + runner per-case hash checks; физическое наличие PE после cleanup
не утверждается. Все211 не скопированные в external stage исходники и DLL
подтверждены wrapper receipt, а не повторным чтением guest этой стороной.
Наличие локальных hashes не является криптографически подписанной аттестацией.

Итог: evidence соответствует stated RED14 и narrow GREEN15; C/H дефектов,
меняющих их квалификацию, не найдено. Это не исправляет четыре отказа14,
не переносится на host4394/будущие marker fixes, не закрывает seven-group
coverage, MSIX/UI/hardware/E2E/T103/T088/T097/release. Только собственный
append изменён; VM/device/build/tests/Git/нормы/checklists/чужие файлы не тронуты.

## Exact SOURCE stage18: retained marker на selected native GET BF, 2026-10-22

**C0/H0, scoped SOURCE GO к frozen27 functional/debug run:** default23 плюс
history-host-get/history-host-quarantine плюс history-pending-read-fence/
history-terminal-held. Это допуск к сборке/исполнению, НЕ утверждение27 PASS,
НЕ full T103 GO. Stage17 runtime здесь отдельно не квалифицировался; stage16
сообщение main не подменяет отдельный saved-runtime review этого опыта.

Проверен полный diff host против retained frozen stage17.Ky63cU:
baseline439460a57f1bbc40e2601c27b361f53c9ac3e005cea7fda6a857e2f8e95da7e2;
candidate8fa80655391e84c78da574aa3d5cff52d0bcf3cb9e8c332c27930ab484d5b05e.
Ровно два hunks: Starting1983+ и WebResourceRequested2211+. Header прежний
f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927.
Test3 проверены actual hashes: cppf926b4443b51a097f802ed1ada907992ecb39cb9fcd10af863c4f69c14c8bd4e,
PY9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e,
PS8831610834eb7bba5e2b99b996e308fd3cf508c2df7c1bb2fabbb966b3aa10fb.
Диагностические3 строки C++ по-прежнему только printf в productionHistoryScenario;
они не приобрели полномочия при расширении запуска с одного до27 scenarios.

Starting теперь сначала вызывает unchanged чистый admitHistoryNavigation,
затем marker check, оба ДО beginDocumentNavigation. Admit сам не меняет owner,
history stage/nonce/latch. Selecting/accepting/resetting всё ещё запрещают все
document starts; idle BF отвергается; permitted требует selected target URL,
nonredirect и BF kind==historyTraversal. Traversal становится true только через
target из полного allGET snapshot текущей session, не через marker presence.
Наличие старого marker больше не отвергает такой уже выбранный actual BF,
но не разрешает BF в idle/pending или ordinary same-URL form. Nontraversal
fresh path всё ещё требует permitted stage, непустой freshTag и exact match.
Обычная marked navigation вне fresh permit отменяется до begin. Earlier fixture
Cancel остаётся первым guard и не отзывает authority accepted current page.

ResourceRequested новый selectedHistoryGet требует одновременно traversal,
navigating stage, historyNavigation==navigationId, target present, exact target
URL и actual browser Method GET. Начало принятой navigation устанавливает эти
IDs; сам marker не делает predicate true. Это узкое исключение из stale-marker
отказа, не новый URL-only controller permit. POST остаётся запрещён по method,
pending/reset/accepting fence не ослаблен, чужой URL/неактивный owner marker
не становится ownedGet. Marker по-прежнему RemoveHeader до сети, независимо
значения. Predicate не ставит proof/nonce/authority; existing response требует
document destination, navigate mode, current generation tag и final method.

Unchanged terminal native snapshot проверяет selected actualID/URL/session/
generation/revision/allGET до tryFinishDocumentNavigation и consume latch;
reset ACK+same singleton и session clear остаются прежними. Concurrent safeGET
другого actual entry не получает authority только из совпавшего URL/marker.
Новых SDK API, lifetimes, async owners или compile-macro конструкций diff нет.

Adjacent native-fresh redirect поведение этим diff не доказано/не исправлено;
нужен отдельный direct test после этого run. Это не повод ослабить27 oracles,
добавить redirect exception или принять все integration groups. Source GO
требует обычного exact frozen source/runner/runtime receipt перед/после run;
prepared external bundle этой стороной не выполнялся и отдельно не квалифицирован.
Использован code-reviewer; только свой report append. Code/tests/spec/plan/
checklists/Git/VM/build не менялись; T103/T088/T097/release остаются открытыми.

## Requirements/checklist/analyze: future fresh-list 302 login opt-in, 2026-10-22

**C0/H0, bounded tests-first GO для авторства одного нового opt-in native test
в прежних CPP/PY/PS.** Не SOURCE GO будущего diff, не разрешение host fix до
meaningful RED, не runtime PASS. Выполняющийся frozen27 stage18 и его oracles
этим gate не меняются. Ownership существующий T103/#7280 (FR-002/005/006,
partial SC-002); T088/#7231 и остальные acceptance/release gates открыты.
Новых продуктовых вопросов, задач или bridge API не требуется.

Оценены финальные actual SHA-256 ПОСЛЕ исправления счётчиков:
plan9b62bbd01908cf3acd100efb3e48ad6154f3e5fed85a1d8035a44b6300426213,
quickstart6bee22669d3a0e75227659ddc563090125fdeabbe9305d89f812b140bc2f7687.
Полностью прочитаны новые plan:3242+ и quickstart:1355+, применены spec:397–428/
586–590/661–694, bridge navigation/auth recovery и §T103 history, data-model:709–722,
Constitution7.1.0. Prefix первых3240 строк plan всё ещё92eea9047baa9121cfed7a6fdd897e42efc5ac39c32fd908768cf9600dc51d42,
первых1353 quickstart698b3f4424614ff53c69040da09d284696dc10e9157ed335189a8f6b9a9acf01.
Таким образом прежние выбранные sections не переписаны; прежние предпосылки
и27 oracles не изменены задним числом. Предварительные версии с counts2 1 0 0 0 0
НЕ получили GO: текущий допуск относится только к исправленным двум SHA выше.

### Actual six-field semantics и измеримый oracle

Existing WebView2AuthLoopback.py SHA9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e
прочитан: line29 определяет cabinetGET/loginGET/emailGET/safeLoginNext/
unexpectedPath/nonGET. parse_request:44–47 учитывает настоящий nonGET независимо
ветки; do_GET:107–111 увеличивает loginGET и отдельно safeLoginNext, когда
parse_qs(query)=={next:[cabinet_path]}. Поэтому будущий путь initial detail C,
fresh list302, loginGET с next=list требует строго **2 1 0 1 0 0**, не2 1 0 0 0 0.
Четвёртое поле — дополнительное подтверждение безопасного next при том же
login request, не четвёртый HTTP request. New case не должен обходить общий
login counter, обнулять safeNext или расширять counts regex ради GREEN.
Исправление снимает техническое противоречие до авторства, не меняет продукт.

Минимальный обязательный native oracle из действующих требований:

1. Настоящий первый GET detail C принят ordinary response/completion latch;
   actual bridge действует до Back. Прежнего list target в profile нет;
   действие — actual host Back/fresh-list fallback, не fixture CDP steering.
2. Сервер действительно отвечает HTTP302 на GET-list с заданным внутренним
   Location. Нужны реальные fresh-list Starting и redirect Starting с тем же
   ненулевым navID/IsRedirected, а не новая host.navigate(login) от fixture.
   Последующий final native response относится к GET-login/текущему document
   owner и обычному completion. Не требовать неизменности generation между
   разными документами/redirect: её ведёт host; owner correlation должна быть
   действительной на каждом событии, а не выставленной тестом.
3. Current/source — ожидаемый внутренний login с безопасным next; форма видима,
   input enabled/editable и synthetic значение сохраняется. Только чтение/
   редактирование, без submit: nonGET0 строго. Форму с HTTP200 ожидает existing
   synthetic login handler; network error/локальная fallback HTML не её замена.
4. После замены C — authRequired и отсутствие native bootstrap/native_ready/
   новой bridge authority; прежний успешный bridge C не выдаётся за authority
   login. Сравнивать callbacks с baseline C, не требовать абсолютного нуля
   всех counters за весь run. Fixture не пишет proof/session/stage/nonce,
   не делает Cancel, fake response, finish или continuation injection.
5. Отсутствующий redirect/final document, wrong navID/method/route, лишний
   callback/POST, неработающая форма или неполные наблюдения — nonzero, не PASS
   по одним server counts. Ошибка build/startup не meaningful redirect RED.
   Сначала exact-source native RED, затем неизменённый тест на минимальной
   shared-root правке и GREEN; до каждого run отдельный SOURCE gate.

### Requirements quality, reuse и оставшиеся границы

Срез полон и измерим для единственного primary/recovery пути: trusted origin/
internal next, настоящая redirect ownership, method preservation, editable
auth form и отсутствие authority. Он согласован с FR-005/006 и bridge auth
contract; не добавляет URL permit/POST replay, не передаёт старый GET proof.
Constitution III/VI/VII соблюдены (synthetic/no-account/no-device, tests-first,
faithful auth recovery без ослабления security). Scoped coverage3 FR + partial
SC-002 → существующий T103, непокрытых scoped требований/новых owners нет.
Ambiguity/duplication/inconsistency/constitution CRITICAL0/HIGH0.

Requirements CHK001/002/004–007/013/019–022, security CHK001–003/007–011/
017–018/022, UX CHK001/002/019/020 перечитаны с новой redirect семантикой.
Остальные неизменные критерии переиспользованы в прежней области. Инвентарь
независимо пересчитан:198 файлов,31 checkbox file,477 checked/0 unchecked;
sorted SHA256+twoSpaces+relativeName+LF hash
6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2.
Это gate качества требований, НЕ runtime acceptance477. Markers не изменены.
Tasks120/93checked/27open/duplicates0, SHA80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f;
T103/T088 остаются unchecked. Новая задача только ради regression не нужна.

Применены speckit-analyze и критерии speckit-checklist в явно ограниченном
review/reuse режиме, без генерации checklist. Prerequisite skill flag
--require-spec не поддержан локальным script; повтор с поддерживаемыми
--json --require-tasks --include-tasks подтвердил F200/artifacts, spec прочитан
непосредственно. Extensions YAML разобран: before/after analyze/checklist
commit hooks disabled; hooks не запускались. Этот локальный CLI mismatch не
недостаток продуктовых требований и не был скрыт под выполненную команду.
Native20s/close10s/case35s, GUID/source/PE/runtime/owned0 и cleanup сохраняются.
External redirects, POST-redirect matrix, metadata ordering, reset/session,
остальные семь групп и installed UI/hardware/E2E остаются отдельными gates.
Только own report append; code/нормы/tasks/checklist/Git/VM/build не менялись.

## Independent saved-runtime qualification: stage18 full27, 2026-10-22

**C0/H0 в границах квалификации сохранённых доказательств: stage18 BUILD PASS,
27/27 native cases PASS, bounded runtime GO только для этого набора.**
Это не full production GO, не закрытие T103/#7280, T088/#7231 или семи групп
integration acceptance. Новый future fresh-list302 case сюда не включён;
его SOURCE review и RED/GREEN остаются отдельными. Ничего не перезапускалось.

Материалы: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history18.CllDOe`.
Прочитаны полностью 1087 строк run.log, result.json, Run-History.ps1,
Invoke-Runner.ps1, Check-Terminal.ps1 и frozen native runner208 lines;
сверены run.cmd, оба manifest216, retained host2/test3 и фактические native
assertions held/history. Применён code-reviewer; сравнение только frozen
stage14/15/17/18, без зависимости от текущих WIP тестов другого автора.

### Seal, source, runtime и ограничения независимого наблюдения

Независимо пересчитаны SHA-256 сохранённых файлов:

- result.json3439576d3d67b02415e0284332318a5ea3dc6a796985909edb8bbb0ff7a2a216;
- run.logcf76c998311a12e8d108034864fe46838700e7574bacad8a6d006c864558faaf;
- run.err0bytes, SHAe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855;
- source4b8f57ba5b0516a636aa2dd6bf4888a0d21abb0adae3a28ac4a1e2652140ee43;
- prior8b16dd294597bdec4e29c86825a281ae16326a5cfe82d363666bcfce9c637e01;
- Run-History95f59763f1607dd408dc8f53aa3001227f60a19a83451bb35698cfa8881200e6;
- Invoke-Runner8533d593a6fe72c44ea473f3c5e19b7a5b6320082e77bf5efa7fa697f255e7d8;
- Check-Terminal207a308fb2023e52fa47154154f57d4a17a71501f6607467f957b1e3c10c7a91.

Оба manifest содержат216 уникальных одинаковых путей. Между prior/source
меняется только WebView2Host.cpp. Все5 реально retained исходников совпали
с manifest: hostcpp8fa80655391e84c78da574aa3d5cff52d0bcf3cb9e8c332c27930ab484d5b05e,
headerf32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927,
testCPPf926b4443b51a097f802ed1ada907992ecb39cb9fcd10af863c4f69c14c8bd4e,
PY9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e,
PS8831610834eb7bba5e2b99b996e308fd3cf508c2df7c1bb2fabbb966b3aa10fb.
Внешняя папка не хранит все216 исходников; проверки остальных211 в guest
подтверждены выполненным wrapper receipt, а не притворным локальным rehash.

Все5 input hashes receipt заново совпали с retained bytes; private key/cert
только хешировались, содержимое не выводилось. Wrapper действительно проверяет
prior216 до staging, staged216 после копирования5, postflight216 после child;
проверяет неизменность inputs5 и runtime3. Receipt terminal=true, run_exit0,
pre/staged/post216, owned_processes0, elapsed214245ms < outer600000ms;
device_started/real_account/installed=false, server=loopback-synthetic.
Runtime hashes receipt: Bootstrap44752d799b8d7cead99d6a20cb9a46009a9a2dfaa9701176a573e50a30ab089c,
Core6eeb1e4091eef101fca4d3c6ec43e4fe183a0188eed624bf8a8ff11a1a24b326,
Loadera9a09232c25805323d4cfb3fc8f545a190a9c8a99c93262ea99d0b88df99ec90.
Их guest pre/post equality проверяет wrapper; DLL bytes в retained bundle нет.

Build log доказывает MSVC arm64_x64 compile/link actual SDK host и fixture,
BUILD PASS и PE3946e721a2501275ef6796ff9764f424094e8993f613dba8d3516fea9b487986.
Runner фиксирует этот PE до cases и заново проверяет его hash после каждого
case до PASS. Main отдельно сообщил actual-guest Check-Terminal216/input5/
runtime3/owned0 PASS. Сохранённый Check-Terminal прочитан: он не хеширует PE;
самостоятельного нового guest/PE readback reviewer не выполнял. После успешной
очистки ownGUID PE не retained, поэтому точная связь PE квалифицирована по
sealed build log + per-case hash guards, а не по несуществующему файлу на Mac.

### Полный requested order и результат каждого case

requested receipt, Invoke-Runner, scenario starts, native results и case PASS
совпали по порядку, без пропусков/повторов. Все строки таблицы — PASS.

| № | Case | Final counts | Elapsed ms |
|---|---|---|---:|
| 1 | initial200 | 1 0 0 0 0 0 | 5187 |
| 2 | login400 | 0 1 0 0 0 0 | 7302 |
| 3 | email503 | 1 0 1 0 0 0 | 7386 |
| 4 | cabinet401 | 1 1 0 1 0 0 | 7539 |
| 5 | cabinet503 | 1 0 0 0 0 0 | 7207 |
| 6 | login429 | 0 1 0 0 0 0 | 7434 |
| 7 | email429 | 1 0 1 0 0 0 | 7359 |
| 8 | email-json503 | 1 0 1 0 0 0 | 7423 |
| 9 | reselect | 1 1 1 1 0 0 | 7636 |
| 10 | billing401 | 1 1 0 1 0 0 | 7737 |
| 11 | meeting401 | 1 1 0 1 0 0 | 7706 |
| 12 | transport-reset | 0 2 0 0 0 0 | 7425 |
| 13 | tls-failure | 0 0 0 0 0 0 | 7246 |
| 14 | login-post400 | 0 1 0 0 0 1 | 7423 |
| 15 | history-get | 7 0 0 0 0 0 | 2910 |
| 16 | history-post | 6 0 0 0 0 1 | 2476 |
| 17 | history-entry | 4 0 0 0 0 1 | 1820 |
| 18 | history-entry-same-url | 4 0 0 0 0 1 | 1716 |
| 19 | cancel-before-start | 3 0 0 0 0 0 | 7426 |
| 20 | history-host-same-url | 6 0 0 0 0 1 | 2596 |
| 21 | cancel-history-host | 5 0 0 0 0 0 | 1631 |
| 22 | cancel-history-script | 4 0 0 0 0 1 | 1742 |
| 23 | history-same-document | 3 0 0 0 0 1 | 2018 |
| 24 | history-host-get | 5 0 0 0 0 0 | 2160 |
| 25 | history-host-quarantine | 6 0 0 0 0 1 | 2852 |
| 26 | history-pending-read-fence | 5 0 0 0 0 0 | 2989 |
| 27 | history-terminal-held | 5 0 0 0 0 0 | 2387 |

27 уникальных caseGUID/profile,27 exact profile checks до первой навигации,
27 native PASS, fixture_exit0, server_exit0 и browser_exitedPASS. Native20s/
close10s, server-ready15×100ms, PS fixture wait≤32s, drain≤3s и case35s
не расширены. Максимальный case7737ms. Counts читались после server join/exit,
server.err0 — обязательный PASS conjunct, не вывод только по exit0.
В конце T103_TEMP_CLEANUP=PASS, CASES_PASSED=27 REQUESTED=27 и CASES=PASS.
Очистка ограничена own freshGUID, ошибки cleanup делают run nonzero; признаков
preserved-failure/timeout/owned-process cleanup error в полном журнале нет.

### Native доказательства исправления прежних четырёх FAIL

initial200: starts1/completions1/current_reads1, actual bridge/update dispatch,
localDuration4cases и inventory300/FOREIGN0/STALE0/ACTIONS0/QUOTA_RETRY1.
Strict expected count1 сохранён; лишней eager initial GET теперь нет.

history-post, history-host-same-url и history-host-quarantine каждый прошёл
все7 phases: actual entry IDs5→6→8→10→12→10→12. Phase1 реальный POST,
остальные final responses GET200, generation tag matches, реальные ContentLoading
IDs/completions и bridge1..7. Phase3 свежий list после ordinary acceptance/reset
стал singleton с тем же committed ID10; FIXTURE_RESET=0/FIXTURE_ALL_NAV_FENCE=0.
Phase4 свежий forward C id12; phases5/6 — actual native BF к10/12, не к старому
POST6. Marker-present1 виден на fresh3/4 и BF5/6; nav7/8 теперь завершились
200 и дали authority/bridge6/7 вместо прежнего OperationCanceled14 на phase5.
Это наблюдение конкретных запросов, не универсальное доказательство способа
хранения extraHeaders браузером. Все3 сохранили ровно один POST, counts6...1.

Frozen PY/PS stage18 побайтно совпадают со stage15. Сравнение stage14→18:
в PY только добавлены controlled2 имена/разрешённые GET ветки, в PS только
ValidateSet и отдельные count branches controlled2; прежние25 counts/deadlines
не менялись. C++ stage15→18 — только3 diagnostic printf lines. Полный diff
stage14→18 добавляет held2 и их guard-ветки; прежний heldRetainedDispatches0
оставляет старую exact bridge формулу phase+1. Старые final method/entryID/
singleton/authority assertions не ослаблены ради четырёх GREEN.

### Остальная полезная история и два controlled отрицательных сценария

history-get прошёл7 реальных GET phases IDs5/6/8/6/5/6/8; host-get —5 phases
5/6/8/6/8. У каждого actual BF, GET proof и новый рабочий bridge на каждой
принятой странице. entry/entry-same-url: unsolicited CDP BF при POST истории
отменён production, FIXTURE_CANCEL=0, ACK1/error14; C id8 сохранён, next fresh
GET/bridge работает. cancel-before-start/cancel-host/cancel-script отдельно
остаются fixture Cancel lifecycle controls, не доказательством production
fence. same-document сохранил C при replace/hash (id8/count3, затем id10/count4)
и принял следующий настоящий document с действующим bridge.

pending-read-fence: оригинальный selecting result удержан один раз UI thread;
повторные native Back/Forward не создают второе read/intent. Три настоящих
конкурента BF/GET assign/form POST имеют отдельные IDs5/6/7, FIXTURE_CANCEL=0,
completion success0/error14, без ContentLoading (иначе немедленный FAIL).
Actual snapshot/DOM подтверждает прежний C id8/count3; generation/cookie/auth
baseline не изменён, EARLY_ACTIVATION=0, реальная кнопка C даёт ровно один
разрешённый retained callback. После однократной доставки original result
обычный host Back nav8→B6 и Forward nav9→C8 приняты; bridge5/6.

terminal-held: actual Back nav5→B6 уже имеет response GET200/ContentLoading/
completion; accepting original result удержан до выдачи authority. Guard
проверяет response+completion owner, historyTerminalValidated=false,
nonce empty, runtime не ready, cookie/auth baseline и activations0. Actual
snapshot/DOM B6 проверен; реальная кнопка не даёт callback до доставки.
После original UI-thread delivery появляется ready/bridge4; subsequent native
Forward nav6→C8 даёт bridge5. В обоих случаях final assertions требуют
captures1/deliveries1/activations2, !held, !unexpected. Fixture наблюдает
activate, но не блокирует ошибочную раннюю активацию; не пишет nonce/proof/
stage/session/finish и не подменяет результат. Нельзя расширять это до
произвольных гонок/всех terminal mismatch/reset/session scenarios.

### Scope / follow-up

Сохранённые данные достаточны для narrow stage18 qualification C0/H0 и
продолжения отдельного tests-first fresh-list302 review. Они не закрывают
полную семигрупповую матрицу, redirect/final-method negative matrix,
current-entry mutation/replacement/session/reset failures, installed UI,
реальные account/upload, audio/hardware или release. Reviewer append только
этот report; VM/device/build/tests/Git/код/нормы/checklist не изменялись.

## SOURCE: opt-in history-fresh-login-redirect vs frozen stage18, 2026-10-22

**C0/H0. Limited SOURCE GO для одного нового opt-in native case на прежнем
host8fa; допускается отдельный frozen runtime RED run.** Это не runtime PASS,
не SOURCE GO будущего host fix и не T103/production/release acceptance. После
meaningful RED нужен отдельно рассмотренный минимальный host diff и тот же
неизменённый test GREEN; build/startup/неполная observability не доказывают
продуктовую причину redirect отказа.

Полностью прочитаны все новые CPP/PY/PS hunks с реальным surrounding context,
existing requestHistoryResetBridge, auth/update/event handlers, native lifecycle
и bounded production response/completion latch callers. Skill code-reviewer
прочитан полностью. Ничего не выполнялось в VM, тесты/сборки не запускались;
изменён только этот собственный report append. Live WIP других авторов не
использован вместо baseline.

Проверены actual SHA-256 review target:

- CPP634b87626fa6379089be04c598ba0f233f85b49667fde3c2d1ec6ea6dd79db16;
- PY80f56385b4e6e38c019d91fe8f9e238a39262f7831d4db127653fbc6b784bff3;
- PS2832eca325741f12c0fb3db3c23187bc67ba404d28a7f6f4bcb841e1231d94c9;
- plan9b62bbd01908cf3acd100efb3e48ad6154f3e5fed85a1d8035a44b6300426213;
- quickstart6bee22669d3a0e75227659ddc563090125fdeabbe9305d89f812b140bc2f7687.

Baseline — retained test3 в stage18.CllDOe, независимо сверены CPPf926b4443b51a097f802ed1ada907992ecb39cb9fcd10af863c4f69c14c8bd4e,
PY9431cfc715c1608763bc3c0bd2f825cc0d22c4ef70f83b98670a646269d97f8e,
PS8831610834eb7bba5e2b99b996e308fd3cf508c2df7c1bb2fabbb966b3aa10fb.
Текущие host CPP8fa80655391e84c78da574aa3d5cff52d0bcf3cb9e8c332c27930ab484d5b05e
и headerf32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927
также совпали с stage18; host этим review не менялся.

### Construction и реальный oracle

1. CPP:1531–1552 сначала требует actual C response GET200, ContentLoading,
   completion того же ненулевого navID, generation/current/source owner,
   ordinary ready и завершённый current cookie callback. Нет старого H1:
   lower async count ждёт в прежнем deadline, лишний callback не принимается.
   Initial DOM history-c/bootstrap/native_ready проверяются отдельно. Existing
   requestHistoryResetBridge:1076 вызывает реальную кнопку/bootstrap с текущим
   nonce, не читая/не выставляя его; harmless update handler:1804 требует ровно
   один настоящий callback от C. Только после него вызывается host->back().
   Fixture не делает navigate(login/list), CDP steering, permit или reset.
2. PY:93–105 реально отвечает detail C200 и fresh list302 с точным internal
   Location, Content-Length0/no-store. Общий login handler:119+ не обойдён:
   request GET-login увеличивает loginGET и safeNext по прежнему parse_qs.
   PS:25 требует exact `2 1 0 1 0 0`, не regex/расширенный диапазон. POST
   ловится native Request observer и общим server parse_request counter;
   diagnostic не отменяет его вместо production, а завершает test nonzero.
3. Starting:2030+ требует ровно C/list/login с точными URI и nonzero IDs;
   fresh list имеет новый ID относительно C, login IsRedirected=true и тот
   же ID, что list; BF kind запрещён. Fixture подписан до attach/product
   subscriber и только наблюдает. На redirect фиксируется actual list
   generation ДО product begin: это сохраняет owner для запоздалого302
   ResponseReceived, а не вычисляет/fabricates response tag.
4. Response observer:1956+ требует browser document/navigate destination/mode,
   actual GET, точные URL и X-GRAF-Desktop-Navigation generation, по одному
   ответу C200/list302/login200, Location у302 и HTML Content-Type у200.
   Response event сам не предоставляет NavigationId: напечатанный navID
   берётся из реально observed Starting slot. Correlation доказывается
   сочетанием URI+native request generation tag+строгой последовательностью
   трёх Starting, а не мнимым response.NavigationId API. Для list302 учтены
   порядки response до/после redirect Starting; final login owner должен
   совпасть с текущим generation, без требования ошибочно сохранить generation
   между redirect событиями.
5. ContentLoading:1893+ требует соответствующий реальный navID, не error page
   и не duplicate. Completion:1853+ требует ровно два документа C/login,
   success200/Unknown и их actual navID; отдельного list302 completion нет.
   Final check:1555+ требует доставленные list302/login200, loaded login,
   sameNav list/login/current completion и actual authRequired. Product сам
   сводит native metadata+completion через observe/tryFinish/complete latch
   (host:718–780/895–925/2240+/2880+); fixture эти методы не вызывает.
6. Final login не выдаётся за кабинет: current/source/next точны,
   pendingAuthRecovery=ignore, нет новых cookie/auth/update callbacks,
   bootstrap/native_ready отсутствуют. Реальная synthetic update-кнопка на
   login не должна вызвать native handler (иначе immediate FAIL). Native
   state authRequired получен ordinary interactiveForm branch, не установлен
   fixture. Internal nonce не читается; absence of authority проверяется
   наблюдаемыми bridge flags/handshake/callback и состоянием host.
7. CPP:1581–1619 проверяет существующую форму, ненулевые размеры/visibility,
   enabled/not-readonly input, focus; редактирует только synthetic значение
   без submit и повторно читает его не ранее200ms. Phase/generation fences
   защищают async DOM results; после повторного чтения опять проверены
   current/source/state/callback baselines. Неполные события/отсутствующий
   callback достигают прежнего deadline, mismatches дают nonzero, не PASS
   по одним server counts. UI-thread dispatch/lifetime/close/error handling
   повторяют существующий fixture; новых process/lifecycle owners нет.

### Retention и предел допуска

Все новые поведенческие ветки ограничены freshLoginScenario; productionHistory,
controlled2/reset/race selectors этот case не включают. Existing handlers не
подменяются у прежних case. PY меняет только allowlist и новую scenario-only
GET branch; PS только ValidateSet и один exact expected row. Старый default23
array побайтно не изменён: stage18 explicit27 по-прежнему23+initial2+controlled2,
новый28-й case только opt-in, не молча default. Прежние27 bodies/oracles/counts,
20s native/10s close/35s case,1.5s ready,GUID/profile/source/PE/DLL/cleanup
guards не менялись. No skips/xfail/URL exception/authority or fixtureCancel.

SOURCE C0/H0 не предсказывает runtime sequence/SDK observability: full native
log должен подтвердить все3 Starting,302 и final GET200, общий navID и latch,
реальный initial bridge, editable retained login и strict counts. При native
RED отдельно установить, где именно отказ (production Cancel/request/latch
или ограничение наблюдателя), прежде чем считать гипотезу доказанной.
Другие redirects/POST matrix, seven integration groups, T088/T097 и release
остаются открытыми. Нормы/checklist/tasks/код/Git не менялись.

## SOURCE: stage20 observer-only diagnostic vs frozen stage19, 2026-10-22

**C0/H0, limited SOURCE GO только для отдельного диагностического запуска
history-fresh-login-redirect.** Не host fix GO и не подтверждение причины RED.
Применён code-reviewer, skill полностью прочитан. Diff прочитан целиком:
ровно2 hunks/+6/-2 lines против frozen stage19 CPP634b87626fa6379089be04c598ba0f233f85b49667fde3c2d1ec6ea6dd79db16.
Actual target CPPfd6b76fab70f4b782318beaf87538117770a7bc9747203b3e21189d8a7ac3d71
совпал с заявленным SHA. PY80f56385b4e6e38c019d91fe8f9e238a39262f7831d4db127653fbc6b784bff3,
PS2832eca325741f12c0fb3db3c23187bc67ba404d28a7f6f4bcb841e1231d94c9
и host8fa80655391e84c78da574aa3d5cff52d0bcf3cb9e8c332c27930ab484d5b05e
не изменились.

- Completion printf вставлен ДО freshLogin guard/раннего return: печатает
  реальный event.NavigationId/IsSuccess/HttpStatusCode/WebErrorStatus, не
  устаревшие общие observedStatus/completions. Типы/форматы корректны:
  unsigned long long/%llu, int/%d, HttpStatusCode int32/%d, enum→int/%d.
  Все исходные conditions и расположение обновления counters сохранены.
- Starting printf дополнен только BOOL Contains(X-GRAF-History-Intent).
  Не читает/печатает значение tag, URL, nonce, cookie или другой секрет.
  Getter не даёт permit, не удаляет/ставит header, не вызывает Cancel.
  Наблюдение находится до later production subscriber; оно может показать
  наличие header в конкретном Starting, но не доказать автоматически, что
  именно header породил отмену или что он дошёл до wire.
- Оба изменения ограничены freshLoginScenario. Все assertions, strict counts
  2 1 0 1 0 0, defaults/прежние27 cases, native20s/close10s/case35s и остальные
  guards byte-identical относительно stage19; lifecycle/authority не изменены.
  Допуск относится к exact CPPfd6b + прежним PY/PS/host, а не к будущей правке.

Только own report append. VM/build/tests/Git/code/norm/checklist не менялись.

## Independent saved-runtime qualification: stage19 redirect RED, 2026-10-22

**C0/H0 к квалификации saved evidence; BUILD PASS, выполненный functional
RED одного case подтверждён. Runtime NO-GO для положительного redirect oracle.**
Это не compiler/startup/deadline failure и не доказательство marker-причины.
Frozen stage19 и новый stage20 diagnostic SOURCE gate выше — разные версии.

Материалы `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history19.fw1fYp`.
Полностью прочитаны run.log92lines, receipt, wrapper/InvokeRunner и точный
frozen early-return completion guard; проверены native runner hash/deadlines/
failure preservation. Независимые SHA-256:

- result04378d54c278c1f3d12034ab3849c74b3f3c21665d7e1a7d293449234ef10caa;
- logf59628216b57c223032702bed508f9b206623077c270b07bb52ea0181db68fad;
- err0bytes/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855;
- source216dd2ac38a73a7fc0d3400ffb4c2a61559fa4c84d5a8d59a87ee12e62633ddf756;
- prior4b8f57ba5b0516a636aa2dd6bf4888a0d21abb0adae3a28ac4a1e2652140ee43;
- Run-History007f5aca63fc992e9fbf5558e3c7a8da3c693b9c174ab15416560ac9d944e161;
- Invoke-Runner76c89e3db590513e0540570bb8237fa146634dde54b4d5bdd82828a96c60712d.

Оба manifest216unique с одинаковыми путями. Между ними меняется только test3,
не host2. Все5 retained исходников совпали с manifest: CPP634b/PY80f5/PS2832
из предыдущего SOURCE gate, hostcpp8fa/headerf32a unchanged. Все5 retained
inputs заново хешированы и совпали с receipt (cert/key только hashes).
Guest source pre/staged/post216 и runtime3 equality подтверждает completed
wrapper: runtime hashes ровно stage18 Bootstrap44752d.../Core6eeb1e.../
Loadera9a092..., inputs также проверены после child. Остальные211 исходников/
DLL bytes не retained на Mac; независимого нового guest readback не было.
Check-Terminal.ps1 в этой retained папке отсутствует; его выполнение здесь
не приписывается. Receipt terminal=true/run_exit1/failure=NATIVE_RUN_FAILED,
elapsed88389ms<600000ms, owned0, synthetic/no-device/no-account/no-install.

Build log actual MSVC arm64_x64 содержит BUILD PASS и
PEaebbbf77c23a881c0f7d78fc41017c0d2754f94577258447f317e4afe903efa9.
Runner фиксирует PE до case и проверяет hash после завершения fixture/server
до публикации FAIL/counts: этот guard выполнен также при fixture_exit1.
Новый PE readback reviewer не выполнял. Ровно1 requested/started case,
freshGUID/profile exact-match, до проверки0 навигаций. Case7693ms<35000ms,
без deadline/cleanup ошибки. Browser exited PASS, fixture_exit1/server_exit0;
server joined до counts. Own process cleanup завершён, diagnostics корректно
сохранены в ownGUID01426267a39445268548fc7664064205, не удалены и не объявлены
TEMP_CLEANUP=PASS. Число passed0/requested1, outer exit1 не скрыт.

### Что действительно наблюдалось

1. C Starting nav2/kind2/redirected0; response GET200/tag-match generation2,
   completion nav2 success1/status200/error0, ready. Marker
   INITIAL_GET_LATCH=1 REAL_BRIDGE=1 исполняется только после actual callback;
   current_cookie_reads1/signedout1/invalidations0. Начальный control принят.
2. После actual host Back — list Starting slot1/nav3/nonBF/redirected0,
   затем login Starting slot2/nav3/nonBF/redirected1, оба FIXTURE_CANCEL=0.
   То есть redirect Starting доставлен, тот же ненулевой nav3 наблюдается.
3. Следующее событие попало в frozen fresh-login-native-completion guard и
   завершило fixture FAIL; login GET сервером не получен: counts2 0 0 0 0 0,
   вместо strict2 1 0 1 0 0. Нет observed final login response/content/latch,
   authRequired/editable-form/retained-input proof. Положительный oracle не
   принят; error не замаскирован counts/fallback/fixtureCancel.

### Что stage19 НЕ позволяет утверждать

Guard:1852+ возвращает ДО ++completions и присвоения observedStatus/error.
Поэтому итоговые completions1/status200 относятся к принятому C, НЕ к
отказавшему completion. Его actual navID/success/status/error не напечатаны:
нельзя назвать OperationCanceled14, транспортный код или даже приписать nav3
этому event исключительно по итоговой summary. Ошибка означает нарушение
одного из guard conjuncts, а не известное конкретное значение.

В журнале нет native list302 RESPONSE строки: server code+counts и redirect
Starting подтверждают достигнутую ветку, но сами по себе не заменяют delivery
проверяемого native response302 metadata. Нельзя приписать finalGET/latch.
HISTORY_INTENT_PRESENT stage19 не наблюдал: наличие/сохранение marker на
redirect и его причинная связь с guard остаются гипотезой. Не установлены
конкретный cancelling subscriber/ветка admit/request fence или другая причина.
Stage20 observer-only gate выше разрешает измерить недостающие поля, а не
заранее исправлять host или ослаблять guard. T103/все remaining gates открыты.
Только own report append; никаких VM/build/tests/Git/кода/норм изменений.

## Independent saved-runtime qualification: stage20 observed cancellation, 2026-10-22

**C0/H0 к целостности saved evidence. BUILD PASS; meaningful functional RED
одного history-fresh-login-redirect подтверждён. Положительный runtime NO-GO.**
Материалы `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history20.h0jFKe`;
прочитаны полностью94lines run.log, result/wrapper/InvokeRunner и frozen8fa
callers, использован code-reviewer. Никаких повторов/VM/build/Git.

Независимые SHA-256:

- result37266cca53d0bb645eaf533b18430e7068db8a9d026ecb95e87b77ad074f01b2;
- logd7b23ec71f5362ad516f845f4cc888c29ae4e533b2a0220fb265b187c66e1d98;
- err0bytes/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855;
- sourcebb0e9e9b720bac0389ddba177304177eafdae5d682178ed53924ef72375f7b23;
- priordd2ac38a73a7fc0d3400ffb4c2a61559fa4c84d5a8d59a87ee12e62633ddf756;
- wrapper661f452287dc29ab2ff24bd234e63deec8cb065b42235f63fd2c8c92f299643e;
- InvokeRunner76c89e3db590513e0540570bb8237fa146634dde54b4d5bdd82828a96c60712d.

Manifest216unique/same paths, единственное изменение от stage19 — testCPP
fd6b76fab70f4b782318beaf87538117770a7bc9747203b3e21189d8a7ac3d71.
Все5 retained host2/test3 совпали с source: host8fa/headerf32a,
PY80f5/PS2832 неизменны. Diff testCPP против stage19 — именно ранее approved
observer-only +6/-2, без подмены assertions. Inputs5 пересчитаны и совпали с
receipt; содержимое synthetic key/cert не выводилось. Wrapper проверил guest
pre/staged/post216 и runtime3 до/после; runtime hashes те же44752d.../6eeb1e.../
a9a092..., что stage18/19. Остальные211 source/DLL/actual PE reviewer заново
в guest не читал: retained5 и receipt не выдаются за новый полный readback.

Actual MSVC arm64_x64 BUILD PASS,
PE65de8251c6f0dd7642b586639e759e2cf0a0e0d5cc8c59fd6d5a7708b19ca1d7
записан до case; unchanged runner повторно проверяет PE после fixture/server
перед final counts/result, в том числе при fixture_exit1. Requested1/started1,
profile exact-match до первой навигации, case7548ms<35000ms, outer84189ms<600s.
Receipt terminal=true/run_exit1/NATIVE_RUN_FAILED, owned0, no-device/account/
install. BrowserExitPASS/fixtureExit1/serverExit0, counts после server join.
Ошибок deadline/process cleanup нет; passed0/requested1. Диагностика оставлена
штатно в ownGUIDe77f9b3bd96548f68b767daeabbfd359, не заявлен TEMP_CLEANUP=PASS.

### Прямые native наблюдения

- C nav2: marker0, responseGET200/generation2/tag-match, completion
  success1/status200/error0, ready и actual initial bridge callback.
- Fresh list slot1/nav3/kind2/nonredirect: HISTORY_INTENT_PRESENT=1.
- Login redirect slot2/nav3/kind2/IsRedirected1: HISTORY_INTENT_PRESENT=1,
  FIXTURE_CANCEL=0. Наличие header теперь наблюдалось, в отличие от stage19;
  его значение не выводилось и его равенство private tag trace не показывает.
- Настоящий completion напечатан ДО guard: nav3/success0/status0/web_error14
  (OperationCanceled). Это больше не устаревший status принятого C.
- Native FAIL fresh-login-native-completion, counts2 0 0 0 0 0: сервер не
  получил final login GET. List302 RESPONSE строка всё ещё отсутствует;
  final GET/content/latch/authRequired/форма не доказаны. Нельзя приписывать
  данным положительное завершение redirect или работу формы.

### Причинный вывод по frozen source, отдельно от trace

host8fa beginDocumentNavigation:674–684 после допущенного fresh list ставит
historyStage=navigating/historyNavigation=id. admitHistoryNavigation:1138–1151
на этой стадии допускает только redirected/same historyNavigation/nontraversal.
Однако Starting:1992–2002 сразу ПОСЛЕ admit при !historyTraversal и markedFresh
снова требует historyStage==permitted. При navigating это условие заведомо
ложно: args.Cancel(true), return ДО begin/новой generation/очистки latch.
HistoryChanged не переводит navigating в permitted; свежий marker не является
новым permit. Таким образом source содержит конкретное противоречие между
допущенным redirect и последующей initial-permit проверкой, согласованное
с наблюдаемыми sameID+marker+error14/no finalGET. Это не branch instrumentation:
live stage/tag equality/точный executing Cancel call не напечатаны, и error14
сам по себе не идентифицирует subscriber. Причинный вывод опирается на actual
trace + прочитанный неизменный control flow, не только на совпадение симптомов.

Есть также смежный source blocker следующего шага: HTTP ownedGet:2210+ всё
ещё требует URL==initial historyTarget.url. После разрешённого internal
redirect login отличается от list; active freshIntent не даёт ему пройти,
даже если marker на HTTP стороне отсутствует. Это source-инференция будущего
request fence, НЕ наблюдавшийся в stage20 HTTP403 и не выполненный второй
баг: Starting отменил переход раньше finalGET. Это обосновывает отдельный
review узкой правки обоих guards, но не разрешение URL-only exception.

## SOURCE + ponytail: host385b vs frozen stage20 host8fa, 2026-10-22

**C0/H0 limited SOURCE GO к одной frozen сборке и28-case run: сначала
unchanged history-fresh-login-redirect, затем прежние27 в точном stage18
относительном порядке.** Не runtime GREEN, не T103/full integration/release GO.
Будущая обвязка/manifest28 должна быть отдельно заморожена и квалифицирована
main; её ещё не предоставленные bytes этим review не объявляются проверенными.

Exact actual SHA:
hostCPP385b1c81570142fed9e04709c6b9b1d3e295fa3b67bb4144d040fcdc1dcbc189,
headerf32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927,
testCPPfd6b76fab70f4b782318beaf87538117770a7bc9747203b3e21189d8a7ac3d71,
PY80f56385b4e6e38c019d91fe8f9e238a39262f7831d4db127653fbc6b784bff3,
PS2832eca325741f12c0fb3db3c23187bc67ba404d28a7f6f4bcb841e1231d94c9.
Baseline retained stage20 CPP8fa80655391e84c78da574aa3d5cff52d0bcf3cb9e8c332c27930ab484d5b05e.
Прочитан весь diff: только2 hunks Starting/ResourceRequested. Header/test3
не менялись; план/quickstart/нормы/assertions/deadlines этим slice не меняются.
Прочитаны оба skill полностью: code-reviewer, затем ponytail-review.

### Starting: узкое продолжение уже принадлежащей native навигации

- admit остаётся ДО дополнительных guards и ДО begin. Initial permitted
  путь по-прежнему обязан иметь exact targetURL и BF-kind из исходного
  выбора; новый freshStart только permitted&&!redirected.
- freshRedirect требует navigating&&IsRedirected и id==historyNavigation
  &&id==navigationId. Общий reject добавляет id!=0, !BF, наличие target,
  непустой private freshTag, marker и exact tag match. Наличие target во
  внешнем условии не даёт молча продолжить active fresh intent без marker.
- Другой ID, script/nonredirect start, POST form Starting без private tag,
  stale/пустой marker, BF либо idle state с marker отклоняются ДО begin.
  TargetURL-only permit не появился. Browser method в Starting не выдуман:
  actual GET доказывается на HTTP шаге. Route evaluate/authContinuation/
  payment/download ограничения begin остаются прежними после admit.

### HTTP: только actual GET текущей допущенной навигации

- ownedGet теперь требует active freshIntent, navigating, ненулевой
  historyNavigation==navigationId, URL==navigationUrl и actual request GET,
  marker==private tag. navigationUrl устанавливается только прошедшим
  beginDocumentNavigation, включая разрешённый sameID redirect, не запросом
  или страницей. Поэтому допуск переносится с initial list URL на текущий
  допущенный URL без выдачи нового разрешения по URL.
- selectedHistoryGet не изменён: traversal/navigating/selected targetURL/
  current navID/actualGET. Initial all-entry confirmedGET policy, CDP selection,
  command ACK и terminal selected actual entryID перед latch/nonce не менялись.
- Fresh/BF POST/PUT, wrong URL/tag, selecting/accepting/resetting сохраняют
  отказ. Header по-прежнему удаляется до wire, metadata tag добавляется
  native; final response требует document/navigate, URL и generation, actual
  method/MIME/status затем использует unchanged ordinary latch. OwnedGet
  не устанавливает ready/nonce/proof и не выбирает auth response decision.

### Callers, revocation и сохранённые границы

Прослежены все production begin/admit callsites, nativeFreshHistory (newNonce,
CreateWebResourceRequest GET, один вызов из requestHistoryNavigation), selection
callback, prepare/finishHistoryAcceptance/reset callbacks. Target+tag не
создаются renderer: pending стоит до async snapshot; callback operation/
session/generation/revision fences сохранены. cancelHistoryIntent сбрасывает
target/tag/historyNavigation и меняет operation; clearHistorySession меняет
session и очищает ledger/singleForward. Bind account/workspace/token/authGen,
cookie-change reconciliation, authRequired/closed, fail/process failure
по-прежнему отзывают контекст; stale callback его не восстанавливает.
Actual AppMain auth handler при смене generation вызывает bindempty, не
переиспользует старый proof. Ни один из этих owners/guards diff не меняет.

После login interactiveForm complete→authRequired история/intent/nonce/bridge
отзываются прежним setRuntimeState; небезопасный history не становится GET
от одного redirect. All-nav reset fence/ACK/sameID-singleton, mutation/session
clearing, полезные actualGET Back/Forward и single fresh forward сохранены.
Точный штатный путь login и отсутствие regressions ещё должен доказать runtime.
Особенно требуются new case exact2 1 0 1 0 0 и прежние27 без перестановки/
ослабления, включая quarantine7 phases/selected BF retained marker/held2.

Ponytail (только сложность): **Lean already. Ship.** Использованы существующие
поля и native flow,2 локальных предиката вместо новой абстракции/owner/API;
безопасного удаления guards или упрощения с сохранением границ не найдено.
Слово Ship здесь — результат complexity review, не разрешение выпуска.
Остальные семь групп negative/session/reset, installed/hardware/E2E остаются
открытыми. Только own report append; код/нормы/checklist/Git/VM не менялись.

## Requirements/checklist/analyze: history-reset-stale-readback, до авторства

Результат: **C0/H0, ограниченный AUTHOR GO** для одного opt-in negative case
существующей группы7 T103. Это не SOURCE/runtime GO, не закрытие группы7,
T103/T088/T097 или выпуска. Stage21 здесь не используется как доказательство.

Проверенные SHA-256:

- plan: `d820a8d3f49245f1ea9cba04fdd016219e95e089d8abf769de6cfadfcda4c642`;
- quickstart: `644631f48ae0b3ac7c04d17ba8bb4705bea87256e3d0af7b052d71da5d914cb3`;
- spec: `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92`;
- tasks: `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.

Применены speckit-checklist (проверка качества существующих требований, без
генерации/изменения checklist) и speckit-analyze в ограниченном review lane.
Оба SKILL прочитаны полностью. Extensions YAML разбирается; commit hooks для
этих команд disabled, ничего не запускалось. Paths-only prerequisite подтвердил
active F200 в Documents/crisp-worktrees; обычный prerequisite не запускался,
поскольку его get_feature_paths может писать feature.json, что вне разрешения.
Spec/tasks прочитаны напрямую; неподдерживаемый локальным script --require-spec
не подменён выполнением изменяющей команды.

Повторно получен неизменный checklist inventory:198 файлов,31 с checkbox,
477 checked/0 unchecked, canonical hash
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`
(sorted SHA256 + two spaces + checklist-relative filename + LF).
Проверены применимые requirements CHK007/013/016, security CHK007/009/011/022
и ux CHK019. Отметки относятся к качеству требований, не к runtime acceptance.
Tasks остаются120:93 checked/27 open; T103 и T088 открыты. Новая задача либо
продуктовый вопрос для конкретизации уже существующего stale-result запрета
не нужны.

Согласованность: spec Session2026-10-22/FR-002/005/006 запрещает возврат старых
полномочий; data-model T103 связывает proof с ID+URL/session и отзывает async
snapshot по revision; bridge T103 запрещает snapshot-as-authority и обход
ordinary latch. Selected plan требует same current singleton после reset ACK,
отказ при same-document mutation/new ID и доступное fresh-GET recovery. Новый
plan3282+ и quickstart совпадают с этими правилами и constitution VI/VII;
общий кабинет, данные/cookies, native owners и scope задач не меняются.

Обязательные конструктивные границы будущего SOURCE review:

1. Arm только после принятого C: prep A/POST-B/C проходит настоящий latch и
   bridge. Удерживать настоящий resetting readback после реального reset ACK,
   не selecting/accepting ответ и не сам ACK; доказать исходный actual singleton
   ID/URL. Callback доставить неизменённым один раз на прежнем UI dispatcher;
   освобождение closure должно завершиться до уничтожения host.
2. pushState должен реально изменить browser current ID и URL при том же DOM/
   document generation, без нового document Starting. Независимый CDP snapshot,
   а не очищаемый host ledger, подтверждает mutation. Не требовать, чтобы после
   mutation host ещё оставался resetting: штатный SourceChanged уже может
   синхронно сделать unavailable/history-mutation и отозвать operation.
3. Нулевые новые activation/auth-cookie/bootstrap/native_ready/dispatch считаются
   относительно baseline после принятого C/до удержанного list acceptance,
   не относительно начала всего case. Original activation wrapper вызывается
   немедленно, чтобы ошибочная активация не была скрыта fixture. После stale
   delivery проверить сохранённый mutated entry и отсутствие traversal/authority;
   один итоговый state или число HTTP запросов этого не заменяет.
4. Recovery — настоящий host.navigate(list), final GET/ordinary latch, новый
   document и entry ID, product reset/readback и действующий bridge. Проверить
   отсутствие прежнего singleForward, не выдавая history.go(-1) на singleton
   без Starting за доказанную отмену BF.
5. Counts точно `4 0 0 0 0 1`; pushState/snapshots/reset не добавляют GET.
   Сохраняются old28/default23, их относительный порядок/oracles,20s/10s/35s,
   GUID/profile/source/PE/runtime/owned0 и cleanup. Safe PASS на текущем host
   достаточен для этого отрицательного класса; искусственный RED не требуется.

Открытых C/H неоднозначностей для авторства не найдено. Другие reset интервалы,
ACK/error/timeout, session/account replacement и вся остальная матрица остаются
открыты. Изменён только собственный report; norm/code/checklist/Git/VM untouched.

## Stage21: независимая квалификация сохранённого полного native28 GREEN

Результат: **C0/H0, ограниченный saved-runtime GO для точного frozen28 прогона**.
Это подтверждение исправленного fresh-list redirect и сохранения проверенных27
регрессий на host385b, не полный feature/host security acceptance и не закрытие
T103/T088/T097. Новый history-reset-stale-readback этим прогоном не проверялся.

Прочитаны все1121 строки run.log, result.json, полные Run-History/Invoke-Runner/
run.cmd/Check-Terminal и frozen runner. Независимо разобраны28 запусков/native
PASS/runner PASS, их порядок, counts, elapsed и markers из сохранённых файлов.
Никаких повторов, VM/build/tests/Git либо чтения текущего guest не выполнялось.
Отдельный real-app build3 не исследован и не включён в это заключение.

### Зафиксированные материалы и происхождение

Bundle: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history21.8NKA2c`.
SHA-256:

- source216: `cc95af66a55aeba4a35e86bbf9bc6ad921845191a116f08ca3969cc13f1d051b`;
- prior216: `bb0e9e9b720bac0389ddba177304177eafdae5d682178ed53924ef72375f7b23`;
- result.json: `b8ef506ea8e6f303643efab6c176ceb88b60a44e45e9c0d6e65a45d3bff5074c`;
- run.log: `8ec9c2dca02bcddc19b4002e3b3f60e760a21c4d10b57a0e4509627c75375c01`;
- run.err: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0bytes);
- Run-History: `8e855662a6fb721963a122b344da6dc82c04b74f3f75bef10674742c83fce2ef`;
- Invoke-Runner: `c62392130c7673105c45ae94b553686ccc305a24b91756eccdb47692a4189d5a`;
- run.cmd: `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`;
- retained Check-Terminal: `079a5d531f6005b4a8326bec0e30c443c3808c2e610b64c6a0a44a9b9fb29318`.

prior.sha256 побайтно равен source.sha256 сохранённого stage20. В manifest216
изменён только host CPP8fa→385b. Все5 физически retained source files совпали
со своими manifest hashes. Header остаётся f32a. Frozen test3 побайтно равны
stage20: CPPfd6b76fab70f4b782318beaf87538117770a7bc9747203b3e21189d8a7ac3d71,
PY80f56385b4e6e38c019d91fe8f9e238a39262f7831d4db127653fbc6b784bff3,
PS2832eca325741f12c0fb3db3c23187bc67ba404d28a7f6f4bcb841e1231d94c9.
Следовательно meaningful RED stage20 и GREEN21 не разделены изменением oracle.
28-й набор — новый case первым и old27 в точном порядке result.stage18;
default23 frozen runner также остаётся прежним, опциональные случаи перечислены
явно в wrapper. Исключений/skips/xfail/fallback ради GREEN в этих bytes нет.

Проверены локальные5 input hashes receipt, включая synthetic TLS inputs только
по хешам, без чтения содержимого private key. Receipt runtime3 равен stage20:
Core DLL6eeb1e4091eef101fca4d3c6ec43e4fe183a0188eed624bf8a8ff11a1a24b326,
Loader DLL a9a09232c25805323d4cfb3fc8f545a190a9c8a99c93262ea99d0b88df99ec90,
Bootstrap DLL44752d799b8d7cead99d6a20cb9a46009a9a2dfaa9701176a573e50a30ab089c.
Сами DLL не retained в bundle: независимая квалификация здесь относится к
receipt и выполненным wrapper hash guards, не к новому локальному чтению DLL.

Wrapper требует prior216 preflight, ровно5 staged source, все216 после копии,
postflight216, неизменные input5/runtime3 после child, outer600s и owned0.
Receipt: terminal=true, pre/staged/post216, run_exit0, elapsed214435ms, owned0,
нет failure; device_started/real_account/installed=false, loopback-synthetic.
Per-case: fresh GUID/profile, ready1.5s; native20s, browser-close10s; runner35s,
server drain не более3s с остатком35s. Максимум case7789ms. Все28 имеют точный
profile match до навигации, browser exited PASS, fixture exit0/server exit0;
runner подтвердил empty server.err, counts и elapsed перед PASS. Общий
own fresh GUID cleanup PASS, diagnostics-preserved/cleanup-failure отсутствуют.

PE из build log:
`6db47ceef520f1ff365d67c4b4523e27fd785ec32a23dae649c4f84afcf90ac6`.
Build PASS: MSVC14.44 arm64_x64, настоящие SDK host/dependencies с двумя явными
fixture exclusions AppMain/production AEC adapter. Runner хеширует built PE
до cases и после каждого case перед PASS; все28 прошли этот неизменённый guard.
Это fixture PE, не GrafWindowsApp.exe и не MSIX. После успешной очистки нового
независимого PE readback нет. Retained Check-Terminal проверяет216/input5/
runtime3/owned0, **не PE**; его PASS после terminal сообщён main, скрипт прочитан
и хеш подтверждён, но reviewer его не исполнял и не выдаёт за собственный guest
readback. Наличие скрипта само по себе не заменяет сохранённый receipt.

### Все28: фактический порядок и неизменные counts

Все строки ниже — native PASS и runner PASS. Counts независимо сопоставлены
с frozen exact/range oracle; разрешённые cache/provisional ranges не расширены.

| № | Case | Actual six counts |
|---|---|---|
|1|history-fresh-login-redirect|2 1 0 1 0 0|
|2|initial200|1 0 0 0 0 0|
|3|login400|0 1 0 0 0 0|
|4|email503|1 0 1 0 0 0|
|5|cabinet401|1 1 0 1 0 0|
|6|cabinet503|1 0 0 0 0 0|
|7|login429|0 1 0 0 0 0|
|8|email429|1 0 1 0 0 0|
|9|email-json503|1 0 1 0 0 0|
|10|reselect|1 1 1 1 0 0|
|11|billing401|1 1 0 1 0 0|
|12|meeting401|1 1 0 1 0 0|
|13|transport-reset|0 2 0 0 0 0|
|14|tls-failure|0 0 0 0 0 0|
|15|login-post400|0 1 0 0 0 1|
|16|history-get|7 0 0 0 0 0|
|17|history-post|6 0 0 0 0 1|
|18|history-entry|4 0 0 0 0 1|
|19|history-entry-same-url|4 0 0 0 0 1|
|20|cancel-before-start|3 0 0 0 0 0|
|21|history-host-same-url|6 0 0 0 0 1|
|22|cancel-history-host|5 0 0 0 0 0|
|23|cancel-history-script|4 0 0 0 0 1|
|24|history-same-document|3 0 0 0 0 1|
|25|history-host-get|5 0 0 0 0 0|
|26|history-host-quarantine|6 0 0 0 0 1|
|27|history-pending-read-fence|5 0 0 0 0 0|
|28|history-terminal-held|5 0 0 0 0 0|

### Native наблюдения, не только итоговый PASS

Новый case: actual CGET200/nav2/gen2 с ordinary ready/latch/real bridge, затем
только host.back. Fresh list Starting nav3 marker1, настоящий redirected login
Starting тот же ненулевой nav3 marker1. Actual document/navigate GET responses:
list302/gen3 и login200/gen4, exact generation tag; ContentLoading только final
login, final completion nav3 success1/status200/error0. Прежний list302 не выдан
за completed document. State authRequired, видимая редактируемая login form:
synthetic input сохраняется после200ms, bridge/native_ready не появились,
real button не добавил dispatch; auth/cookie counters остались на baseline C.
Strict counts2 1 0 1 0 0, POST0. Причина RED20 устранена на unchanged test3;
вывод ограничен собственным same-ID fresh redirect, не разрешением по URL.

Old27: initial200 снова starts1/completions1/current_reads1, update real dispatch,
duration4/inventory300/quotaRetry PASS; double first load не замаскирован oracle.
history-get actual IDs5/6/8/6/5/6/8, host-get5/6/8/6/8, actualGET/response tag/
ContentLoading/completion/new generation/bridge на каждой фазе. Полезная BF
история реально работает, не заменена always-deny либо одними свежими загрузками.

Все3 quarantine variants history-post/host-same-url/host-quarantine: AGET5,
POST-B6, CGET8 → fresh-listGET10, actual same committed singleton без fixture
reset/all-nav fence → fresh forwardGET12 → настоящий BF обратно10 и вперёд12.
7 phases/7 bridges, actualGET на фазах3–6; retained history marker1 на BF не
вызывает прежнюю OperationCanceled14. Единственный POST — preparation B,
counts6 0 0 0 0 1. Это unchanged GREEN для прежних трёх phase5 failures.

history-entry и same-url: actual unsolicited BF nav5 и CDP ACK, production
cancel success0/error14 без fixture Cancel; currentID8/DOM/authority retained,
следующий ordinary GET работает. Cancel-host/script controls отдельно помечены
fixture-owned cancellation и не выдаются за production security fence.
Same-document control сохраняет authority и следующий документ; ни counts,
ни этот PASS не означают переноса GET proof на изменённый ID/URL.

Pending-read: настоящий selecting result held; три реально доставленных
конкурента nav5/6/7 (BF/GET/form POST) получили OperationCanceled14, нет
ContentLoading; actual C ID8/DOM/authority сохранены, real retained button
dispatch работает, EARLY_ACTIVATION0. После однократного original delivery
selected Back nav8 ID6 и Forward nav9 ID8 прошли actualGET/latch/bridge.
Terminal-held: selected Back nav5 GET200/ContentLoading/complete уже получены,
actual accepting result held, ID6/DOM проверены; до delivery нет activation,
новых auth/cookie counters/ready/bootstrap/dispatch от real button. После
delivery production сам выдал ready и bridge, следующий Forward ID8 работает;
fixture PASS требует captures1/deliveries1/held=false/final activations2.

Итого: frozen28 GREEN доказан в указанной synthetic native полосе. Остальные
negative/race/reset/session варианты, real AppMain wiring/runtime AEC, установка,
дизайн/клавиатура/accessibility, hardware/auth-upload E2E и релиз остаются вне
этого GO. Изменён только собственный отчёт; остальные материалы не тронуты.

## appBuild3: SOURCE и сохранённые доказательства fresh compile/link

Результат: **C0/H0, ограниченный SOURCE/saved-evidence GO для fresh compile/link
GrafWindowsApp Release x64**. Исходный wrapper по-прежнему **terminal FAIL
APPMAIN_OBJECT_CHANGED**. Это не полный solution/clean rebuild, не runtime,
установка, AEC functional test, MSIX либо закрытие T103. Code-reviewer SKILL
прочитан полностью; проверены полные Build-App.ps1 и Check-FreshApp.ps1, оба
JSON, весь build.log и связанные frozen project/AEC verification paths.
Никаких VM/build/tests/Git или исполнения этих scripts reviewer не выполнял.

Bundle: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-app-build3.hJWWps`.
Локально вычисленные SHA-256:

- Build-App.ps1: `f09a2d776c31174047d2e66dbcbbdbc15ebb8a3c650ec944b9df624b381ede3f`;
- Check-FreshApp.ps1: `12f339157a1113e6c2e95d1acb07c6948a7518df6ed8bbeb06fdd34e46d80e01`;
- original result.json: `9976c4e77bf6b4315882ad3874c5e9109800b3e2fce918bc1697712a0ba247f3`;
- fresh-app-verification.json: `24bd09ac158cc3aa3aaa739e846a0f5ce8ac4cb771ffb9f8e29a4a8df8f73936`;
- build.log: `df038d3a5bb01a07d750c574ee116618efc7384f805c52c5e721f8b194b6af33`;
- build.err: empty, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- source216: `cc95af66a55aeba4a35e86bbf9bc6ad921845191a116f08ca3969cc13f1d051b`,
  побайтно совпадает с independently qualified stage21 manifest.

### Почему compile/link подтверждены, но старый wrapper не PASS

Build-App требует source216/owned0/free10GB, фиксирует runner/AEC provenance,
проверяет старый AppMain.obj47c39d… ДО запуска MSBuild. Затем /t:Build для одного
GrafWindowsApp.vcxproj Release x64 с genuine AEC root/build,600s timeout,
actual exit0, свежие EXE/WebView2Host.obj, compile/link/verified log и MZ/PE8664.
Только после сохранения exe metadata снова требует неизменный AppMain.obj.
Именно этот поздний guard бросает APPMAIN_OBJECT_CHANGED: receipt содержит
build0 и exe, elapsed121014ms, owned0, но **не содержит postflight,
appmain_object_reused или host_object**. Исходный FAIL/его checksum сохранены;
последующие source/AEC/runner guards исходного wrapper не выдаются за выполненные.

Actual log: MSBuild17.14.51, pinned AEC identity verified; компилировались
AppMain.cpp, CabinetWindow.cpp, WebView2Host.cpp, WebViewBridge.cpp и
WebViewRoutePolicy.cpp, затем линковка exact GrafWindowsApp.exe. Есть штатное
warning D9025 (/W1 overridden /W4), не заявляется warning-free build.
LTCG сообщает2081/29650 recompiled functions, остальные reuse: это свежий
инкрементальный build/link, **не clean rebuild всех translation units**.

AppBuild2 manifest имел header354ef351a519bce05af0aa60bf480b84434061d331000df856ad5471ec0d0cd1,
appBuild3 — f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927;
AppMain.cpp source a7927bb8… неизменен. AppBuild2 действительно зафиксировал
reused object47c39d… и тот же AEC provenance. Новая перекомпиляция зависимого
AppMain согласуется с изменением header; необходимость старого object hash
для новой header версии ошибочна. Точная compiler dependency trace не сохранена,
поэтому единственная причина изменения object не доказывается догадкой.

### Что отдельно доказывает Check-FreshApp

Это отдельная квалификация уже выполненного build, не повтор и не переписывание
старого результата. Она принимает только terminal original build0 с exact
APPMAIN_OBJECT_CHANGED, preflight216 и owned0; проверяет exact manifest и все216
текущих source hashes, исходный wrapper hash и прежний AEC provenance hash.
Требует реальные3 compile names/verified/link path, empty stderr, actual EXE
hash равный original receipt (machine8664 уже проверен исходным wrapper).
Все3 actual .obj имеют LastWriteTimeUtc не раньше creation build.log; AppMain
обязан отличаться от прежнего47c39d…, а не быть тайно переиспользованным.
Затем проверяет runtime DLL по stage21 receipt и отсутствие owned процессов.
Только после всех guards пишет новый отдельный JSON с create-once guard.

Сохранённый fresh JSON согласован с original по exact manifest/EXE и ограничению
fresh-compile-link-only. Actual PE по original parse/hash и отдельному hash guard:
`6ec3c4a857cbdd896908231b5a176bbe7299b0e00c133827b0ea8f416d5ec9bf`,3390464bytes,
machine0x8664, written2026-10-22T00:59:58.3363521Z. Зафиксированы новые objects:

- AppMain: `7a08167a0f5eecf1ad88a8ea7e41c37e90f9f524ffa9d02c0497b5a872ea9d53`;
- CabinetWindow: `f8b35a2a36a5b364a2cfc304628773b8d8ce6b68175e53433cba2d2c36ab4416`;
- WebView2Host: `e81eefd4fe3447854364fe6a8477b679f5c3f1735e1398b56ed2bf6beb6e9148`.

Runtime3 берутся из конкретного independently qualified stage21 receipt с тремя
известными DLL, не из неизвестного пустого inventory; checker не является новым
универсальным валидатором произвольных receipt. Source216 post-check/objects/
DLL/PE guest hashes и timestamps здесь квалифицируются по сохранённым результатам
выполненных guards, а не по новому чтению guest. В JSON object timestamps не
сериализованы: их доказательство — guard перед записью результата. Main сообщил
actual guest PASS; reviewer этот запуск не повторял.

### Genuine AEC, но не проверка работы AEC

Frozen vcxproj0925c31b… и lock78016ed6… сверены с manifest. Project включает
production GrafAEC3WebRtcAdapter.cpp, GRAF_AEC3_AVAILABLE и обязательную standard
static backend library; ValidateGrafAEC3 BeforeTargets=PrepareForBuild запрещает
не-x64/нет backend и вызывает -VerifyBuildArtifacts. Recipe98eb5cc65e858d5b99ecb0a7ad5c922d364cf9531a0a061942c5b8d264c364cf
также совпал с source216: проверяет pinned clean source commit846fe90a289f58b7c9303a635142aa2c7caa93e5,
license files, architecture/config/lock/cross/recipe identity, source digest,
Meson x86_64/windows/source root и полный ненулевой artifact hashes inventory
против provenance. Лишь затем печатает observed verified и exit0.
Original/separate check сохраняют provenance hash
`ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe`.
Это genuine pinned compile/link lane, не fixture с исключённым AEC adapter.
Сам provenance/архивы/PE reviewer из guest не считывал и алгоритм на звуке
не запускал; из verified build нельзя выводить AEC runtime/hardware PASS.

Итог: исходный terminal FAIL честно остаётся; отдельная узкая fresh compile/link
квалификация принимается C0/H0 на указанных bytes. Restore/install/launch/audio/
functional app acceptance/full solution/MSIX/release не доказаны и не разрешены.
Изменён только собственный report; оригинальные bundles/код/нормы/Git не менялись.

## SOURCE: history-reset-stale-readback, new opt-in и full29 runtime proposal

Результат: **C0/H0, ограниченный SOURCE GO к одному fresh build и full29 run**:
новый history-reset-stale-readback ПЕРВЫМ, затем exact stage21 old28 в прежнем
относительном порядке, без изменения counts/oracles/deadlines. Это разрешение
main заморозить и выполнить проверку reviewed bytes, не утверждение runtime
PASS/полной группы7/T103/установленного приложения. Freeze216 с priorcc95af66…,
input/runtime/PE/GUID/owned0 guards обязан квалифицировать main перед запуском.
Reviewer VM/build/tests/Git не выполнял; изменён только собственный отчёт.

Skills code-reviewer и ponytail-review прочитаны полностью. Прочитаны все hunks
test3 относительно frozen stage21, окружающие prep/bridge/response/ContentLoading/
Starting/completion/teardown callers и production reset/readback/SourceChanged.
Проверенные SHA-256:

- CPP: `5172b2dea7cdd89f13fe3a0f4eb3877fc7e216e1cee37eac5b198084c6d8db7e`;
- PY: `2d5aa85618f0637dbfeb686d8a540f5fbe8bcacdb43d1be7eb6c405d0ab2799b`;
- PS: `53ab9962d6d91bf666a1d4288dbee6137b8c7a4c40a83721470c124c99e7aac1`;
- unchanged host CPP: `385b1c81570142fed9e04709c6b9b1d3e295fa3b67bb4144d040fcdc1dcbc189`;
- unchanged header: `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`;
- approved plan: `d820a8d3f49245f1ea9cba04fdd016219e95e089d8abf769de6cfadfcda4c642`;
- approved quickstart: `644631f48ae0b3ac7c04d17ba8bb4705bea87256e3d0af7b052d71da5d914cb3`.

Baseline test3 — retained stage21 fd6b/80f5/2832, не текущие изменяемые копии.

### Настоящий reset ACK, настоящий ответ, отсутствие подмены полномочий

Fixture install вызывается после обычного принятия C с actual method/latch/
bridge и baseline counters. Новый holdReset default=false сохраняет selecting/
accepting поведение controlled2. Capture выбирает реальный HistoryStage::resetting,
не ordinal CDP call; прежний originalRead действительно вызывается. В frozen
host единственный такой read внутри finishHistoryAcceptance находится ПОСЛЕ
успешного nativeResetHistory ACK и его operation/session/generation/URL guards.
Fixture не оборачивает и не подменяет reset adapter/ACK. При доставке real result
повторно проверяет resetting, actual singleton/currentIndex0, сохраняет только
наблюдённые ID/URL; malformed/missing result не может пройти PASS.

В pending closure перемещается неизменённый original result+continuation;
deliver проверяет исходный UI thread/held/one-shot и освобождает pending через
std::exchange до вызова continuation. Original activation вызывается немедленно
в наблюдающем wrapper; activation не скрывается fixture. На finish restore
original adapters и settle удержанного closure идут ДО host.close/view.Close,
host в этот момент жив. Изменения stage/proof/session/revision/nonce и fake
finish/Cancel отсутствуют.

### Независимый oracle mutation и отказа, CPP1563–1724

После completion actual fresh-list GET и ContentLoading snapshot наблюдатель
проверяет committed ID, generation/tag/method/response/load и отсутствие ранней
authority. Отдельный настоящий Page.getNavigationHistory доказывает singleton
ID, равный captured readback и actual committed ID, но отличный от A/POST-B/C.
DOM marker/input синтетические; fixture не устанавливает bridge или native_ready.
No-authority button проверяет отсутствие dispatch, counters сравниваются с C,
а не с нулём всего prep. Auth/cookie/signedOut/update не могут вырасти скрытно.

pushState реально исполняется в DOM, результат script проверяется. После него
test ждёт настоящий product unavailable, а не вызывает fail сам. Проверки
требуют exact history-mutation, пустые nonce/ledger/singleForward, quarantine и
canGoForward=false; starts остаётся4, generation/navigation принадлежат list.
Независимый snapshot требует2 entries/index1: прежний singleton и новый ID с
exact #synthetic-reset URL; input retained, bridge/bootstrap отсутствуют.
Это исключает замену документа/имитацию mutation только локальным флагом.

После этого original old singleton доставляется ровно один раз UI thread.
Немедленно проверяется отсутствие resurrection/activation/auth, а отдельный
следующий actual snapshot/DOM снова подтверждает ТОТ ЖЕ mutated current ID и
URL. До recovery нет нового Starting; extra document ContentLoading также
отвергается existing observeProductionCommit/resetDocument.loaded guard.
Неполученный SourceChanged/readback/неподтверждённый snapshot даёт unchanged
deadline/nonzero, а не успешное заключение по одним HTTP counts.

### Реальное восстановление, а не безопасный тупик

Recovery выполняет только host.navigate(list); prep/fresh/recovery URL/method
наблюдаются прежними native subscribers, response требует actual GET/document/
navigate/generation tag200 HTML и ContentLoading/complete. Product самостоятельно
снова делает reset/readback. Recovery owner требует ready, новое generation/
NavigationId, activations ровно1, auth/cookie baseline+1, resetRecovered и
пустой singleForward/canGoForward=false. Независимый snapshot требует singleton
с новым ID, отличным от old prep/captured/mutated IDs и равным actual committed
ID. Ordinary bootstrap/DOM readiness затем реальная bridge button dispatch
дают ровно baseline+1 update; fixture не читает/не выдаёт nonce.

Reset recovery здесь проверен по source-конструкции, не заранее объявлен
runtime PASS. Не заявляется BF cancellation через history.go на singleton без
Starting. Безопасный PASS текущего host допустим, искусственный RED не нужен.

### Сохранность old28/default23 и пределы исполнения

PY добавляет только case membership и существующее A/POST-B/C обслуживание;
GET-B остаётся запрещён, прежняя форма/валидатор POST unchanged. PS меняет
только ValidateSet и exact expected `4 0 0 0 0 1`; новый case не попадает под
широкий quarantine range, поэтому exact counts обязателен. Четыре GET — A/C/
fresh-list/recovery-list, один POST-B; pushState/CDP/reset не добавляют GET.
Default23 array, все old28 bodies/oracles, server readiness1.5s, native20s/
close10s/case35s, PE hash per case, fresh profiles, server drain/owned cleanup
не изменены. Изменения общих predicates применяются только к new case;
holdReset false оставляет оба прежних controlled cases настоящими регрессиями.
Поэтому полный предложенный29-case порядок в одной свежей сборке уместен и
входит в этот limited SOURCE GO. Сам external wrapper/source216 ещё должен
зафиксировать main; этот review не квалифицирует несуществующий runtime result.

Ponytail: **Lean already. Ship.** Новый framework/owner/API/dependency не добавлен;
существующие prep/response/bridge/hold/cleanup переиспользованы. Повторные actual
snapshot и owner checks относятся к разным временным границам; безопасного
удаления без потери oracle не найдено. Ship — только итог complexity review,
не разрешение product release. Все остальные reset/error/timeout/session,
installed/hardware/E2E и полная feature acceptance остаются открытыми.

## Stage22: независимая квалификация сохранённого full29 GREEN

Результат: **C0/H0, ограниченный saved-runtime GO** для exact frozen native
fixture29: history-reset-stale-readback первым, затем прежние stage21 old28
в точном относительном порядке. Это квалификация выполненного синтетического
опыта и сохранности прежних регрессий, не full T103/группы7/product GO.
Reviewer не запускал VM, устройство, сборку, тесты или Git. Использован
code-reviewer; прочитаны полный result.json, все1179 строк run.log, пустой
run.err, все Run-History/Invoke-Runner/run.cmd, frozen native runner210 строк
и retained Check-Terminal.ps1. Только собственный отчёт дополнен.

Bundle: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history22.3LHhEG`.
Независимо вычисленные SHA-256:

- source216: `3f3759145cfaffd115536a43e8d5aaaf6444e936a9584a9a7c4b245a18a5b7de`;
- prior216: `cc95af66a55aeba4a35e86bbf9bc6ad921845191a116f08ca3969cc13f1d051b`;
- result.json: `2e4907311f207362b2e735bb78934d1c8fc0d6c305bf297f4c64de510f6f7a20`;
- run.log: `48483186ca754496796f410071eb392b6dd6298b80ad05152e5ad14092e98c49`;
- run.err: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (0 bytes);
- Run-History.ps1: `f5b9f9c3fee177d20c978c1e1eda6937c595319aedc55cd68f00cc8c4178b697`;
- Invoke-Runner.ps1: `d6e2502aadd0411c715c090f4972305019b8cf97d9099b1d5c4d6cf35a2ecf17`;
- run.cmd: `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`;
- Check-Terminal.ps1: `95b690e82b02be37990cbf11982ed435e89e999ec4640f4b42841c0c30d84a74`.

### Происхождение исходников, PE и границы проверок

Оба manifest действительно содержат216 уникальных путей; prior byte-identical
stage21 source.sha256. Единственная manifest delta — test CPP/PY/PS. Все5
retained staged source файлов непосредственно совпали с manifest и SOURCE GO:

- CPP `5172b2dea7cdd89f13fe3a0f4eb3877fc7e216e1cee37eac5b198084c6d8db7e`;
- PY `2d5aa85618f0637dbfeb686d8a540f5fbe8bcacdb43d1be7eb6c405d0ab2799b`;
- PS `53ab9962d6d91bf666a1d4288dbee6137b8c7a4c40a83721470c124c99e7aac1`;
- unchanged host CPP `385b1c81570142fed9e04709c6b9b1d3e295fa3b67bb4144d040fcdc1dcbc189`;
- unchanged header `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`.

Wrapper проверяет prior216 до копирования ровно5, новый216 после копирования
и после child; inputs5 и runtime3 хешируются до/после. Все5 retained inputs
непосредственно совпали с receipt; synthetic key только хеширован, содержимое
не читалось/не публиковалось. Runtime3 в receipt идентичен stage21: Bootstrap
`44752d799b8d7cead99d6a20cb9a46009a9a2dfaa9701176a573e50a30ab089c`, Core
`6eeb1e4091eef101fca4d3c6ec43e4fe183a0188eed624bf8a8ff11a1a24b326`, Loader
`a9a09232c25805323d4cfb3fc8f545a190a9c8a99c93262ea99d0b88df99ec90`.
Receipt terminal=true/run_exit0/pre-staged-post216/owned0/no failure,
elapsed211818ms. Никаких install/real account/device_started в этом run.

Журнал подтверждает fresh native fixture build/link x64 MSVC14.44.35207 и PE
`5a1b775bab306642f3e00e1e22d5eee08567df629d64613c1203f986c8d3957c`.
Frozen runner вычисляет PE hash после build и проверяет неизменность после
каждого case до runner PASS. Это не production AppMain/AEC/full solution build:
runner исключает AppMain.cpp и production AEC adapter. PE собственного GUID
удалён после успеха; новое postterminal чтение PE НЕ заявляется.

Main отдельно сообщил actual guest postterminal PASS SOURCE216/INPUTS5/
RUNTIME3/OWNED0. Retained Check-Terminal с указанным SHA прочитан: проверяет
terminal receipt, manifest и реальные guest files/DLLs/процессы, но не PE и
не повторяет case oracles. Сам reviewer его не выполнял, отдельного saved
stdout/receipt этого recheck в bundle нет; факт выполнения взят из сообщения
main. Это дополнение, не подмена primary run receipt/per-case PE guards.

### Новый отрицательный stale readback: наблюдения и обязательные assertions

Prep действительно A GET/nav2/id5/gen2 → POST-B/nav3/id6/gen3 → C GET/nav4/
id8/gen4; real bridge1/2/3, actual response method/tag, ContentLoading и
completion. Затем только host Back приводит к fresh-list GET/nav5/id10/gen5,
200 и реальному native reset/readback. Журнал явно содержит
RESET_READBACK_HELD id10/RESETTING1/ORIGINAL_RESULT1. Независимый actual
snapshot phase0 подтверждает singleton id10/gen5, без дополнительного Starting.

Настоящий pushState создаёт id12, entries2, generation остаётся5; product
переходит в unavailable (HOST_STATE0). Snapshot phase2 видит новый current ID,
phase4 после доставки original stale singleton снова видит ТОТ ЖЕ id12,
entries2/gen5. До recovery нет нового Starting/замены документа. Далее
host.navigate(list) даёт настоящий GET/nav7/id13/gen6, 200, обычное ready и
новый actual singleton. Final native reason:
stale-reset-revoked-real-result-fresh-get-recovery; starts5/completions5.
Counters current_reads4/signed_out4/invalidations0, strict counts
`4 0 0 0 0 1`, runner2440ms. Пропуск nav6 не выдаётся за отдельно наблюдённый
NavigationStarting: журнал фиксирует именно5 starts.

Не все свойства печатаются отдельными строками. Exact frozen CPP assertions
обязательны для PASS и проверяют: real resetting result приходит после
настоящего reset ACK (production call chain), original callback доставляется
однократно на UI thread без подмены результата; original activation не
перехватывается; exact failureDetail history-mutation, пустые nonce/ledger/
singleForward/quarantine, отсутствие ранних auth/cookie/update/activation,
retained input/DOM и отсутствие bridge/ready до recovery. После доставки
проверки повторены сразу и на независимом snapshot. Recovery требует новый
ID, native final GET proof, generation/nav корреляцию, ordinary bootstrap и
реальную bridge dispatch, ровно1 activation/auth/cookie/update прирост и
отсутствие old Forward. Closure settle/restore до host close. Эти свойства
квалифицированы как assertion-backed, не выдуманные дополнительные log fields.
Fixture не пишет product stage/proof/session/nonce, не подделывает ACK/finish
и не отменяет navigation вместо host. Безопасный negative PASS не требует RED.

### Полный29 порядок, counts и длительность

Независимая read-only Ruby сверка receipt/requested, трёх log списков
(scenario/native PASS/runner PASS), unique29 GUID profiles, exact/range counts
и29 elapsed завершилась PASS. Первые строки — новый case + точные old28;
пропусков/дублей нет. Default23/oracles неизменны согласно SOURCE review;
transport-reset3 разрешён прежним диапазоном1..3, это не ослабление.

| # | Case | Final counts | ms |
|---|---|---|---:|
|1|history-reset-stale-readback|4 0 0 0 0 1|2440|
|2|history-fresh-login-redirect|2 1 0 1 0 0|7683|
|3|initial200|1 0 0 0 0 0|4694|
|4|login400|0 1 0 0 0 0|7134|
|5|email503|1 0 1 0 0 0|7166|
|6|cabinet401|1 1 0 1 0 0|7340|
|7|cabinet503|1 0 0 0 0 0|7004|
|8|login429|0 1 0 0 0 0|7310|
|9|email429|1 0 1 0 0 0|7116|
|10|email-json503|1 0 1 0 0 0|7362|
|11|reselect|1 1 1 1 0 0|7580|
|12|billing401|1 1 0 1 0 0|7447|
|13|meeting401|1 1 0 1 0 0|7454|
|14|transport-reset|0 3 0 0 0 0|7129|
|15|tls-failure|0 0 0 0 0 0|7183|
|16|login-post400|0 1 0 0 0 1|7490|
|17|history-get|7 0 0 0 0 0|2455|
|18|history-post|6 0 0 0 0 1|2430|
|19|history-entry|4 0 0 0 0 1|1608|
|20|history-entry-same-url|4 0 0 0 0 1|1812|
|21|cancel-before-start|3 0 0 0 0 0|7659|
|22|history-host-same-url|6 0 0 0 0 1|2552|
|23|cancel-history-host|5 0 0 0 0 0|1721|
|24|cancel-history-script|4 0 0 0 0 1|1523|
|25|history-same-document|3 0 0 0 0 1|1952|
|26|history-host-get|5 0 0 0 0 0|1961|
|27|history-host-quarantine|6 0 0 0 0 1|2367|
|28|history-pending-read-fence|5 0 0 0 0 0|2983|
|29|history-terminal-held|5 0 0 0 0 0|2362|

Прежний redirect остаётся actual list302/gen3 → login200/gen4 на одном
nonzero nav3, editable form retained/authRequired/new authority0, strict
`2 1 0 1 0 0`. initial200 по-прежнему starts1/completions1/cookie1 с real
update1/duration4/inventory300/quotaRetry. history-post/host-same-url/
host-quarantine проходят все7 фаз: IDs5/6/8 → actual fresh/reset singleton10 →
fresh forward12 → полезный actual BF10/12 с actualGET/bridge на каждой фазе.
history-get сохраняет IDs5/6/8/6/5/6/8; host-get —5/6/8/6/8. Unsolicited
entry negatives отменены product без fixture Cancel, retained authority и
следующий GET сохранены. cancel-host/script остаются явно fixture controls,
не выданы за production cancellation proof; same-document остаётся регрессией.

Controlled selecting hold: три actual конкурента nav5/6/7 завершены
OperationCanceled14/FIXTURE_CANCEL0, без ContentLoading/early activation;
после real result delivery полезные BF id6/8 и real bridge сохранены.
Controlled terminal hold: actual selectedGET nav5/id6/200/load/completion
уже произошёл, но real accepting result удержан; EARLY_ACTIVATION0, real
button/DOM/ID проверены до release, затем product ready/bridge4 и Forward8/
bridge5. Новый holdReset default=false не выключил эти старые проверки.

Все29 имеют verified profile до навигации, browser exited PASS, fixture0,
server0. Final counts читаются только после server drain; пустой server.err
входит в неизменённый PASS guard. Server ready1.5s/native20s/close10s/case35s/
outer600s не ослаблены. Максимум7683ms, общий211818ms. Финал журнала:
TEMP_CLEANUP=PASS; CASES_PASSED=29 REQUESTED=29; CASES=PASS. Cleanup относится
к собственному fresh GUID, failure paths по-прежнему сохраняют diagnostics.

### Пределы заключения

Stage22 доказывает exact tested stale-reset mutation/recovery schedule и
old28 synthetic regression на unchanged production host385b/f32a. Не доказывает
все перестановки reset/session/error/timeout, семь integration groups целиком,
T103/T088 closure, production AppMain функциональность, установленный MSIX,
живой сервер/account, визуальную/macOS parity, аудио/hardware или release.
Все оставшиеся gates открыты; новый code/нормы/checklist/task/issue/Git state
не менялись. SOURCE GO, saved runtime GO и конечная приёмка остаются разными
видами доказательств.

## T103 history-reset-account-boundary: bounded requirements/checklist/analyze

**C0/H0 — AUTHOR GO только к новому opt-in test3, не к host implementation
или runtime.** Прочитаны последние plan3321–3353/quickstart1385–1399,
действующий spec FR-002/003/005/006 и Session2026-10-22, bridge §§2–3/T103,
SafeHistory data model, T103/T088, Constitution III/VI/VII и применимые guidance.
speckit-checklist/analyze прочитаны полностью; применены как bounded review
качества требований и cross-artifact consistency. По прямому ограничению main
новых checklist/markers нет; prerequisites с Git и тестовые команды не запускались.
Feature200/high-risk-product подтверждён .specify/feature.json; это очередной
срез T103/#7280 с существующим владельцем, не новая задача/контракт/продуктовый выбор.

Независимо вычислены точные hashes норм:

- plan: `8ebca554ca46d215faa50cea3e302a9b0d3eb7bad488f8c40b694acbc081be17`;
- quickstart: `1acb880f5603d40132e45ff4f9b5a487c4e864f408035661ae87b520db28c0c4`;
- spec: `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92`;
- bridge: `2d31f0f9bd1548ca592561062788aa87a521cf8f9661bf320a7c9177cb456dc5`;
- data model: `338653d8c905eb5db07e33394bbf441978df5b49899cb88a0203047017a885a7`;
- constitution: `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`;
- tasks: `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.

| Требование / качество | Действующее основание и покрытие | Вывод |
|---|---|---|
| Реальная граница workspace без подделки authority | Spec Session2026-10-22/bridge boundary/model; actual cookie через AuthSession, public bind A→B, тот же user/token, явно выбранная authGeneration | Полно и проверяемо; token не печатать, current B сохранять в следующем обычном auth callback |
| Завершение отменённой операции, а не вечный loading | FR-002/SC-002 и полезный recovery выбранного plan; unavailable≤5с до reload, никаких новых HTTP/authority | Измерять монотонным временем вокруг public bind; не перезапускать старый history budget, не выдавать idle/not-ready за terminal |
| Stale result не возвращает старую сессию | Spec/bridge/session model; настоящий reset-held readback после ACK, original once/UI, session/operation/revision и proofs/singleForward отозваны | Inert delivery требует сохранения B/current document/entry и counters; original activation не блокировать fixture |
| Полезный штатный повтор | Spec сохраняет reload после ошибки; public host.reload, actual GET-list/nonzero nav/new generation/native response-completion/reset/readback/singleton/GET proof/ordinary bridge | Нет искусственного navigate(list), fake ready/finish; новый числовой entry ID не обязателен |
| Мера HTTP и полномочий | Exact counts4 0 0 0 0 1; auth/cookie3→4, signedOut/invalidation0, activation0→1, bridge3→4 | Prep A/C/list + recovery4GET и прежний POST; отсутствие HTTP до reload подтверждать по фазе/наблюдениям вместе с total, не одним ready |
| Нет регрессии initial bind / нет расширения acceptance | initial200 actual first-ready bind/1GET; прежние29 и limits unchanged; T103/T088/T097 открыты | Проверка не разрешает eager GET для обычного ready bind, не принимает AppMain account-me/UI/hardware/release |

Checklist gate: byte-identical inventory **198 files /31 checkbox files /
477 checked /0 unchecked**. SHA canonical sorted per-file SHA + two spaces +
checklists-relative name + LF:
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Релевантные security CHK001–007/017–018/022, ux CHK019/020 и requirements
CHK004/005/009/013/016/020 согласованы с новым срезом; прочие исторические
отметки не объявлены новой функциональной приёмкой. Tasks120/93/27; T103 и
T088 unchecked. Ни один marker/task не изменён. Extension hooks для
checklist/analyze разобраны: активных before/after нет.

Текущие host385b/headerf32a и test3 5172/2d5/53ab независимо хешированы,
совпадают со stage22; нового test source ещё нет и SOURCE GO ему не выдан.
Caller audit предложения Sagan (captured interruptedReset при resetting/
initializing/nav0, затем clear/rebindB и fail) не противоречит этому gate как
гипотеза минимальной корневой правки ПОСЛЕ meaningful native RED. Exact reason
history-session-changed не норма и не должен стать oracle нового fixture.
Ни конкретная guard-реализация, ни reentrancy/callback order этим review не
одобрены: отдельный actual diff SOURCE review обязателен.

Следующий шаг: авторство одного bounded теста в existing test3 → SOURCE review
точных bytes → unchanged meaningful RED, различающий terminal unavailable и
вечно initializing ДО recovery → минимальная host правка с отдельным SOURCE →
unchanged GREEN и прежние29. Действующие20s/10s/35s/профили/source/PE/runtime/
owned0/cleanup не ослабляются. Findings: C0/H0, новых нормативных пробелов или
вопросов владельцу нет. Это requirements AUTHOR GO, не production/runtime GO.
Изменён только этот собственный отчёт; VM/tests/Git/чужие файлы не затронуты.

## SOURCE: history-reset-account-boundary test3 против frozen stage22

**C0/H0 — ограниченный SOURCE GO к отдельному stage23 single-RED run** нового
opt-in после main freeze/source/input/runtime/PE qualification. Не host fix GO,
не compile/runtime PASS и не полная T103. Skills code-reviewer/ponytail-review
прочитаны полностью; просмотрен весь diff3 и нужные prep/native event/bridge/
reset ACK/readback/reload/teardown callers. VM/build/tests/Git не запускались.

Проверенные current SHA-256:

- CPP `96161237561e962d4d7f4c02fd29f938e466e281660132b6cfc69e5d2a2048ed`;
- PY `ca034b5c1b0553c4cabbf4db9b89861f612b6501dd9474ece07cbc39d0524cec`;
- PS `991832e12ed52246b71a326d39d782a6a654458db78d65df5be4cfd52d3b5417`;
- unchanged host `385b1c81570142fed9e04709c6b9b1d3e295fa3b67bb4144d040fcdc1dcbc189`;
- unchanged header `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`.

Baseline — retained stage22 test3 5172/2d5/53ab, не другая текущая копия.
Approved plan8ebca554/quick1acb880 повторно совпали. Findings C0/H0.

| Граница | Фактическая конструкция / вывод |
|---|---|
| Genuine cookie и чистая смена workspace | PY только new-case выдаёт synthetic HttpOnly Secure cookie. Token берётся исключительно из actual current AuthSession callback, проверяется непустым; public bind сначала A, затем B с теми же user/token/authGeneration1. Новые friend account/boundary только читают поля. Recovery callback не переприсваивает A; signedOut/invalidation0 обязательны. |
| Реальный reset-held / отсутствие early authority | После real A/POST-B/C latch/bridge3 устанавливается прежний originalRead decorator. Capture только resetting, его production call находится после real reset ACK; retained result/singleton ID/URL не подделаны. Existing wrappers original activation исполняют немедленно. В pre-bind phase0 independently observed singleton/retained DOM без nonce/bootstrap/dispatch. |
| Terminal до recovery | GetTickCount64 фиксируется перед public bind. Phase2 ждёт unavailable, иначе >=5000ms даёт account-boundary-loading-timeout и finish(false) ДО reload. Первый actual unavailable timestamp обязан уложиться≤5000ms; последующий уход из unavailable до recovery sticky-fails. Session/operation/revision обязаны вырасти, proofs/singleForward/nonce отозваны, counters/ID/gen/doc сохранены. Exact failure reason намеренно не проверяется. |
| Stale result и useful recovery | Original singleton доставляется once/UI; немедленный owner check и повторный independent snapshot требуют прежний actual singleton, B и отсутствие activation/auth/cookie/bridge. Затем именно host.reload(), actual native GET/tag/ContentLoading/completion/new nav/gen, production reset/readback/current singleton/GET proof и ordinary bridge3→4. Account B/authGen1, cookie/auth3→4, activation0→1, signedOut/invalidation0 обязательны; recovery ID равен actual committed ID, но может совпасть с прежним числовым ID. |

No-HTTP до reload не выводится из final counts: existing All-resource/All-source
WebResourceRequested наблюдатель для new-case/accountBoundAt/historyPhase3
немедленно проваливает любой HTTP(S) запрос. Before bind fresh-list response уже
получен. Перед public reload phase становится4; после этого actual final GET
наблюдается обычными productionHistory events. Strict server counts остаются
`4 0 0 0 0 1`, новый case не включён в более широкий quarantine counts range.

Missing/late/malformed result, неверный singleton/account/counters, early
activation, extra navigation/response или rebound A не имеют PASS пути. До
reload original stale result обязан быть доставлен, а независимый snapshot
после него завершён. Existing finish restores adapters и settles retained closure
до host.close/view.Close и на failure пути; pending освобождается std::exchange
до original callback. Наблюдатели не вызывают fixture Cancel, fake ACK/reset/
finish, не пишут product session/stage/proof/nonce и не скрывают activation.

Old29 paths сохраняются: новые account branches включаются только new-case;
heldReset расширяет прежний staleReset без изменения его условий. Для старого
stale-reset новый-ID и exact history-mutation проверки сохранены. CPP позволяет
signedOut0/B/reload/нефиксированный recoveryID исключительно новому case. PY
меняет только membership и его cookie; old bodies не ослаблены. PS default23
array и весь suffix от `$failed =` (old oracles, build/PE/hash/GUID/deadlines/
cleanup) независимо сравнивались с stage22 и byte-identical; ValidateSet/expected
добавляют один opt-in. Это SOURCE сохранности, не новый old29 runtime PASS.

Ponytail: **Lean already. Ship.** Прежние hold/snapshot/owner/recovery helpers
переиспользованы; новых framework/owner/API/dependencies нет. Дополнительные
read-only поля относятся к конкретному workspace/terminal oracle, удаление
снимет доказательство. Ship относится лишь к complexity review.

Предполагаемый old-host stranded initializing — цель meaningful RED, не уже
наблюдённый результат. При RED main должен квалифицировать actual stage, terminal
reason/elapsed/no recovery/source/PE/owned cleanup; unrelated compile/startup
failure не доказывает дефект. Минимальная host правка требует отдельного SOURCE,
затем unchanged GREEN и old29 regression. Другие session/reset schedules,
AppMain/UI/installed/hardware/E2E и release gates остаются открытыми. Изменён
только этот report.

## Stage23: saved-runtime meaningful RED, account boundary до recovery

**C0/H0 по квалификации доказательства; meaningful native RED принят.** Это
не product PASS и не SOURCE GO будущей правке. Полностью прочитаны114 строк
run.log, receipt и три wrapper; сохранённые files/manifest проверены read-only.
Bundle: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history23.G5jLuQ`.

- source216 `edbb28729236ddbf9f5222c25b44b9c0bedfadf491aee8e826beb36aaf96d156`;
- prior216 `3f3759145cfaffd115536a43e8d5aaaf6444e936a9584a9a7c4b245a18a5b7de`;
- receipt `6e9ec5a23ccde3337d1797a07bf8d86674644e7a902b316f61b5157dce860712`;
- log `1446514e272a375dc93aa51def5d772f4b55c4d727be461be70d02e38d92a63c`;
- err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- reported fixture PE `9b8e748a544b93d5d07cdf87444e61807ff4aa33448f40c219acba657d3f3719`.

Manifest216/prior216 valid, prior byte-identical stage22; delta только3 tests.
Все5 retained staged files совпали с manifest и approved SOURCE: host385b/
headerf32a, test CPP9616/PYca03/PS9918. Inputs5 непосредственно хешированы и
совпали с receipt; synthetic key только hash, runtime3 идентичен stage22.
Run-History SHA9728b0e316d9e23b38f70a9f0af0ba583926b1e5cbfc42ca31146ad9dc70bac6,
Invoke-Runner SHAb3732300ae5d4f3364ab1cc71ae9e04aae78a03f04558d85e18545da4dd1f831.
Wrappers требуют prior preflight/new staged/postflight216, неизменные inputs/
runtime, bounded600s/owned cleanup. Receipt terminal/exit1/owned0/pre-staged-
post216, failure NATIVE_RUN_FAILED, elapsed81035ms. SDK fixture BUILD PASS;
per-case PE guard исполнен после server drain до case verdict, не новый
независимый guest PE readback. Reviewer VM/guest commands не выполнял.

Наблюдаемая последовательность: A GET/id5 → POST-B/id6 → C GET/id8 с real
bridge1/2/3; fresh list GET/nav5/id10/gen5, actual200/tag/content/completion;
ORIGINAL_RESULT held в resetting, independent singleton10 phase0. Real reset
ACK — установленное SOURCE call-chain условие этого read, не отдельный printed
ACK. Затем PUBLIC_BIND=1; exact fixture вызывает public bind B с прежними user/
cookie/authGen1. После него native FAIL account-boundary-loading-timeout,
starts4/completions4/status200/state1. Новый GET/recovery не начался. Current
cookie reads3/signedOut0/invalidation0; final counts `3 0 0 0 0 1`.

Пятисекундная граница подтверждена достигнутой веткой точного fixture, которая
сравнивает monotonic time с before-bind timestamp до любой recovery; отдельного
числового bind-to-failure elapsed в журнале нет. Case7203ms включает prep/close,
не объявляется временем самого зависания. Unavailable/phase2 snapshot/stale
delivery/retained B после доставки/reload GREEN не достигнуты и не принимаются.
Недостающий четвёртый GET объясняет counts mismatch: обязательная recovery не
исполнялась, но первичный отказ уже native loading-timeout, не server startup,
build либо один counts oracle. Лог не доказывает иную конкретную первопричину.

Browser exited PASS, fixture1/server0, err0; diagnostics retained в собственном
GUID38344ccf06514318be8a549a0687071a, общий owned0. Успешная очистка diagnostics
НЕ заявляется: fail path намеренно сохраняет их. Далее допустима отдельная
SOURCE проверка минимальной правки, unchanged GREEN/newcase+old29. Не полная
T103/session/AppMain/UI/release acceptance. Изменён только собственный report.

## SOURCE: host interrupted-reset terminal, три добавленные строки

**C0/H0 — ограниченный SOURCE GO к stage24 full30**, new account-boundary
первым, затем exact old29 relative order/unchanged oracles. Stage23 meaningful
RED квалифицирован отдельно выше; GREEN ещё нет. Main обязан заморозить новый
source/input/runtime/PE bundle перед запуском. Skills code-reviewer и
ponytail-review прочитаны полностью, VM/build/tests/Git не выполнялись.

| Файл | Проверенный SHA-256 |
|---|---|
| Current host CPP | `2f037dfc72aef95ce792718f0b47f8bd7b255801d7b7d3ab2c32be29e368560f` |
| Frozen stage23 baseline CPP | `385b1c81570142fed9e04709c6b9b1d3e295fa3b67bb4144d040fcdc1dcbc189` |
| Unchanged header | `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927` |
| Unchanged test CPP | `96161237561e962d4d7f4c02fd29f938e466e281660132b6cfc69e5d2a2048ed` |
| Unchanged test PY | `ca034b5c1b0553c4cabbf4db9b89861f612b6501dd9474ece07cbc39d0524cec` |
| Unchanged test PS | `991832e12ed52246b71a326d39d782a6a654458db78d65df5be4cfd52d3b5417` |

Diff действительно один hunk/+3/-0, bindUserTimeAccount453–466. Нужные
bind callers AppMain1181/1222/1902/3221 и host reconciliation/cancellation/
reset/readback/refresh/reload просмотрены; иных source изменений не включено.

| Проверка | SOURCE finding |
|---|---|
| Scope и порядок | interruptedReset фиксирует resetting && initializing && nav0 внутри changed ДО clearHistorySession; existing clear/invalidate/assignment завершают B, затем fail ДО refresh. Поэтому runtime observer видит уже новый account, старый context после callback не переприсваивается. |
| Latch-safe отмена | Existing clear повышает session/operation/revision и отзывает proofs/singleForward. Existing fail ещё отзывает intent/response/committed URL/bridge/nonce и публикует unavailable. Original readback имеет operation/session/generation/stage fences и не возобновляет старый finalizer; fake response/nonce/GET proof не появляется. |
| Callbacks и повторный вход | invalidateUserTime/clear здесь не вызывают внешний account handler. fail использует прежние bounded cleanup/runtime callbacks; actual AppMain unavailable handler показывает fallback и не пересоздаёт host/rebind A. userTimeAccount B fail не очищает; setRuntimeState снимает nativeReadUserTime/publish/nonce, поэтому последующий refresh не делает чтение/HTTP. В SDK reset interval уже нет usable bridge; закрытие/очистка используют прежние handlers. |
| Ready/closed и отсутствие eager GET | Ready first bind не проходит initializing/resetting guard; неизменённый initial200 должен сохранить1GET. Unchanged bind и closed path не получают новый fail. Условия не охватывают early navigating/nav!=0 — этот отдельный существующий group5 gap не исправлен и не принят. |
| Нет глобальной очистки/новой authority | Изменение завершает только незавершённый host reset через existing failure path; не удаляет cookies/профиль/записи/queue, не меняет capture/server policy, не инициирует навигацию. Recovery остаётся обычным reload и native response/latch/reset/readback; словесный reason не oracle теста. |

Ponytail: **Lean already. Ship.** Один локальный captured predicate и existing
fail, без нового helper/state owner/dependency/timer. Перенос проверки после
clear потеряет resetting, перенос fail до assignment ухудшит callback ordering;
безопасного сокращения не найдено. Ship — complexity review, не release GO.

Это SOURCE допускает один frozen build/run30: actual newcase unchanged GREEN
и прежние29 регрессий, с неизменными counts/сроками/профилями/source/PE/owned0.
Не принимает native execution, AppMain workspace UI, все7групп/T103/T088/
installed/hardware/release. Написан только собственный report; нормы, тесты,
host, Git и внешнее состояние reviewer не менял.

## Stage24: независимая saved-runtime квалификация FULL30

**C0/H0 — bounded runtime GO для исполненного frozen30, не полная T103
acceptance.** Полностью прочитаны1239 строк run.log, result и все3 wrapper;
read-only проверены manifests, retained5, inputs5 и последовательности verdicts.
Bundle: `/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-history24.SfVyzI`.
Ничего в VM не запускалось; validation lane — read-only evidence review.

| Evidence | Независимо вычисленный SHA-256 |
|---|---|
| source216 | `d174be29d5e9e8603188b733213c584ee51aecf891e59a74e5dc4b7aed26cbc0` |
| prior216, byte-identical stage23 | `edbb28729236ddbf9f5222c25b44b9c0bedfadf491aee8e826beb36aaf96d156` |
| result.json | `d872c1418654be998baf39fe698c3c18ced13ff376803b25746a61e490ffccdc` |
| run.log | `063294d825567fc7661742dfe9977483233e44516efec0e1aa60b660d4728b6e` |
| run.err, 0 bytes | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Run-History.ps1 | `0e7f913730e3a22c6f0a5a081ca46a8bc129d2284b55060909cf2e69a7ebd156` |
| Invoke-Runner.ps1 | `a7406a60c4ac1db5834a72ce2799e049c2542f4acf96e4c4b4cdcad603fa6723` |

Manifest delta против stage23 — только approved host CPP2f037dfc…; headerf32a
и test3 CPP9616/PYca03/PS9918 без изменений. Все5 retained bytes совпадают
с manifest и предыдущим SOURCE GO. Input5 хешированы непосредственно, включая
synthetic key только по хешу; runtime3 в receipt совпадает со stage23. Wrapper
сохраняет prior/new/pre-staged-post216, inputs/runtime pre/post, outer600s и
owned-process guard. Receipt terminal, exit0, elapsed210441ms, owned0, без failure.

Requested30 = новый account-boundary + точные прежние29 из stage22; arrays
SCENARIO/native PASS/runner True совпали по именам, порядку, числу и уникальности.
Все30 case GUID различны; environment/profile-before-navigation30/30,
browser-exited/fixture0/server0 — по30/30. Server counts независимо сопоставлены
с неизменными exact/range oracles, не только с напечатанным PASS. Максимум8044ms
(billing401) <35000ms, final temp cleanup PASS и CASES_PASSED=30/REQUESTED=30.
SDK fixture BUILD PASS; reported/per-case-guarded PE
`144cc5467fe2637f9d2bc48a58be7eb53839f751ecfc817e0b04e819e070a81f`.
Reviewer не делал guest PE readback: runner проверяет тот же PE после каждого
case до verdict и удаляет только собственный GUID после успеха.

Новый case: actual A GET/id5 → POST-B/id6 → C GET/id8, real bridge1/2/3;
fresh list nav5/id10/gen5, native GET200/tag/content/completion. Original reset
readback held, independent phase0 singleton10. Public bind B даёт HOST_STATE0;
phase2 singleton10, elapsed0ms, SESSION_OPERATION_REVISION_CHANGED/ACCOUNT_B1/
AUTHORITY0. Exact fixture проверяет <=5s от before-bind и неизменные counters,
nonce/ledger/singleForward revoked. Это actual public host bind, не workspace UI.

После once UI delivery исходного результата независимый phase4 всё ещё
singleton10/gen5, unavailable/B без authority. No HTTP до reload — исполняемый
All-resource observer вместе с unchanged starts/completions/cookie/bridge,
а не вывод только из общего server counts. Public host.reload затем actual
GET/nav6/id12/gen6/200/tag/content/completion, phase5 singleton12/ready. Final
native PASS требует ordinary recovery bootstrap/activation1 и bridge3→4,
account B/cookie сохранены; auth reads4/signedOut0/invalidation0. Strict counts
`4 0 0 0 0 1`; starts5/completions5. Real reset ACK и held-result ordering
подтверждаются исполненным frozen call chain, не отдельной printed ACK строкой.

Прежние29 без ослабления: initial200 starts1/completions1/counts1GET плюс update,
duration4/inventory300; fresh-login302→200 same nav/authRequired; allGET actual
IDs; три quarantine variants по7 фаз с native BF10/12; unsolicited negatives
cancel14 без fixture Cancel; pending3 competitors cancel14/no early activation;
terminal hold до authority, затем useful Back/Forward. Старые fixture-cancel
controls остаются controls, не доказательством production cancellation.

Отдельный portable CTest log действительно48/48/44.78s; SHA
`1a1da0a1d5f7b61dd2d6f4388abce46ebdaecf6d608a6a6b0e3730fa4353ea3f`,
build log SHA`32377383bb72179c57c7744aafbb15583e99af00c0f4b28b05aef30266874cd2`.
Это отдельный Mac portable результат, не Windows/native runtime или SDK app.
Temp365M deletion reviewer не наблюдал. Все7групп, early-navigating account
boundary, actual AppMain/workspace UI, full solution/package/install/audio/
hardware/E2E/release не приняты. Добавлен только этот раздел собственного report.

## appBuild4: ограниченная SOURCE/saved-evidence квалификация compile/link

**C0/H0 — GO только для сохранённого real-app compile/link Release x64.**
Полностью прочитаны Build-App.ps1, result.json и build.log; проверен полный diff
wrapper против appBuild3 и checksums. Bundle:
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t103-app-build4.XW4AJ5`.
Validation lane read-only; VM/build/tests/Git reviewer не запускал.

| Проверка | Результат и граница |
|---|---|
| Wrapper delta | Только source pin, removal старого AppMain.obj reuse assertion с записью actual object hash, runtime3 pre/post guard. Прежние prior-process/free-space/create-once/source216/600s/build0/fresh EXE+host/MZ+PE8664/AEC/runner guards сохранены. AppMain source не объявляется изменённым по одному object hash. |
| Receipt/source | Terminal/build0/pre216/post216/owned0, без failure, elapsed101224ms. Manifest побайтно равен stage24 d174…; runtime3 равен stage24. Restore/install/launch/device/app_network false. |
| Actual compile/link | Весь15-line log: MSBuild17.14.51, AppMain.cpp/CabinetWindow.cpp/WebView2Host.cpp, link exact GrafWindowsApp.exe. Fresh EXE и host-object timestamp проверены wrapper относительно before-build UTC. LTCG6/29650 functions, остальные reuse: это incremental, не clean/full solution. Warning D9025 присутствует; warning-free не заявляется. |
| AEC provenance | Сохранённый log содержит verified846fe90a289f58b7c9303a635142aa2c7caa93e5. Project/verify script/lock совпадают с manifest; mandatory BeforeTargets=PrepareForBuild вызывает VerifyBuildArtifacts, проверяющий pinned clean source/licenses, x64 cache, identity/tree digest/nonempty artifact hashes. Receipt provenance ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe совпадает appBuild3 и guarded post. Reviewer не перечитывал guest vendor/cache; это квалификация saved executed verification, не новая AEC runtime проверка. |
| Actual PE/objects | Wrapper реально разбирает MZ/PE machine0x8664 и хеширует EXE; reported3390976bytes, written2026-10-22T01:45:14.8763625Z. AppMain object144bbaf7185063fc2d0c4004c282d1aca551204f8eacb5c07d0e61adc72a3199; host objecta52e87eafe57cc8716d6d51a88fe8e15edf06d0880a6ebc940933addc0520226. Нет независимого reviewer guest PE readback и нет нового AppMain/Cabinet object timestamp guard; compile names видны в log. |
| История результата | Оригинальные appBuild3 receipt9976c4e77bf6b4315882ad3874c5e9109800b3e2fce918bc1697712a0ba247f3/logdf038d3a5bb01a07d750c574ee116618efc7384f805c52c5e721f8b194b6af33 независимо совпали; terminal APPMAIN_OBJECT_CHANGED остаётся FAIL. Новый lane его не переписывает. |

Независимо вычисленные SHA-256:

- Build-App.ps1 `d6704898fc70dd71ebdc5b53c8ed2174a98d95638770433f28198dafcd98f98f`;
- result.json `0190c9edfe6ab038e7b70cd9845c0d62b0f16e157e627f5f6c3dc4ca73102b13`;
- build.log `c0e75079e7a934469e8a3ef35a10f459f1981b40481dd424458a650646fa2daa`;
- build.err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- source216 `d174be29d5e9e8603188b733213c584ee51aecf891e59a74e5dc4b7aed26cbc0`;
- actual EXE по saved parse/hash guard `71e5703576450fffb845a8133418e9cfc23537445aeeac4e968d816dce3b8e97`.

Это не package/sign/install/launch, не real AppMain workflow/auth/audio/AEC
functional/hardware проверка, не полный solution/clean build и не T103/product/
release GO. Stage24 fixture PE144cc… и этот real-app PE71e570… — разные
артефакты с разными доказательствами; результаты не подменяют друг друга.
Изменён только собственный report, старые bundles и чужие файлы не тронуты.

## T103 history-account-boundary-redirect-held: requirements/checklist/analyze

**C0/H0 — AUTHOR GO только к одному opt-in test3, не host/runtime GO.**
Прочитаны новые plan3355–3394/quickstart1400–1416, selected T103 plan3100+,
spec FR-002/003/005/006 и Session2026-10-22, bridge §§6/9/T103, SafeHistory
data model, T103/T088 и Constitution III/VI/VII. Skills speckit-checklist и
speckit-analyze прочитаны полностью; по прямому scoped запрету новых checklist/
markers/норм нет. Пути подтверждены feature.json (200/high-risk-product),
prerequisite scripts с Git не запускались; активных hooks checklist/analyze нет.

Точные SHA-256 норм этого допуска:

- plan `423c96172e29308dcf725b9eecaf30f9ad0bb4d763dcb483271c1eb65c084ac7`;
- quickstart `186bf12092bddc97e4b8e054e66c510d758c8870548c1166c4ec66d305eb5a4e`;
- spec `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92`;
- bridge `2d31f0f9bd1548ca592561062788aa87a521cf8f9661bf320a7c9177cb456dc5`;
- model `338653d8c905eb5db07e33394bbf441978df5b49899cb88a0203047017a885a7`;
- constitution `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`;
- tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`.

| Требование / качество | Основание / достаточность для авторства |
|---|---|
| Настоящая незавершённая навигация | Plan/quick согласованы: AGET/POST-B/CGET, actual cookie A/authGen1/bridge3; public navigate(list), именно unmarked GET. Server-held marker только вместе с actual Starting/nonzero nav/navigating/no response/completion. Не подмена reset-held или Back/fresh marker сценарием. |
| Смена workspace до ответа | Spec session boundary/bridge stale callbacks/model: public workspace-only bind B отзывает authority и завершает loading unavailable≤5с ДО release. Нет нового HTTP/nav/auth/bridge; сроки измеримы от bind, причина отказа строкой не навязывается. |
| Доставленное позднее событие | Требуются release настоящего HTTP302 safe-next list, actual IsRedirected того же navID и его terminal OperationCanceled без fixture Cancel. Нет GET-login, новой authority или loading resurrection; B сохраняется. Не требуется сохранность DOM/entry после позднего ответа. Marker отправки302 и ранний terminal без redirect НЕ покрывают этот класс. |
| Штатное восстановление | Только после terminal старого nav — public reload/actual GET/new nav+generation/обычный latch/reset/singleton/ready/B/bridge4. Original activation исполняется; исходные history results здесь не удерживаются. Новый числовой ID не постулируется. |
| Измеримость и завершение | Counts4 0 0 0 0 1 = A/C/held-list/recovery-list и один POST-B; cookie3→4/signedOut0/invalidation0/activation0→1. Отсутствие HTTP до release и после bind до reload проверять фазовыми наблюдениями, не одним total. Hold≤8с monotonic вне counts lock, responsive stop/release на всех путях, узкий disconnect отдельно от прочих ошибок; drain/join до counts. Старые1.5s/20s/10s/35s/600s и собственная cleanup неизменны. |

Cross-artifact: 5/5 scoped групп требований имеют существующее покрытие T103
(#7280, group5); T088/#7231 остаётся связанным открытым gate. Новых unmapped
работ, противоречий constitution/spec/contract, неоднозначных критериев уровня
C/H или продуктовых вопросов не найдено. Это качество постановки, не 5/5
исполненных runtime групп. Security CHK001–007/017–018/022, ux CHK019/020,
requirements CHK004/005/009/013/016 применимы без изменения отметок.

Свежий inventory:198 files/31 checkbox files/477 checked/0 unchecked, canonical
SHA`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`;
tasks120/93/27, T103/T088 unchecked. Host2f037…/headerf32a… и test3
9616…/ca03…/9918… непосредственно хешированы, byte-identical frozen stage24;
никакого нового SOURCE review тестов или production diff ещё нет.

Следующий шаг — авторство только этого bounded opt-in в existing test3,
SOURCE review frozen bytes, затем meaningful native RED. Если browser не
доставит redirect Starting, это не PASS позднего-event класса и не доказательство
новой причины; нельзя выдать coverage по marker либо внедрить fake event/Cancel.
Обобщённый bind guard/idle-unowned-redirect rejection остаётся гипотезой до RED
и отдельного SOURCE. После минимальной правки нужен unchanged GREEN + прежние30,
особенно initial2001GET и положительный owned fresh302. Другие late200/session
перестановки, все7групп, AppMain UI, T103/T088/T097 и release не принимаются.
Изменён только собственный report; VM/tests/build/Git/нормы/чужие файлы не тронуты.

## T103 history-account-boundary-redirect-held: frozen test3 SOURCE review

**C0/H0 — limited SOURCE GO только к одному native RED-запуску нового opt-in
на неизменённом host2f/f32a.** Это не runtime PASS, не допуск production fix,
не приёмка прежних30 или всех7 integration groups. Полностью прочитан diff
трёх файлов против frozen `t103-history24.SfVyzI`, реальные новые callers,
observer/phase/recovery/cleanup и соответствующие host callers. Применены
code-reviewer и ponytail-review; VM/build/tests/Git reviewer не запускал.

Повторно независимо вычисленные SHA-256 frozen bytes:

- CPP `6750c42b990c56c2727eff61b6b63838f954472952e6a0bf755a9a401bd9292e`;
- PY `69db054da4a038fcd5e8c5f97f19de2868e2e9edc8991fad51088a8c074fdfbd`;
- PS `e70ad62604a3fa516b085d607051383e2ac65ca201092cc06d498d57dc2bb0d0`;
- host CPP `2f037dfc72aef95ce792718f0b47f8bd7b255801d7b7d3ab2c32be29e368560f`;
- host header `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`;
- plan `423c96172e29308dcf725b9eecaf30f9ad0bb4d763dcb483271c1eb65c084ac7`;
- quickstart `186bf12092bddc97e4b8e054e66c510d758c8870548c1166c4ec66d305eb5a4e`.

Baseline test3 независимо хеширован: CPP96161237561e962d4d7f4c02fd29f938e466e281660132b6cfc69e5d2a2048ed,
PYca034b5c1b0553c4cabbf4db9b89861f612b6501dd9474ece07cbc39d0524cec,
PS991832e12ed52246b71a326d39d782a6a654458db78d65df5be4cfd52d3b5417.

| Проверенная конструкция | SOURCE вывод |
|---|---|
| Реальная подготовка | Сохраняются AGET/POST-B/CGET, genuine synthetic cookie A и real bridge3. Затем только public navigate(list): actual nonzero Starting, unmarked GET request, server-held before headers и peer navigating/no response/completion проверяются совместно до public bind workspaceB/authGen1. Marker сам по себе не заменяет native evidence. |
| Server hold / cleanup | Только третий counted GET удерживается; monotonic8s вне counts lock, stop/release проверяются каждые10ms. Настоящий302 с safe next отправляется после release; disconnect/timeout отдельно дают FAIL. Join до final counts сохранён. Native finish освобождает hold на успехе/ошибке; runner finally пишет release+stop, ограниченно ждёт и сохраняет прежнюю owned cleanup. |
| Boundary oracle | Отсчёт от public bind, unavailable≤5s ДО release; нет HTTP, нового auth/cookie/bridge, activation, proof/singleForward/nonce. Boundary counters должны строго вырасти и затем оставаться неизменными; возврат из unavailable до recovery — sticky FAIL. Зависший loading не маскируется release. |
| Настоящее позднее событие | Обязательны actual IsRedirected на login safe-next с прежним nonzero navID, без fresh marker/BF, затем actual OperationCanceled14 того же ID. Ранний cancel не проходит. Наблюдатель не выставляет Cancel, не пишет product stage/latch/nonce/ACK. Полученный ResponseReceived302 дополнительно проверяет URL/method/generation/Location; его наличие отдельно не является условием PASS: late class доказывают серверный ответ и доставленные native redirect+terminal, не response-sent marker. |
| Восстановление | Только после старого terminal — public reload, actual GET/новые nav+generation, ordinary latch/reset/current singleton/ready, сохранённый B и реальный bridge4. Activation wrapper немедленно вызывает original; без nativeRead replacement/held result. Доказательства не фабрикуются; произвольный новый числовой entry ID не требуется. Counts строго4 0 0 0 0 1; auth/cookie3→4, signedOut/invalidation0, activation0→1. |
| Сохранность прежнего | Новый opt-in не добавлен в default23. Default23 и старый PS case/oracle block побайтно равны Stage24; старые30 assertions/фазы не ослаблены. Общий recovery helper различает новый observer-only captures/deliveries0 и прежние held cases1; restore сохраняет original callbacks и освобождает held closure перед close. Таймеры1.5/20/10/35/600s не увеличены. |

Concrete C/H findings: **0/0**. Ponytail: дополнительных зависимостей,
framework или production seam нет; переиспользованы существующие phase/recovery
и observer peer. Безопасного обязательного удаления не найдено (Lean already).

На host2f SOURCE виден узкий interrupted-reset guard, не общий navigating guard;
поэтому loading-timeout — ожидаемая, но пока не наблюдённая гипотеза RED.
Compile/startup failure не станет meaningful native RED. Если поздний redirect
не доставлен, этот late-event класс остаётся непокрытым, даже при server marker
или раннем terminal. После runtime потребуется отдельная квалификация saved
evidence и отдельный SOURCE review любой host-правки; этот GO их не подменяет.
Добавлен только данный раздел собственного report, остальные файлы не изменены.

## Stage25 meaningful RED + host9308: combined bounded qualification/SOURCE

**Квалификация saved RED: C0/H0. Host SOURCE: C0/H0 — limited GO к одному
frozen build/run: неизменённый новый сценарий первым, затем прежние30 в их
точном относительном порядке.** Это не новый requirements gate и не T103 GO.
Применены code-reviewer и ponytail-review, прочитаны все108 строк run.log,
result.json, Run-History/Invoke-Runner/run.cmd и frozen native runner; полный
двухучастковый host diff и релевантные actual bind/admission/finalizer callers.
VM/build/tests/Git reviewer не запускал; изменяется только этот report.

### Сохранённый Stage25

Bundle `t103-history25.niP0ym` независимо проверен по сохранённым bytes:

- source216 `b89f4900d35997332c57d2fbfdbfa678a278df0f2bcc59e7d7b4e8cfdf8cedde`;
- prior216 `d174be29d5e9e8603188b733213c584ee51aecf891e59a74e5dc4b7aed26cbc0`, побайтно Stage24 source;
- result `444b542c8a88235329f6e560a1284d5117a002b25be14d966c8cc9a618103ba5`;
- log `1fcd22fc9558e519d15ea24f05ce95adbe29ae5973ee0e2c146dfca910845e98`;
- run.err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
- Run-History `84f13dcced68d0739f758b1c7671e8dc61f5b901ef42029ce0eea9c0f02e8a99`;
- Invoke-Runner `e964c39160bc0345881ddbf97f05aaaffb4ceb0d095e82dc8691aeeb5e7d18bd`;
- run.cmd `0a75f74b7466383a1cafc79665c5daf61c48f6e5a831dce6bc958c09eae0d856`.

| Saved observation / guard | Квалификация |
|---|---|
| Запуск и provenance | Ровно один requested/scenario; BUILD PASS. Wrapper требует prior216→staged216→post216, post input5/runtime3 equality и owned0; receipt содержит эти результаты, terminal=true/run_exit1/failure NATIVE_RUN_FAILED/elapsed74030ms. Все5 retained staged source и input5 независимо совпали с manifest/receipt; runtime3 в receipt совпадает Stage24. Полные216 guest files и guest DLL reviewer повторно не читал. |
| Actual meaningful RED | AGET nav2/id5, POST-B nav3/id6, CGET nav4/id8: actual200/content/completion и bridge1→3. Затем phase3 nav5, kind2, HISTORY_INTENT_PRESENT0; REAL_UNMARKED_GET_HELD/PUBLIC_BIND подтверждает исполнение conjunction request/server-held/navigating/no response-completion и public B bind. FAIL held-redirect-account-loading-timeout, state1, starts4/completions3; auth/current_reads3, signedOut0/invalidation0. Это функциональный loading RED, не compile/startup/counts-only failure. |
| Release / покрытие | До FAIL нет UNAVAILABLE/redirect/terminal/recovery; finish освобождает hold уже после FAIL для cleanup. Поэтому доставленный поздний redirect и recovery здесь НЕ приняты. После drain server exit0/counts3 0 0 0 0 1; expected4 отсутствует из-за недостигнутого recovery, не разрешено ослаблять oracle. |
| Сроки / PE / cleanup | Case6965ms<35s, outer74030ms<600s; PROFILE_EXACT_MATCH1/BROWSER_EXITED PASS, owned0, ошибок cleanup нет. Failed GUID diagnostics намеренно retained, TEMP_CLEANUP PASS не заявляется. PE14e14011a434fcb01c4650e932cf7b8301ec84f0f3efe5309804062476caad3c — saved build hash и пройденный post-case same-PE guard до verdict; не новый independent guest PE readback. |

Исходниковая причинная связь, отдельно от наблюдения: old2f bind вызывал fail
только для resetting/initializing/nav0. Здесь actual navigating/initializing/nav5;
clearHistorySession отзывал intent, но не завершал loading. Это объясняет
наблюдённый RED. Поведение позднего redirect пока выводится из SOURCE, не из
Stage25: до него тест не дошёл.

### Новый host: ровно два участка diff относительно Stage25

Current CPP SHA-256 `9308f42ec30605765188fb75eaba5d66aab7f8361ba00c7cb53765a897011251`;
baseline CPP `2f037dfc72aef95ce792718f0b47f8bd7b255801d7b7d3ab2c32be29e368560f`.
Header побайтно unchanged `f32a165b5737913a865fc5a830c1638f4fa9a12b1b8e584e7c5d4971047bc927`.
Test3 побайтно frozen Stage25: CPP6750c42b990c56c2727eff61b6b63838f954472952e6a0bf755a9a401bd9292e,
PY69db054da4a038fcd5e8c5f97f19de2868e2e9edc8991fad51088a8c074fdfbd,
PSe70ad62604a3fa516b085d607051383e2ac65ca201092cc06d498d57dc2bb0d0.

| SOURCE участок | Проверка / finding |
|---|---|
| bind445+ | interruptedHistory фиксируется как historyBusy&&initializing ДО clear. Прежний clear/invalidate/присвоение B сохранён; fail вызывается ПОСЛЕ присвоения, ДО refresh. Поэтому runtime callback видит новый account и уже отозванные proof/session/operation. fail обнуляет nav/response/completion/committed URL/nonce/bridge, делает unavailable; refresh отсекается ready/nonce guard. Нет eager GET, нового account owner или произвольного переноса proof. C0/H0. |
| admission1140+ | В idle отклоняются BF И redirected до begin, без смены generation/latch. select/accept/reset fences и permitted/navigating owner checks неизменны; действующий owned ordinary/fresh redirect остаётся в navigating и проверяется по sameID, fresh marker guards не ослаблены. После bind old nav0/idle, late redirect не может заново стать document owner. C0/H0. |
| Callers / reentrancy | First cookie bind происходит после ready/idle, поэтому не попадает под interruptedHistory и не добавляет first-load GET. AppMain authGeneration callback bindempty на ready также не вызывает новый fail. History callbacks сохраняют operation/session/generation fences; поздний Completed отсекается nav0/sameID, nativeFinish требует nav+completion, activation требует idle/committed response. Close/process paths не менялись. Runtime callback остаётся прежним синхронным callback; новой async границы или post-callback account overwrite нет. C0/H0. |

Direct download first nonredirect admission и существующий download fast path
не изменены. Download fast path не создаёт history owner, поэтому реальная
redirected-download chain теперь может быть отклонена idle veto: совместимость
таких цепочек остаётся ОТКРЫТОЙ, не объявляется полной parity. Сообщённый caller
audit directResponse/StreamingResponse/blob не равен runtime-доказательству всех
downloads. Спекулятивный chain-owner/URL exception не добавлялся и не требуется
для этого ограниченного SOURCE GO. Auth/payment/download full parity не приняты.

Ponytail: **Lean already. Ship.** Два локальных guard changes без новых полей,
зависимостей, browser framework или ослабления method/route/latch/session gates.
Безопасного обязательного удаления не найдено. Следующий допуск — unchanged
GREEN нового сценария + old30 (31 total, старые counts/deadlines/order), включая
first-load1GET, owned fresh302 и held reset account boundary. Успех пока НЕ
заявляется; full7groups/AppMain workflows/T103/T088/release остаются открытыми.

## Stage26: bounded oracle semantics review, не final runtime qualification

**C0/H1 у текущего notification oracle; HOLD на дальнейшее авторство до main
norm gate.** Прочитан только новый case prefix saved Stage26 плюс реальные
observer/finish/close/production request guard и plan3355+/quickstart1400+.
Полные31 receipts/portable suite этим разделом не квалифицируются; сообщённые
main old30 PASS и portable48/48 не переоцениваются. Исходники/нормы/VM/Git/tests
не менялись; добавлена только эта запись собственного report.

Факт prefix `t103-history26.KlJon8`: после public B bind state0,
UNAVAILABLE elapsed0, actual redirect Starting nav5; затем FAIL
account-boundary-http-before-reload, starts5/completions3/state0. Server после
drain показывает3 0 0 0 1 1. Нет terminal14/recovery evidence этого case.
URI вызвавшего notification не записан: нельзя называть его GET-login.

**H1 — observer не отличает попытку от отправки и вмешивается до product.**
CPP2415+ subscriber зарегистрирован раньше production; любой HTTP notification
вызывает finish. Finish343+ синхронно закрывает host/view; close946+ ставит
alive=false. Production subscriber2210+ начинает с alive guard и теперь может
выйти до Response403/остальных guards. Поэтому extra unexpected server request
реален, но причинно загрязнён fixture teardown. Это не доказательство обхода
production guard при невмешивающемся наблюдении. Ошибка oracle существовала
в прежнем SOURCE GO и здесь явно исправляется как вывод review, не замалчивается.

Отдельное SOURCE наблюдение: текущий request guard отвергает fresh/marker/BF/
selecting/accepting/resetting, но не содержит явного idle/unavailable unmarked
Document veto. После fail такой запрос сам по себе не удовлетворяет данным
условиям. Это основание проверить production, не утверждение точного URI или
единственной причины unexpected1; production review остаётся у Sagan.

Минимальный кандидат уточнения norm/oracle, БЕЗ внесения норм:

1. Разделить browser request notification/attempt и HTTP, фактически полученный
   synthetic server. Запрет «нет новой HTTP» означает zero additional server
   receives между bind и public recovery reload, а не отсутствие callbacks.
2. В новом case только после release настоящего302 допускается наблюдать
   попытку document request, вызванную late redirect; это НЕ разрешение отправки,
   authority или новой initial navigation. До release прежние ограничения
   сохраняются; old reset-account-boundary/default30 не ослабляются.
3. Observer сохраняет metadata/sticky unexpected observation, не вызывает finish,
   close, Cancel, Response и не берёт deferral внутри этого callback. На следующем
   UI timer/turn оценивается observation после возможности product обработать
   событие; очередь UI сама по себе не доказывает отсутствие HTTP в сети.
   Для ожидаемой попытки проверять bounded route/method/context по actual args,
   не объявлять отсутствующий у WebResourceRequested NavigationId binding.
4. Решающий network oracle остаётся sealed server counts после drain/join:
   строго4 0 0 0 0 1 вместе с independently real A/C/held-list/recovery GET и
   единственным POST-B. Login/unexpected/non-GET extra не разрешаются; отсутствие
   ResponseReceived либо наличие synthetic403 само по себе не доказывает zeroHTTP.
5. Реальные same-ID IsRedirected→OperationCanceled14 без fixture Cancel,
   unavailable/B/no auth-cookie-bridge-activation/loading resurrection до recovery,
   затем public reload/ordinary GET/latch/reset/ready/B/bridge4 остаются обязательны.
   Server marker/early cancel/error page не заменяют этот late class. Сроки,
   counts, profile/source/PE/runtime/cleanup guards неизменны.

Такой scoped semantic correction устраняет ложный немедленный FAIL, но не
превращает Stage26 в PASS и не оправдывает фактический extra HTTP. После main
norm gate нужны отдельный SOURCE новых bytes и новый frozen runtime; Stage26
сохранить FAIL. Full runtime qualification/production fix/parity этим review
не одобряются; никаких download-chain исключений отсюда не следует.

## Stage26 saved qualification + measurement correction: bounded author gate

**C0/H0 — AUTHOR GO только для диагностической поправки existing test3 по
новым plan/quickstart.** Не SOURCE/runtime/production GO. Это plan-level
исправление измерения существующей T103/group5, не business/spec ambiguity:
попытка браузера не разрешает отправку, старый session не получает authority.
Skills speckit-checklist/analyze прочитаны полностью; disabled hooks проверены,
Git-dependent prerequisite/VM/build/tests не запускались. Ни нового checklist,
ни markers/tasks/issues/норм не изменено; только этот append собственного report.

Точные текущие SHA норм:
plan `fcd797ecae009dc0d816e35b3c9dbb69c7cda1acacf4f39fa0c2ecaeb45795ff`;
quickstart `f0d3a8236184e6f33a8abb01e4feeed91f3775a39aa44dc6ca5fa89a49b72b8a`.
Spec04f708…/bridge2d31f0…/constitutiond28f83…/tasks80fc15… unchanged от gate3150.
Свежие totals: checklist198files/31checkboxfiles/477checked/0unchecked;
tasks120/93/27, T103 OPEN. Эти totals — состояние требований, не приёмка продукта.

| Requirements/checklist/analyze scoped coverage | Вывод |
|---|---|
| FR-002/005/006, spec Session2026-10-22, bridge T103 | Не меняются owner/session/route/latch/nonce или полезная история; дополнительный HTTP всё ещё запрещён. User choice не нужен, новый task не нужен; existing T103/group5 покрывает поправку. |
| Clarity/measurability, requirements CHK005/007/009/013/020 | Before-release zero attempt сохранён. После release наблюдается лишь exact known same-origin GET-login Document; metadata категории вместо URL/query/headers/cookie. Неизвестная категория не расширяет допустимую ветку и не считается доказанным login. |
| Security CHK001/003/007, constitution III/VI | Existing ранний observer только наблюдает эту ветку и возвращает управление product; без finish/close/Cancel/Response/deferral/нового subscriber. Native same-ID Starting/terminal14 и B/no authority/loading resurrection остаются обязательными, не заменяются notification/marker. |
| Negative + recovery | Actual server marker даёт явный FAIL; sealed counts4 0 0 0 0 1 после drain обязательны. Public reload/новые nav+generation/ordinary latch/reset/ready/B/bridge4 сохранены, old reset-account fence/default30 не ослабляются. |

Обязательные детали минимального test construction для последующего SOURCE:
marker публикуется только из real server handler после учёта actual unexpected
GET, вне counts lock, ДО записи response headers/body; ошибка записи даёт
server error/nonzero, не подавляется. Собственный fresh GUID, sticky marker,
только известная категория метода/пути без raw данных. Native проверяет его
до terminal acceptance/recovery/final verdict; отсутствие marker НЕ proof
zeroHTTP: публикация и UI poll могут разойтись во времени, final drain/counts
закрывает этот остаток. Никакого дополнительного sleep/deadline/handshake не нужно.
Для exact request category использовать actual args/full synthetic target
сравнение без вывода URI; не выдумывать NavigationId в WebResourceRequested.
Допустимая attempt-ветка должна выйти до старого duplicate-request/early-finish
кода. Browser может вообще не выдать Requested после отмены: для GREEN его
наличие не заменяет mandatory late Starting/terminal и не обязано создаваться
fixture. Для diagnostic RED перед production fix нужны actual origin/context
и server marker; одно уведомление, другой category или только итоговый mismatch
не принимаются как доказательство предполагаемого missing network veto.

### Сохранённый Stage26: квалификация с границей oracle

Прочитаны все1283 строки log, result, полные wrappers и retained native runner
(byte-identical Stage25); independently structured audit сверил requested31,
native verdict31 и runner verdict31 без omissions/duplicates: новый FAIL первым,
затем exact old30 Stage24 order, все30 PASS. BUILD PASS; source216 pre/staged/post,
input5/runtime3 stable/owned0/exit1/elapsed219334ms; 5 retained staged bytes и
inputs независимо совпали, runtime3 совпадает Stage24. Maxcase7673ms<35s,
31 browser exit PASS/31 server exit0. Failed own GUID diagnostics retained,
общий TEMP_CLEANUP PASS/новый guest PE readback не заявляются. PE saved build+
post-case guards `6fbc036631e1d8431c3d4350f092588ab90e9047925f04353d07d55e97612e0d`.

Новый case: unavailableelapsed0/B/noauthority, actual redirected nav5, затем
account-boundary-http-before-reload starts5/completions3; sealed3 0 0 0 1 1.
Остаётся FAIL с H1 observer/teardown из раздела3311; raw URI/terminal14/recovery
и невмешивающаяся причинность extra HTTP не доказаны. Old30 действительны в
своём scope: initial2001GET/bridge+wire, owned302/login editable/noauthority,
allGET+quarantine7phases, cancel retention, held competitors3 и terminal no-early
activation, stale reset/accountB recovery. Это не общий green31 или full7groups.
Portable retained ctest log содержит48/48 PASS47.51s; его source/build provenance
здесь повторно не квалифицируется и native defect им не закрывается.

Независимые saved SHA: source `4a5ab3bbf4257f63883ddbf6351ded0296f1ad32e8e9abe8c1278ef6a9c7eb08`;
prior `b89f4900d35997332c57d2fbfdbfa678a278df0f2bcc59e7d7b4e8cfdf8cedde`;
result `cf5ec63f41d8f3be4d5ff393c124b562f3dd1fa4c1686cb232f2d7ad17925fd6`;
log `144d6786943e81af2bfa6aeb38931455671d9e8f57095b0c97feb93948987344`;
err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
Run-History `d8f8d7de5a4d14b382776813727ecc23d98a199bda93a16ce9e70dc0d1a48f88`;
Invoke-Runner `03f3512f6c0fe489ad339a67ef864dfd6ea257b96c685902036733d77d070fba`.
Current host9308/test6750/69db/e70a непосредственно повторно хешированы unchanged.

Следующий шаг — только test authoring → frozen SOURCE → diagnostic RED на9308.
Network veto не одобрен до доказанного actual category/context и marker;
GREEN+old30 потребуются после отдельного host SOURCE. Stage26 не переписывать.

## Diagnostic test3 after Stage26: bounded SOURCE gate

**C0/H0 — limited SOURCE GO к одному diagnostic RED на unchanged host9308.**
Code-reviewer: полностью прочитан новый CPP/PY diff против frozen Stage26 и
релевантный observer/phase/finish/server/runner поток. Нормы AUTHOR GO unchanged:
planfcd797ecae009dc0d816e35b3c9dbb69c7cda1acacf4f39fa0c2ecaeb45795ff /
quickf0d3a8236184e6f33a8abb01e4feeed91f3775a39aa44dc6ca5fa89a49b72b8a.
VM/build/tests/syntax/Git reviewer не запускал; только этот report append.

Точные независимо проверенные SHA-256:

- CPP `5750b682313dd3419c6e7a9908a0770e7cdc4d43a079821481ffa5dfdef69267`;
- PY `76ec96381003872c96b59e35d7b4f21092f5ca3c8dfd68d61db00e57f7969a94`;
- PS `e70ad62604a3fa516b085d607051383e2ac65ca201092cc06d498d57dc2bb0d0`, побайтно Stage26;
- host `9308f42ec30605765188fb75eaba5d66aab7f8361ba00c7cb53765a897011251`, побайтно Stage26;
- baseline CPP6750c42b990c56c2727eff61b6b63838f954472952e6a0bf755a9a401bd9292e /
  PY69db054da4a038fcd5e8c5f97f19de2868e2e9edc8991fad51088a8c074fdfbd.

| Scoped SOURCE проверка | Результат |
|---|---|
| Attempt observer | Только новый case после release допускает максимум одну actual same-origin exact origin+loginNext GET Document попытку. Лог — bool origin, finite path/method class и context number, без raw URI/query/headers/cookie. Return происходит ДО finish и старого duplicate-request guard; нет Cancel/Response/close/deferral/нового subscriber. Before-release и old reset-account fence unchanged. |
| Actual server evidence | Marker только из do_GET: после реального приёма/учёта unexpected GET (или запрещённого marked held-list), вне counts lock, перед page()/headers. Содержимое лишь GET+finite path category; native использует sticky existence собственного GUID. Не появляется fabricated HTTP/response или новое разрешение сети. |
| Marker write failure | write_text не обёрнут в suppress/catch: ошибка выходит из handler, штатный ThreadingHTTPServer пишет traceback в redirected server.err. Сам сервер при handler exception не обязан иметь nonzero exit; unchanged runner отдельно требует server.err Length0 ПОСЛЕ server exit/join и чтения final counts. Поэтому failure записи не даёт ложный PASS даже без marker. Это SOURCE вывод, не fault-injection runtime. |
| Polls / остаточная гонка | Проверки в checkRedirectHeld, Completed перед terminal acceptance, recovery check и общем finish покрывают разные переходы. Повтор harmless, обязательного удаления нет. Late публикация после последнего poll всё ещё закрыта strict sealed counts4 0 0 0 0 1; marker absence/Response403 не объявляются proof zeroHTTP. |
| Retention | Старые30/default23/assertions и same-ID redirect/terminal14/B/noauthority/reload-ready-bridge4 неизменны. Runner byte-identical: counts/deadlines/profile/PE/server-drain/error/owned cleanup не ослаблены. Новая ветка не устанавливает native stage/proof/latch/nonce/ACK. |

Точный origin/context/class runtime всё ещё неизвестен. Данный SOURCE GO не
обещает RED именно server-marker reason: если actual category отличается,
немедленный diagnostic FAIL не доказывает missing network veto, расширять
ветку без review нельзя. Для корневой правки нужны safe actual attempt metadata
и marker реального HTTP при невмешивающемся observer; compile/startup/counts-only
failure недостаточен. Production edits/full31 GREEN/T103/release не одобрены.

## Stage27 diagnostic RED + host9d5e: bounded evidence/SOURCE gate

**Meaningful functional RED подтверждён, но НЕ clean runtime/teardown.
Host SOURCE C0/H0 — limited GO к unchanged newcase + exact old30 Stage26
relative order, одному full31 frozen build/run.** Code-reviewer: прочитаны
полные110 строк saved log, result и wrappers; точный one-line diff/current
bind/fail/begin/Starting/request paths. Нового requirements цикла нет.
VM/build/tests/Git/code/нормы reviewer не менял; только этот append.

Stage27 `t103-history27-bf6ad9`: independently retained source/input guards:
source216 `f552db6ae9622fb731d96e60a8f50a0d91eb67b1ee601cdb176c306b02a8c4bb`,
prior216 `4a5ab3bbf4257f63883ddbf6351ded0296f1ad32e8e9abe8c1278ef6a9c7eb08`
побайтно Stage26. Все5 retained staged files и input5 совпали; runtime3 в
receipt совпадает Stage26, pre/staged/post216/owned0/exit1/elapsed81205ms.
Wrapper post source/input/runtime guards реально стоят до NATIVE_RUN_FAILED.
Reviewer не перечитывал216 guest files/DLL. Case5152ms<35s, outer<600s,
run.err0; own failed GUID diagnostics retained, не TEMP_CLEANUP PASS.

| Evidence | Вывод и предел |
|---|---|
| Actual class / causality | BUILD PASS; AGET/POST-B/CGET bridge3, held unmarked nav5→publicB→unavailableelapsed0. Затем actual same-ID redirected nav5 и Requested same_origin1/pathlogin/methodGET/context1. Exact safe-target/context ветка frozen5750 возвращает управление без finish/Cancel/Response. После неё explicit FAIL held-redirect-server-received-unexpected-get; serverexit0/sealed3 0 0 0 1 1. Marker создаётся только real server handler до ответа; extra HTTP уже был принят ДО FAIL/close, прежняя Stage26 teardown-помеха не объясняет этот transfer. |
| Independent readback boundary | Main дополнительно сообщил readonly guest marker GET login/server.err0 и PE729f… machine8664 match. Отдельного сохранённого readback receipt в inspected bundle пока нет: это main-reported confirmation, не собственный guest readback reviewer. Printed reason+frozen marker writer+sealed counts уже дают meaningful functional RED, не лишь attempted notification. |
| Crash — не скрывать | После printed functional FAIL: FIXTURE_EXIT=-1073741819=0xC0000005. Нет BROWSER_EXITED PASS/штатного terminal14/recovery. Причина AV и принадлежность fixture/product не доказаны. owned0 не равен clean shutdown; функциональный RED не аннулируется более поздним crash, но clean error/teardown acceptance остаётся открытой. |

Saved SHA-256 result `dfdc93d8677132b46d33715f8be38000aaa3003833f1abca75ee5ac95205b0b7`;
log `792412f0c13a5c96aa06e2f409dbdf5f4032e4b5c4161f17e78a798cf883de19`;
err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
Run-History `72e97a14a7640159d46038a80af5f3a326cb221586c6e733a06cb7f3d6504f5b`;
Invoke-Runner `e964c39160bc0345881ddbf97f05aaaffb4ceb0d095e82dc8691aeeb5e7d18bd`.
PE build/post-case guard `729f327ca1303696c50d2412b4fb4b916bbfe5e14f553ced0ec87b68cd871a69`;
это квалификация saved guard, не новое чтение PE reviewer.

Host current CPP `9d5ee17226cbe4e08d49dd17d3921d03c0706950d55029b2d529ec0f74716a3d`;
baseline `9308f42ec30605765188fb75eaba5d66aab7f8361ba00c7cb53765a897011251`.
Полный diff — только OR-disjunct unavailable&&navigationId0 в существующем
Document403 veto (2228). Headerf32a/test5750/76ec/e70a independently hashed
и побайтно unchanged Stage27; counts/defaults/deadlines/observer неизменны.

SOURCE C0/H0: fail обнуляет navigationId ДО unavailable; bind присваивает B ДО
fail и отзывает прежние history/session/nonce/latch. Late unmarked own-origin
Document request теперь получает existing synthetic403 до network, без begin,
новых permissions/URL exception/authority. Accepted initial/reload/owned redirect
проходит begin, который ставит nonzero nav и initializing ДО request; ready
download fast path не удовлетворяет unavailable, resource filter остаётся Document.
Прежние route/method/fresh/BF/reset/selected-ID/terminal/latch guards неизменны.
Новых callbacks/fields/framework нет; обязательного упрощения не найдено.

Это не universal stale-navigation fix: callback exception с unavailable/nonzero
nav и прочие branches данным disjunct не закрываются. Redirected-download
compatibility и AV остаются открытыми; никакой speculative chain-owner не нужен.
Runtime эффект403 (включая mandatory same-ID terminal14), recovery/B/bridge4,
strict4 0 0 0 0 1 и old30 ещё должны быть доказаны unchanged GREEN. Stage28
bundle/run этим SOURCE не квалифицируются; T103/full7groups/AppMain/release OPEN.

## Stage28: independent saved-runtime qualification full31

**C0/H0 — bounded runtime GO для frozen full31, не full T103/product GO.**
Прочитаны все1295 строк run.log, result.json, оба wrapper, run.cmd и frozen
runner; независимо сверены requested/native/runner order31/31 без omissions
или duplicates, все31 native PASS/runner True/browser-exited PASS/fixture0/server0.
Это сохранённые доказательства, без нового VM/build/test/Git. Единственная
запись reviewer — этот append; нормы/код/checklists/tasks не менялись.

Bundle `t103-history28-76cda1`: source216
`4e7ddbeb128a20a72a540675ca9eeab4d09fdea78f7a12bae07ec3dc8faaba21`,
prior `f552db6ae9622fb731d96e60a8f50a0d91eb67b1ee601cdb176c306b02a8c4bb`
побайтно Stage27. Все5 retained staged files соответствуют source manifest;
input5 соответствуют receipt; test3 побайтно Stage27 (5750/76ec/e70a),
host9d5e/headerf32a совпадают одобренным. Runtime3 receipt совпадает Stage26.
Run-History vsStage26 меняет ТОЛЬКО frozen/prior hash pins, Invoke-Runner
побайтно unchanged; полный31 order ровно Stage26, новыйcase первый/old30 retained.
Receipt pre/staged/post216, exit0, owned0,230612ms; run.err0. Независимая
структурная сверка: maxcase7687ms<35s, новый2525ms; outer<600s. Server-ready
1.5s и остальные frozen runner limits не расширены. TEMP_CLEANUP PASS после31,
per-case hash guards выполнены до True; после ownGUID cleanup нового PE readback нет.

| Наблюдение | Квалификация |
|---|---|
| Новый late redirect | AGET/POST/C bridge3; unmarked nav5 held→publicB→unavailable0ms/noauthority. Реальный same-ID redirected Starting5, уведомление same_origin1/login/GET/context1, затем Completed5 success0/error14 и FIXTURE_CANCEL0. Само уведомление НЕ networktransfer: sealed counts4 0 0 0 0 1 при serverexit0 и empty-server.err predicate исключают фактический GETlogin/unexpectedGET. |
| Реальное восстановление | Public reload nav6, actualGET200/tag/gen6, ContentLoading entry11, singleton/readiness. Frozen PASS predicates проверяют B, unchanged revoked boundary до terminal, no loading resurrection/earlyauthority, ordinary nonce/bootstrap bridge3→4, auth/cookie3→4, signedout0/invalidation0, nooldForward. Нет fixture Cancel/Response/proof fabrication. |
| Old30 retention | initial200 starts1/completions1/auth1/strict1GET сохранён. history-post/host-same-url/host-quarantine имеют actual7 phases ids5/6/8/10/12/10/12, bridge7 и strict-range counts6 0 0 0 0 1; allGET history полезна. Оба held scenarios PASS: pending3 actual cancel14, terminal noearlyactivation, затем реальный useful BF. Остальные auth/cancel/same-document и fresh-login302200 проходят без изменения test3/oracles. |
| Завершение | Все31 BROWSER_EXITED PASS, fixture/server exit0 и ownGUID cleanup PASS. Stage27 AV не повторился на этом успешном пути; причина прежнего AV и безопасность аварийного FAIL/teardown этим НЕ доказаны/не закрыты. |

Saved SHA-256 result
`7c46ac9a8844f19ae0e4938154007c6fc316b6f9b4340f438c87301f75a51715`;
log `21f466ae1301cabd066da317c1412e8498c93abb56430c0bb6345cd30e6ad412`;
err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`;
Run-History `10c4c88cb56d9037e4991272035edb0b857acdc3998388d5e650f13cfbcf2458`;
Invoke `03f3512f6c0fe489ad339a67ef864dfd6ea257b96c685902036733d77d070fba`.
PE build/per-case saved guards:
`53075101e0324431f14b6f6c49f50f496a8554c471c7d9f7f1ea2ef849dcb49e`.
Reviewer не читал заново216 guestfiles/DLL/PE: эти pre/post проверки квалифицированы
по frozen wrapper+receipt+успешному control flow, не как собственный guest readback.
Дополнительно сохранён portable CTest48/48/44.35s; Debug/cache-origin/365MB cleanup
сообщены main, отдельно здесь не переисполнялись/не квалифицировались.
AppBuild5 ещё выполнялся по сообщению main и НЕ входит в данный GO; нет выводов
об установке, реальном аккаунте, audio/device, full7groups, T103 closure или выпуске.

### AppBuild5: same-source compile/link qualification после Stage28

**C0/H0 — сохранённый real-app compile/link Release x64 принят в узких границах.**
Bundle `t103-app-build5.LKEfQe`: полностью прочитаны Build-App.ps1/result/build.log;
code-reviewer, только own report append, без VM/build/tests/Git/других правок.
Независимая сверка: source216 побайтно Stage28 (`4e7ddbeb128a20a72a540675ca9eeab4d09fdea78f7a12bae07ec3dc8faaba21`),
pre/post216/build0/no failure/owned0/elapsed108207ms<600s/err0. Runtime3 равен
Stage28 и AppBuild4, provenance ebe9b371… равен AppBuild4; Build-App diff ровно
одна замена source pin, остальные guards побайтно сохранены.

Полный log: genuine pinned AEC verified846fe90a289f58b7c9303a635142aa2c7caa93e5,
компиляция AppMain.cpp/CabinetWindow.cpp/WebView2Host.cpp и link GrafWindowsApp.exe.
Wrapper проверяет свежесть EXE+hostobj относительно before-build UTC, MZ/PE8664,
source/runtime/provenance/runner postguards. EXE по сохранённому parse/hash:
`3fa18a6122ab601351ce26686f3e9fdfc3a8f68751b2fa207502cc39a057a179`,
3390976bytes, written2026-10-22T02:52:43.1862422Z; hostobj
`f12dc60859c6a0dda0f52f5625c427b3969d52e02231bbcb0f91fd2e2e2b8f3c`.
Нет собственного guest PE/object readback reviewer; AppMain/Cabinet compile
виден в log, отдельного freshness timestamp guard для этих2objects нет.
LTCG22/29650/reuse остальных и warningD9025 сохранены: НЕ clean/fullsolution/
warning-free. False restore/install/launch/device/app_network в receipt согласованы
с единственным Build действием wrapper; это не продуктовая runtime приёмка.

SHA-256 Build-App `68c39512fdf035bbf796e0888bddb95c5374ad77b8b50c7f3b54531722f85f51`;
result `e656cf7d921ecd9a71f46c940a661adc56a3c2dc7b6bf210b862fc0304a898a5`;
log `c65f159b564ebf9f754c178227f99d25354a8e5ff4a2f058adbe2b8481b3373e`;
err0 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
О первом PRL exit255 до создания файлов и отсутствии duplicate jobs сообщил main;
этот prelaunch эпизод не доказывается данным build bundle и не трактуется как buildFAIL.
CommonJS/browser PASS здесь не перепроверялись. Совместно со Stage28 приняты
два разных доказательства на одном source216: native synthetic full31 и real-app
compile/link; это НЕ app launch/install/package/audio/full7groups/T103/release GO.
Commit approval pending human по сообщению main; reviewer не делает commit и
не начинает следующую реализацию до checkpoint/integration order.

## T087/T083: current requirements gate перед protected local-open RED — 2026-10-22

**AUTHOR GO / C0 H0 — только существующий узкий RED→minimal fix**, не SOURCE
GO ещё не написанному diff и не implementation acceptance. Пользователь теперь
явно запросил этот срез независимо от pending commit approval; прежний hold
после Stage28/AppBuild5 не отменяет новый запрос. Commit/push остаются вне допуска.

На 2026-10-22T03:22:50Z read-only Git подтвердил branch
`codex/200-windows-followup`, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`; feature pointer и prerequisite
`--json --require-tasks --include-tasks` указывают на этот F200. Применены
speckit-implement/checklist/analyze как независимый preimplementation review,
не генерация новых требований. Extensions YAML разобран: активных hooks
before_implement, before/after_checklist и before/after_analyze — 0.

Полный ранее прочитанный набор checklist повторно проверен по отсортированным
именам относительно `checklists/` и SHA каждого файла: **198 files /31 checkbox
files /477 checked /0 unchecked**, canonical SHA
`6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
Все файлы byte-identical принятому inventory; новых неподтверждённых пунктов
или оснований менять markers не обнаружено. В частности security CHK007–009,
012–015/017–018, ux CHK019/020 сохраняют смысл качества требований, не runtime PASS.

Известные неизменные основания проверены по полным SHA, релевантные удалениям
разделы перечитаны непосредственно:

| Артефакт | SHA-256 |
|---|---|
| spec | `04f708f040e23fcca0f1e8d386c181421c5da2c81a37033155ad9f3a0536ed92` |
| plan | `fcd797ecae009dc0d816e35b3c9dbb69c7cda1acacf4f39fa0c2ecaeb45795ff` |
| tasks | `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f` |
| quickstart | `f0d3a8236184e6f33a8abb01e4feeed91f3775a39aa44dc6ca5fa89a49b72b8a` |
| constitution | `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859` |
| bridge contract | `2d31f0f9bd1548ca592561062788aa87a521cf8f9661bf320a7c9177cb456dc5` |
| protected-custody contract | `a13d0e693565c332e5ae286b3682b0318f19e8f5c02ffe88c00f52fc5d035490` |

Прочитаны active AGENTS, guidance index, codex-worktrees, spec-kit-flow,
product-gates, tracker-policy/github-issue-canon и применимые правила
release-and-validation; сверены PRD deletion/lifecycle и current status.
Это active high-risk-product slice (deletion/auth/custody), не tiny-code lane.

**Current analyze AFTER current tasks:** заново сопоставлены действующие
требования и существующие задачи на приведённом tasks SHA, а не перенесён
исторический analyze от сентября. Tasks: **120 unique /93 checked /27 open**.

| Требование и действующее основание | Владелец и scoped вывод |
|---|---|
| FR-002/006/013/022, bridge §8: native display capability и повторный допуск действия соответствуют текущей записи/состоянию | T087 + T083; `canOpen` не новое полномочие и не purge acknowledgement |
| Protected custody §7: durable delete intent запрещает новые reads/upload/playback до фактического завершения очистки | T087; делегирование существующему `deletionBlocks(item)` устраняет расходящийся предикат, не создаёт новый lifecycle |
| Immutable local identity, текущие owner/workspace и запрет чужого действия | T083/T087; localRecordingId не обязан совпадать с directoryId; различать deletion target и сохранить прежние native guards |
| Constitution IV/VI, FR-021, quickstart recovery/deletion | Те же owners; test-first на искусственных данных, затем проверка точного diff/результата, без обещания полной очистки либо live acceptance |

Контекст источников проверен: WebView2Host.cpp:1473–1488 сравнивает operation
targetId с localRecordingId; DesktopUploadQueueService.cpp:351–355 сопоставляет
ownOrigin с directoryId, meeting с meetingId, а :1020–1026 уже предоставляет
owner/workspace/phase-aware `deletionBlocks`. NativeCapture.h:1517–1532 использует
тот же предикат перед playback. Это несогласованность реализации, не конфликт
норм и не доказанная выдача звука: исполнитель имеет собственный запрет.
Gate разрешает RED этого ID mismatch и минимальный reuse, не изменение
server-origin policy, формата ledger, nonce/session либо остальных guards.

Live read-only `gh issue view` подтвердил **T087 → #7230 OPEN** и
**T083 → #6640 OPEN**, совпадение task ID/feature:200/priority:P1 и областей
deletion/contract; оба gate:pr-blocker, type:hardening. Персональные assignees
обоих пусты: owner здесь означает существующую задачу/issue, не назначенного
человека. Новая issue/задача и повторная синхронизация не нужны для неизменного
объёма. Разделение общей Web/ поверхности остаётся обязанностью main.

Неразрешённых **CRITICAL=0/HIGH=0** по качеству требований этого среза;
constitution conflicts=0, blocking clarifications=0, unmapped scoped work=0.
Открытые 27 implementation tasks не объявлены закрытыми findings и не приняты
этим GO. Требования не изменены, поэтому новый clarify/plan cycle не нужен.
Существующие последующие SOURCE/RED/GREEN/validation остаются обязательными;
этот gate не принимает весь T087/T083, Stage27 teardown AV, T103, оборудование,
реальный сервер, установленное приложение, commit либо release. Изменён только
этот отчёт; checklist markers, продукт, тесты, нормы, tasks, Git и VM не менялись.

## T087/T083: независимая portable RED/GREEN qualification — 2026-10-22

**Scoped evidence PASS / C0 H0**, не full-product GO. Применён code-reviewer;
прочитаны сохранённые configure/baseline-build/baseline-test/red-build/red-test/
green-build/green-test в `t087-open-permission.SvZUfa`, actual test helper,
public callers и прежний host из Stage28. Ничего не запускалось повторно.

| Сохранённая проверка | Непосредственное наблюдение |
|---|---|
| Baseline | CalendarJoinHostTests 1/1 PASS, 1.09с |
| RED | Тест перекомпилирован/связан; CTest 0/1, Subprocess aborted на CalendarJoinHostTests.cpp:340 — public `localRecordingActionAllowed("open", "synthetic-row-0") == allowed`, 0.64с; это functional assertion, не compile/dependency failure |
| GREEN | Host перекомпилирован; полный журнал содержит ровно48 уникальных последовательных результатов 1..48, все PASS, 43.80с; CalendarJoinHostTests 1.07с |

Configure указывает AppleClang21 и отдельный `/tmp/graf-f200-open-permission.ALROKj`;
существующий CMakeCache read-only подтверждает Debug и active `apps/windows`
как home. В тесте assertions включены явно даже при NDEBUG; production host
связан через существующий common target, не копию policy. Это Mac portable
ветвь, не Windows/COM execution. Десять новых вариантов вызываются из main:
queued/sending/resolving/accepted/verified блокируют ownOrigin(directoryId),
rejected разрешает; wrong local-ID target, wrong meeting target, foreign actor
и foreign workspace не блокируют строку. Для первых восьми local ID отличен
от directory ID. Ожидания заданы явным массивом; отдельно проверяются
`deletionBlocks`, public open и сериализованное `rows[0].canOpen` с точным id.
Старые active-session/incomplete/epoch/account/document/close guards и проверка
возврата CustodyOwnedMemory retained. Это value snapshot через test peer, не
доказательство durable deletion persistence, actual playback или UI/native bridge.

Точные current и сохранённые source bytes совпали:
- host `ab7f676828418e6a688e9b6cab7138b7f85502d51096bd9ae8bf6febeb72e04f`;
- test `120f268d0b0573e1bc4a2e6e6e9c91488213c8471f42db347ed07429e3c65224`.

Saved source manifest SHA `225d3f83713b8cd8c0656c17c9b8cc88a95a107bc76e15f4cfaf2ff01115f74f`:
216 unique entries, все current files совпали; против prior manifest
`4e7ddbeb128a20a72a540675ca9eeab4d09fdea78f7a12bae07ec3dc8faaba21`
изменены ровно host и CalendarJoinHostTests. Host diff против retained Stage28
ровно заменяет прежний none_of на `!protectedLocalValue_->deletionBlocks(item)`.
Portable bundle сохраняет GREEN source copies и журналы, но не отдельные
sealed binary/source receipts каждого portable этапа: их exact pre/post identity
не приписывается задним числом. Meaningful RED согласуется с прочитанным old
predicate и первым новым blocking case; последующие nine RED cases до abort
не достигнуты. Их успешный проход принят по full GREEN и вызову loop в source.

SHA-256 baseline-test `7fa5fff10a80d89db5732a51bf1f39b0c2e426ad02cf057f959fa3c46b7bece3`;
red-test `12068fd3ff5620283421748ad678a054a70e607a9377eb7bb0cafa536b3e0d37`;
green-test `adf8cf482d96e0232a3633addf9cc281820e9a8827b38bc7fd87394599435cfe`.
Windows App Release/x64 lane main ещё не квалифицируется этим отчётом.
Package31da на source4e7 — прежний пакет, НЕ post-fix artifact. T087/T083,
markers/tasks, установку/полный продукт не закрывать. Изменён только этот отчёт;
нет VM/build/test/Git/product/norm writes и новых требований.

## T120 — focused technical requirements/checklist/analyze, 2026-10-22

**C0/H0/M0; AUTHOR GO к предусмотренному test-first RED.** Это независимый
допуск технического решения, не SOURCE/runtime acceptance и не закрытие T120.
Рабочая копия Documents/crisp-worktrees/200-windows-followup, HEAD
`b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`. Применены текущие
speckit-checklist и speckit-analyze; новые checklist/tasks/issue не создаются.
Scope после уточнения main: подробно все12 privacy-pause items; прочие пункты
сохраняют историческую оценку, а не получают новый несвязанный source audit.

### Проверка каждого пункта privacy-pause.md

| Пункт | Решение и текущая связь с нормами |
| --- | --- |
| CHK001 | Checked: spec Session2026-10-22 и research T120 связывают FR-002/009 с точным Mac c8d67c… и снимком9b286…; ранний logical CLOSE отделён от ADC/click/UI ACK. Новый owner choice не нужен. |
| CHK002 | Checked: desktop §3.1/4/8 сохраняет обязательный OPEN до Pause; T0 лишь значение будущего CLOSE, которое применяется после принятого Resume и сохраняется best-effort. Раннее получение T0 не закрывает OPEN заранее. |
| CHK003 | Checked: desktop §3.2/3/8, plan T120 сохраняют queued/in-flight/prefetch/timeline/partial suppression, старые epoch guards и неизменность committed pre-Pause prefix. B-prefix не разрешает вернуть старый acquisition. |
| CHK004 | Checked: same-stream worker обслуживает mailbox между пакетами после consumePacket/успешного ReleaseBuffer; fixed L и исходный deadline не ждут пустой FIFO; B задаёт замену остатка, не сумму потерь. |
| CHK005 | Checked: только проверенное stale q<L остаётся pending; identity/integrity/receipt/arithmetic/native failures отвергаются. Pending/rejected остаётся paused/OPEN, Stop доступен; rejected seq не становится принятым от позднего COM result. |
| CHK006 | Checked: prefix применяется до normalizer после исходных проверок; system/reference, PTS/count, format/route/AEC и прежняя fail-closed policy сохранены. Нет wall-clock padding, epsilon subtraction, raw fallback, max-подгонки B или clock repair. |
| CHK007 | Checked: защищённый OPEN/CLOSE по-прежнему зависит от T116; mailbox/receipt не становится новым plaintext journal или storage owner. |
| CHK008 | Checked: data-model §1 и desktop §3.6 сохраняют logical v5/ISO8601/optional OPEN/legacy. Floor-to-ms обоих концов не меняет схему, не вычисляет UTC из QPC и не добавляет скрытый max/ceil. Недопустимый receipt отвергается. |
| CHK009 | Checked: полный manifest≤64KiB остаётся отдельным metadata пределом; остальные audio/queue/job/cache/root budgets не меняются. L/B/packet-end arithmetic и overflow явно проверяемы, а не превращены в новый допуск часов. |
| CHK010 | Checked: ошибка/вместимость OPEN по-прежнему не принимает Pause, не режет историю и не ослабляет validator. Новый bounded Resume wait не подменяет обязательный storage ACK OPEN. |
| CHK011 | Checked: один worker/mailbox, seq+expected epoch, READY после установки B, apply под указанным admission fence; accepted после commit необратим. Retry получает новый seq/T0/L; исключение/Stop освобождают ожидание, late completion не меняет новую сессию. UI/callback storage I/O не добавлен. |
| CHK012 | Checked: plan/quickstart различают требования, RED/SOURCE, synthetic/native, installed/hardware/release. Предыдущая metadata measurement RED и unread RED не объявлены PASS; T116/T120 остаются открытыми. |

### Focused analyze: L, CLOSE и согласованность

Для F>0, Q≥0 положим x=Q·10^7/F и d=10^7/F. При достоверной
коррелированной паре консервативная граница для не более позднего observation
с межпоточной неоднозначностью одного QPC tick и единицей квантования —
floor(x)+ceil(d)+1. Принятое L=floor(x)+ceil(d)+2 строго выше неё.
Это математическая оценка при соблюдении API correlation, не доказательство
достоверности любой старой пары только по S_OK. Microsoft отдельно описывает
[межпоточный QPC tick и независимость от UTC](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps)
и [коррелированную p/q пару, её единицы и S_OK/S_FALSE](https://learn.microsoft.com/en-us/windows/win32/api/audioclient/nf-audioclient-iaudioclock-getposition).
План требует exact S_OK, fixed same-client frequency/format, nondecreasing p,
checked B≥releasedEnd и q≤floor(current QPC-after). Он не заменяет эти проверки
ожиданием. QPF F и частота device clock для B — разные величины.

Обе составляющие T0 предшествуют первому before и неизменному L; значит
достоверный witness≥L и исключённый текущий frame B не позволяют выпустить
backlog до T0. Старые acquisition/dispatcher/timeline guards обязательны.
Неподтверждённая свежесть не двигает T0/L/seq/исходный1s; новый before110ms
не отвергает сам по себе допустимый witness106.5ms после фиксированного fence.
Для normative RED p5112@48k даёт B5113: unread4800..5279 имеет313 нулевых
prefix frames и167 возможных suffix frames, а не prefix length0. CLOSE105ms,
не110ms/UI ACK. Дополнительная тишина T0→B допустима; metadata не обещает
физическую PCM границу. Ранний T0 совместим с прежним «CLOSE после успешного
Resume»: получение отметки и принятие/запись CLOSE — разные события.

Старые desktop §3.1–7, data-model §1, план T120/T116 и конституция I/II/III/VI/VII
не конфликтуют с уточнением. Изначальный1s ограничивает admission, не обещает
прервать COM/mutex. Предписанные integer-edge/overflow, stale-only pending,
producer/timeout, same-epoch retry/late result, Stop/exception/commit и быстрые
OPEN/CLOSE проверки сохранены; новых требований этим review не добавлено.

### Снимок, владельцы и предел допуска

Все198 checklist files побайтово совпадают с ранее оценённым baseline:
manifest SHA `6aaf78544635814de7c4feacc8f153eee2876226b9702bf70b0e16bfb4f351b2`.
31 marker-bearing file, всего477 checked/0 unchecked, включая privacy12/0.
Markers не менялись; unrelated source reports не перечитывались заново и не
принимают это решение или будущую реализацию. Tasks неизменны:120/93/27;
live read-only GitHub подтвердил существующий T120 **#7590 OPEN**, P0/security/
pr-blocker; prerequisite T116/#7444 не подменяется новой задачей.

SHA-256 проверены повторно перед записью:
- spec `69e8b6cadae116cb8b59684738583e64d953c4243e9020653390dc9695befe9f`;
- plan `1afadff31435700bcbb599ee9293c0b2a350d59a1e78869d827cd2067ae087b6`;
- desktop contract `f4998b06d753850335727fad2b99e1cd1b9689f23a978451ef94af0c6a5aae9c`;
- quickstart `a570a94724f9023ed75bd7f8c5430efb01f54b9307e8642519a7925be50531a4`;
- research `43e612d7a73108c9a6b4b468c2746fd22d9949d825ad698400e6c69f8f65b2a2`;
- tasks `80fc15cd25570d9567d39dd9bc4a8815a620bed2d34cf220d80d94cb2f0e024f`;
- constitution `d28f8312a88fe4b32d5f5f1aa2f76a5c7eaf47fcd9025ffd27ea8cc61b43d859`.

Source manifest `225d3f83713b8cd8c0656c17c9b8cc88a95a107bc76e15f4cfaf2ff01115f74f`:
216 unique entries сверены с current files, mismatches0. Runtime source не
менялся; сообщённые main baseline13 tests здесь не запускались/не квалифицировались.
9b286… — pinned historical comparison, не утверждение о текущем origin/master;
main сообщил новый eb929969fd9323b7b6489d1d25c245562f2d7e7c и отдельно сверяет
Mac delta. Этот review не выдаёт непроверенную delta за unchanged runtime.

Открытых C/H/M требований в данном срезе нет. GO только к уже предусмотренному
RED→минимальному patch→SOURCE/runtime по T120, не к снятию прежнего unread RED
до исполнения. Ни новая реализация, ни T116/T120, installed capture, hardware
или release не приняты. Добавлен только этот раздел; нет product/norm/tasks/
checklist marker/Git/issue/VM/audio/build/test mutations.

## T120 fixed fence — independent saved portable evidence, 2026-10-22

**C0/H0/M0 в ограниченной квалификации сохранённых доказательств.** Прочитаны
полные baseline/configure/build/test, RED, первоначальный GREEN, edges/edges2
и завершённые full-build/full-test журналы из
`/Users/yshishenya/Documents/graf-f200-public458.po8CtB/t120-fixed-fence.C1JiH2`.
Применён code-reviewer в границах evidence review: construction/source review
worker и native fixture остаётся отдельному reviewer, не дублируется здесь.
Я не запускал команды сборки/тестов, VM или аудио; добавлен только этот раздел.

| Этап | Независимо наблюдаемое в сохранённых материалах |
| --- | --- |
| Baseline | Configure AppleClang21, отдельный /tmp/graf-f200-resume-fence.sbJXhq; common/core compilation+CaptureFaultStateTests link. Test log:13 rejected/retry/EOS/finalizer, late retry/Stop без late epoch commit, три ACK сценария. |
| Test-only RED | Build дошёл до link; test log падает на assert933 `resume_fixed_fence_must_accept_post_request_witness`. Точный assert есть в retained RedCaptureFaultStateTests.cpp; сохранённые baseline worker/header совпадают с baseline manifest. Это functional RED, не ошибка компиляции. |
| Первоначальный GREEN | Пересобраны worker и зависимые capture units/test; log даёт B5113, releases4/frames4/AEC4/EOS3/finalizer1/old_suppressed1; сохранены13 reject/retry, late и ACK. Это ещё не финальные17/7, не смешивать этапы. |
| Failed edges | edges-build.log сохраняет3 compile errors: несовместимое chrono time_point присваивание и два C++20 structured-binding capture при C++17/Werror. Ninja остановлен; этот этап НЕ PASS. |
| Исправленный edges2 | Build+link завершены; test log B5113 и17 reject/retry/EOS/finalizer,7 integer edges/fixed serial/EOS/finalizer, late retry/Stop/no late commit, accepted-after-deadline/Stop-after-commit/throwing-handler. |
| Полный portable | Прочитан завершённый log:48 отдельных Passed, IDs1..48 ровно по порядку,48 unique, без omissions/duplicates; terminal100%,0 failed;43.43s, max10.89s у CaptureFaultStateTests. Full-build завершает остальные targets этого же incremental build tree, не отдельная clean/full Windows solution. |

Проверены только assertion-to-log связи, не новая construction acceptance:
unread case действительно проверяет recording после post-request witness,
CLOSE wall/monotonic равны первоначальному receipt,2 clock calls, неизменный
system/PTS/pre-Pause prefix, B-dependent microphone suppression и возвращение
fresh microphone. Checkpoint fixture явно control-only, не protected-storage
proof. Integer loop имеет7 explicit expected fences, L−1→L и тот же serial;
guards loop17 проверяет paused/no CLOSE до retry, EOS/finalizer после него.
Debug cache при чтении: active apps/windows source, CMAKE_BUILD_TYPE=Debug,
flags -g без NDEBUG; compile failure log также фиксирует -std=c++17/Werror.
Ни реальные WASAPI calls, ни native AEC/hardware по portable PASS не заявляются.

Source scope подтверждён: baseline manifest
`225d3f83713b8cd8c0656c17c9b8cc88a95a107bc76e15f4cfaf2ff01115f74f`;
GREEN manifest `e4eaf4f5e16b02011059056327b17baa0ae328123dcfd3760cb8dfca5a54e244`.
Оба216 entries; изменены ровно4 paths, GREEN/current mismatches0:
- WasapiCaptureWorker.cpp `260dd44de8ab5f1dfeea0dc8333e4c49cd0db0037704f3af203d6b78b47ca062`;
- WasapiCaptureWorker.h `3b4f3351d676ffec85f2da4cc5e1dc78a0e10360a6b5acf7823551bc1d597bf3`;
- CaptureFaultStateTests.cpp `154fb83ed208ed6c73bbbe749a531b40f5fb1f2bca367e917008e51bbd02318d`;
- NativeCaptureStorageIntegrationTests.cpp `23ec47f80c52cb152af81f29d4657ae3f35b79d403371e037193a2012c0edb72`.

Baseline retained test SHA a3066e2ec5c2259e88fe3ba3ead49970e363e8750d5cff685210c3a41c5b25ad;
retained RED test b3ee62b96047f3042e61ede96033ff9bfcac1e967ca68176f8a914338cd0fd3d.
Они не выдаются за final154f. Отдельных сохранённых per-stage binary/exit
receipts в просмотренном portable наборе нет: численные exit0/134 сообщил main;
независимая опора здесь — actual assert/build/test logs и перечисленные
source snapshots/current match, не ретроспективное доказательство каждого
процесса/двоичного файла по SHA. CTest имеет явный terminal success.

SHA-256 сохранённых журналов:
- baseline-test `87cf37f3445bd73789b9543410cb5829fa5905e3557b38daaf9ba379b563fefb`;
- red-test `0f1c2b42bc035d81eee6b88cf0eb74d7808ee059ce502e9d8612d12a9f30b672`;
- green-test `34bf76a8891ef495ce3d2818f7cd4813750ac52251730ce2fe8cdc49523c0aa4`;
- failed edges-build `cd97e0dc6a7ff4817fa10961a58a86f961b9558405e7e4d581f6a7eed98bb672`;
- edges2-test `43a2602d6af18c5b333d29f1605de3be5437fc1d9378eec94c67965a67e2dbc7`;
- full-build `f4afa10d47185065a7e60b8c01899daafe34f30bfa721fbbcdd9fda78ce0b517`;
- completed full-test `7048aaa394029587d458beceb86b8994272c955803aa1279bef086b02f4c57fb`.

**Scoped portable evidence ACCEPTED**, включая meaningful RED и финальные48/48.
Не SOURCE GO worker, не Windows compile/app/installed runtime acceptance:
NativeCaptureStorageIntegrationTests добавляется CMake только при WIN32 и
в этих48 не исполнялся. Новый Build-App.ps1/копии для следующего lane не
квалифицировались. T120/T116, protected integration, аппаратная/релизная
приёмка и task/checklist markers не закрыты; failed edges stage сохранён.

## T120 — отдельная saved App Release/x64 compile/link qualification

**C0/H0/M0; scoped App compile/link evidence ACCEPTED**, не installed/app
functional acceptance. Portable48/48 из предыдущего раздела не пересчитывается.
В том же t120-fixed-fence.C1JiH2 прочитаны полный Build-App.ps1, result.json,
полный build.log и пустой build.err. Code-reviewer применён только к обвязке
и границам её доказательств, не повторяет worker construction review.

Receipt terminal=true, failure отсутствует, build=0,68471ms, prior216,
preflight216/postflight216, owned_processes0. Frozen manifest e4eaf4f5… точный,
current216 mismatch0, все4 retained source copies совпали; prior225d3f…
проверяется до копирования этих4 файлов в guest. Runner hash в receipt
побайтово совпал с сохранённым Build-App.ps1. Проверки runtime3 pre/post,
AEC provenance и runner выполняются после build до terminal receipt.

Журнал фиксирует genuine AEC source/license identity verified
`846fe90a289f58b7c9303a635142aa2c7caa93e5`, compilation AppMain/worker/
CaptureReasonMapping/controller и link GrafWindowsApp.exe. D9025 override
W1→W4 сохранён как warning, не скрыт. LTCG31/29649 functions показывает
incremental compile/link, НЕ clean/full solution. Wrapper требует свежие
worker object/EXE timestamps относительно начала, build exit0, compile/link/AEC
markers, PE MZ/PE/0x8664 и повторную сверку source/runtime/provenance/runner.

Captured EXE SHA `96be8bcfb72ab3a3f31e313d8ded8c950b139f178179650bb01bee31e097acee`,
3390464B, machine0x8664, written2026-10-22T04:02:42.4377459Z;
worker object `c50afe3bc54f1d5f3ac57fd497df9ce01ae164243d4c1b7f8defdfd10b08cad7`.
Это hashes из проверенной guest receipt, НЕ новый независимый PE readback.
AEC provenance `ebe9b371f9ef9ab8e78f45c607ab7a661235ad9396d4001e2079395b08aae0fe`.
Receipt сохраняет installed/launched/device_started/app_network/restore=false;
обвязка не устанавливает и не запускает приложение. owned0 — проверка процессов,
не заявление об удалении persistent guest build/source directories.

SHA-256 Build-App.ps1 `18217d3e9f2ba2c614612f17b0525a485a8a649d08793e40e30c2cdce168a096`;
result.json `7c6ac975a835492a58089032c66c9cede1685dd32a7c5aa8067f998e0c8a41bb`;
build.log `eb482a207956f37a80f18d615c8154ca893979bbb09457c748dd5d86d8499d1d`;
build.err empty, SHA e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.

Validate-Native.ps1 прочитан, но на момент проверки native-result.json ещё
отсутствовал; partial native-clock/storage logs НЕ принимаются за terminal
native PASS. Последующая Debug synthetic clock/generated-storage qualification
отдельная. Ни T120/T116, ни native/app functional/package/installed/hardware/
release gates этим разделом не закрыты. Изменён только этот отчёт; нет запуска
VM/build/test/audio, product/norm/tasks/checklist/Git/issue mutations.

## T120 — отдельная terminal native Debug evidence qualification

**C0/H0/M0; scoped native synthetic/generated-storage evidence ACCEPTED.**
Это последующее дополнение: ранее partial native logs не принимались;
теперь прочитаны terminal native-result.json и полные3 пары log/err в том же
t120-fixed-fence.C1JiH2. Portable48/48 и App Release/x64 из предыдущих разделов
остаются самостоятельными доказательствами, не новой общей приёмкой T120.

Receipt: terminal=true, failure отсутствует, Debug/x64, source216 pre/post,
manifest e4eaf4f5…, owned_processes0; device_audio_read/real_network/installed=false.
Runner/manifest SHA совпали с сохранёнными файлами; повторная текущая сверка
всех216 inputs дала matches=true. Прочитанная Validate-Native.ps1 собирает
ровно2 существующих target, требует fresh EXE timestamps, сохраняет hashes,
запускает точные два opt-in с прежними120s/300s и после их успеха проверяет
обязательные markers, source216, неизменные2 EXE и runner до terminal receipt.

| Отдельный шаг | Actual saved result |
| --- | --- |
| native-build | exit0/15666ms; журнал содержит worker/capture dependents, CaptureFaultStateTests.cpp и NativeCaptureStorageIntegrationTests.cpp compile+оба Debug EXE link. |
| native-clock --privacy-resume-clock | exit0/4458ms; B5113/unread2/releases4/frames4/AEC4/EOS3/finalizer1/old_suppressed1;17 reject/retry/EOS/finalizer;7 integer edges/fixed serial/EOS/finalizer; late retry/Stop/no late epoch commit и все3 ACK markers. |
| native-storage --protected-privacy-flow | exit0/63844ms; case0 start→frames_3000→finalized→cold_read→cold_read_verified→done; two_durable_segments_closed1; unread2/B1200/old_suppressed1/fresh_suffix240/canonical_samples1440000/eof1. |

Build/clock stderr пустые. Storage stdout пустой, весь ожидаемый результат
пишется в storage stderr373B: это progress/oracle строки, не скрытая ошибка.
Нет assert/error, а wrapper отдельно требует exit0 и точные storage markers.
B5113 относится к synthetic clock/controller test; защищённый durable flow
использует B1200. Нельзя склеивать их в новый заявленный B5113 real-WASAPI→
durable/installed end-to-end proof. Нет чтения реального устройства по этому
допуску; фактические аппаратные clock/route/AEC gates остаются отдельно.

Captured EXE hashes (post-run rehash предусмотрен принятой обвязкой, не новый
независимый guest PE readback reviewer):
- CaptureFaultStateTests `aa6202d152c5a6efc028b14857d530f83ddc02ff503a00ab6047879c11327135`;
- NativeCaptureStorageIntegrationTests `aa224db257f148eafa30a2e7f7a237bf7afbb55925d918cea091b79527149665`.

SHA-256 Validate-Native.ps1 `72f5297743a95b5589575de81f107229e6eca1691df3c77fe43db68d55f9f8e8`;
native-result.json `dbb00a315fe8a0a2ea0b572be38cd3b081035e02ae8ccd5e32aaa447111bf9a1`;
native-build.log `9711fddfc08559f0509ae15e3be23dc141af473a369b0cb4c698ebc992aaf5af`;
native-clock.log `b2e960c71842ff6924b726c7894a54e29c3f73d0e7e64beb7348433a00049436`;
native-storage.err `aacae275a153cca88ac041962299eea213cdc915a9a7ebe20a75bfdd3120cb86`.
Пустые native-build.err/native-clock.err/native-storage.log имеют SHA
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.

Это квалификация двух terminal native opt-in запусков на замороженном
source216, не full native suite, не worker construction SOURCE GO, не установка/
запуск App EXE и не полная T120/T116/hardware/release acceptance. Ничего не
перезапускал, VM/device не использовал, источники/tasks/norms/markers/Git/issues
не менял; добавлен только этот раздел отчёта.
