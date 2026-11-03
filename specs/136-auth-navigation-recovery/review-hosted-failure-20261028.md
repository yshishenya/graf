# F136: предварительное независимое ревью отказа macos-pr

Дата: 2026-10-28. Ветка: `codex/136-provider-link-continuation`.
Проверенный HEAD: `63272ac68dd3dda584d019c173fca39f4b0fa7c3`, PR #7785.
Решение: **допуск ограниченного tracing и контролируемой доставки synthetic POST**.
Это не APPROVE исправления и не снятие отказа GitHub.

## Факты отказа

Журнал `f136-macos-pr-40609780164-failure-20261028.log` run40609780164:
SHA-256 `3d1977eab3478c7bce0286349ccb285cad444867af9075fc38796c59b6858cca`.
Самостоятельный пересчёт:1296 terminal rows,1296 уникальных test IDs,
1293 PASS/1 FAIL/2 SKIP. Две ошибки — assertions836/837 одного
`testProviderLinkStaleCallbacksKeepCurrentContinuation`, а не два упавших теста.
Общий XCTest завершился exit1. Два SKIP — необязательный экспорт изображений;
они не считаются PASS. Старый локальный успех hosted отказ не отменяет.

Тест не обнаружил controller.isLoading и прежнюю currentItem после явной
передачи didCommit/didFinish/didFail старого WKNavigation. Весь остальной
контроль этого теста дошёл до terminal-callback, новых assertion failures
в нём журнал не содержит. Лог не фиксирует порядок настоящих commit/finish
POST относительно injection; по нему нельзя установить причинность.

## Самостоятельно прослеженная цепочка

1. `testProviderLinkStaleCallbacksKeepCurrentContinuation` вызывает общий
   checkSessionBoundary с method POST, providerLink и probeStaleCallbacks,
   но без cancel/supersedesPendingForm/committedCancellation.
2. После готового Settings GET выполняется настоящий reload, его WKNavigation
   сохраняется как старый. После второго GET сохраняется initialItem.
3. document.forms[0].submit запускает настоящий WebKit POST; test ожидает
   серверное expectation submitted, затем вручную доставляет старые callbacks.
4. В receiveSessionFixtureRequest submitted.fulfill стоит до построения/отправки
   короткого полного ответа200. Для этой комбинации параметров нет hold:
   connection.send немедленно разрешает новому POST commit и finish.
5. await fulfillment отдаёт управление. Само получение submitted не гарантирует,
   что новый POST ещё pending при возобновлении теста. Законно завершённый POST
   имеет isLoading=false и другую currentItem даже без старых callbacks.
6. Controller.navigationDidCommit/Finish/Fail проверяют attached/current identity;
   isCurrentNavigation с ненулевым token требует pendingNavigationURL==nil и
   activeNavigation===token. Coordinator.didFinish/didFail применяют изменения
   только после принятого controller callback. Старый reload отличается от
   нового token; после законного finish нет activeNavigation и старый token
   также отклоняется. Отдельный новый bypass в просмотренных путях не найден.
7. Настоящий action проходит approved Settings POST, observeNavigationRequest,
   cookie barrier dispatch, navigationDidStart, response policy и commit/finish.
   Provider-link transient finish сохраняет ready и continuation; он вправе
   сменить документ и завершить loading. Это делает ожидаемый отказ836/837
   совместимым с завершением нового POST до injection.

**Подтверждено чтением:** отсутствует серверный барьер, гарантирующий
предусловие pending POST в этой пробе. **Не подтверждено:** что именно этот
порядок событий произошёл на GitHub, либо что продукт имеет естественную гонку.
Новых runtime запусков, тестов, сборок и внешнего OAuth проверяющий не выполнял.

## Минимальный допустимый план и критерии проверки

До вывода о причине получить synthetic-only trace: принятие POST, удержание/
отправка его ответа, настоящий start/commit/finish с различимыми локальными
navigation tags и состояние непосредственно до/после каждого старого callback.
Не выводить cookies, аккаунты, реальные callback URLs или секреты.

Допустима малая правка существующего fixture: для этой stale-callback пробы
удержать реальный ответ POST до завершения injection, подтвердить его получение
и pending loading/ту же initialItem до injection, затем сохранить те же
проверки после injection. Сохранить прежние boundary/view/route/identity и
ровно один исходный POST; никакого GET-replay. После проверок явно отпустить
полный ответ с верным Content-Length, дождаться настоящих commit/finish и
проверить прежнее разрешение provider continuation тем же policy probe.
Очистка собственного удержанного соединения при любом выходе обязательна.
Уточнённый план основного агента допущен: holdResultResponse ограничен
providerLink && probeStaleCallbacks; соединение и готовые HTTP bytes
регистрируются до submitted.fulfill. Release забирает собственные данные
под существующим lock, а сетевую отправку выполняет вне него.
Диагностическая проба без hold с явно завершённым POST перед injection
проверяет альтернативный порядок, но не доказывает причину прежнего CI FAIL.

