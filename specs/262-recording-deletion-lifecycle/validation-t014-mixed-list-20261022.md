# Повторная приёмка F262/T014: смешанный список

Дата: 2026-10-22. Задача: #6889; исходная реализация: PR #6911.
Lane: active-spec-kit, повторная приёмка существующей F262/T014.
Текущая основа: `269edab937525f3c71730eff32a20b38da5e25f8`.
Точный новый PR SHA и проверенная основа фиксируются в PR и комментарии
закрытия после обязательных GitHub checks. Старый CI #6911 не используется:
обязательный артефакт больше недоступен.

## Результат и изменение

Существующий `mixed-meeting-list.test.cjs` повторно исполнен в Chromium
headless на `4b5aaf5252303a85d9eba6969e41dc9a65ec399e`: PASS, exit 0,
ошибок страницы 0. Это один сквозной сценарий, не число отдельных assert.
После переноса на `a5efee374cfa2676b736e81af53f84dbb8f1ee16` все его
продуктовые исходники и сам тест побайтно сохранены.

Дополнительно исполнены существующие local-recording-focus и
meeting-delete-focus: PASS, exit 0. Первый работает в Chromium, второй
проверяет обработчик клавиатуры в Node VM и не является запуском WebKit.

В дополнительном `recording-deletion-acceptance.test.cjs` воспроизведено
падение ожидания: тест искал «ещё», действующий интерфейс пишет «еще».
Исправлены только два соответствующих ожидания. Код продукта, контракт,
обработка удаления и зависимости не меняются; ограничения проверок не сняты.
После исправления весь набор из восьми сценариев прошёл с exit 0:
threeTypes, offlineCopy, selection, filter, lastRow, aliases, partialBatch,
timing. Замер timing: один образец, remoteMs=29999, reconnectMs=11,
штатный timerMs=30000; p95 и аппаратная задержка не заявляются.

В mixed-meeting-list добавлены две независимые комбинации capabilities:
canDelete=true/canOpen=false и canDelete=false/canOpen=true. Проверяются
состояние флажка и наличие кнопки открытия; рабочий renderer не меняется.
Это закрывает ограничение браузерной проверки S17, отмеченное reviewer.
Его первоначальный обзор сохранён с исходной версией/хешами; из копии
для Git убраны только локальные пути, выводы не переписаны.

## Что доказано

- Семь сортировок с устойчивыми равными значениями; поиск/даты/часовой пояс,
  фильтры доступа и готовности, счётчик выдачи.
- Связанная локальная и серверная строки не дублируются; отсутствие
  серверной строки в выдаче не возвращает локальную копию.
- При переходе local→server сохраняются выбор и фокус. Неизменная
  публикация не пересоздаёт сфокусированные узлы; изменение действия,
  фильтрация и исчезновение строки дают доступный запасной фокус.
- Sending блокирует действия; rejected запрашивает актуальную выдачу без
  шторма повторов; accepted не отменяется поздним HTML/событием afterSwap.
- Смешанный набор local-only/server+local/server-only считает записи один
  раз, использует один диалог и один вызов synthetic native bridge.
- Новая строка и фильтр при открытом подтверждении не изменяют исходный
  набор. Отсутствие сети показывает pending, не серверный успех.
- Последняя строка даёт count=0, пустое состояние и фокус на заголовке.
  Пакеты lifecycle ограничены 100 целями; ошибка следующего пакета
  не отменяет уже принятый результат и обновлённый счётчик.

## Независимая проверка и смежные доказательства

Независимый reviewer подтвердил узкую T014: CRITICAL 0, HIGH 0,
requirements 10/0 и security-ux 10/0. Его самостоятельный отчёт:
`review-t014-mixed-list-20261022.md`. Исходные требования, задачи и
контракты не меняются. Нового уточнения или обязательной задачи в узкой
T014 не обнаружено; T015/T016 и остальная F262 этим не принимаются целиком.

Браузер не исполняет файловую миграцию, native capabilities или плеер.
Соответствующие текущие XCTest отдельно прошли в macos-pr run
39723990907 на исходном SHA 4b5aaf5252303a85d9eba6969e41dc9a65ec399e:
`testDamagedItemCannotBeSentAndCanBeDeletedLocally`,
`testLocalPlaybackRejectsMissingTrackAndPathOutsideRecordingRoot`,
`LocalRecordingPlayerTests.testManagedSourceIsReleasedOnDeletionAccessLossAndReplacement`
и обе `RecordingDeletionLegacyAcceptanceTests`.
Это смежное native-доказательство текущих исходников, не новая
установленная приёмка и не обязательные checks нового PR SHA.

## Воспроизведение и границы

Использованы существующие Node/Playwright; новые зависимости не добавлялись.
Команды: `node apps/server/tests/browser/<имя>.test.cjs` при NODE_PATH,
указывающем на существующее окружение Playwright. Браузерные имена:
mixed-meeting-list, local-recording-focus, recording-deletion-acceptance.
meeting-delete-focus использует стандартные модули Node.

Журналы, JSON и SHA-256 находятся в локальном реестре
`issues-334-audit`: `f262-t014-current-recheck-20261022.json`,
`f262-t014-t016-current-acceptance-summary-20261022.json`,
`f262-t014-t016-acceptance-current-20261022.log` (исходный отказ),
`f262-t014-t016-acceptance-fixed-20261022.log` (8 PASS),
`f262-t015-local-focus-current-20261022.log`,
`f262-t016-delete-focus-current-20261022.log`.

DOM, сеть, native bridge и события HTMX синтетические. Проверяется
настоящий cabinet.js, но не настоящая сессия сервера, установленный
GRAF Dev/WebKit, звук, VoiceOver, физическая сеть Mac или production.
Историческая установленная приёмка не выдаётся за новый запуск.
Закрытие #6889 допустимо только после нового связанного PR, точных
governance-fast/macos-pr/pr-metadata, merge и live closeout.

Legacy Impact: untouched; новых alias/fallback/dependency/legacy путей нет.
Формат очереди, схема и API сохранены; выпуск и развёртывание не выполняются.

## Окончательный повтор на текущей основе

На основе269edab937525f3c71730eff32a20b38da5e25f8 с указанной дельтой
тестов mixed-meeting-list PASS/exit0, затем весь acceptance-набор8PASS/exit0.
Последний единственный образец timing: remoteMs=29992, reconnectMs=8;
предыдущие29999/11 не прибавляются и не образуют p95.
Журналы: f262-t014-final-mixed-browser-20261022.log и
f262-t014-final-acceptance-20261022.log в issues-334-audit/.

- `apps/server/tests/browser/mixed-meeting-list.test.cjs`: SHA-256 `f122b06b90d4b68c591dcd6873d7d01892022a6a88c61920e5f40d1d7d808089`.

- `apps/server/tests/browser/recording-deletion-acceptance.test.cjs`: SHA-256 `b59def24c94f37ef16c3967827fb6fd919221465b7e46c2794df4e76472d78dd`.
