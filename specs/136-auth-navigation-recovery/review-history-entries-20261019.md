# Независимое ревью истории F136 — 2026-10-19

Рецензент `/root/f263_performance_review`. Просмотрен локальный diff поверх
`e415145a85e5b8af4a79c3ad5ee11b950460ccc0` в
`codex/136-auth-navigation-recovery`. Полоса high-risk-product / auth-navigation.

**Предварительное решение: REQUEST CHANGES.** Положительный сценарий нового GET
доказан, однако новый pending-флаг не очищается на всех существующих терминальных
путях. Слияние и продуктовая приёмка остаются на стопе.

## Найденные проблемы

### R1 — очистить pending-флаг и отделить завершение ресурса от документа

`pendingHistoryRequestIsSafe` очищается в didFail/didCancel, attach/detach и
commit boundary, но не в `navigationDidStart(nil)`, `cancelPendingNavigation`
и `clearPendingNavigation`. Более того, `observeNavigationRequest` для разрешённого
artifactDownload возвращается до нового присваивания, сохраняя прежний флаг.
При этом один `navigationDidFinish` используется как для настоящего didFinish
документа, так и для download/cancelResource/didBecome download. Новый блок
на строках484–491 всегда изменяет **текущий** WKBackForwardListItem, даже если
terminal относится к ресурсу, который не заменил документ.

Поэтому последовательность «запрос с pending safe=true → его отмена/перехват →
разрешённый download → его terminal» может применить чужой safe-флаг к прежней
POST-записи. На этом пути код удалит item из unsafeHistoryItems и его URL из
unsafeHistoryURLs; это нарушает главное требование не реабилитировать старый POST.
С pending=false возможна обратная порча: прежняя безопасная страница становится
unsafe из-за чужого resource terminal. Вывод основан на полном статическом
проходе вызывающих, не выдаётся за воспроизведённую реальным WebKit доставку.

Нужно очистить новый флаг на всех отменённых/исключённых путях и ограничить
реабилитацию подтверждённым завершением именно документной навигации. Требуется
направленная регрессия «старый документ/POST → отменённый запрос → download
terminal», чтобы этот путь не повышал старый item до safe. Один green сценарий
POST→настоящий GET недостаточен.

### R2 — заменить300ms на подтверждённое решение настоящего policy delegate

В новом test последнее `web.go(to:postItem)` проверяется лишь после фиксированных
300ms. Если policy отложен или WebKit медленнее, неизменный текущий URL и счётчик
ещё не доказывают отклонение: проверка может закончиться до решения.
Нужно дождаться наблюдаемого `.cancel` настоящего coordinator и затем проверить
неизменный item/POST count. Предложенный test-only forwarding WKNavigationDelegate
подходит при условии, что он вызывает сохранённый настоящий Coordinator с тем
же action/WebView и передаёт WebKit полученный policy без подмены. Он должен
оставаться жив до callback; исходный delegate восстанавливается штатно. Сам
наблюдатель не должен принимать решение `.cancel` за продукт или менять action.

## Проверенная часть решения

- Реальная RED `history-new-get-red-clean.log`: ровно один отказ — новый GET
  не восстановил Reload. Предыдущие промежуточные эксперименты не принимаются
  за итоговые прогоны.
- `history-url-only-incomplete.log` и method experiment показывают, почему одного
  восстановления URL недостаточно: при выборе старого item WebKit сообщает POST,
  а разрешённые записи дают GET. Временные print в финальном diff отсутствуют.
- Текущий `history-entry-green.log`: новый полный тест PASS. Он проверяет actual
  GET, Reload, повторный native Back/Forward через одинаковые URL, отличный
  oldPOST item, отсутствие второго POST и сохранение живого WebView. Его
  последний direct-history шаг имеет ограничение R2.
- Weak NSHashTable переиспользует существующий подход invalidNavigations и
  не удерживает историю навсегда. Native selection исключает конкретный unsafe
  item до nearestDistinctHistoryItem; это правильнее голой реабилитации URL.
