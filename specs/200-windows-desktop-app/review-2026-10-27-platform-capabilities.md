# Независимая проверка платформы и действий общих settings

2026-10-27. Scoped source review; новых запусков/сборок/тестов нет.
Authoritative checkout: `/Users/yshishenya/Documents/crisp-worktrees/200-windows-followup`.
HEAD: `b1eb3d5f847645ac41ad4163f1bc0f22e4c26ed1`.
Mac comparison: локальный ref `origin/master` =
`c6e49f52a32de8dcb49673509cbfd64bc20e7bfe` (commit time
2026-10-27T23:43:19+03:00). Fetch/GitHub не использовались; это точная версия
прочитанного ref, а не отдельная проверка свежести удалённого сервера.

## Итог

C0 / H0 / M0 в ограниченной области: новых доказанных кнопок Mac, которые
показываются Windows без соответствующего действия, или Windows-кнопок на Mac
не найдено. Проверены три общие страницы: account, recording, notifications;
их platform bootstrap и актуальный для указанного ref Mac notification bridge.
Calendar/support gaps не пересматриваются. Это не runtime/installed acceptance.

## Проверенные связи

Пути ниже относительно authoritative checkout; Mac references относятся к
содержимому указанного `origin/master`, а не к рабочему Mac-файлу.

- `apps/windows/RecApp/Web/WebView2Host.cpp:232–238`: bootstrap ставит
  `GRAFDesktopPlatform='windows'` как presentation hint и вызывает refresh.
  `cabinet/static/cabinet/cabinet.js:4–14` меняет только адресные
  `data-platform-copy`; отсутствие Windows-маркера сохраняет Mac copy.
  `cabinet.js:9087–9091` применяет тот же механизм после HTMX swap.
  Здесь нет общего нового capability registry, требующего реализации на Mac.
- `apps/windows/RecApp/Web/NativeSettingsBridge.cpp:195–230`: shim объявляет
  `grafRecordingSettings` и `grafNotificationSettings`; это transport handlers,
  а не обещание системных разрешений или перехода в системные настройки.
  `AppMain.cpp:1254–1255` подключает реальный `answerNativeSettings`;
  `AppMain.cpp:2035–2079` обрабатывает оба имени, read/set/setAll recording
  и notification через текущий presenter/context.
- Recording: `cabinet/templates/cabinet/pages/settings_recording_content.html:6–24`
  показывает правила только embedded; селекторы all/target и retry обслуживает
  `cabinet.js:6198–6232` через v1 `grafRecordingSettings`. Это общий сценарий;
  Mac `EmbeddedCabinetRecordingSettingsBridge.swift:74–136` в прочитанном ref
  принимает те же read/set/setAll и возвращает targets/rules.
  Публичная ссылка `/download` находится в ветке `embedded=false` и сама по
  себе не доказывает ошибочную Windows-кнопку во встроенном кабинете.
- Notifications: `cabinet/templates/cabinet/pages/settings_notifications_content.html:11–27`
  содержит пять preferences, offset 0/1/5, test/retry/reload. Старых кнопок
  запроса системного разрешения/открытия System Settings там нет.
  `cabinet.js:6237–6256,6272–6289,6334–6347` использует version 2,
  read/set/test, nonce и canEdit; test привязан к preview. Windows reply
  `NativeSettingsBridge.cpp:171–185` возвращает эти же preferences/canEdit/message,
  без `canOpenSystemSettings`. `NativeSettingsBridgeTests.cpp:1746–1755` явно
  проверяет отсутствие устаревшего поля; исходник теста прочитан, не запущен.
- Mac `origin/master:apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift:67–97,99–138`
  принимает v2 read/set/test с теми же полями и offset; test вызывает presenter,
  snapshot содержит version/preferences/canEdit/message/error. Поэтому общая
  страница не рассчитывает на отсутствующий Mac capability API. Bootstrap
  Windows не внедряется в Mac этим общим JS.
- Account: `cabinet/templates/cabinet/pages/settings_account_content.html:31–58`
  использует серверные profile/preferences формы и общий theme picker; действия
  входа/провайдеров/сессий/закрытия аккаунта также заданы формами и серверными
  маршрутами, не Mac-only native settings handlers. Темы дополнительно связаны
  с Windows через `WebView2Host.cpp:329–338` и
  `AppMain.cpp:1253`. Полную бизнес-логику этих серверных действий этот разбор
  не квалифицирует.
- Выбор трёх templates находится в
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py:565–569`.

Для краткости `cabinet/...` выше означает
`apps/server/src/twobrain_rec_server/cabinet/...`.

## Границы T097 / T104 / T109

Текущие T097/T104/T109 остаются открытыми. T097 требует свежую установленную
визуальную/сквозную приёмку, T104 — полный сценарий напоминаний и его evidence,
T109 — адресную платформенную адаптацию и матрицу Windows/Mac/старого Mac.
Существование обработчика не доказывает исполнение полного пользовательского
сценария. Этот scoped review не отмечает реализацию или приёмку выполненной,
не меняет маркеры и не создаёт дополнительных предположительных defects.
Pending cert session 84586 не затронута.

## SHA-256 прочитанных байтов

| Источник | SHA-256 |
| --- | --- |
| AppMain.cpp | `a85f5024813dbe4fdabbf879485bf12b4343b65b4a1709af1dbe8fdb012436c0` |
| Web/NativeSettingsBridge.cpp | `bc667b52197b9ae0c7b3163e3d83963d131326ebbefda7abd7cbc4cf48073845` |
| Web/WebView2Host.cpp | `ab7f676828418e6a688e9b6cab7138b7f85502d51096bd9ae8bf6febeb72e04f` |
| cabinet.js | `7862f2375188a1f3b9a1f5cb6a330028411cfb5ab5709c81b5f73cbab08ce948` |
| settings_account_content.html | `779fc6a9ff995b1e7ef125d56a5c5603100b0312686f319ba53ee64c4177ae5b` |
| settings_recording_content.html | `2bbe1ce851c382e0f9234b945d5b1ea697b86cb311ccd1f31a0a636ceb1f998f` |
| settings_notifications_content.html | `3981ea571554f8b9e34a58c5f6a12cd6501ab13f7814b8c94ec94c01b3bcea37` |
| Mac notification bridge, bytes from origin/master above | `90e5478b81f4b230e56a47bcae9ba056c131dc7f0947da2ddc20adf2002eebca` |

Единственный созданный reviewer-файл — этот отчёт; code/spec/tasks/checklists,
GH и guest не изменены.
