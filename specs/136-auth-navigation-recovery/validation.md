# F136: текущая проверка границы сессии — 17.10.2026

Полоса: **high-risk-product**, текущий срез T005/T006/T010/T017/T018.
Исторический статус 18.10: локальный срез T005/T006/T010/T018 проверен,
независимое итоговое review Approved; findings0, checklist36/0.
Synthetic P2 снят как неподтверждённый продуктовый блокер; отдельный root-only
auth gap T018/#7652 исправлен и проверен. На18.10 отдельные коммит и PR тогда ожидали разрешения.
Исторические Request Changes ниже сохранены с датой; актуальное решение — в конце.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Это состояние до опубликованных коммитов; SHA старой базы не является SHA исправления.
Issues #4732/#4733/#4737 остаются открытыми до проверки и принятия соответствующего объёма.

## Причины и исправление

- Protected POST ставил `historyFencePending`; finish/fail/cancel меняли
  `sessionBoundaryID`. SwiftUI `.id` пересоздавал WebView и терял результат.
  Теперь форма сама по себе не создаёт границу; успешная граница применяется
  после сохранения стабильных route, request identity и состояния кабинета.
- 401/выбор пространства сохраняют немедленную защиту; переход на защищённую
  главную недоступен при истёкшей сессии. Выход на стабильный login очищает историю.
- POST→303 WebKit сообщает как новую action `.formSubmitted` с тем же
  WKNavigation. Прежний код ошибочно отбрасывал identity и не принимал finish.
  Теперь pending action блокирует прежний terminal callback до нового start
  либо подтверждённого native server redirect того же активного WKNavigation.
- Принятая отмена текущего завершённого перехода получает существующее состояние
  malformedResponse вместо бесконечной loading; POST не повторяется.

## Исходное воспроизведение и регрессии

Внешний реестр доказательств:
`/Users/yshishenya/Documents/Codex/2026-10-16/graf-issue-by-issue/`.

1. Неизменный исходник: диагностическая WKWebView/SwiftUI-проба GET PASS,
   POST 200 FAIL по изменению boundary. Исходник и результат сохранены отдельно.
2. Постоянная матрица на исходном коде: **1 PASS / 7 FAIL / 0 unexpected**,
   21 assertion failure. Обычный GET — контроль; остальные случаи выявляют
   потерю результата, ложный remount или неверную защиту границы/главной.
   Журнал: `F136-session-boundary-red-final-20261017.log`.
3. Дополнительный реальный POST→303: **1 FAIL / 0 unexpected**;
   журнал `F136-redirect-red-20261017.log`. Причинная диагностика identity:
   `F136-redirect-identity-diagnostic-20261017.log`; временные print удалены.
4. После исправления: **10 PASS** — 9 новых сценариев и существующая проверка
   same-URL stale finish до нового start. Журнал:
   `F136-redirect-and-boundary-green-20261017.log`.

Ранняя матрица `F136-session-boundary-red-20261017.log` завершилась ошибкой
самой fixture при повторном initial GET; она не считается чистым RED.
Промежуточная green-проба с незавершённой loading при отмене тоже не считается
положительной приёмкой. Учитываются только окончательные результаты выше.

## Полный локальный набор до итогового ревью

Команда: `swift test --package-path apps/macos --scratch-path /private/tmp/graf-f136-build`.

**1243 различных теста: 1234 PASS / 9 SKIP / 0 FAIL / 0 unexpected**,
161.490 секунды. `_SWIFTPM_SKIP_TESTS_LIST` в окружении отсутствовал.
10 профильных проверок входят в этот набор и повторно к уникальному итогу не прибавляются.
Журнал: `F136-full-swift-20261017.log`.

Пропуски: 7 существующих проверок фокуса AppKit не получили обычный оконный
фокус в тестовой среде; 2 необязательных экспорта изображений интерфейса не
запрашивались. Они не объявляются PASS и не заменяют ручную проверку GRAF Dev.

- Нативный `ContractValidation`: PASS; `F136-native-contracts-20261017.log`.
- `python3 scripts/check_spec_kit_governance.py`: PASS;
  `F136-governance-20261017.log`.
- `python3 scripts/validate-changelog-fragments.py`: PASS.
- `git diff --check`: PASS; новые документы проверяются отдельно, поскольку untracked.
- Независимое requirements review: **35 checked / 0 unchecked**, см.
  `checklist-review-20261017.md`.
- Независимое итоговое ревью кода 18.10.2026: **Request Changes**, один P2;
  см. `review-session-boundary-20261018.md`. Предыдущий полный GREEN не
  опровергает найденную после него ошибку переходов состояния.

## Дополнительная проверка 18.10.2026

Повторный допуск требований: **35 checked / 0 unchecked**, см.
`checklist-recheck-before-stale-fix-20261018.md`. Хеши spec/plan/tasks совпали
с анализом `F136-analyze-preimplementation-20261017.json`; все 17 задач имеют
прежних владельцев в GitHub, семь исходных незавершённых issues открыты.

