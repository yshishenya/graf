# F211/T108: независимая проверка готовности JavaScript — 31.10.2026

**Решение: SCOPED PASS для минимального тестового дополнения и нового CI.**
Открытых замечаний P1/P2, HIGH/CRITICAL в проверенном diff нет.
Это не приёмка T108/T106, #7834, PR #7835 или всей F211.

Проверенная основа `dc4e97d1b6aeae5857796979d7028b54ca194e75`, ветка
`codex/211-macos-runner-migration`, плюс текущий локальный diff. Активные
F211/T105–T108 подтверждены `.specify/feature.json`. Полоса
`active Spec Kit slice`, минимальная правка подготовки существующего теста.
Рецензент изменил только этот отчёт. Контрольный список, код, требования,
Git/GitHub, CI, приложение, разрешения, выпуск и серверы не менял.
Тесты и сборки самостоятельно не запускал; других агентов не запускал.

## Что проверено

Полностью прочитан `EmbeddedCabinetJavaScriptConfirmTests.swift`, diff к HEAD
(13 добавленных строк / 1 заменённая строка), A14/FR059–063 и дополнения
плана, весь `checklists/runner-image.md`, дополнение журнала валидации.
Сверены действующие `allowsJavaScriptConfirm`, настоящий WKUIDelegate callback,
`requestJavaScriptConfirmation`, cancel/finish и `didFinish` в coordinator.
Прочитаны точные отказы третьего закреплённого native и итог локального focused.
Применён порядок проверки code-reviewer; область ограничена заданием.

Новая проверка `responds(to:)` подтверждает наличие ожидаемого Objective-C
selector у настоящего coordinator; она сама по себе не доказывает, что WebKit
его вызвал. Делегатом остаётся тот же coordinator. Proxy/forwarder, поддельный
WKFrameInfo, прямой вызов confirm вместо JavaScript и изменение продукта в diff
отсутствуют.

Перед каждым из двух confirm настоящий `evaluateJavaScript(document.readyState)`
должен завершиться без ошибки и вернуть `complete`. Ожидание ограничено 5 s
через XCTest expectation. Если callback не пришёл, XCTest регистрирует отказ,
а guard предотвращает последующий confirm; тайм-аут не становится PASS.
Если пришли ошибка или иной readyState, отдельные XCTAssert уже дают FAIL,
даже при последующем продолжении. Это наблюдение реального документа,
а не замена готовности фиксированной задержкой или готовым результатом.

Сохраняются исходные ожидания navigation/WebKit/URL, отсутствие прежнего sheet
и pending confirmation, настоящий видимый NSAlert и его принадлежность окну.
Return по-прежнему посылается через performKeyEquivalent, Escape — через
NSApp.sendEvent; JavaScript должен закончиться с false и не выполнить
защищённое действие. Не удалены проверки default Cancel/явного Continue,
чужого origin/route/subframe, невидимого/занятого/отсоединённого окна,
повторов, запоздалого completion, навигации, detach/close/process termination.

Список всех шести test IDs до/после diff совпадает. Нет новых skip, ослабления
assertions, изменения timeout существующего confirm, обхода guards, нового
helper/dependency, изменения схемы доверия или пользовательских разрешений.
Новый текст ошибки показывает только состояние синтетического тестового окна.

## Сопоставление с доказательствами

Третий native run `41220589209` на указанном HEAD остаётся **FAIL**:
1296 XCTest, 9 прежних skip, 3 failures (1 unexpected), 213.976 s.
Журнал строк 11410–11414 показывает один реальный тест confirm: Return не
показал alert, XCTUnwrap не получил NSAlert, expectation JavaScript осталась
без ожидания после аварийного выхода. Строки 10911–10916 подтверждают PASS
трёх consumer cases. Их успех не скрывает общий отказ native.

Локальный журнал `/tmp/f211-t108-confirm-readiness-local.log` после окончательной
правки подтверждает **6 PASS / 0 SKIP / 0 FAIL**, 7.090 s. Прочитаны результаты
всех шести cases, включая настоящий JavaScript Return/Escape. SHA-256 source
совпадает с заданием: `2e6e3043b5228f7590bb8ac45a44568dcaa40d3f16313c3737072735b50b338e`.
Эти результаты подтверждают локальное исполнение; закреплённый
Swift6.0.3/Xcode16.2/SDK15.2 ими не принимается.

Гипотеза о разнице loading-флага и готовности JavaScript не доказана как корень
настоящего CI-отказа. Дополнение корректно выделяет эту предпосылку и сохраняет
проверяемый отказ. Отдельный selector assertion также является диагностикой,
а не подтверждением вызова callback. Дополнение validation правильно оставляет
причину неизвестной; формулировки об устранении дефекта не добавлены.

## Ограничения и дальнейшие ворота

После этих строк новый полный локальный XCTest здесь не подтверждён:
прежний полный локальный PASS нельзя выдавать за повтор этого source.
До завершения T108/T106 нужны новый полный native на закреплённой среде и
обязательные governance-fast/macos-pr/pr-metadata точного SHA и текущей основы
с общим валидатором. Старый native FAIL не отменяется этим review.
При новом отказе зависимая приёмка останавливается; продуктовый дефект нельзя
обойти изменением тестовых ожиданий. Merge и закрытие #7834 при FAIL запрещены.
Установленная приёмка macOS14, GRAF Dev, выпуск и production не входят.

Контрольный список перечитан полностью: **7 отмечено / 0 открыто**.
Он не менялся; это качество требований A14/T107/T108, не новая полная приёмка.

## Контрольные суммы

SHA-256 фиксируют проверенный рабочий текст и прочитанные журналы:

```text
2e6e3043b5228f7590bb8ac45a44568dcaa40d3f16313c3737072735b50b338e  apps/macos/Shared/Tests/EmbeddedCabinetJavaScriptConfirmTests.swift
3bc5278f9f42c2a90b7b68957ae65ae2ba0ebcfb640c66d6b31c6f1e56e2788f  apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
d795b863dd92d8a71648a30dfacae40ca01fef2936116b89d1df8fd935c28b48  specs/211-optimize-ci-cd/spec.md
ebe1487b5e8ceffbf3863441fad59135eaec066a8ec4fdffdc93672569a816ad  specs/211-optimize-ci-cd/plan.md
62a23dcf484d2c8cad5d1a1f152ed520cc66bd4faa1f0f3b80a385037a16e1aa  specs/211-optimize-ci-cd/checklists/runner-image.md
f67a1432c1f2c2c5b2a9bfd747a4a7fa4b8784757a58dcb7f7ffe876e5518483  specs/211-optimize-ci-cd/validation-runner-image-20261031.md
c94f8e089751159e381cfc4dc8c077279fb54a4bc4534da06e7c3b51b6fd658e  /tmp/f211-native-attempt3.log
a3d634230a953f9742a045f6cf8029b4f47fc6473ba0d264d10cc515c06a733a  /tmp/f211-t108-confirm-readiness-local.log
```
