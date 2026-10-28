# Quickstart: проверка границы сессии F136

## Продолжение T004/T011/T012 — 2026-10-28

Текущая основа: `888ad9539c8bc21a9fe4c3935d6647e035272aa3`.
Переиспользовать команды XCTest ниже и существующий loopback fixture.
До исправления воспроизвести поведение одобренного Settings provider-link POST:
отдельный завершённый start/auth документ, затем callback и стабильный результат,
а также цепочку только с перенаправлениями без промежуточного didFinish.
На каждом этапе проверить прежние sessionBoundaryID/WebView, число POST=1,
отсутствие повторного GET действия, сохранение route/identity до результата.
Промежуточный providerLink не становится expiredSession. Настоящие кнопки и
история не повторяют start/callback; финальные Settings снова безопасны.

Проверить запрет внешнего перехода без approved continuation: GET вместо POST,
нет завершённого authenticated Settings, чужой source/origin, subframe.
Текущая ошибка/отмена/blocked/superseding и завершённый результат снимают
разрешение; stale callbacks не снимают новое. 401/reselection, logout/root login
по-прежнему закрывают прежнюю историю. Сохранить primary sign-in, POST history,
download/payment и отсутствие desktop headers за пределами origin.
Для автоматического исследования реальных внешних провайдеров не вызывать;
положительная работа внешнего сервиса относится к отдельной T016.
Исходные PASS не переименовывать в RED. Записать точные команды, результаты,
ограничения и хеши нового среза в отдельный раздел validation.

## Условия

База среза: `c6c5441c930b8c1ecffed6de9b80773aa0e757e5`.
Перед сборкой проверить `df -h /System/Volumes/Data`: запас 80 ГБ;
менее 50 ГБ — не начинать тяжёлую проверку, сохранив рабочие данные.
Использовать отдельный временный scratch-path SwiftPM и удалить промежуточные
сборки после проверки. Журналы и итоговый отчёт сохранить.

## Автоматические проверки

В текущем worktree выполнить XCTest без установки/запуска отдельного GRAF.app:

```sh
swift test --package-path apps/macos --scratch-path /private/tmp/graf-f136-build --filter DesktopCabinetWorkspaceTests
swift test --package-path apps/macos --scratch-path /private/tmp/graf-f136-build --filter DesktopCabinetRoutePolicyTests
swift test --package-path apps/macos --scratch-path /private/tmp/graf-f136-build
python3 scripts/check_spec_kit_governance.py
```

Сначала выделенная регрессия ordinary settings POST должна показать RED по
изменению границы на исходном коде, затем GREEN после исправления. Проверить
200, ошибку и отмену без remount; ровно один POST; стабильный route/request
identity перед успешной сменой сессии; немедленную блокировку старой истории
при 401/выборе пространства; Back/Forward/Reload и устаревшие callbacks.
Переиспользовать имеющийся WKWebView fixture; не вызывать живые аккаунты и OAuth.
Полный результат и ограничения записать в `validation.md`, не переносить старые
645/2456 tests в текущие доказательства. Локальные `ci-local.sh --fast`/`--full`
— только диагностический резерв. После коммита PR требует текущие
`governance-fast`, `macos-pr`, `pr-metadata` через `validate-pr-checks.py`.

## Отдельная ручная приёмка T016 (пока открыта)

Прочитать `docs/agent-guidance/local-development.md`. Все ручные/сквозные
сценарии выполнять исключительно в `/Applications/GRAF Dev.app`, обновляемом
через штатный dev-harness. Не запускать копию из worktree или /tmp, `swift run`
или принудительный сброс разрешений. Если стенд недоступен — указать ограничение,
не считать ручную приёмку выполненной.

1. В разрешённом тестовом аккаунте проверить email, VK ID и Яндекс, отмену
   провайдера и безопасный повтор вручную.
2. В процессе входа Back возвращает на безопасную страницу; Forward/Reload не
   повторяют форму, start или callback.
3. В настройках сохранить форму и подключить тестового провайдера: результат
   появляется один раз и активная сессия не теряется.
4. Обычная навигация встреч/настроек работает. После выхода/нового входа,
   истечения сессии и выбора пространства прежняя история недоступна.

Хранить только pass/fail, команды, SHA и ограничения. Не сохранять аккаунты,
коды, cookies, callback URL, секреты и содержимое встреч. Выпуск/развёртывание
не входят в проверку этого среза.

## Дополнительные регрессии двух замечаний PR

Выход на `/login/` и `/sign-up/` обязан менять session boundary после фиксации
целевого документа и блокировать прежнюю protected history. Для ожидаемой
provisional отмены формы настоящее DesktopCabinetWorkspaceView сохраняет тот
же WKWebView, DOM и завершённую GET history item после SwiftUI reconciliation;
настройки повторно активируются защищённым существующим путём. Первая загрузка
без didFinish и уже committed POST не восстанавливаются в ready. Сохранить
регрессии 401/reselection, stale/detach, history/Reload и один POST.

Отдельно отменить предварительный GET A→B (разные разрешённые адреса):
проверить фактический GET B до stopLoading, сохранение документа A, его
маршрута и GET identity после SwiftUI reconciliation, Reload A и отсутствие
повтора B. Это тот же T020 и прежние ограничения восстановления.