Не заменять синхронизацию sleep/retry/skip, не снимать assertions836/837,
не увеличивать timeout вместо подтверждения события и не подменять настоящие
события искусственным успешным finish. Повторная доставка старого настоящего
WKNavigation — контролируемая callback-проба, не естественная гонка сети.
Если trace выявит иное, этот предварительный план пересмотреть до продуктовой
правки. Действующие product guards не ослаблять по предположению.

После изменения нужны отдельная регрессия, кабинетный и полный XCTest из
quickstart, ContractValidation/проектные проверки по существующему плану,
независимое итоговое ревью и новые обязательные проверки GitHub точного SHA
и основы. Одного локального PASS недостаточно. Текущий hosted FAIL сохраняется.

## Checklist gate и границы чтения

Полностью перечитаны оба checklist и текущие spec/plan/quickstart/contract;
текущие tasks и применимые целые controller/coordinator/fixture методы
сопоставлены с ними. Применены прочитанные в текущем диалоге AGENTS,
document-reading, конституция7.1.0, Spec Kit и правила доказательств/PR.
Полные исходники приложения и все сценарии серверного OAuth не аттестуются.
Это ограниченное предварительное исследование тестового порядка событий,
не повторная полная приёмка продукта или всей матрицы требований.

Существующие CHK018/019 уже требуют сохранения текущего продолжения при stale
callback и отделения исходного воспроизведения от предположения. Новых
продуктовых требований/способов входа/архитектуры для указанного tracing
не требуется. Требование не снимается из-за нестабильного результата.

Фактические counts после полного чтения: requirements16 checked/0 unchecked;
auth-navigation20 checked/0 unchecked. Отметки и исторические записи
не менялись. Это counts качества требований, а не36 PASS исполнения.
Предварительный gate для tracing и описанной ограниченной синхронизации
fixture удовлетворён; реализация и её итоговое ревью ещё не приняты.

Проверяющий записал только этот отдельный отчёт; checklist/code/spec/plan/tasks,
Git/GitHub, приложение, пользовательские данные, выпуск и deployment не менял.
T016, вся F136, installed GRAF Dev и внешний OAuth остаются отдельными воротами.
Согласованное окно серверного выпуска не является разрешением слить F136.

## SHA-256 исходного снимка HEAD до правок исполнителя

После предварительного допуска основной агент начал менять тест и план.
Таблица фиксирует прочитанные байты HEAD63272ac, а не эти новые рабочие
изменения; им потребуется отдельное итоговое ревью.

| Файл | SHA-256 |
| --- | --- |
| `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` | `4d1d05138a4a29d1bcc01353f33e2fb36d7c00dcaf7cd3a6b5d669920005dd2e` |
| `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` | `ea878feea392f0bdc3c24174c9cef2d1641b9338c943af731f19170194699df2` |
| `specs/136-auth-navigation-recovery/checklists/requirements.md` | `8f699db1eece911255ce4722b89cda5c192be63d7ad9782aa66889f3621c251b` |
| `specs/136-auth-navigation-recovery/checklists/auth-navigation.md` | `dc28283df729d2a978ee7e36b8b03d532c098516592891c67e5f161d17896e11` |


## Итоговое независимое ревью поправки fixture — 28.10.2026

Решение: **APPROVE ограниченной локальной поправки тестового fixture**.
Открытых замечаний и блокеров: **0**. Полоса остаётся существующей
high-risk-product F136/T012; продуктовая логика в этой поправке не меняется.
Предварительное решение и исходные контрольные суммы выше сохранены как
история; настоящее решение относится к окончательным рабочим байтам ниже.

### Проверка реализации и минимальности

Полностью перечитаны изменённые plan.md и validation.md, оба checklist,
spec.md, quickstart.md и действующий contract; текущий tasks.md сопоставлен
с ними. Полностью прослежены checkSessionBoundary, HTTP receive helper,
SessionBoundaryRequests, все три callers receive helper и пути hold/release/
очистки, включая прежний history fixture и superseding form. Полный большой
тестовый файл не объявляется перечитанным целиком. Проверен весь текущий diff;
продуктовый EmbeddedCabinetWebView.swift и tasks.md побайтно совпадают с HEAD.