Reviewer воспроизвёл поздний redirect A после принятой action B и до start B:
redirect очищает pending B, после чего старый finish A завершает B либо
применяет к ней границу сеанса. Две адресные пробы FAIL; контроль stale finish
без redirect PASS. Исправление этого замечания пока не выполнено.

Проверено предложение определять новый переход по navigationType: оно
некорректно. Подробности — `review-navigation-type-proposal-20261018.md`.
Дополнительно выполнен отдельный диагностический XCTest-пакет с настоящим
WebKit, непостоянным website store и loopback HTTP: **5 различных PASS**.
Он не использует код GRAF и не прибавляется к полному набору продукта.

- POST303 сохраняет type=1 и WKNavigation, меняя POST на GET.
- POST307 сохраняет type=1, POST, тело и WKNavigation.
- GET-форма302 сохраняет type=1/GET для обоих actions.
- JavaScript302 сохраняет type=-1 для обоих actions.
- При второй форме и удержанном ответе первой WebKit сообщил fail A до policy B;
  попытка отправить поздний ответ A не дала redirect/finish A после policy B, B завершилась.
  Callback send в отдельном диагностическом пакете не различает успех/ошибку;
  получение ответа WebKit этим опытом не доказано.

Последний опыт не воспроизвёл reviewer-последовательность на macOS 26.6.2,
но не доказывает её невозможность на всех версиях и не отменяет Request Changes.
Источник, журналы, receipt и контрольные суммы:
`/Users/yshishenya/Documents/Codex/2026-10-18/f136-native-navigation-order/`.
Временный пакет и сборка удалены после сохранения доказательств; код продукта
на этом этапе не менялся. GRAF и GRAF Dev не запускались.

## Оставшиеся ворота

Converge и итоговое ревью должны определить завершённый объём без переноса
частичного успеха на всю F136. T004/T011/T012 (OAuth), T016 (ручная приёмка),
архивные root-only/auth-history утверждения и все неподтверждённые критерии
остаются отдельными задачами. Исторические 645/2456 тестов не используются
как текущая приёмка.

Implementation commit требует отдельного согласия пользователя после проверки.
Затем PR требует governance-fast, macos-pr, pr-metadata на точном SHA/основании
через `scripts/validate-pr-checks.py`; принятие, выпуск и deploy отдельно.
Тесты не меняли установленный GRAF/GRAF Dev и не обращались к рабочим аккаунтам,
внешним OAuth или пользовательскому аудио и содержимому встреч. Матрица
границы сессии использовала только синтетические страницы; полный набор
использует собственные тестовые данные и синтетические cookies. Рабочие
учётные данные и одноразовые коды не сохранялись.


## Актуальное решение независимого ревью и новый converge — 18.10.2026

`review-native-overlap-disposition-20261018.md` снимает прежний P2 как
продуктовый блокер: достижимый сбой не подтверждён. Это не исправление;
Swift-код продукта при диагностике не менялся. Синтетические FAIL сохранены
как поведение методов при вручную заданном порядке событий. Новый постоянный
`testSessionBoundaryNewFormSupersedesPendingFormWithoutRemount` выполняет
настоящие callbacks через Coordinator; адресно 1 PASS, 0.515 с.
`old_response_send=written` подтверждает запись в соединение, не доставку WebKit.

Полный повтор на этом снимке: **1244 различных теста: 1242 PASS / 2 SKIP /
0 FAIL / 0 unexpected**, 97.519 с, exit 0 (`graf-full-swift.log`). Два пропуска —
необязательные экспорты изображений. ContractValidation, governance, changelog
и diff check PASS. Предыдущие семь пропущенных оконных тестов теперь прошли.
Адресный новый тест входит в эти 1244 и повторно к итогу не прибавляется.

Сопоставление всей F136 с кодом выявило новый реальный пробел: вложенные
`.authLogin/.authSignup`, например `/login/vk/start`, считаются безопасными
для истории и SwiftUI. Он учтён append-only задачей **T018/#7652** по FR-002,
FR-003, FR-005, SC-002, SC-003; это отдельная причина не объявлять F136 завершённой.
Предварительный анализ согласованности документов PASS: 13 требований,
18 задач, coverage 100%, artifact CRITICAL/HIGH/MEDIUM 0. Пробел реализации
HIGH учтён T018; этот анализ не означает готовность кода. Issue sync без дублей,
обязательный canon validation: OK (300 Spec Kit issues checked).


## T018: исключение вложенных auth-действий — 18.10.2026

Независимый допуск до реализации: requirements 16/0, auth-navigation 20/0,
всего **36 checked / 0 unchecked**,
`checklist-review-before-t018-20261018.md`. T018 имеет владельца #7652.
Хеши spec/plan/tasks совпали с `analyze-before-t018.json`; sync validation PASS.

Одна новая постоянная регрессия
`testOnlyRootAuthDocumentsCanEnterHistoryAndSwiftUIRecovery` проверяет
12 URL: корневые login/signup с query и завершающим слешем; вложенные
VK/Яндекс/email start/verify. Проверяются live route allow, безопасный
документ, GET history, обе SwiftUI identity overloads, Back и отказ POST.
До исправления: **1 FAIL, 32 assertion failures, 0 unexpected** (`t018-red.log`).
После исправления: **83 различных PASS**, Workspace 60 + RoutePolicy 23
(`t018-focused-green.log`). Никаких новых пропусков не вводилось.