- Неоднозначный прямой history/gesture к URL с retained unsafe item отклоняется:
  public action не несёт item identity. Это сознательное fail-closed ограничение,
  может блокировать и безопасный GET item того же URL; native controls выбирают
  проверенный item и остаются полезными. Это ограничение нужно честно сохранить
  в validation, не выдавать за полную эквивалентность жестов и native selection.
- `isCurrentNavigation` проверяется перед терминальной записью; stale identity
  не должна менять ledger. Redirect обновляет target в существующей identity,
  actualGET после303 должен доказаться реальными action callbacks. Ошибки/отмена,
  повторная отправка и resource terminal требуют регрессии нового состояния.
- Attach/detach/commit boundary очищают weak items и pending-флаг. При401 прежние
  protected commands блокируются существующим sessionExpired. Это не заменяет
  исправление R1 и отдельную подтверждённую проверку hosted CI.

Рецензент не запускал окон, Dev, тестов или сборок, код и чужие документы не
менял; создан только этот отчёт. Полный текущий прогон на момент просмотра
ещё записывался, поэтому окончательные числа не приводятся. Checklist36/0
ранее подтверждает качество требований, а не приёмку этого алгоритма.


## Повторное независимое ревью после R1/R2

**Текущее решение: APPROVE ограниченной реализации; R1 и R2 сняты.**
Предварительное REQUEST CHANGES выше описывает первый просмотренный вариант.
Решение ниже относится к контрольным суммам в конце раздела. Merge и итоговая
приёмка GitHub/всей F136 остаются отдельными воротами.

### R1: фактическая повторная проверка

Прочитан весь обновлённый product diff и повторно сверены все пять вызывающих
общего `navigationDidFinish`. Новый `confirmsDocument` по умолчанию false;
единственное `confirmsDocument: true` находится в настоящем
Coordinator.webView(_:didFinish:). Следовательно, didBecome download в обоих
вариантах, download response и cancelResource не могут выполнить блок изменения
weak unsafe item/реабилитации URL. Они по-прежнему завершают загрузочное состояние
через прежний helper, не объявляя resource новым документом.

Новый pending-флаг теперь очищен при navigationDidStart(nil),
clearPendingNavigation, cancelPendingNavigation и перед ранним artifact return.
Ранее имевшиеся сбросы attach/detach/commit/didFail/didCancel сохранены. Смена
identity сохраняет новый action-флаг, а проверка isCurrentNavigation выполняется
раньше изменения ledger; старый terminal не должен присвоить pending-результат
новой навигации. Redirect использует существующую identity и action-флаг
настоящего последнего запроса. Само finish-синтезирование URLRequest имеет
registersNavigation=false и не устанавливает pending safe.

Важное уточнение доказательства: новый реальный supersededGET→artifact404
сценарий **не воспроизвёл** статически найденный риск R1 на прежнем ledger.
После исправления ожидания rollback сам `history-resource-terminal-red-settled.log`
показывает 1 PASS. Первый отказ теста был преждевременной проверкой transient
currentItem до rollback, а не повышением POST до safe. Поэтому прежний вывод R1
сохраняется как найденная неполнота общего состояния/потенциальный риск, не как
подтверждённый реальным WebKit повтор POST. Его минимальная защита теперь явна
в коде; текущий real-resource сценарий проверяет инвариант сохранения unsafe
POST-документа при ресурсе и не выдаётся за RED→GREEN этого риска.

### R2: фактический forwarding probe

Перечитан `HistoryPolicyProbe`: он передаёт исходные WebView/action настоящему
сохранённому Coordinator, получает фактический policy, сохраняет method/policy,
вызывает исходный decisionHandler с тем же policy и только затем fulfils expectation.
Он не выбирает cancel и не заменяет продуктивное решение. Тест ожидает callback,
проверяет `.cancel` и `POST`, восстанавливает coordinator и условно ждёт
реального rollback currentItem/isLoading. Фиксированного300ms больше нет;
после ожидания сохраняются проверки URL/item/POST count. На проверенном пути
cancel не создаёт нового запроса или состояния документа, требующего
подмены terminal callback рецензентом/тестом. Остальные шаги используют настоящий
Coordinator без probe.