- Новый holdResultResponse включён только providerLink && probeStaleCallbacks.
  Единственный соответствующий caller проверяет внешний policy после terminal
  и возвращается до дальнейшего callback/result GET; новая ветка не удерживает
  дополнительный запрос результата в этом сценарии. Остальные callers получают
  false по умолчанию и сохраняют прежнюю отмену/ресурс/redirect обработку.
- Полные HTTP bytes с точным Content-Length и соединение сохраняются под
  существующим NSLock до submitted.fulfill. Ожидание submitted теперь означает,
  что текущий ответ удержан; WebKit не может закончить его до проверки.
- До прежней ручной доставки старых didCommit/didFinish/didFail проверяются
  loading, тот же currentItem и sessionBoundaryID. После неё сохранены исходные
  assertions loading/currentItem и добавлена та же проверка boundary. Ни один
  исходный callback, assertion или timeout не снят.
- Release атомарно извлекает и очищает connection/bytes под lock; настоящий
  send выполняется вне lock. Отсутствие удержанного ответа вызывает XCTFail,
  а не искусственный успешный callback. Прежний defer отменяет оставшееся
  соединение и очищает bytes при ошибке/выходе. Старые hold callers передают
  response=nil; attemptHeldRedirect не пересекается с новым активным сценарием.
- После release ожидается настоящий terminal; сохранены один POST, отсутствие
  GET-повтора действия, прежняя boundary и реальная action/policy probe.
  Retry/sleep/skip вместо серверного барьера не добавлены. Новых зависимостей,
  инфраструктуры, условий продукта или ослабления current/attachment guards нет.

### Независимая проверка журналов

Проверяющий самостоятельно пересчитал terminal test IDs и SHA-256 полных
журналов. В контексте прочитаны относящиеся к решению traces, ошибки,
terminal summaries и причины SKIP; все многостраничные журналы не выдаются
за прочитанные построчно. Новых тестов/сборок проверяющий не запускал.

| Журнал | Проверенный результат |
| --- | --- |
| f136-macos-pr-40609780164-failure-20261028.log |1296 уникальных:1293 PASS/1 FAIL/2 SKIP; исходный hosted отказ сохраняется |
| f136-stale-scheduling-diagnostic-20261028.log |1 уникальный FAIL,2 assertions,0 unexpected; до injection loading=false/sameItem=false |
| f136-stale-held-response-focused-20261028.log |1 уникальный PASS,0 FAIL/0 SKIP; before/after-stale traces и terminal присутствуют |
| f136-stale-held-cabinet-20261028.log |106 уникальных PASS,0 FAIL/0 SKIP,0 дублей |
| f136-stale-held-full-20261028.log |1296 уникальных:1287 PASS/9 SKIP/0 FAIL,0 дублей;165.926s tests/166.050s suite |
| f136-stale-held-contract-20261028.log |Build complete; ContractValidation PASS |

106 профильных ID совпадают с прежним окончательным профильным набором;
1296 полных ID совпадают с прежним окончательным полным набором. Добавленных
и удалённых ID нет. Направленный тест и весь профиль входят в полный набор;
их результаты не суммируются. Исполнитель сообщил exit0 полного запуска и
ContractValidation; прочитанные terminal summaries подтверждают успешный
XCTest и ContractValidation PASS.

Семь SKIP — пять DesktopNotificationAccessibility и два
DesktopNotificationPromptLifecycle: среда не подтвердила фокус обычного
AppKit-окна без карточки. Ещё два — необязательные экспорты без
GRAF_CARD_SNAPSHOT_DIR и GRAF_PERMISSION_PREVIEW_DIR. Все девять остаются
пропусками, не PASS и не установленной приёмкой доступности GRAF Dev.

Диагностическая проба без hold подтверждает недостаточное предусловие при
явно достигнутом допустимом порядке завершённого POST. Она **не доказывает
историческую причину** GitHub FAIL и **не является продуктовым RED**.
Ручная повторная доставка старого настоящего WKNavigation проверяет заданный
порядок callbacks, а не естественно доставленную сетевую гонку WebKit.
Дополнение plan/validation сохраняет эти различия. Новый локальный PASS
не отменяет отказ macos-pr40609780164 и не подменяет будущий hosted результат.

### Повторный checklist gate и границы решения

