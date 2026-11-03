# F136/T019–T020: независимое ревью настоящего Workspace — 21.10.2026

## Предварительный допуск уточнения T020: отмена другого GET

**План PASS, блокеров требований 0. Итоговая приёмка реализации ожидается.**
Requirements: **16 checked / 0 unchecked**; auth-navigation:
**20 checked / 0 unchecked**, всего **36/0**. Полоса high-risk-product;
ветка `codex/136-auth-navigation-recovery`, HEAD
`0c0cfba5690dead496aaa1bc00cabbe9cc0b6a76`.

Проверены текущие spec/plan/tasks/quickstart/research/data-model/contract,
validation и каждый пункт обоих checklist. После сжатия полностью восстановлено
чтение AGENTS, guidance index, document-reading, development-process,
codex-worktrees, spec-kit-flow, constitution, PRD, current-product-status,
product-gates и release-and-validation. Использован code-reviewer. Полная
таблица предыдущего допуска каждого из 36 пунктов находится в
[review-workspace-presenter-plan-20261021.md](review-workspace-presenter-plan-20261021.md);
основания повторно сопоставлены с текущими требованиями, а не приняты по хешу.

Дополнение не меняет пользовательские требования: FR-002/006/007 и SC-004
уже требуют сохранить обычный безопасный документ и ожидаемую навигацию после
отмены. Plan §«Согласование маршрута после отмены другого GET» и последний
абзац quickstart теперь явно включают A→B с удержанным ответом и stopLoading.
CHK001/005/006/008/010/011/017/018/019 подтверждены этим уточнением и прежними
ограничениями safe currentItem/current navigation/session/attachment.
Остальные CHK002–004/007/009/012–016/020 сохраняют прежние явные основания
spec/contract/quickstart; отдельные OAuth, безопасность, доступность, ручная
приёмка и root-only auth остаются без расширения. Все 16 общих пунктов
качества подтверждены заполненными US/AC/FR/SC/Assumptions/Edge Cases и ясной
границей среза; техническое решение остаётся в plan, а не в spec.

Чтение реального caller flow подтвердило риск: decidePolicyFor вызывает
trackPendingRoute до разрешения GET B; тот записывает currentRoute и
container.lastLoadedRequestIdentity=B. updateNSView сравнивает восстановленный
маршрут с сохранённой identity. Прежняя restore-ветка восстанавливала состояние
и bridges, сохраняя B, хотя WebKit показывает завершённый документ A.

Исполнитель добавил настоящий
`testRealWorkspaceRestoresRouteAfterDifferentGetCancellation` в существующий
Workspace helper и loopback receiver, продуктовый код не менял.
Независимо прочитан `workspace-different-get-red.log`: **1 FAIL, 2 assertion
failures, 0 unexpected, 0.981 с**. Падают ровно route
`/desktop/settings/account` и identity GET B вместо
`/desktop/settings/recording` и GET A. Остальные проверки документа,
currentItem, реального дерева представлений и отсутствия повтора не упали.
Это действительное исходное воспроизведение расхождения; оно не является
GREEN. Название/содержимое теста и источник его запроса прочитаны.

Допускается минимально вернуть currentRoute через существующий trackedRoute
и container.lastLoadedRequestIdentity через loadIdentity(url:) из фактического
webView.url **до присваивания ready**, только внутри уже защищённой ветки
restoresFinishedDocument. Новый ledger, запрос, принудительный GET или
ослабление guards не нужны. Начальная незавершённая загрузка, committed POST,
401/reselection, stale/detach и unsafe/synthetic/resource terminal не получают
нового права восстановления. Восстановление bridges сохраняет прежние
cookies/authEpoch/current-document проверки и не повторяет календарную операцию.

После правки необходимы новый отдельный GREEN, кабинетный и полный quickstart,
ContractValidation и чтение окончательных изменений/журналов проверяющим.
Предыдущие 100/1254 относятся к предыдущим исходникам и не доказывают новую
правку. T019 исходно 2/2 PASS, runtime-дефект не воспроизведён; это согласование
predicate, без утверждения RED/GREEN. Прежний hosted FAIL39607758091 требует
нового действительного hosted результата. T017, OAuth T004/T011/T012 и ручная
T016 остаются открытыми. PR/слияние/выпуск/установка/production не аттестованы.

Проверяющий меняет только этот отчёт и два checklist; тесты, сборки, код,
spec/plan/tasks, Git/GitHub, GRAF Dev и пользовательские данные не меняет.

### Контрольные суммы предварительного допуска