### Независимо проверенные журналы и пределы

Рецензент самостоятельно пересчитал уникальные XCTest outcomes:

| Журнал | Различных | PASS | SKIP | FAIL | Область доказательства |
|---|---:|---:|---:|---:|---|
| history-current-full.log | 1246 | 1244 | 2 | 0 | Первый entry-ledger до последних R1/R2 дополнений |
| history-resource-terminal-red-settled.log | 1 | 1 | 0 | 0 | Старый ledger с исправленным ожиданием; не red R1 |
| history-entry-terminal-workspace.log | 61 | 61 | 0 | 0 | Текущий класс после confirmsDocument/reset/probe/resource изменений |

Эти числа не суммируются. Два SKIP первого полного запуска относятся к
необязательным image-export. Текущий полный повтор после последних изменений
ещё нужен: первый full не является full-проверкой последних контрольных сумм.
Ни локальный класс, ни первый full не подменяют новые обязательные GitHub
проверки точного будущего source SHA/текущей основы.

Рецензент новых окон, Dev, тестов или сборок не запускал: просмотр, анализ
вызывающих и самостоятельный пересчёт журналов не выдаются за второй runtime.
Новых подтверждённых ошибок текущего исправления не найдено. Ограничение
неоднозначного gesture/direct-history для URL с unsafe item остаётся сознательным
fail-closed: безопасный native item доступен, неоднозначное действие может быть
отклонено. В validation это нужно прямо указать; старый POST ни при каких
обстоятельствах не становится разрешённым только из-за более позднего GET.

### Принятые контрольные суммы

