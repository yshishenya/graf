# F211/A14/T107: независимое ревью исправления типов WebKit

Дата: 2026-10-31. Полоса: существующий срез Spec Kit, CI.
**Код: SCOPED PASS. Критических/высоких замечаний, P1/P2: 0.**
Местная сборка и ContractValidation завершены успешно; XCTest: 1296 всего,
1287 PASS, 9 SKIP, 0 отказов. Новый настоящий запуск закреплённого CI
обязателен. Этот результат не закрывает T106, #7834 или общую F211.

## Область и источники

Рабочая ветка `codex/211-macos-runner-migration`, исходный HEAD
`45f783a5a6789db03e3530194be92453c0a86974` плюс текущий diff.
Reviewer может менять только этот отчёт. Изменения других участников
сохранены; source/spec/tasks/checklist/Git/GitHub/Dev не менялись.

Использованы текущие FR038/059–061/SC026/T105–107 и целые разделы A14
из spec/plan/tasks/quickstart. Требования и действующие инструкции прочитаны
в предшествующем формальном проходе этого же диалога, не пересказаны
другим агентом; их текущие хеши и checklist совпали с принятыми при
проверке требований `review-webkit-types-20261031.md`.
Checklist остался **6 отмечено / 0 не отмечено**, reviewer его не менял
в проходе реализации. Прежняя программа F211 вне повторной приёмки.
Использован навык code-reviewer.

Прочитан полный diff двух изменённых Swift files. Шесть alias и все
девять product/пять test declaration consumers независимо рассмотрены
в requirements review непосредственно перед этой реализацией.
Сейчас проверено отсутствие изменений в телах методов и consumers.
Использован исходный журнал failed native run41215353665 и завершённые
местные журналы сборки, списка XCTest, исполнения тестов и ContractValidation.
Журналы переданы исполнителем, reviewer заново
не получал их через GitHub и не выполнял сборку самостоятельно.

## Точность минимального изменения

| Файл | Фактическая правка | Проверка |
| --- | --- | --- |
| `EmbeddedCabinetRecordingSettingsBridge.swift` | Удалены 4 строки: `#if swift(<6.1)`, старый alias, `#else`, `#endif`. Существующий `RecordingSettingsReply = @MainActor @Sendable (Any?, String?) -> Void` сохранён. | PASS |
| `EmbeddedCabinetWebView.swift` | Удалены 13 строк: начало условной группы, пять старых двухстрочных alias, `#else`, `#endif`. Сохранены прежние пять аннотированных alias для action/response, file picker, download и confirm. | PASS |

Итого **0 добавлений / 17 удалений**, ровно два source files.
Независимая механическая проверка прочитала исходные bytes через
`git show HEAD:<path>`, заменила каждый единственный условный блок его
существующей ветвью `else` в памяти и потребовала полного равенства текущему
файлу. Оба сравнения PASS; сохранено соответственно 1 и 5
`@MainActor @Sendable` aliases. Никаких файлов эта проверка не создавала.
`git diff --name-only -- apps/macos` содержит ровно эти два пути;
notification bridge, Package.swift и все тестовые consumers неизменны.

Таким образом, тела методов и все проверки origin/nonce/access/frame,
auth epoch/актуальности документа, navigation/payment, active/attachment,
отмены/выбора файла и JavaScript confirmation сохранены побайтно.
`@MainActor` классов и нынешние async/Task boundaries не менялись.
Новые адаптеры, права, fallback, зависимости или ожидания тестов не появились.

## Соответствие фактическому отказу