Исправление переиспользует общий `isSafeDocument` в `isSafeHistoryRequest`;
одно правило по компонентам пути исключает вложенные login/signup из
документов и сохранения SwiftUI. Split совпадает с действующей route policy.
Сами действия по-прежнему разрешены живому WebKit; сервер и его контракты
не менялись. Сохранены origin guards, email-link guard и обычные страницы.
Обе conditional реализации SwiftUI identity согласованы.

Первый полный запуск после T018: **1245 различных тестов: 1241 PASS /
3 SKIP / 1 FAIL**, 6 assertion failures в одном прежнем тесте
`DesktopNotificationAccessibilityTests.testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus`,
104.069 с, exit 1 (`t018-full-swift.log`). Фокус карточки не принят,
`canKey=false`; остальные тесты прошли. Отдельный повтор того же теста
без изменения кода — **1 PASS**, 0.512 с (`t018-focus-recheck.log`).
Первый отказ не стёрт и не считается PASS; причина нестабильности фокуса
не установлена. Полный повтор записывается отдельно без skip/filter.

Нативный ContractValidation: PASS (`t018-native-contracts.log`).
Governance и fragment validation: PASS (`t018-governance.log`,
`t018-changelog.log`). GRAF/GRAF Dev не запускались и не менялись.


Полный повтор на неизменных source/tests/fragment завершён: **1245 различных
тестов: 1243 PASS / 2 SKIP / 0 FAIL / 0 unexpected**, 100.129 с, exit 0
(`t018-full-recheck.log`). Прежний упавший notification test прошёл, как
и ранее пропущенная проверка оконного фокуса. Два оставшихся пропуска —
необязательные экспорты изображений. Пропуски не добавлялись, фильтр и
`_SWIFTPM_SKIP_TESTS_LIST` не применялись. Не суммировать focused/recheck
с полным набором как новые уникальные тесты. Первый отказ сохранён;
причина нестабильности уведомления остаётся не установленной.


## Итоговое независимое ревью и границы принятия

`review-final-session-boundary-t018-20261018.md`: **Approved, findings 0**.
Reviewer независимо сверил source/tests/fragment и все пять журналов,
перечитал tasks/convergence/validation и оба checklist: **36/0**.
T005/T006/T010/T018 отмечены [X] как локальная реализация; T017 остаётся [ ].
#4732/#4733/#4737/#7652 не закрыты: пока нет коммита, принятого PR и hosted
checks точного SHA/основы. Отдельное согласие пользователя на implementation
commit требуется после этой проверки. OAuth T004/T011/T012 и ручной T016
сохраняются открытыми, вся F136 не завершена.

Source SHA256: `c1d60d7951d3a8ac40ddff8453b0ab48ed44eff34eac0e69a30bbf6ac73eaf1b`.
Tests SHA256: `32888dc19731c9d53ca28415b45698c81456ef2df87e0af6bd2ee42d8a14c839`.
Fragment SHA256: `5157ebc1ca2e3eb3cdf77daceb0ab9c4e2814326112362bda8d9c1529d5f169f`.
Полный повтор: `b9d027826e131be814d48c64782d3eb8ed1cec4790e04fbc87145e10c8551c87`.

Основной master18.10 чист, live SHA `adc0acba0a05b9353ccfe521a6a005904721c728`.
Два изменённых Swift-файла не менялись между базой F136 и текущим master;
это не заменяет проверки основы будущего PR. Временная scratch-сборка
удалена после сохранения журналов и контрольных сумм; приложения не менялись.


## Отказ GitHub macos-pr — 2026-10-19

Точный PR #7668 SHA `b8244213457be7c8e4e5b349c152fb2940eba680`:
`governance-fast` 39225807716 PASS, `pr-metadata` 39225807702 PASS;
`macos-pr` 39225807767 FAIL с nil unwrap в
`testSessionBoundaryExpiredSessionImmediatelyDisablesProtectedCommands`.
В журнале нет стека и точной строки. Причина не установлена;
слепой повтор и слияние не выполнялись.

Локальная диагностика неизменного коммита, Swift 6.3.3/macOS 26:
точный тест PASS; весь класс 60/60 PASS; полный набор 1245,
1243 PASS / 2 необязательных image-export SKIP / 0 FAIL.
Это не заменяет отказавший Swift 6.0.3/macOS 14 GitHub gate.
Синтетический fixture получает поэтапные stderr-маркеры без адресов,
портов, данных и секретов для установления места отказа в следующем
проверяемом коммите. Проверки и продуктовый код не ослабляются.

Отдельное замечание GitHub review 4311975859: URL после POST остаётся
исключённым даже при последующем настоящем безопасном GET.
Содержание замечания подтверждено чтением ledger; исправление и
регрессия ещё необходимы. Слияние/закрытие issues остаются заблокированы.
Журналы: `/Users/yshishenya/Documents/Codex/2026-10-19/f136-current-preflight/`.


## Текущая перепроверка PR — 19.10.2026

