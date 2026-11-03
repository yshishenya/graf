# F262: независимый повторный обзор проверки Cabinet bridge

Дата: 2026-10-23. Проверяющий: `f262_requirements_reviewer`.
Исходный HEAD: `5a4485481a441b7a75dc224cb6c5e853c8b617e2`.
Полоса: существующая `high-risk-feature` F262; узкое исправление отказа общего JS в Node contract проверках после T024. Продуктовые требования не меняются.

**Решение: PASS для рассмотренного исправления. Неустранённых обязательных замечаний не найдено.** Проверено новое содержимое `cabinet.js`, его вызывающие, передача видимых IDs через существующий native bridge и связь с сервисом приоритета. Исправление сохраняет передачу видимости в поддерживаемом GRAF WebView и прекращает ненужное планирование этой native функции там, где мост отсутствует. Предыдущий независимый обзор T020/T024/T025 остаётся применим к совпавшим неизменённым байтам; новые JS байты рассмотрены здесь отдельно.

## Полномочия и точный diff

Проверяющий не запускал тесты, приложение, сборки и не менял код, spec, plan, tasks, чек-листы, Git/GitHub. Разрешена и выполнена запись только этого отдельного отчёта. Исполнитель работает в той же копии; его изменения сохранены.

При начале обзора dirty diff содержал только `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`: 3 добавленные и 2 удалённые строки, одна функция. Фактическая правка:

```diff
 const publishVisibleRecordings = () => {
-  if (visibleRecordingsFrame !== null) return;
-  visibleRecordingsFrame = requestAnimationFrame(() => {
+  if (visibleRecordingsFrame !== null || !window.webkit?.messageHandlers?.grafLocalRecording
+      || window.GRAFRecordingDeletionBridgeVersion !== 1) return;
+  visibleRecordingsFrame = window.requestAnimationFrame(() => {
```

Прочитан весь helper и его существующие вызовы. SHA-256 окончательного рассмотренного `cabinet.js`:

`0ae5cbcce998004589cfa30760bc1fe3ad8ca9484024e5c78038ee98c411e02f`.

Сопоставление всех 10 runtime/test путей с манифестом [предыдущего обзора](review-t020-20261023.md) показало: **9 совпали, изменён только cabinet.js**. В частности, native App/workspace/bridge/player/service/client/model/tests и browser test не менялись относительно рассмотренного манифеста. Старый JS hash `208a69a8ffd5f0c1ca0d1fba1a5d9b99a4c93d4fb01810242c3456614986e08b` больше не описывает текущий JS.

## Причина отказа и оценка исправления

Общий `cabinet.js` исполняется обычными web страницами и существующими Node contract стендами без `grafLocalRecording`. В прежнем коде helper сначала обращался к глобальному `requestAnimationFrame`, а наличие native bridge проверял только внутри callback. Поэтому окружение без глобального имени падало ещё до проверки применимости native функции. Прочитанный отрицательный журнал содержит `ReferenceError: requestAnimationFrame is not defined` в 18 проверках, включая CSRF, responsive rail, list/detail recovery, focus и access loss. Этот результат не принят за успешный.

Новый guard проверяет наличие обработчика и версию 1 до планирования. При отсутствии моста или другой версии helper возвращается без изменения `visibleRecordingsFrame`, поэтому позднее появление поддерживаемого моста не блокируется устаревшим признаком запланированного кадра. Использование `window.requestAnimationFrame` соответствует браузерному API и форме существующих Node window fixtures. Дополнительного таймера, зависимости, обхода native проверок или изменения тестовых стендов не добавлено.

Проверка внутри callback сохранена: кадр сначала сбрасывает свой признак ожидания, затем заново проверяет текущий bridge/version. Исчезновение либо замена контекста между планированием и выполнением не приводит к вызову отсутствующего обработчика; после возвращения корректного контекста последующие события снова могут запланировать кадр.

## Общий путь и отсутствие ослабления видимости

