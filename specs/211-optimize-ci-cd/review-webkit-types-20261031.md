# F211/A14/T107: независимая проверка требований WebKit

Дата: 2026-10-31. Полоса: существующий срез Spec Kit, инфраструктура CI.
**Итог требований: SCOPED PASS. Критических/высоких замечаний: 0.**
Checklist перечитан после изменения: **6 отмечено / 0 не отмечено**.
Это проверка требований до реализации T107, не приёмка исправленного кода.

## Назначение и версия

Ветка `codex/211-macos-runner-migration`, HEAD
`45f783a5a6789db03e3530194be92453c0a86974`. Активный указатель и
`check-prerequisites.sh --json --paths-only` подтверждают F211, каталог
`specs/211-optimize-ci-cd`; указатель перечисляет T105/T106/T107.

Основной агент явно ограничил повторную приёмку целыми применимыми разделами
A14, FR038/059–061/SC026/T105–107 и зависимостями выбора WebKit callback types.
Прежняя программа F211 повторно целиком не принимается. Предыдущее ревью
требований A14 сохранено в `review-runner-image-20261031.md`.

Прочитаны root AGENTS, guidance README/document-reading/codex-worktrees/
development-process/spec-kit-flow и конституция; применимые целые разделы
Local Validation, Validation Lanes, Local development, PR and merge,
Git Safety/Evidence Safety из release-and-validation. Повторно прочитаны
текущие A14 и T107 в spec/plan/tasks/quickstart и checklist целиком.
Использован навык code-reviewer. Новые требования не меняют захват,
авторизацию, предпочтения, разрешения, публичный выпуск или доверие.

Разрешены и изменены только `checklists/runner-image.md` и этот отчёт.
Остальные незакоммиченные изменения принадлежат основному агенту и сохранены.

## Фактическое основание