PR#7668, текущий опубликованный SHA e415145a85e5b8af4a79c3ad5ee11b950460ccc0,
проверенная основа03cea84dc5deb1d77ea7b4ac2356fa9819123aa9.
Два прежних native отказа сохранены:39225807767 и39228243168.
Диагностические фазы второго прогона достигали initial-loaded перед nil unwrap.
В двух командах теста JSundefined заменён на явныйtrue после отправки формы;
assertions, ожидания, таймауты и число запросов сохранены. Независимое ревью
этой поправки APPROVE; на точном опубликованномSHA governance-fast39229930021,
macos-pr39229930216 и pr-metadata39230178598 PASS, общий validator PASS.
Это подтверждает устранение наблюдавшегося native отказа в среде GitHub,
но ещё не доказывает новую непубликованную поправку истории.

Новое замечание4311975859 воспроизведено настоящим WebKit:
history-new-get-red-clean.log содержит один отказ восстановления Reload
после новогоGET того жеURL. Первый вариант fixture использовал неверный
calendar path и неверно ожидал новую identity при прямой повторной загрузке
того жеURL; этот журнал сохранён, но не является чистым продуктовым RED.
Исправленный fixture разделяетPOST и позднийGET промежуточной страницей.

Промежуточное снятие запрета поURL вместе с methodguard оказалось недостаточным:
history-url-only-incomplete.log показывает выбор старогоPOST вместо полезного
native Back. После учёта WKBackForwardListItem реальная повторяющаяся история
проходит; старыйPOST не повторяется. Последний policy наблюдается передачей
настоящему Coordinator, с проверкой реальногоcancel и отката currentItem.
НоваяGET-запись допускает Reload и оба направления native history.

Первое итоговое review потребовало очистить pending-флаг на всех terminal
путях и не смешивать завершение ресурса с подтверждением документа. Добавлены
явный confirmsDocument (true только реальномуdidFinish), сбросы состояния и
реальный сценарий supersededGET→artifact404 без подмены WebKit action/response.
Последний сценарий на промежуточном коде ужеPASS после исправления проверки
асинхронного отката currentItem в самомтесте; отдельного productRED дляресурса
не заявляется. Новое правило закрывает выявленный чтением риск общих callers.

Класс61PASS после окончательной поправки: history-entry-terminal-workspace.log.
Предыдущая полная матрица1246:1244PASS+2 необязательныхexportSKIP относится к
промежуточному ledger; окончательный полный повтор описан ниже.
Неоднозначный WebKit-жест при существующей опасной записи того жеURL
отклоняется; native кнопки выбирают безопасную конкретную запись.
OAuth T004/T011/T012, установленная T016, итоговая T017, принятие PR и выпуск
остаются открытыми. Новых реальных аккаунтов, данных и установки не было.
Слияния удерживаются по согласованному выпускному окну F280.


## Окончательный локальный результат и сверка — 19.10.2026

Текущие source/tests совпадают с независимо принятыми SHA256:
`dca71fb3eaf1fd9609daca1adec01691c8f9d9e62d48887c4d8203189c2a3dfa`
и `8e8d1cef5d86543fa35fed11c6e7d615c390cdbc605ff0aa80af3e4db83deed8`.
Полный `swift test --package-path apps/macos --scratch-path <temporary>`:
**1246 различных тестов: 1237 PASS / 9 SKIP / 0 FAIL**, 113.132 с, exit 0;
журнал `history-entry-terminal-full.log`. Фильтры и принудительные пропуски
не добавлялись. Два SKIP — необязательные image-export. Ещё семь — проверки
фокуса карточек уведомлений: среда не подтвердила фокус контрольного обычного
AppKit-окна. Это ограничение среды, а не доказанная приёмка этих семи сценариев;
причина текущей недоступности фокуса не установлена. Все 61 проверки workspace
прошли, в том числе новый сценарий истории. Полный набор не суммируется с
предыдущими прогонами. development-process, governance, fragment и diff checks PASS.

Сверка текущей реализации с намерением охватила 9 FR, 4 SC и 7 сценариев
трёх пользовательских историй, 7 решений плана (платформа, общий policy,
граница сессии, identity/callback, ledger отдельных записей, native controls,
синтетическая проверка и отдельная установленная приёмка) и 7 принципов
конституции. Для текущего среза T005/T006/T010/T018 новых незаведённых
обязательных работ не обнаружено. Существующий общий controller сохраняет
origin/header guards, защищённую границу, native Record/Stop и доступные имена;
новых зависимостей, серверных контрактов, совместимых обходов или содержательных
логов нет. Неоднозначные жесты консервативно отклоняются, как раскрыто выше.

Сверка всей F136 остаётся частичной: OAuth continuation/provider linking
(FR-001/003/006/008, US1/AC1 и US3/AC1, SC-001) требует существующих
T004/T011/T012; установленная приёмка SC-001/US1 и T016 ещё не выполнена.
T017 содержит оформление, принятие PR и hosted evidence. Эти остатки уже
имеют task IDs и issues, повторные задачи не добавлялись; `tasks.md` сохранён
побайтно. Нарушений MUST конституции и нового незапрошенного кода в текущем
срезе не выявлено. Отсутствующие runtime-доказательства не приравниваются к PASS.
Новые GitHub-проверки нужны после следующего коммита; e415 доказывает только
свой опубликованный код. Слияния пока удерживаются для выпуска F280.


