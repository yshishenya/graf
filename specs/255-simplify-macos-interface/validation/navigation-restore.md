# F255: возврат навигации по отзыву владельца

2026-09-07. Active Spec Kit slice, high-risk UX. Исходный вариант `c6bbcf3765ff7a23221ced2aca64dd809dc420f8`; отменённый вариант `976d7a74dc8d5c1ce1c2b6520de7f459bbb6461a`.

Восстановлены исходные workspace, HTML sidebar/profile, CSS/JS и три серверных контракта. Удалены native sidebar/profile и bridge с единственными потребителями и его отдельными тестами. Поиск по apps/macos, server/src и server/tests не находит EmbeddedCabinetShell/grafDesktopShell/data-native-navigation/data-shell-item. Сохранены компактная автозапись, отложенная публикация detach состояния WebView, semantic background и удаление недостижимой compact queue.

Проверки рабочей ревизии:

- 122 server tests PASS: navigation model, web shell, template sections, shell response, settings UI. Лог `/tmp/graf-f255/rollback-server.log`.
- 183 Swift tests PASS, один worker/parallel isolation: DesktopCabinet, EmbeddedCabinet, DesktopMeetingShellWebViewBoundary, AppControlAccessibility, CaptureControlV5. Лог `/tmp/graf-f255/rollback-swift.log`.
- Ruff трёх изменённых Python suites, diff whitespace, Spec Kit governance PASS.
- Первоначальный запуск pytest в локальном окружении не состоялся: pytest отсутствовал; повтор выполнен с существующим окружением основного checkout. Новые зависимости не устанавливались.

Установка/живой проход выполняются отдельной интеграционной ревизией с F249/schema0086; старый server этой ветки напрямую на существующий Dev не продвигается. До подтверждения установленной версии T019 открыт. Full CI, выпуск, macOS14.5 и полная доступность этим результатом не закрыты.
