# F136: текущая проверка границы сессии — 17.10.2026

Полоса: **high-risk-product**, текущий срез T005/T006/T010/T017/T018.
Текущий статус 18.10: локальный срез T005/T006/T010/T018 проверен,
независимое итоговое review Approved; findings0, checklist36/0.
Synthetic P2 снят как неподтверждённый продуктовый блокер; отдельный root-only
auth gap T018/#7652 исправлен и проверен. Коммит и PR пока не разрешены.
Исторические Request Changes ниже сохранены с датой; актуальное решение — в конце.
База: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Изменения пока незакоммичены; SHA базы не является SHA исправления.
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