## Исправление замечания PR4312424786 — 21.10.2026

База: `845e6dcff7eb7f8e0e2b884902080ecb96582a3a`; локальный HEAD перед
поправкой: `3ca5da7a9745e543414643ae3917b0e790ba9203`.
Полоса: существующая high-risk feature, T005/T006/T010/T018 и оформление T017.
Исторические ограничения/удержание F280 выше относятся к своим датам;
действующее поручение владельца разрешает завершение проверенных PR.
Выпуск, production и замена установленного GRAF Dev в этот срез не входят.

Причина: при обычном POST к адресу текущего GET контроллер помечал адрес
опасным ещё до принятия нового документа. Отказ сети, response policy503 или
отмена до commit сохраняли прежний GET, но лишали его Reload и полезной истории.
Теперь observeNavigationRequest сохраняет только ожидающий признак метода;
настоящий didCommit после проверки attachment/current WKNavigation помечает
новую POST-запись опасной. После commit запрет остаётся и при отмене до finish.
Старые POST-записи, неоднозначные жесты, stale callbacks и resource terminals
не получают нового права повторения. Сервер, credentials, origin/header policy,
billing/download и native Record/Stop не менялись.

Журналы сохранены отдельно в каталоге `f136-review-fix` от21.10.2026;
контрольные суммы и подробное независимое чтение —
[review-final-20261021.md](review-final-20261021.md).

| Проверка / журнал | Результат |
|---|---|
| provisional-red.log: исходный runtime и первая версия регрессий | 3 FAIL: network failure,503,provisional cancellation оставляли прежний GET без Reload |
| provisional-green.log | 3 PASS после переноса маркировки на настоящий commit |
| session-matrix-final.log | 12 PASS, включая committed-but-cancelled POST и stale commit/finish/fail |
| cabinet-final.log | 86 PASS до исправления пустых TCP-соединений |
| macos-full.log | 1248 выбранных,9 SKIP,1 FAIL,exit1; неуспешный результат сохранён |
| unused-connection-red-final.log | 1 FAIL с точным Incomplete synthetic session request при пустом TCP EOF |
| cabinet-fixture-final.log | Окончательные исходники/тесты:86 PASS,0 SKIP,0 FAIL,3.491с |
| macos-full-final.log | Окончательный полный повтор:1248 выбранных,1239 PASS,9 SKIP,0 FAIL,160.033с,exit0 |

Первый общий отказ происходил в receiveSessionFixtureRequest и асинхронно
попал в отчёт последующего теста F277. Пустое соединение воспроизвело ту же
ошибку; байты первого сбоя не сохранялись, поэтому их пустота не утверждается.
Все три существующих HTTP receive handler теперь закрывают только пустое
терминальное соединение до декодирования и подсчёта запросов. Непустые
неполные/malformed/oversize запросы по-прежнему дают отказ. Проверка пустого
TCP включена в прежний ordinary GET сценарий; реальные HTTP counts/expectations
сохранены. Новых зависимостей и отдельной инфраструктуры нет.

Промежуточные ошибки новых тестов не считаются продуктовым RED:
session-matrix.log получил11 unwaited expectations из невыбранных веток helper;
unused-connection-red.log без finalMessage получил timeout. Обе ошибки
исправлены в тесте и сохранены в истории журналов. Ранний продуктовый RED
не выдаётся за прогон окончательных bytes тестов на старом runtime.
Пересекающиеся3/12/86/полный набор не суммируются. Из9 итоговых SKIP семь
относятся к независимой проверке фокуса обычного AppKit-окна для уведомлений,
два — к ненастроенным каталогам image-export. Они не считаются PASS или
ручной приёмкой; в86 кабинетных проверках пропусков нет.

Независимое итоговое ревью: APPROVE,0 замечаний;
requirements16 checked/0 unchecked,auth-navigation20/0. Основной агент перечитал
оба checklist и отчёт; фактические SHA256 совпали с проверенными:

- EmbeddedCabinetWebView.swift: `8dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078`.
- DesktopCabinetWorkspaceTests.swift: `0f4bdc8c5542f270aa39d57a36df24f251c20e3f089b58b48d37fe91e15dfd7e`.

### Повторная сверка реализации с намерением

Сопоставлены9 FR,4 SC,7 сценариев приёмки,7 решений плана и7 принципов
конституции. В текущем срезе T005/T006/T010/T018 новых обязательных пробелов
не выявлено:0 missing,0 partial,0 contradicts,0 unrequested;0 CRITICAL/HIGH.
Проверены: существующая платформа/модуль; единая политика stable/transient;
порядок границы; identity/callback lifecycle; отдельные записи безопасной
истории и нативные команды; синтетическая матрица; отдельные ручные/release gates.
Перенос unsafe на commit согласован с FR-002/003/005/006,SC-002/003/004,
US2/AC2 и заданным порядком plan21.10. Непринятый POST сохраняет GET;
принятый POST не становится безопасным при ошибке. FR-007/009 и остальные
сессионные критерии сохранены текущей общей матрицей и прочитанными guards.
Захват/consent/AI/deletion/distribution/reference principles не ослаблены.

