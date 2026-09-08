# F255: возврат навигации по отзыву владельца

2026-09-07. Active Spec Kit slice, high-risk UX. Исходный вариант `c6bbcf3765ff7a23221ced2aca64dd809dc420f8`; отменённый вариант `976d7a74dc8d5c1ce1c2b6520de7f459bbb6461a`.

Восстановлены исходные workspace, HTML sidebar/profile, CSS/JS и три серверных контракта. Удалены native sidebar/profile и bridge с единственными потребителями и его отдельными тестами. Поиск по apps/macos, server/src и server/tests не находит EmbeddedCabinetShell/grafDesktopShell/data-native-navigation/data-shell-item. Сохранены компактная автозапись, отложенная публикация detach состояния WebView, semantic background и удаление недостижимой compact queue.

Проверки рабочей ревизии:

- 122 server tests PASS: navigation model, web shell, template sections, shell response, settings UI. Лог `/tmp/graf-f255/rollback-server.log`.
- 183 Swift tests PASS, один worker/parallel isolation: DesktopCabinet, EmbeddedCabinet, DesktopMeetingShellWebViewBoundary, AppControlAccessibility, CaptureControlV5. Лог `/tmp/graf-f255/rollback-swift.log`.
- Ruff трёх изменённых Python suites, diff whitespace, Spec Kit governance PASS.
- Первоначальный запуск pytest в локальном окружении не состоялся: pytest отсутствовал; повтор выполнен с существующим окружением основного checkout. Новые зависимости не устанавливались.

Установка/живой проход выполняются отдельной интеграционной ревизией с F249/schema0086; старый server этой ветки напрямую на существующий Dev не продвигается. На момент исходных проверок T019 оставался открыт; установленный результат приведён ниже. Full CI, выпуск, macOS14.5 и полная доступность этим результатом не закрыты.

## Установленный результат

Штатная интеграционная ревизия `fd70f843a082fcbc26711c7eebc017858663e8bd` в `/tmp/graf-f255-dev-validation`: rollback применён поверх `559a44672a7ecb96261f189fe062ff6543640aa5`, сохранены F249/schema0086 и компактная автозапись. Единственный CSS конфликт разрешён удалением F255 native/matte блока и сохранением отдельного блока уведомлений F249. Основные workspace/WebView/menu template совпадают с PR; добавочный JS относится к F249. Интеграционные проверки: 122 server, 182 Swift PASS.

Build → promote dry-run → promote → status → smoke PASS; манифест `dev-fd70f843a082`, 13/13 live checks, bundle `pro.2brain.graf.dev`, `/Applications/GRAF Dev.app`. Проверенный предыдущий checkout `/tmp/graf-f255-dev-before-restore` оставлен для штатной компенсации. Полные результаты локально: `/tmp/graf-f255/restore-{dev-build,promote,status,smoke}.json`.

Живой проход: Мои встречи → Поделились со мной одним действием; раскрытие старой sidebar; профиль по нажатию → Вид с тремя вариантами; Escape закрыл меню и вернул фокус. Перейти из профиля в настройки удалось. Нативная автозапись показывает компактные кнопки без заглушек, галочки/контекстные AX названия сохранены. Правила автозаписи и тему не меняли. Снимки — `krisp-review.md`.

T019 завершён. T020 и полная матрица остаются открыты. Стенд после проверки передан обратно F249: эта задача не обещает неизменность активного Dev после согласованного следующего promote другой задачи.

PR документы дополнительно согласованы коммитом `e42bf8618`; этот коммит не меняет продуктовые исходники. GitHub governance-fast на нём PASS (run34086286788). Финальный документирующий коммит требует собственного governance-fast; прежний результат не переиспользуется как exact-SHA допуск.