| Файл | SHA256 |
|---|---|
| spec.md | `6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668` |
| plan.md | `8adc7df649012d3af75ddb35720198b024734e5e5393c2b267892162c308ae60` |
| tasks.md | `6f45332b2d11ae58af45cd930f309c12a2319868d196289f490be87af4ea039b` |
| quickstart.md | `75ca40acf6c2591223e7bda7a88316091bf103dcb8da87a7a6a6750026aff58d` |
| validation.md | `74bed20f527883b98064b2a21771a00c0657743612c388224560fff1101e63c1` |
| Workspace.swift | `e6e5c5e140a91d641dce0d1355f41640c72b73f1853e87fca4db659b9e1832fa` |
| Embedded.swift до правки маршрута | `cf2ce97db293bafc4b37876109f55368ee9ef3db26a98d5828aa15f752391152` |
| WorkspaceTests.swift с GET RED | `43c638b988237c60c04432d7b27be1ac5836ea5313a623a5de7f9863da830110` |
| workspace-different-get-red.log | `d1ac1a35aff12d48501d431cfefd3a506e2b9632a329d2e4420f479cc97aa1c7` |

Хеши всех обязательных неизменных документов совпали с таблицей предыдущего
отчёта; полное чтение восстановлено в текущем контексте, совпадение хешей
само по себе не использовалось как доказательство чтения или работы продукта.

## Итоговое решение по окончательным исходникам и журналам

**APPROVE для локальной реализации T019/T020; замечаний 0, блокеров
проверяющего 0.** Предварительный допуск выше завершён итоговой проверкой.
Область решения — три Swift-файла с контрольными суммами ниже и описанный
в этом отчёте срез. Это разрешает исполнителю продолжить оформление коммита
и проверку PR в рамках поручения владельца; принятие PR и закрытие issues
требуют отдельных фактических доказательств GitHub.

Независимо прочитаны окончательный продуктовый и тестовый diff, настоящие
Workspace-сценарии, чистый RED и GREEN другого GET, профильный и полный
журналы, ContractValidation и окончательный раздел validation.md. Текущие
байты повторно сверены с прочитанными контрольными суммами. Изменение
tasks.md после предварительного допуска добавило ссылки на issues к
T005/T006/T010/T017/T018; T019/T020 пока не отмечены исполнителем.

### Продуктовые основания решения

Последний подтверждённый безопасный документ хранится единственной weak
ссылкой на WKBackForwardListItem. Его подтверждает только принятый настоящий
didFinish текущей навигации с безопасным ожидающим методом и общим правилом
безопасного документа. Принятый настоящий finish сначала снимает прежнее
подтверждение; unsafe/неподтверждённый документ его не получает. Attach,
detach, истечение сессии и завершение границы сессии очищают ссылку;
синтетические и ресурсные завершения ничего не подтверждают.

Восстановление допускается только после принятой текущей provisional отмены,
для которой общий mapper оставил loading, при том же currentItem и прежних
history/session/attachment guards. Внутри этой ветки currentRoute и GET
identity контейнера возвращаются к фактическому завершённому документу до
ready. Дополнительного запроса, ledger и повтора POST нет. Первичная
незавершённая загрузка, committed POST, другой документ, 401/выбор пространства,
устаревшие callbacks и detach не получают ложного ready. Состояния настоящей
сетевой ошибки не заменяются успешным состоянием.

Recording settings повторно активируются существующим методом; notifications
возобновляются через прежние cookies/current-document/revision/authEpoch
проверки. Bridge и чтение authEpoch используют один переданный presenter.
Optional зависимость Workspace сохраняет обычный default, а тест изолирует
UserDefaults и contextProvider без системной доставки. Календарная операция
не повторяется; origin/header guards, billing/download и native Record/Stop
не расширены. Серверные контракты, доступы и хранение сессий не менялись.

### Окончательные автоматические доказательства

| Журнал | Независимо проверенный результат | SHA256 |
|---|---|---|
| workspace-different-get-red.log | 1 FAIL, ровно 2 assertion failures route/identity B вместо A, 0 unexpected; 0.981 с | `d1ac1a35aff12d48501d431cfefd3a506e2b9632a329d2e4420f479cc97aa1c7` |
| workspace-different-get-green.log | Тот же тест, 1 PASS / 0 FAIL / 0 SKIP; 0.838 с | `0ded58a70082425f125d7b022b79bf2c5e21612fe6c67e6762fd3492268f3aa2` |
| workspace-cabinet-route-green.log | 101 различных PASS / 0 FAIL / 0 SKIP: 70 Workspace, 23 RoutePolicy, 8 NotificationSettingsBridge; 6.393 с | `0c8a205a102045accebd92028af4c2198cf9235c34a085cb82510adbd701b956` |
| workspace-full-route-green.log | 1255 различных: 1246 PASS / 9 SKIP / 0 FAIL / 0 unexpected; 123.041 с, exit 0 | `68fe3d9519bc63225f4cf1cb37e25e61feec0eba1d590053a743777598bb7611` |
| contract-validation-green.log | ContractValidation: PASS | `17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87` |
| contract-validation-build.log | Успешная сборка ContractValidation; 0.36 с | `d4f5ff5c8293ac5268ac53712359f547ec1c7526c32abe65d5e5803c68e3a9e3` |