Вся F136 ещё не завершена. FR-001/003/006/008,SC-001,US1/AC1 иUS3/AC1 в части
OAuth/provider linking требуют существующих T004/T011/T012; установленная
матрица остаётся T016. T017 требует нового коммита, трёх hosted checks
точного SHA/основы и принятия PR. Эти остатки уже учтены; новые дублирующие
задачи не добавлялись. Во время самой convergence tasks.md не переписывался.
Prerequisite script не поддерживает --require-spec: после явного отказа
использован --require-tasks --include-tasks и отдельная проверка наличия spec.
До/после converge hooks отсутствуют; auto-commit hooks отключены.


## Доставка синтетического POST после отказа GitHub — 21.10.2026

PR#7668 на adb345c42a55ea5a5acf7777fa4e13b7eacef7fc получил настоящий
macos-pr FAIL39607758091: один committed-cancellation сценарий дал шесть
ошибок утверждений после отсутствующего didCommit. Исходный журнал
hosted-final-failure.log сохранён. Прежний локальный PASS этот отказ не отменяет.

Независимый допуск [review-hosted-commit-plan-20261021.md](review-hosted-commit-plan-20261021.md):
requirements16/0, auth-navigation20/0, блокеров0. Анализ уточнённого плана:
CRITICAL0/HIGH0; существующие T006/T017 и открытая #4733 сохраняют ownership,
нового требования или дублирующей задачи нет.

Исправлен только синтетический HTTP fixture: POST получает полный HTML с точным
Content-Length и img на /f136-held-resource. Сервер фиксирует отдельный GET
и удерживает его без ответа. Прежняя отмена main connection исключена только
для committedCancellation; остальные сценарии сохранены. Тест ждёт настоящий
didCommit и ровно один GET ресурса, затем проверяет новый history item,
isLoading=true и finishCount=0 перед прежним stopLoading. Reload/Back/новый
безопасный GET и единственный POST проверяются прежними assertions.
Таймаут didCommit не увеличен, callbacks не подставляются, новых skip нет.
Точный порог буферизации неполного HTML WebKit не установлен и не заявляется.

| Текущий журнал | Результат |
|---|---|
| held-resource-focused.log | 1 PASS,0FAIL/0SKIP,0.929с |
| held-resource-cabinet.log | 86 PASS,0FAIL/0SKIP,3.873с |
| held-resource-full.log | 1248 выбранных,1246 PASS,2 SKIP,0FAIL,111.939с,exit0 |

Два SKIP — существующие экспорты card/permission изображений без настроенных
каталогов. Они не считаются PASS или установленной приёмкой. Наборы1/86/1248
пересекаются и не суммируются. Локальная macOS26/Swift6.3.3 не заменяет
новую проверку GitHub macOS14/Swift6.0.3. check_spec_kit_governance,
check-development-process и git diff --check:PASS.

Product EmbeddedCabinetWebView.swift не менялся в этой поправке,
SHA2568dd084e32763ac4d16df6ea6ff76a8114c959e642b0c66fbe83b12331b285078.
Test SHA256e374b04a579464737a97d9d411a3d5c260edf7ac882a42d9a82986c36b3f0552.
Сверка по speckit-converge: новых обязательных кодовых остатков данного
fixture-среза не найдено. T017 остаётся открытой до нового независимого
итогового ревью, трёх exact-SHA/base checks и принятого PR; OAuth T004/T011/T012,
ручная T016 и вся F136 остаются открытыми. Приложение/Dev/production не менялись.


Итоговое независимое ревью доставки POST:
[review-held-resource-final-20261021.md](review-held-resource-final-20261021.md),
APPROVE, замечаний0/блокеров0, requirements16/0 и auth-navigation20/0.
Основной агент прочитал фактический отчёт и оба списка; тестовый и продуктовый
SHA256 совпали с указанными выше. T017 ожидает новые три проверки GitHub
точного SHA/основы и принятие PR; OAuth и ручная T016 остаются открытыми.


## Настоящий Workspace после отмены — 21.10.2026, T019/T020

Полоса high-risk-product; исходный HEAD0c0cfba5690dead496aaa1bc00cabbe9cc0b6a76.
Обязательный допуск уточнённого плана: review-workspace-presenter-plan-20261021.md,
36 checked/0 unchecked, блокеров0. analyze-workspace-isolation-plan.json:
9FR,4SC,20tasks,CRITICAL/HIGH/MEDIUM/LOW0; контрольные суммы plan/tasks совпали.
T019/#7688 и T020/#7689 синхронизированы до реализации; T020 включает Workspace.

T019: оба исходных настоящих WebKit-сценария `/login/` и `/sign-up/`
прошли,2PASS/0FAIL,1.062с (`trailing-slash-red.log`; название историческое).
Foundation URL.path удаляет завершающий слеш; прежнее утверждение о доказанной
ошибке отозвано, issue#7688 уточнена. Удалено лишь дублирующее точное
сравнение: auth kind и общий safe predicate сохраняют root-only границу.
Нельзя представлять эти регрессии как RED/GREEN исправленного runtime-дефекта.

