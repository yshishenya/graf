# Implementation Plan: запись из меню и понятные уведомления

**Branch**: `codex/6788-macos-notification-recovery` | **Date**: 2026-09-08 | **Spec**: [spec.md](spec.md)

## Summary

Объединить F249/F255 после релиза: общий путь команд захвата, удаление
постоянного виджета, прямой вход в нативные настройки и стандартные действия
macOS. Повторно использовать существующие модели, очередь и маршрутизацию.
Импортированный diff — кандидат для проверки, его живое исправление не доказано.

## Technical Context

- Swift tools 6.0, macOS 14+, AppKit/SwiftUI/UserNotifications, существующие
  ScreenCaptureKit/AVFoundation; сервер Python/FastAPI/Jinja и текущий JavaScript.
- Хранение: прежние UserDefaults/dedup, локальная очередь и серверный inbox.
  Новых зависимостей, таблиц, миграций и фоновых служб нет.
- Проверки: существующие XCTest/Swift Testing, pytest и браузерные проверки;
  ручная приёмка только единственного GRAF Dev через dev-harness.
- Risk / Validation Lane: **high-risk-product**, управление захватом и приватность.
- Release Gate: **no deploy** в этой задаче; PR с governance-fast на точном SHA.
  Публикация требует отдельного замороженного кандидата/release-full и разрешения.
- Существующий аудиопоток и производительность не меняются: нет нового опроса,
  таймера меню или работы на аудиопотоке; измеряются запуск/Stop/длительность
  синтетической записи, завершение ресурсов и сохранность без новых ошибок.

## Constitution Check

- Системный звук — основной источник; существующие source/permission/storage/
  transition guards и F214 не ослабляются. Команда не является разрешением.
- Пользователь явно заменил постоянный widget на F255 menu-bar indicator и
  Stop первым пунктом. Это явное продуктовое исключение к буквальному
  «one-action Stop» из §II: раскрытие меню + Stop — два нажатия. Не объявлять
  это одним кликом; системное автоскрытие строки меню уважать. Правило видимой
  индикации внутри открытой строки меню остаётся, setting скрытия записи нет.
- Приватные названия/звук выключены по умолчанию, сохранённые значения остаются.
  Trusted origin и текущий owner проверяются до любого внешнего действия.
- Krisp используется как наблюдаемый UX-образец, код и ресурсы не копируются;
  GRAF использует стандартные системные действия вместо непроверенного Take Notes.
- До реализации нужен независимый requirements review без HIGH/CRITICAL;
  после реализации — код, convergence и точные проверки. VoiceOver исключён
  владельцем, остальные требования доступности действуют.

## Implementation

1. `TwoBrainRecApp.swift`: проследить готовность `DesktopControlModel.onAction`,
   перенести четыре tray-команды на общий путь. Ошибки не теряются, обычные
   команды не поднимают кабинет. Проверить закрытие/восстановление окна.
2. `DesktopControlPanel.swift`, `CalendarTray.swift`: убрать NSPanel/widget и
   UI, используемый только им. Сохранить общий snapshot/model, очередь,
   восстановление, временный запрос F214. Длительность доступна в открытом меню.
   Удалить/заменить подавление по видимости уже несуществующего виджета.
3. Повторно использовать `presentSettingsWindow` с выбираемой вкладкой.
   `DesktopCabinetRoutePolicy.swift`, `EmbeddedCabinetWebView.swift` и
   `DesktopCabinetWorkspaceView.swift` проводят только доверенный переход
   к уведомлениям. Существующее окно и черновик не пересоздаются.
4. `settings_notifications_content.html`: разделить этот Mac, историю кабинета
   и письма/подсказки. Браузер объясняет Mac-границу; embedded даёт рабочий CTA.
5. `DesktopNotificationPresenter.swift`: категории UNNotificationCategory,
   default/join/settings/dismiss с проверкой owner/event/expiry/HTTPS при клике;
   время HH:mm, без обещаний захвата. Дополнить текущий dedup для безопасного
   disable/enable и переносов; не строить второй планировщик.