Подсчёт полных идентификаторов проверок подтверждает уникальность 101 и 1255.
С предыдущим полным набором 1254 совпадают все прежние идентификаторы:
удалённых 0, добавлен ровно testRealWorkspaceRestoresRouteAfterDifferentGetCancellation.
Профильный и полный наборы пересекаются и не суммируются.

Настоящий Workspace подтверждает сохранение того же WKWebView, окна, DOM и
currentItem после обновления SwiftUI; bridge после отмены снова читает/изменяет
синтетическую настройку, notification read принимает новый nonce и отклоняет
старый. Другой GET B отправлен один раз, Reload загружает A и не повторяет B
или форму. Initial и committed отрицательные случаи проходят; committed
fixture ждёт настоящий didCommit, отдельный удержанный ресурс и отсутствие
didFinish до stopLoading. Проверки, таймауты и запреты не ослаблены, новых
условных пропусков нет.

Девять пропусков полного набора не считаются PASS: семь существующих проверок
фокуса уведомлений не получили подтверждённый фокус независимого AppKit-окна
(пять Accessibility и две PromptLifecycle); два необязательных image-export
не имеют заданных каталогов. Кабинетные/settings проверки не пропущены.
Reviewer не запускал тесты или сборки, а независимо читал исходники и журналы.

### Честная граница RED и качества требований

T019 исходно прошла оба настоящих trailing-slash сценария, 2 PASS / 0 FAIL;
Foundation URL.path уже нормализует завершающий слеш. Runtime-дефект T019 не
воспроизведён, удаления лишнего сравнения нельзя выдавать за RED/GREEN.
Чистый T020 RED настоящего Workspace записан отдельно в
workspace-navigation-red-confirmed.log: 3 сценария, 2 PASS / 1 FAIL,
2 assertion failures / 0 unexpected. Прежняя страница получала malformedResponse
и удалялась из настоящего дерева. Последующий другой GET имеет собственный
чистый RED/GREEN выше. Crash singleton до навигации, ранний fixture failure,
ошибка компиляции и исторические 100/1254 сохранены и не подменяют эти результаты.

Повторная сверка 9 FR, 4 SC и требований обоих списков не выявила нового
пробела текущего T019/T020. FR-002/003/005 и SC-003 подтверждаются общим
root-only/history правилом и регрессиями; FR-004/006 и SC-004 — сохранением
документа и маршрута с прежними границами сессии; FR-001/007 и SC-002 —
единственным запросом и отсутствием обходов/повтора; FR-008 — безопасным
терминальным состоянием ограниченного сценария; FR-009 — неизменными native
controls и общей policy-матрицей. Это не утверждение о завершённой OAuth части
FR-001/003/006/008 или SC-001. План и текущие task owners сохраняют эту границу.

После повторного полного чтения обоих checklist отметки качества требований
сохранены: requirements **16 checked / 0 unchecked**, auth-navigation
**20 checked / 0 unchecked**, всего **36/0**. Они не означают завершённую
реализацию всей F136 или установленную приёмку.

### Точные проверенные байты и оставшиеся ворота

| Файл | Окончательный SHA256 |
|---|---|
| apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift | `e6e5c5e140a91d641dce0d1355f41640c72b73f1853e87fca4db659b9e1832fa` |
| apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift | `ba955ff6dab10d6c32fcf64db01ce80bedc019287c97be9c3824d32aa91c62d8` |
| apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift | `43c638b988237c60c04432d7b27be1ac5836ea5313a623a5de7f9863da830110` |
| spec.md | `6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668` |
| plan.md | `8adc7df649012d3af75ddb35720198b024734e5e5393c2b267892162c308ae60` |
| tasks.md до итоговой отметки исполнителя | `487997ab7987749e732183f316b53b45c2b8c888c90048187d7ca197ed756a77` |
| quickstart.md | `75ca40acf6c2591223e7bda7a88316091bf103dcb8da87a7a6a6750026aff58d` |
| validation.md | `802cf3016c23c512e9980eb2122382c487e193b3f46f0a89ac353d216a95aedc` |

OAuth T004/T011/T012 и установленная ручная T016 остаются открытыми. T017
требует нового коммита, трёх обязательных GitHub checks точного PR SHA и
проверенной основы через общий validator, затем принятого PR. Прежний
macos-pr39607758091 FAIL не отменён локальным PASS. Новый фактический hosted
результат необходим. Вся F136, слияние, выпуск, подписание, установка и
развёртывание этим ревью не подтверждены. После rebase необходимо сверить
эти продуктовые/тестовые байты и получить новые проверки GitHub; изменение
любого из трёх Swift-файлов требует обновления ограниченного ревью.

Проверяющий изменил только этот отчёт и два разрешённых checklist. Код,
spec/plan/tasks, Git/GitHub, приложения, реальные аккаунты, пользовательские
настройки и содержимое встреч не менялись.