T020: прежнее утверждение, что malformedResponse сохраняет страницу, неверно
для настоящего DesktopCabinetWorkspaceView: его visibility predicate удаляет
WebView. Всегда смонтированное старое представление скрывало этот отказ.
Первый запуск `trailing-cancellation-red.log` аварийно завершился при создании
singleton presenter до отмены: UNUserNotificationCenter.current в консольном
XCTest не имеет bundleProxy. Это не продуктовый RED.

Сначала передана существующая optional зависимость presenter через Workspace;
Coordinator использует authEpoch того же экземпляра, что notification bridge.
Обычный default сохранён. Тест использует собственный UserDefaults domain и
синтетический contextProvider, очищает domain; системной доставки и изменения
пользовательских настроек нет. На прежней navigation logic итоговый
`workspace-navigation-red-confirmed.log`:3сценария,2PASS,1FAIL/2assertions,
0unexpected,1.744с. Положительный сценарий получил malformedResponse и удаление
настоящего WebView; initial и committed POST отрицательные сценарии прошли.
Предыдущий `workspace-navigation-red.log` также имел unwaited expectations
самого теста; этот недостаток исправлен и сохранён в истории.

Исправление хранит одну weak ссылку на безопасный current history item,
подтверждённый accepted real didFinish и безопасным pending method. Synthetic/
resource terminal ничего не подтверждают. Attach/detach/session fence и unsafe/
неподтверждённый настоящий finish снимают сертификат. Только accepted current
provisional cancellation из loading при том же currentItem и прежних
history/session/attachment guards восстанавливает finishedState. Новый документ,
initial, committed POST,401/reselection и stale callbacks не получают ready.
Recording bridge активируется заново; notifications возобновляются через
существующее согласование cookies, authEpoch и актуальность документа.
Календарное действие и POST не повторяются; общий mapper ошибок не менялся.

`workspace-navigation-green.log`:5PASS/0SKIP/0FAIL,2.175с. После добавления
настоящего чтения notification settings и отклонения прежнего nonce:
`workspace-cabinet-green-final.log`100PASS/0SKIP/0FAIL,6.276с —69Workspace,
23RoutePolicy,8NotificationSettingsBridge. Эти наборы пересекаются и не
суммируются. Новый тест сохраняет тот же WKWebView/DOM/window/currentItem
после SwiftUI reconciliation, один GET до отмены, один POST, новый nonce/
повторную активацию настроек и безопасный GET Reload. Удержанный synthetic
HTTP-ответ освобождается при cleanup без произвольного таймера.
Промежуточная ошибка компиляции async в XCTest autoclosure сохранена в
workspace-cabinet-green.log; исправлен только тестовый unwrap.

`workspace-full-green.log`:1254 выбранных,1245PASS/9SKIP/0FAIL/0unexpected,
164.886с,exit0. Семь существующих оконных focus-тестов пропущены из-за
неподтверждённого фокуса обычного контрольного окна; два optional image-export
не имеют настроенных каталогов. Кабинетные/settings тесты не пропущены.
ContractValidation, governance, development-process, changelog и diff-check PASS.
Итоговое независимое ревью, convergence и три свежих hosted проверки точного
SHA/основы ещё ожидаются. Найденная чтением гипотеза отмены другого GET
проверяется отдельно; исходный полный результат не является её доказательством.
T017 остаётся открытой.
OAuth T004/T011/T012 и ручная T016 не закрываются. Выпуска, установки,
подписания, production или изменения GRAF Dev нет.


## Окончательная проверка восстановления маршрута — 21.10.2026

T020 включает отмену предварительного GET A→B: настоящий документ A остаётся
видимым, но trackPendingRoute уже записал B в маршрут и identity контейнера.
`workspace-different-get-red.log` на промежуточном исправлении подтвердил
1 FAIL/2 assertion failures/0 unexpected,0.981с: сохранились route B и GET
identity B вместо A. Это отдельный воспроизведённый дефект, в отличие от T019.

Минимальное исправление в уже защищённой restore-ветке возвращает currentRoute
и lastLoadedRequestIdentity к URL подтверждённого документа до присваивания
finishedState. Использованы существующие trackedRoute/loadIdentity; условия
допуска, методы запросов, history/session guards и остальные callbacks не менялись.
`workspace-different-get-green.log`:1 PASS/0 FAIL/0 SKIP,0.838с. Настоящий
Workspace подтверждает WebView/window/DOM/currentItem и route/identity A после
SwiftUI reconciliation, ровно один GET B и отсутствие его повторения при Reload A.