```text
dca71fb3eaf1fd9609daca1adec01691c8f9d9e62d48887c4d8203189c2a3dfa  apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
8e8d1cef5d86543fa35fed11c6e7d615c390cdbc605ff0aa80af3e4db83deed8  apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

`git diff --check` PASS. Изменения этого рецензента ограничены этим отчётом;
предыдущие checklist36/0 отражают качество требований и не переведены в
заявление о завершении всего продукта, OAuth, T016, выпуска или production.


## Финальная сверка полного набора и описания — 2026-10-19

**Решение по текущему исправлению: APPROVE; новых замечаний к коду нет.**
Контрольные суммы обоих Swift-файлов повторно вычислены и совпали с принятыми
выше. Новых тестов/окон/Dev рецензент не запускал.

Самостоятельный пересчёт `history-entry-terminal-full.log` по уникальным
XCTest исходам: **1246 различных тестов, 1237 PASS, 9 SKIP, 0 FAIL**.
Завершившийся suite сообщает113.132s. Это полный запуск последних принятых
контрольных сумм, который заменяет ожидание текущего full в предыдущем разделе.
Не суммировать его с предыдущим1246 или class61.

Два SKIP — прежние необязательные image-export. Ещё семь — самостоятельная
проверка фокуса обычного AppKit окна, не тест карточки:

- DesktopNotificationAccessibilityTests.testEscapeRestoresPreviousWindowAndCallbackReplacementKeepsItsFocus;
- DesktopNotificationAccessibilityTests.testExplicitFocusAndKeyLoopReachCloseCheckboxAndActions;
- DesktopNotificationAccessibilityTests.testExplicitFocusFromInactiveAppDoesNotDependOnAnotherSuiteActivation;
- DesktopNotificationAccessibilityTests.testFocusedKeyboardEventsToggleActAndCloseWithoutGlobalEscape;
- DesktopNotificationAccessibilityTests.testKeyboardScrollSurvivesTickAndTabReachesAction;
- DesktopNotificationPromptLifecycleTests.testKeyFocusHoldAndHoverOverlapResumeOnlyAfterBothEnd;
- DesktopNotificationPromptLifecycleTests.testPromptAndMeetingDeadlinesIgnoreHoverAndKeyFocus.

Причина каждого из семи в журнале одинакова: тестовая среда не подтвердила
фокус обычного AppKit окна без карточки. Перечитан существующий
F277CardTestSupport.requireFocusHost: он проверяет отдельное обычное окно до
проверки продукта, а skip прямо обозначен отсутствующим GUI-доказательством,
которое требует отдельной проверки в GRAF Dev. Эти guards и notification files
не менялись текущим diff. Поэтому семь SKIP не являются найденным отказом
истории F136, но их нельзя объявлять PASS, необязательным экспортом или
завершённой проверкой доступности/фокуса установленного приложения.

Фактически прочитаны актуальные новые разделы plan/spec/validation и fragment:

- Spec однозначно различает отдельные POST/последующий настоящий GET и сохраняет
  запрет синтетической реабилитации и старого POST.
- Plan описывает weak item ledger, реальный didFinish, reset, реальные callbacks,
  а также честно отделяет static resource-risk от воспроизведённого продуктового RED.
- Plan и fragment явно сохраняют ограничение неоднозначных gestures: native
  controls выбирают конкретный безопасный item, а public action без его identity
  может консервативно отклоняться при unsafe item того же URL. Новая безопасная
  GET-запись не легализует старую POST-запись; полной эквивалентности gesture/native
  navigation не заявлено.
- Validation сохраняет оба прошлых CI отказа и результат опубликованного
  e415145a85e5b8af4a79c3ad5ee11b950460ccc0 отдельно от непубликованной истории.
  Его упоминание трёх PASS и checked base сверено с сохранённым
  js-result-exact-pr-checks.json: base03cea84dc5deb1d77ea7b4ac2356fa9819123aa9,
  governance39229930021, native39229930216, metadata39230178598. Это просмотр
  сохранённого доказательства, не новый live validator и не доказательство
  нового будущего коммита.
- На момент чтения концовка validation ещё говорила, что окончательный full
  выполняется отдельно; владелец дополняет её настоящими1237/9/0 и converge.
  Результат1244/2 относится только к прежнему промежуточному ledger. До
  окончательного commit нельзя оставлять устаревшее текущее ожидание full или
  подменять им новые семь пропусков. Reviewer чужую validation не редактирует.

Reviewer-owned списки перечитаны и пересчитаны: auth-navigation20/0,
requirements16/0, всего36/0. Их состояние не менялось; эти отметки принимают
качество требований, не установочную приёмку. Все правки этого reviewer
ограничены данным отчётом.

Свежие GitHub checks точного нового SHA/base, обычный общий validator, принятие
PR и разрешённое окно слияния остаются обязательными. Семь focus-проверок
остаются неполученным GUI evidence; OAuth, T016, итоговая T017, выпуск и
production не объявляются завершёнными этим результатом.


### Заключительное чтение обновлённой validation

После записи предыдущей сверки владелец добавил раздел «Окончательный
локальный результат и сверка —19.10.2026». Он перечитан фактически целиком:
числа1237PASS/9SKIP/0FAIL из1246 и113.132s совпадают с журналом;7focusSKIP
не названы приёмкой; пределы всей F136, новые GitHub-проверки и окно слияния
сохранены. Старое текущее ожидание full заменено ссылкой на новый результат.
Содержательных замечаний к описанию нет; предыдущее ожидание обновления
validation закрыто. Доказательство рискаresource не выдаётся за productRED.

Окончательные просмотренные документы:

```text
6810346229072b50319c981607a0fb2a3164105075a4024a624f0e4b7bcd2668  specs/136-auth-navigation-recovery/spec.md
4ed5a71e20986ff25ee7d2acf5bd7a2a02d44311f3a971b46ab59d9e1c63291a  specs/136-auth-navigation-recovery/plan.md
9fee7784243109604d81015a75fcacec6c720ded7eb4d67731ff67e2f31d331f  specs/136-auth-navigation-recovery/validation.md
38e92efa7ef4921bc5ec39b789b6b8564a886cf7f363d2192909a5d9b430df64  changes/unreleased/F136.yaml
```

Итог независимой сверки кода и фактического описания: **APPROVE в указанном
объёме; findings0**,36checked/0unchecked по качеству требований. Это остаётся
одобрением подготовленного исправления и отчётности, не завершением F136,
семи отсутствующих GUI-проверок, нового hosted CI или разрешением merge/release.
