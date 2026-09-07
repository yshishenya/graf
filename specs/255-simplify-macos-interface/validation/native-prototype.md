# F255: нативная основа — промежуточная проверка

Дата: 2026-09-06. База: `c6bbcf3765ff7a23221ced2aca64dd809dc420f8` плюс незакоммиченная реализация. macOS 26.5 (25F71), Xcode 26.6, Swift 6.3.3.

## Что доказано

- Реальный `NavigationSplitView` с системным `List(.sidebar)` работает рядом с WKWebView и существующими кнопками истории/записи. После удаления лишней заливки macOS сохраняет скруглённую форму также при Reduce Transparency.
- В системе фактически включено уменьшение прозрачности. Увиденное непрозрачное исполнение **не доказывает** внешний вид Liquid Glass при разрешённой прозрачности.
- `EmbeddedCabinetShellBridgeTests.testRealDocumentHandoffThemeAndStaleSessionFallback` запускает настоящий HTTP-сервер, производственный JavaScript, WebKit и `NSHostingController<DesktopCabinetWorkspaceView>`. При resize, скрытии/возврате sidebar и смене темы остаются один и тот же WKWebView и маркер текущего документа.
- Тест воспроизвёл конфликт публикации ObservableObject внутри SwiftUI dismantle. Исправлено в bridge и существующем navigation controller: команды отвязываются синхронно, публикация состояния отложена с защитой от нового подключения.
- Автосохранение темы проходит существующий POST/303 без ухода со встречи. HTTP 503 возвращает предыдущую тему и видимое сообщение. Query/якорь текущего документа сохраняются.

## Исправление порядка сборки

Первый диагностический запуск ошибочно использовал `build-local-app.sh` и отдельный пробный bundle. Это не установленный GRAF Dev и не приёмка фичи. По замечанию владельца пробное приложение остановлено; quickstart исправлен.

Канонический путь: `docs/agent-guidance/local-development.md` и `development-process.md`, `dev-harness build → promote → status → smoke`. Только `/Applications/GRAF Dev.app`, `pro.2brain.graf.dev`, штатная подпись, чистый точный SHA. Нельзя переименовать Local в Dev и считать требование выполненным.

Проверенный активный Dev manifest: `dev-3de3eec50430`, Feature 249, SHA `3de3eec50430f99b4540822518bf3ed5dc7337b3`. F255 его не заменяла. Историческое `health: pass` в manifest не является новым smoke F255.

## Открыто

T002 не закрыта: повторить композицию и сценарии в штатном GRAF Dev на выбранном коммите; подтвердить стекло и матовый вариант, активное/неактивное окно, минимальное окно с раскрытой правой панелью. macOS 14.5 ещё не запускалась. Не изменять глобальные настройки доступности молча ради снимка.

## Exact-SHA Dev candidate 2026-09-07

- Собран и установлен только `GRAF Dev`: manifest `dev-46d693849973`, source SHA `46d6938499730af3712e31e52abd227268cdf19c`, Feature `255`, migration head `0087_merge_calendar_timezone`.
- Штатные `build --live`, `promote --dry-run`, `promote --live`, `status --json` и `smoke --live` завершились успешно. Все 13 live checks имеют `pass`: API, `/login`, auth bootstrap, representative API, Postgres, MinIO, migration, Temporal, processing/media workers, app identity/presentation и exact source SHA.
- Исправлен и проверен общий Compose-контракт: `GRAF_DEV_EXPECTED_MIGRATION_HEAD` теперь передаётся в `rec-migrate`; профильные governance-тесты — `22 passed`.
- Предыдущая Dev база с неизвестной текущему checkout ревизией `0088_merge_notifications` удалена только в изолированном `graf-dev` namespace; новый namespace мигрирован с нуля. Production и GRAF Local не использовались.

Нативное окно и визуальные hover/accessibility сценарии этого exact-SHA кандидата пока не наблюдались: CUA остановлен системной блокировкой Mac. Поэтому T015/T016 не закрываются по одному smoke; нужна повторная проверка после разблокировки.