| Окончательный журнал | Результат | SHA-256 |
|---|---|---|
| workspace-different-get-red.log | 1 FAIL,2 ожидаемых assertions,0 unexpected | d1ac1a35aff12d48501d431cfefd3a506e2b9632a329d2e4420f479cc97aa1c7 |
| workspace-different-get-green.log | 1 PASS,0 FAIL/0 SKIP | 0ded58a70082425f125d7b022b79bf2c5e21612fe6c67e6762fd3492268f3aa2 |
| workspace-cabinet-route-green.log | 101 PASS,0 FAIL/0 SKIP,6.393с | 0c8a205a102045accebd92028af4c2198cf9235c34a085cb82510adbd701b956 |
| workspace-full-route-green.log | 1255 выбранных,1246 PASS/9 SKIP/0 FAIL,123.041с,exit0 | 68fe3d9519bc63225f4cf1cb37e25e61feec0eba1d590053a743777598bb7611 |
| contract-validation-green.log | ContractValidation: PASS,exit0 | 17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87 |

Полная команда: `swift test --package-path apps/macos --scratch-path <temporary-build>`.
Профиль: тот же swift test с фильтром
`DesktopCabinetWorkspaceTests|DesktopCabinetRoutePolicyTests|EmbeddedCabinetNotificationSettingsBridgeTests`.
ContractValidation собран через `swift build --product ContractValidation` и
запущен из того же scratch-path без установки приложения. В профиле70Workspace,
23RoutePolicy,8NotificationSettingsBridge. Пересчёт имён подтвердил101 и1255
уникальных проверок. По сравнению с предыдущим1254 добавлен ровно GET A→B,
удалённых проверок0; наборы пересекаются и не суммируются.

Пропуски прежние:7AppKit focus (5Accessibility и2PromptLifecycle),
2необязательных image-export без каталогов. Они не считаются PASS или ручной
приёмкой. Прежние полный1254, профиль100, исходные отказы и crash сохранены;
эта таблица относится только к окончательным bytes после восстановления route.

SHA-256 проверенных исходников:
- DesktopCabinetWorkspaceView.swift: e6e5c5e140a91d641dce0d1355f41640c72b73f1853e87fca4db659b9e1832fa.
- EmbeddedCabinetWebView.swift: ba955ff6dab10d6c32fcf64db01ce80bedc019287c97be9c3824d32aa91c62d8.
- DesktopCabinetWorkspaceTests.swift: 43c638b988237c60c04432d7b27be1ac5836ea5313a623a5de7f9863da830110.

### Analyze и convergence текущего среза

Analyze:9FR,4SC,20tasks,100% требований имеют задачи;CRITICAL0/HIGH0,
новых несогласованностей или запросов уточнения0. Отображение:
FR001→T001/T002/T005/T007/T008/T011/T012;
FR002/003→T003/T007/T009/T018/T019/T020;
FR004→T005/T010/T019/T020;
FR005→T002/T006/T009/T010/T018/T019;
FR006→T005/T006/T009/T010/T020;
FR007→T005/T017/T020;FR008→T004/T008/T011/T012/T020;FR009→T009/T010.
SC001→T004/T008/T011/T012/T016;
SC002→T001/T002/T005/T006/T008/T012/T018/T020;
SC003→T002/T009/T010/T018/T019;SC004→T006/T009/T010/T020.
T013–T015 — историческое сопровождение, T017 — текущие проверки/доказательства.

Convergence сопоставила9FR,4SC,7AC,7решений плана и7принципов конституции
с текущими controller/coordinator, Workspace и настоящими WebKit-тестами.
Для T005/T006/T010/T018/T019/T020 новых missing/partial/contradicts/unrequested
пробелов0,CRITICAL/HIGH0. Проверены native stack, stable/transient predicate,
порядок session boundary, current navigation identity, отдельные history items,
настоящая синтетическая матрица и отдельные ручные/release gates. Новый GET
восстанавливает только свой завершённый документ; чужой/unsafe/initial/committed
документ,401/reselection,detach/stale не расширяют доступ. Принципы capture,
consent,observability,deletion,distribution и reference fidelity не менялись.

Вся F136 не converged: OAuth/provider continuation FR001/003/006/008,
SC001,US1/AC1,US3/AC1 остаётся partial/HIGH в существующих T004/T011/T012;
установленная матрица — T016, hosted/принятие — T017. Новые дубли задач
не добавлялись; во время convergence tasks.md оставлен неизменным.
Hooks before/after converge отсутствуют; auto-commit hooks отключены.

Независимый предварительный допуск GET A→B записан в
[review-workspace-cancellation-final-20261021.md](review-workspace-cancellation-final-20261021.md).
Итоговое ревью окончательных журналов и новые GitHub проверки ещё ожидаются.
GRAF Dev, пользовательские настройки и production не менялись; выпуска нет.


Итоговое независимое ревью окончательных исходников и журналов:
[review-workspace-cancellation-final-20261021.md](review-workspace-cancellation-final-20261021.md)
— APPROVE, замечаний 0, блокеров 0. Основной агент прочитал итоговый отчёт,
сверил три Swift SHA256 и оба списка: requirements 16 checked / 0 unchecked,
auth-navigation 20/0. T019/T020 отмечены [X] как проверенная локальная реализация.
T017, новые обязательные GitHub checks точного SHA/основы и принятие PR остаются
отдельными воротами. OAuth T004/T011/T012, ручная T016 и вся F136 не завершены.