Прочитаны относящиеся к среде и первым отказам фрагменты завершённого
журнала `/tmp/f211-native-attempt1.log` запуска
[41215353665](https://github.com/yshishenya/graf/actions/runs/41215353665).
Reviewer не получал этот журнал через новый запрос GitHub; это локальная
копия настоящего запуска, переданная исполнителем. Её SHA-256 записан ниже.

- Строки 949–956: оба compiler сообщают Apple Swift 6.0.3; developer path
  указывает на Xcode16.2, SDK — MacOSX15.2.sdk. Ошибка выбора среды отсутствует.
- Строки 1058–1114: recording и notification settings не соответствуют
  `WKScriptMessageHandlerWithReply`. Требуемый callback имеет тип
  `@MainActor @Sendable (Any?, String?) -> Void`; выбранный старый alias —
  `(Any?, String?) -> Void`.
- Строки 1158–1183: Coordinator не соответствует `WKDownloadDelegate`.
  Требуется `@MainActor @Sendable (URL?) -> Void`, выбран старый `(URL?) -> Void`.
- Строки 1185–1260 дополнительно показывают несовпадение необязательных
  delegate methods подтверждения JavaScript, navigation action/response и
  выбора файла. Их callback также должен быть `@MainActor @Sendable`.
  Поэтому исправление охватывает всю существующую группу из пяти alias,
  а не только один обязательный download method.

Два `#if swift(<6.1)` в текущем коде выбирают старые типы на Swift6.0.3.
В обеих существующих ветвях `else` уже записаны требуемые атрибуты и payload.
Требование FR061 убрать старый выбор обосновано фактическим SDK, без смены
compiler/SDK, новых адаптеров, обходов или изменения ожиданий тестов.

## Все alias и места использования

Поиск точных шести имён по репозиторию и чтение объявлений/методов выявили
следующие места, помимо самих объявлений. Номера строк относятся к исходному
состоянию до T107; удаление условных ветвей их сдвинет.

| Alias и сохраняемый тип после `@MainActor @Sendable` | Места использования | Почему требования достаточны |
| --- | --- | --- |
| `RecordingSettingsReply`: `(Any?, String?) -> Void` | recording bridge:132; notification bridge:140 | Обе bridge class имеют `@MainActor`. Сохраняются проверки webView/main frame/origin/nonce/route, у уведомлений также auth epoch и проверка актуального документа после await. Notification consumer использует общий alias, поэтому третий source file менять не требуется. |
| `EmbeddedCabinetNavigationDecisionHandler`: `(WKNavigationActionPolicy) -> Void` | WebView:2012,2306,2326; WorkspaceTests:2278,2302; SessionBridgeTests:551; PaymentPopupTests:248 | Coordinator и тестовые delegate class изолированы MainActor. Сохраняются async preparation, auth barrier, актуальность навигации, payment handoff, разрешение маршрутов и все решения allow/cancel/download. |
| `EmbeddedCabinetNavigationResponseDecisionHandler`: `(WKNavigationResponsePolicy) -> Void` | WebView:2804; WorkspaceTests:2273 | Существующие MainActor delegate/probe, состояния сессии и cancel/download policy остаются прежними. |
| `EmbeddedCabinetOpenPanelCompletionHandler`: `([URL]?) -> Void` | WebView:2643 | Сохраняются attached/active, same-origin/main-frame allowlist, единственный файл и отмена. |
| `EmbeddedCabinetDownloadCompletionHandler`: `(URL?) -> Void` | WebView:2573 | Сохраняются active, безопасное имя, настоящий save panel, отмена и выбранный URL. |
| `EmbeddedCabinetConfirmCompletionHandler`: `(Bool) -> Void` | WebView:2120 | Сохраняется передача существующей функции подтверждения с проверкой origin/main frame/window, отменой по умолчанию, защитой от двойного ответа и отменой при смене документа. |

Итого: 9 мест использования в продуктовых объявлениях и 5 в тестовых
delegate/probe declarations, в трёх source и трёх test files. Других мест
использования этих имён за пределами объявлений/документации не найдено.
Тела методов и тестовые consumers изменять FR061/T107 запрещает.

## Проверка качества CHK006

| Часть требования | Конкретное основание | Итог |
| --- | --- | --- |
| Причина и точная среда | FR061 связывает изменение с failed run41215353665, Swift6.0.3/SDK15.2; журнал содержит реальные compiler signatures. | PASS |
| Минимальный объём | Ровно две существующие группы объявлений; удалить старые ветви/directives и сохранить нынешние MainActor/Sendable aliases. Новые helpers, fallback и разрешения запрещены. | PASS |
| Полнота consumers | Plan требует проверить все consumers; найденные три product files и три test files перечислены выше. Notification получает исправление через общий alias. | PASS |
| Неизменные ограничения поведения | FR061 явно сохраняет все тела, callback/async, origin/nonce/access, навигацию, загрузки и настройки; plan/quickstart запрещают изменения других code bodies. | PASS |
| Проверяемая приёмка | T107 и quickstart требуют compilation, существующие XCTest/ContractValidation и независимое ревью реализации. Plan различает локальный текущий SDK и настоящий закреплённый CI. T106 зависит от T107 и требует новый native и три exact-SHA/base checks с общим валидатором. | PASS |
| Совместимость | FR061 разрешает прекратить сборку старым SDK14, сохраняя deployment target macOS14. `Package.swift` действительно задаёт `.macOS(.v14)`; это отдельное понятие, а не обещание сборки SDK14. | PASS |

CHK001–CHK005 не переписаны и сохраняют прежнюю приёмку требований A14.
Дополнение FR061 явно расширяет прежний объём «только CI» двумя
объявлениями типов; это уточнение читается вместе с прежними формулировками.
Оно не даёт права менять UX или доверие. Противоречий, блокирующих
ограниченную реализацию T107, не найдено. Требование отдельного нового тестового
каркаса не нужно: compiler проверяет protocol conformance, а существующие
тесты содержат настоящий WebKit exchange записи/уведомлений, JavaScript
confirmation и navigation probes, а также отрицательные route/file guards.
Их исполнение ещё требуется; существование теста не объявляется его PASS.

## Ограничения и следующие ворота

Это SCOPED PASS качества требований. Reviewer не запускал тесты, сборку,
приложение, CI или сеть; не менял Git/GitHub, продуктовые файлы, задачи,
spec/plan/quickstart, выпуск или развёртывание. Локальный журнал доказывает
исходный отказ; исправление ещё не реализовано и не принято этим отчётом.

До кода основному агенту требуется оставшийся analyze/issue-sync gate.
Далее обязательны минимальный diff, компиляция/существующие регрессии,
независимое ревью реализации, настоящее build/XCTest/ContractValidation
на Swift6.0.3/SDK15.2 и новые проверки точного SHA/основы. После любого
нового коммита прежние результаты не принимаются за proof нового SHA.

GRAF Dev, установленная совместимость macOS14, публичные пакеты,
подпись/нотаризация, выпуск, production, Windows, остальные задачи F211
и закрытие #7834 этим ревью не принимаются. Будущий замороженный выпуск
по-прежнему требует один authoritative release-full.

## SHA-256 проверенных исходных документов

Хеши ниже фиксируют прочитанное состояние, не результат исполнения продукта.

```text
24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958 AGENTS.md
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8 .specify/memory/constitution.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411 docs/agent-guidance/document-reading.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e docs/agent-guidance/spec-kit-flow.md
ff0d996c95101d5f782259661131db1b7528b3bf58991603f5652092e1e5256f docs/agent-guidance/release-and-validation.md
41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864 docs/agent-guidance/development-process.md
d7d8c9cce8315c17efaa1da05ece80c2542ca01b966f81fb848580104b785e1d docs/agent-guidance/codex-worktrees.md
3c961064d16d79cb1812f79255287b927deec8afeda5569c8564183853049ecb specs/211-optimize-ci-cd/spec.md
bdcb031ef259f4b8e1a76a9de24b4f5afad13312bc6dc8cacdf2e36404fb4312 specs/211-optimize-ci-cd/plan.md
18449885ef7753e692d67b010749827d106e192ebd1144c450114bb7efa095fa specs/211-optimize-ci-cd/tasks.md
7104f049cab290463b8812cf1801cbb6c6e3031d9ea4aae5c5348133ec2f2951 specs/211-optimize-ci-cd/quickstart.md
51194127db5fbf544eb5325250e43f6c7ba75a67a0b22185db05652a9e680358 apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetRecordingSettingsBridge.swift
90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift
4d1d05138a4a29d1bcc01353f33e2fb36d7c00dcaf7cd3a6b5d669920005dd2e apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
00be33a568134c2addbd2d14a722c4fbb9accf54b915862293373e8cb753eca7 apps/macos/Package.swift
0ea17779b4d1489c9b363fbcc424534f2c318fee0b2902e69954604326c63eff f211-native-attempt1.log
```