Оба checklist перечитаны полностью после поправки и сопоставлены с текущими
требованиями: **requirements16 checked/0 unchecked; auth-navigation20 checked/
0 unchecked**. Отметки и исторические записи не менялись. Это 36 требований
к качеству спецификации, а не 36 успешных runtime сценариев.

Существующие FR-001/004/006/007/008 и CHK018/019 сохраняются; поправка делает
предусловие проверки старого callback явным, не добавляет продуктовую механику.
Текущий анализ/convergence в validation.md отделяет локальную реализацию от
непринятых GitHub gates и T016; tasks.md при этой поправке не менялся.

APPROVE разрешает продолжить оформление проверенной поправки по действующему
поручению. Нужны новый коммит, три новые обязательные GitHub проверки точного
SHA и проверенной основы через общий validator, освобождение согласованного
окна и обычное принятие PR. #4731/#4738/#4739 не закрываются этим ревью.
T016/#4743, реальный внешний OAuth, установленный GRAF Dev, вся F136, выпуск
и production остаются отдельными неподтверждёнными воротами.

Проверяющий изменил только этот отчёт. Код, spec/plan/tasks/validation,
оба checklist, Git/GitHub, приложение и пользовательские данные не менял;
тесты, сборки, release/deploy не запускал. git diff --check PASS.

### SHA-256 окончательных входов итогового ревью

| Файл | SHA-256 |
| --- | --- |
| apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift |4d1d05138a4a29d1bcc01353f33e2fb36d7c00dcaf7cd3a6b5d669920005dd2e |
| apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift |059c238cc07ce1dae7b5c12890c4d7b7a2e999e306164a5b63df5a1b8ad209c8 |
| specs/136-auth-navigation-recovery/spec.md |69234779eb8f5a0daa792972e0851aeeda1911dae7a8fc507883fed93a2436e7 |
| specs/136-auth-navigation-recovery/plan.md |32ba7add4a7ac20329061080d463c05bf632b9afd7cd421fcb85764bb2c5ee71 |
| specs/136-auth-navigation-recovery/tasks.md |3c1bfdca97f971ee791600a4d3d551f1c78c02a4ea29c624fe841aaa8f2b15a9 |
| specs/136-auth-navigation-recovery/quickstart.md |cf4e6d9f0e507b26a112e9560079c5cdf3db30dde5f026cfaa577bffdf896be9 |
| specs/136-auth-navigation-recovery/contracts/cabinet-navigation-lifecycle.md |3321cf9d068ae6bd2cc995f1523c9034addbdcbe61ed49b03017d19d3e9d1a29 |
| specs/136-auth-navigation-recovery/checklists/requirements.md |8f699db1eece911255ce4722b89cda5c192be63d7ad9782aa66889f3621c251b |
| specs/136-auth-navigation-recovery/checklists/auth-navigation.md |dc28283df729d2a978ee7e36b8b03d532c098516592891c67e5f161d17896e11 |
| specs/136-auth-navigation-recovery/validation.md |86daa7e7df08aecf602a631e8c5ac46c26b5a647ef01d79480db7239efe6994a |

Все журналы сохранены во внешнем реестре `graf-repository-audit`
за 27–28.10.2026.

| Журнал | SHA-256 |
| --- | --- |
| f136-macos-pr-40609780164-failure-20261028.log |3d1977eab3478c7bce0286349ccb285cad444867af9075fc38796c59b6858cca |
| f136-stale-scheduling-diagnostic-20261028.log |50a3573fe80cb6b2f6c027938c4123828c4723238796657926345ffc6a79a0d1 |
| f136-stale-held-response-focused-20261028.log |cbeeee9e0d6e33d88d4b18e37f37ba5fcc8695334c365cac98ac8d394b1f9b11 |
| f136-stale-held-cabinet-20261028.log |c7443c6f53a8579b71e97e7ddd4518997bb08b7e6dd739762c53c248a4d62b31 |
| f136-stale-held-full-20261028.log |f2b4343fdf892501c40aedb636c80641f4d7a894acdac357b701bacbeecce8c3 |
| f136-stale-held-contract-20261028.log |a45b459282e79884f8aeecf1bfc2d0a221e641c3824ba857969b52a69f7e1f6c |
| f136-provider-link-stale-same-url-green-20261028.log |4b1023ede56bf53d583855fe56fd69b79bea96f2482f8704e23aa3de85b63ab9 |
| f136-provider-link-full-final-20261028.log |1dee5139e4124ce4c6cd90f9d536a0bc3f49d9e326cbbdaebbcbe3111acdedef |
