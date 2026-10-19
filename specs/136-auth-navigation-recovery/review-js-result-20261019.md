# Независимое ревью результата JavaScript в fixture F136 — 2026-10-19

Рецензент `/root/f263_performance_review`; рабочая ветка
`codex/136-auth-navigation-recovery`, HEAD
`303a7573594b364bc6c25aaa7f980590ef41326b`, PR #7668.
Полоса: ограниченная поправка существующего теста внутри high-risk-product F136.

**APPROVE узкой поправки теста; новых замечаний к diff нет.**
Отказ GitHub ещё не объявляется исправленным, продуктовая приёмка и merge
по-прежнему не одобрены. Замечание unsafe history остаётся отдельным блокером.

## Фактически проверенное изменение

Две команды `evaluateJavaScript` в `checkSessionBoundary` заменяют только
последнее выражение `undefined` на `true`:

```swift
_ = try await webView.evaluateJavaScript("document.forms[0].submit(); true")
```

Stdlib-сравнение с HEAD подтвердило, что весь изменённый Swift-файл равен
старому файлу после ровно этих двух замен. Ни одно assertion, ожидание, timeout,
число отправок, условие supersedesPendingForm, порядок отмены, сессионные
проверки и проверка видимого результата не изменились. Код продукта не менялся.

Команда по-прежнему выполняет настоящий `submit()` в живом WKWebView; `true`
предоставляет явный ненулевой результат JavaScript для перехода в Swift.
Он не подменяет ответ сервера и не означает успешность формы: результат вызова
по-прежнему игнорируется, а успех проверяют прежние ожидания запроса, счётчики,
состояния сессии и DOM результата. Две явные отправки в overlap-сценарии
сохранены. Существующий соседний fixture
`DesktopCabinetSessionBridgeTests.swift:468` использует тот же приём
`document.forms[0].submit(); true`. Новых зависимостей и обходов теста нет.

## Журналы и пределы вывода

Самостоятельно прочитан
`/Users/yshishenya/Documents/Codex/2026-10-19/f136-current-preflight/native-instrumented-failed.log`:
в GitHub run39228243168 первая sessionBoundaryExpired проверка достигает фаз
start/listener-ready/host-attached/host-laid-out/initial-loaded, затем падает с
`Fatal error: Unexpectedly found nil while implicitly unwrapping an Optional value`
до terminal-callback. Это сужает место отказа, но не устанавливает точную строку.
Версия о nil при переносе JS undefined в async Swift Any правдоподобна и
соответствует выбранной минимальной поправке; по одному этому журналу она
не доказана окончательно. Новый hosted run на изменённом SHA обязателен.

Самостоятельно пересчитан
`current-explicit-js-result-workspace.log` из того же каталога:
**60 различных XCTest / 60 PASS / 0 SKIP / 0 FAIL**. Каждая из шести фаз
записана десять раз, итог selected suite PASS, 2.442s. Это локальная проверка
другой среды Swift6.3.3/macOS26; она не подменяет GitHub Swift6.0.3/macOS14.
Рецензент окна, Dev, тесты и сборку не запускал; просмотр журнала не выдаётся
за второй независимый запуск.

## Контроль и решение

```text
c870387e37b8e32b70c9649c7240a838b325addf0c94fd60d9d4a51f48998abf  apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

`git diff --check` PASS. Прочие локальные изменения требований и reviewer
checklist не откатывались и не изменялись этим ревью. Единственный созданный
рецензентом файл — этот отчёт. Небольшая поправка допустима для нового
проверяемого коммита в разрешённых пользователем границах. До принятия PR
нужны свежий hosted результат точного SHA, обычные обязательные проверки и
исправление/приёмка отдельного unsafe-history замечания; сам этот отчёт не
даёт продуктового или release approval.