6. Существующие локальные записи и серверные статусы: проверить переход к
   конкретной локальной записи и blocked_config; исправить только доказанный
   разрыв, сохраняя производителей inbox и технические повторы тихими.

## Validation Plan

Сценарии и команды — [quickstart.md](quickstart.md). Сначала регрессии на
изменяемые переходы и маршруты, затем компиляция приложения и scoped server
tests. Governance-fast в GitHub — обязательный PR-gate. Старые результаты
F249 не засчитываются новой версии. `git diff --check`, проверка changelog,
независимый review, Ponytail review и convergence завершают ветку.

Перед Dev promotion повторно проверить manifest/source/schema и владение
общим стендом. Сейчас Dev другой фичи на схеме0090, база этой ветки0089:
понижение и подмена manifest запрещены; использовать только совместимый
переход harness после устранения конфликта. Отчёт разделяет unit, сборку,
реальный Dev и PR CI; невозможная проверка не становится PASS.

## Project Structure

- `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- `apps/macos/RecApp/Sources/{Notifications,Calendar,Cabinet}/`
- `apps/macos/Shared/Tests/`
- `apps/server/src/twobrain_rec_server/cabinet/{templates,static}/`
- `apps/server/tests/{contract,integration}/`
- `specs/6788-macos-notification-recovery/`, `changes/unreleased/F6788.yaml`

## Complexity And Compatibility

Legacy Impact: **remove**. Старый мост и постоянный widget удаляются после
поиска всех ссылок. Миграции/decoder/файлы/очередь/настройки остаются.
Откат — прежний проверенный код через штатный harness без удаления данных.
Нет новых обёрток, зеркальной очереди, fallback-приложения. Единственный новый GET возвращает проверенный контекст владельца.

## Обнаруженный блокер инструмента

T016: allocator выдал F6788, но installed issue canon использует `\d{3}`,
усекает owner до678 и отклоняет полный title. Исправление ограничено полным
числовым ID (минимум3цифры) и числовой сортировкой fallback, без ослабления
body/label validation. Источник расширения и встроенная копия обновляются
одинаково с регрессией коротких/длинных ID. Это prerequisite ремонта рабочего
процесса, а не переименование фичи или обход issue gate.

## Объединение F258 по решению владельца

Источник — PR #6824, d747ce43cf958de089a4b9563eb9078d5130ca86, та же база e81b412.
До переноса — affected requirements review/analyze и issue sync. Затем:

1. Перенести общую проекцию `outcomes/progress.py` и её HTML/processing/sync
   потребителей, выбор audio revision, узкий SELECT/grant media worker с тестами.
2. Перенести обновление выбранного summary fragment в `cabinet.js`,
   сохраняющее player/draft/focus и блокирующее detached/stale responses.
3. Совместить native owner/epoch/incident и `DesktopUploadClient`/queue/model:
   transcript_available отдельно от review.available, pending summary продолжается.
   Только необходимые метаданные состояния; recap delivery и его отдельные
   UUID/time/dedup/UI не переносить, если у них нет оставшегося потребителя.
   Проверенный GET notification-context сохранить для локальных ошибок без календаря.
4. Не переносить widget, recap category и прежнее post-Stop окно.
   Все решения FR002/008 текущей фичи действуют поверх F258.
5. Повторить server/Node/Swift, actual media role и installed Dev acceptance,
   включая первый embedded вход без ручного reload. Старые PASS F258 — provenance.

Дополнительные пути: `apps/server/src/twobrain_rec_server/{api,processing,outcomes,
ingest,normalization}/`, `apps/server/scripts/bootstrap_runtime_database_roles.py`,
`apps/macos/Shared/Sources/Models/AudioModelCore.swift`, существующий Upload.
Новых таблиц, миграций, фоновых процессов и зависимостей нет.