Исходный native run
[41215353665](https://github.com/yshishenya/graf/actions/runs/41215353665)
действительно выбирал Swift6.0.3 и Xcode16.2/SDK15.2. Compiler требует
`@MainActor @Sendable (Any?, String?) -> Void` у двух
`WKScriptMessageHandlerWithReply` implementations и
`@MainActor @Sendable (URL?) -> Void` у `WKDownloadDelegate`.
Старые ветви по версии языка выбирали другие типы; выбранные теперь
существующие aliases точно соответствуют этим payload/атрибутам.

В том же отказе компилятор сообщил о несовпадениях optional navigation
action/response, open-panel и JavaScript-confirm callbacks. Для них также
сохранены именно существующие аннотированные типы, а не ограниченное
исправление только download. Все consumers остаются в MainActor классах.
Это устраняет выявленный неверный выбор типов без переноса логики в новые
методы или изменения trust rules.

`Package.swift` сохраняет deployment target `.macOS(.v14)`. FR061 прямо
не требует сборки старым SDK14; версия SDK сборки и минимальная версия
установленной системы различаются. Установленная совместимость macOS14
этим ревью не проверена и не принимается.

## Проверки исполнителя и независимая сверка

Команды сообщил основной агент:

```sh
swift build --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift
unset _SWIFTPM_SKIP_TESTS_LIST
swift test --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift list
swift test --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift --skip-build
swift run --package-path apps/macos --scratch-path /tmp/graf-f211-t107-swift --skip-build ContractValidation
```

Заявленная исполнителем местная среда: Apple Silicon arm64,
Swift6.3.3 (`swiftlang-6.3.3.1.3`), Xcode26.6 build17F113, SDK26.5.
Reviewer не запускал собственную команду определения среды.
Это диагностическая местная проверка; она не заменяет новый hosted
Swift6.0.3/SDK15.2 и не называется одинаковым окружением исходного RED.

- Прочитан завершённый журнал `/tmp/f211-t107-swift-build.log`:
  `Build complete! (31.05s)`, 0 `error:` diagnostics. Скомпилированы
  recording/notification/WebView, AppCore и исполняемые targets.
  Существуют предупреждения об отсутствии эффекта `@preconcurrency`,
  устаревших API и предпочтении async API. Предупреждений `nearly matches`
  в сводке сборки не найдено; предупреждения не скрыты изменением compiler flags.
- Прочитаны завершённые `/tmp/f211-t107-swift-list.log` и
  `/tmp/f211-t107-swift-tests.log`: список содержит 1296 уникальных XCTest,
  а журнал — ровно те же 1296 итоговых записей, без отсутствующих,
  дополнительных или повторных имён. Независимый разбор дал **1287 passed,
  9 skipped, 0 failed**. Итог `All tests` подтверждает те же числа и
  `129.987 (130.105) seconds`. Все команды завершились с кодом 0 по
  сообщению исполнителя; terminal success XCTest и список результатов
  независимо прочитаны reviewer. Завершающая строка Swift Testing с 0 tests
  не подменяет настоящий результат XCTest выше.
- Все девять причин пропуска прочитаны. Пять случаев
  `DesktopNotificationAccessibilityTests` и два
  `DesktopNotificationPromptLifecycleTests` не получили подтверждённого
  фокуса обычного AppKit-окна. Их поведение в GRAF Dev остаётся
  непроверенным этим запуском. Ещё два случая — необязательный экспорт
  изображений: `DesktopNotificationCardTests.testCardSurfacesCanBeCapturedForReferenceComparison`
  без `GRAF_CARD_SNAPSHOT_DIR` и
  `SystemAudioPermissionUXTests.testRenderSyntheticPermissionStates`
  без `GRAF_PERMISSION_PREVIEW_DIR`. Эти 9 случаев не считаются PASS
  или установленной приёмкой; никаких новых skip/filters исправление не вводит.
- Непосредственно относящиеся к consumers группы выполнены полностью:
  recording settings **5/5**, notification settings **8/8**, JavaScript
  confirmation **6/6**, workspace **83/83**, session bridge **13/13**,
  payment popup **8/8**, route policy **23/23**, WebView boundary **19/19**.
  Всего **165 PASS, 0 SKIP, 0 отказов**; их имена сверены с перечнем XCTest.
- Полностью прочитан `/tmp/f211-t107-contracts.log`, единственная строка:
  `ContractValidation: PASS`.
- Независимо выполнен только read-only `git diff --check`: PASS,
  а также описанные сравнения bytes, status и SHA-256.

## Остальные обязательные ворота

Код соответствует FR061; новых обязательных задач по этому diff не найдено.
Местные XCTest/ContractValidation завершены и независимо сверены с указанными
ограничениями. Оба исходных файла повторно совпали с записанными ниже
SHA-256 после завершения тестов. До приёмки оставшихся условий T107/T106
основному агенту нужен новый точный native PR run, выполняющий
build/XCTest/ContractValidation на Swift6.0.3/SDK15.2.
Три обязательных checks и общий validator должны связать новый head с
правильной основой до/после защищённого слияния. Новому коммиту нельзя
приписать старые source proofs.

Выпуск/production, GRAF Dev, установленная приёмка, подпись/нотаризация,
Windows, остальные критерии F211 и закрытие #7834 не входят. Никакого
нового release-full reviewer не запускал; будущий замороженный выпуск
по-прежнему требует собственное единичное авторитетное исполнение.

## SHA-256 проверенного состояния

```text
3c961064d16d79cb1812f79255287b927deec8afeda5569c8564183853049ecb specs/211-optimize-ci-cd/spec.md
bdcb031ef259f4b8e1a76a9de24b4f5afad13312bc6dc8cacdf2e36404fb4312 specs/211-optimize-ci-cd/plan.md
18449885ef7753e692d67b010749827d106e192ebd1144c450114bb7efa095fa specs/211-optimize-ci-cd/tasks.md
7104f049cab290463b8812cf1801cbb6c6e3031d9ea4aae5c5348133ec2f2951 specs/211-optimize-ci-cd/quickstart.md
8792320565e7d59eb83a608704309c732ac057aa4d0bc1c2d943cb5e93670ca9 specs/211-optimize-ci-cd/checklists/runner-image.md
14a62a3581d42b252cd6f8dd88b234e856632b7c2f1e0fc5caac350b08cdd870 apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetRecordingSettingsBridge.swift
3bc5278f9f42c2a90b7b68957ae65ae2ba0ebcfb640c66d6b31c6f1e56e2788f apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift
00be33a568134c2addbd2d14a722c4fbb9accf54b915862293373e8cb753eca7 apps/macos/Package.swift
059c238cc07ce1dae7b5c12890c4d7b7a2e999e306164a5b63df5a1b8ad209c8 apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
0659d1d46abe719db5f14931a1385b31a7997e6beed64a51fce0dc22433fa1a1 apps/macos/Shared/Tests/DesktopCabinetSessionBridgeTests.swift
51160ccd94c4149f0fd36a01b6e79a44a9b6e6f22cffd640635cc86902f63c30 apps/macos/Shared/Tests/DesktopCabinetPaymentPopupTests.swift
0ea17779b4d1489c9b363fbcc424534f2c318fee0b2902e69954604326c63eff f211-native-attempt1.log
af892cf6faf379fcc8d8deccb9fcfc0a4b3d0caeeef455fd0414ca1f0f98458b f211-t107-swift-build.log
20ec30e4c6e40db1ff74ca2412574cb250bc2245ce03648beb999ff3e8d1cfa4 f211-t107-swift-list.log
820e2540674757a4f43c0d2ceba0c869faa1d2578030bc23c4d59701742c7175 f211-t107-swift-tests.log
17189bd7192c0e37e850670a49ed6602566a183b4d772c368024c2674e389c87 f211-t107-contracts.log
```