1. Все существующие точки вызова остались: scroll с capture/passive, visibilitychange, resize; завершение рендера local rows, включая пустое состояние; `GRAFLocalRecordings.update`; существующий lifecycle refresh. Никакой caller не удалён и не заглушён.
2. В native WebView обработчик `grafLocalRecording` регистрируется конфигурацией; document script устанавливает `GRAFRecordingDeletionBridgeVersion = 1` в main frame на `atDocumentEnd`. `applyLocalRecordingRows` выполняет `GRAFLocalRecordings.update` после загрузки и при обновлении представления; этот путь явно вызывает helper повторно. Ранняя попытка до готовности document bridge не является единственной попыткой передачи.
3. Определение viewport и clipping ancestors, связанные local/server aliases, фильтры, пустое состояние, detail meeting ID, `document.hidden`, metadata-only payload `{action, version, ids}` и предел 100 IDs не изменены. Здесь не добавлены содержимое встреч, файловые пути или credentials.
4. `EmbeddedCabinetLocalRecordingBridge.visibleItemIDs` по-прежнему принимает максимум 100 уникальных известных native row IDs, только текущую list/detail route, для detail — matching UUID встречи. Coordinator сохраняет проверки main frame, attached WebView, текущего document URL, route policy и active состояния.
5. Callback по-прежнему проходит через workspace в `DesktopUploadQueueService.setVisibleRecordingItemIDs`; service добавляет эти IDs в общий priority set. Hint меняет порядок проверок, не разрешает доступ, открытие или физическую очистку. Пересмотренные SC-003 и lifecycle contract:39 требуют прежнего приоритета видимых/open origins; изменения этому требованию не противоречат.
6. App open и текущий managed player, объединение lifecycle tasks, scope/generation guards, два native HTTP разрешения и retry/jitter в этой правке не изменены. Их прошлое доказательство не выдано за новый запуск после JS правки.

В прочитанной цепочке не найден пропуск отправки поддерживаемых visible IDs или ослабление границ доступа/удаления.

## Прочитанные доказательства выполнения

Тесты запускал исполнитель. Проверяющий прочитал журналы и текущие browser assertions; собственного исполнения не заявляет.

| Проверка | Наблюдаемый результат | SHA-256 журнала |
|---|---|---|
| `f262-cabinet-contract-red-20261023.log` | До исправления: 18 failed, 58 passed, 1 deselected; непосредственный `ReferenceError` в helper. | `5d721dafd69038056e445d6e88aef0536f1273631430416c34f027c32115d43d` |
| `f262-cabinet-contract-green-20261023.log` | После исправления: 76 passed, 1 deselected, 2 warnings, 2,19 с. Исключённая проверка не считается пройденной. | `6d2a41699362fc5ae669ba386bbfb4cbfe86d75b926841b33d94a2bd6b89c1dc` |
| `f262-bridge-guard-chromium-20261023.log` | Окончательный `mixed-meeting-list.test.cjs` завершился PASS; stdout подтверждает весь файл. | `91cd7e45e767a84628f4c30ce45395082efec43ac694339f4128f26f38e83d71` |
| `f262-bridge-guard-webkit-20261023.log` | Тот же существующий browser файл завершился PASS в WebKit. | `91cd7e45e767a84628f4c30ce45395082efec43ac694339f4128f26f38e83d71` |

Журналы находятся в `/Users/yshishenya/Documents/Codex/2026-10-21/issues-334-audit/`. Текущее содержимое browser test проверяет наличие local/linked видимости, исключение offscreen/absent строк, изменение после прокрутки, очистку при пустой выдаче, matching detail и 100 уникальных IDs. Поэтому успешный browser файл подтверждает положительный native-bridge путь, а contract набор — восстановление выполнения общего JS без native bridge. Результаты разных наборов не складываются в число уникальных тестов.

Два предупреждения GREEN относятся к повторному pytest import rewrite и текущей Starlette/httpx deprecation; журнал не содержит падения теста из-за них. Отдельного утверждения о 77 успешно исполненных проверках здесь нет.

## Требования и reviewer-owned чек-листы

Полностью перечитаны оба существующих файла:

- `checklists/requirements.md`: **10 отмечено, 0 не отмечено**; SHA-256 `1f2eb553be24085e58d41a5238b2f68464bd1821522b811d5da1d4857f73f7dc`.
- `checklists/security-ux.md`: **10 отмечено, 0 не отмечено**; SHA-256 `7b98a6757ee1bc74d7635c7c22d14c01c1dddc996fa24baa2be696c1be857fc3`.

Нового противоречия качеству требований, scope, privacy/access/deletion, доступности и сохранению ручного Stop не обнаружено. Все отметки и предыдущая история сохранены. Эти итоги относятся к качеству требований и не превращают checklist в доказательство готовности приложения или выпуска.

## Пределы вывода

PASS относится к приведённому diff и SHA-256 JS. До закрытия T020/#6895 нужны обязательные GitHub проверки нового точного SHA и проверенной основы, общий валидатор, слияние и актуальная итоговая проверка. Неуспешный governance attempt 2 не объявляется успешным; новые локальные результаты его не заменяют.

Полная F262, T019/T021/T022/T023, установочные остатки T013/T016, GRAF Dev/VoiceOver/keyboard, SC-002/003/006/007, upgrade/rollback/restore, release-full и выпуск/развёртывание сохраняют отдельные доказательства и открытые границы, перечисленные в предыдущем отчёте. Этим узким повторным обзором они не закрываются. При изменении рассмотренных JS байтов требуется заново проверить применимость вывода.
