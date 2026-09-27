# Implementation Plan: Единые компактные уведомления

**Branch**: `277-compact-notifications` | **Date**: 2026-09-26 | **Spec**: [spec.md](spec.md)

## Summary

Один собственный AppKit-компонент для пяти сценариев; одна очередь, настройки и сроки. Удалить системное планирование и его потребителей, а не оставить выключенную реализацию. Сохранить восьмисекундный договор записи, полезные предпочтения, контекстную изоляцию и безопасные действия. Верхний левый крестик накладывается на край, не занимает колонку; видимая ширина380pt, высота по содержимому.

## Technical Context

- Language/version: Swift6 (`apps/macos/Package.swift`), AppKit + существующая SwiftUI оболочка; JavaScript/HTML встроенных настроек; Python для статической проверки удаления.
- Dependencies: существующие AppKit, Combine, Foundation, TwoBrainRecShared; новых пакетов и фоновых служб нет.
- Storage: существующие локальные owner-scoped preferences/incident claims; до50 нейтральных событий в памяти текущего запуска и контекста. Серверного хранения истории нет.
- Tests: XCTest, существующие Node-контракты cabinet.js, pytest контракт страницы, Python retirement gate.
- Risk / Validation Lane: `high-risk-product` — управление записью, приватность и доступность. Полный Spec Kit, независимый reviewer, анализ без CRITICAL/HIGH, issue sync до реализации.
- Release Gate: no deploy. PR требует exact-SHA `governance-fast`, `macos-pr`, `pr-metadata`; `release-full`, публикация и production относятся к отдельно разрешённому релизу.
- Platform: macOS14+, Apple Silicon; ручная проверка только `/Applications/GRAF Dev.app` через dev-harness.
- Performance: одно окно, не более одного активного секундного ticker; обновление секунды без пересоздания дерева и объявления; очередь/история ограничены. Нет поиска чужих окон/частных настроек Focus.
- Scope: desktop notification module, app integration/tray commands, local settings bridge + embedded page, связанные tests/contracts и активная документация. Разрешённое 2026-09-27 расширение: состояние принятия запуска в writer/manifest/recovery и допуске очереди. Серверные inbox/billing notifications, обработка аудио, история specs вне удаления.

## Constitution Check

### Before research: PASS

- I/II: обработка аудио не изменяется; права, storage, approved target, видимый индикатор/Stop и8секунд сохраняются. Закрытие отменяет предложение, только explicit start/skip сохраняют настройку. Подтверждённое расширение усиливает долговечный отказ отменённого запуска без новой политики согласия.
- III/IV: новых внешних сервисов, секретов и meeting-content storage нет. История не содержит аудио, названий, участников, ссылок или transcript; очищается при смене контекста. Семантика удаления встречи не изменяется.
- V: никакого релиза; установленный Dev сохраняет bundleID/подпись/TCC через штатный harness.
- VI: clarify в spec, reviewer-owned ux/security/audio-capture checklists, tasks/analyze/issues до кода.
- VII: собственный код, SF Symbols и системные шрифты; никаких извлечённых Krisp assets. Отступление от старого эталона явно одобрено ради компактности; требования доступности обязательны.

### After design: PASS with validation obligations

Системные запросы очищает единственная выполняемая retirement-функция; она не отправляет уведомления и не имеет permission/delegate/action пути. Это не fallback. Нейтральная история и явный переход с клавиатуры компенсируют утрату Notification Center, но не обещают интеграцию с Focus или доставку при завершённом процессе. Восемь секунд — утверждённое поведение, не доказательство полной доступности; ручное управление доступно без таймера.

## Architecture and ownership

1. `DesktopNotificationCardPresenter.swift`: семантическое содержимое, одна AppKit-панель, измеряемая раскладка, update-in-place, первый click, явный focus, Escape и announcements. View не запускает запись и не хранит правила приложения.
2. `DesktopNotificationPresenter.swift`: owner/context, дедупликация, актуальность/приоритеты, meeting deadlines0/1/5, prefs, bounded history, sound/quiet. Capture callbacks проверяют текущий prompt/token; устаревшие действия отбрасываются.
3. Изолированный retirement helper: удалить pending/delivered уведомления только собственного bundle без authorization. Не хранить старые категории для нового показа. Owner binding записей сохраняется; rollback dual-write aliases/reservations удаляются после ограниченной миграции необходимых incident claims.
4. `EmbeddedCabinetNotificationSettingsBridge.swift` + `cabinet.js` + template: один новый локальный контракт; удалить permission status/request/open-system-settings. Сохранить main-frame/origin/route/nonce/epoch checks; несовместимая версия требует обновления страницы, не двух протоколов.
5. `TwoBrainRecApp.swift` и `Sources/Calendar/CalendarTray.swift`: убрать `DesktopRecordingNoticePresenter`; прямой общий presenter; команда перехода к текущей карточке и служебная история в существующем меню. Прежний отдельный SwiftUI prompt уже отсутствует: не создавать его заново. Индикатор записи не временное уведомление и сохраняется.
6. Удалить непроизводимый текущей страницей маршрут `/desktop/settings/notifications/mac` и цепочку `onOpenNotificationSettings` в `DesktopCabinetRoutePolicy.swift`, `EmbeddedCabinetWebView.swift`, `DesktopCabinetWorkspaceView.swift`, `TwoBrainRecApp.swift`. Обычный маршрут остаётся. Старый URL получает штатный отказ route policy без запуска отдельного окна и без нового alias.
7. Сохранить и обновить живой `DesktopNotificationsSettingsView`, используемый `LocalSettingsFallbackView` при недоступном кабинете: тот же набор полей/quiet/проверка без системного разрешения. Это альтернативный доступ к настройкам, не второй канал уведомлений. Сохраняются `DesktopUploadClient.notificationContext()` и встроенный `CalendarPromptView`: они обслуживают удаление/управление, а не старую плавающую карточку.

## Validation Plan

### Разрешённое расширение P1 — 2026-09-27

- `AudioModelCore.swift`: optional `LocalRecordingStartAcceptance` (`pending`, `accepted`), поле `startAcceptance`; nil означает исторический пакет с прежними gates. Неизвестное значение не декодируется в разрешение.
- `V5LocalRecordingWriter.swift`: параметр `requiresStartAcceptance` (false для прежних/ручных вызовов). До включения timer сохраняется active manifest с pending и **без scopeApproval**, если требуется принятие. Это удерживает запрет также для прежнего клиента, не знающего нового поля. Подтверждение `acceptStart(sessionId:)` синхронно на writer queue проверяет текущую сессию, сохраняет accepted + исходный scopeApproval атомарно и только после успешной записи меняет память. Финализация сохраняет тот же признак и не возвращает scopeApproval для pending.
- `TwoBrainRecApp.swift`: meeting-detection запуск требует принятия. После await проверяет текущий token/context, переводит capture controller в capturing и подтверждает ту же сессию без нового await между проверкой и подтверждением; затем сообщает accepted. Ошибка идёт через существующий failure cleanup, не снимая pending. Аудиоисточники/индикатор/Stop и ручной запуск остаются прежними.
- `CaptureRecoveryService.swift`: pending не ремонтируется в ready; возвращается blocked/permissionDenied без удаления аудио и без восстановления scopeApproval. Ошибка записи blocked оставляет исходный pending, тоже запрещённый. У accepted и исторического nil путь восстановления прежний; accepted сохраняется в новом manifest.
- `DesktopUploadQueueService.swift` и прямой вход `DesktopUploadClient.swift`: общий admission отвергает pending независимо от status/tracks; retry и отправка повторно читают локальное принятие, а не доверяют только сохранённому artifactProfile. Проверка sessionId/directoryId manifest и отказ при ошибке чтения/декодирования выполняются до первого transport-вызова (включая reconcile) и на существующих границах приостановки; локальный отказ не увеличивает attemptCount/serverCreationAttempted. nil снимает только новый барьер, не прежние gates. Серверный протокол, transport и retry расписание не меняются.
- Граница предыдущего пункта — попытка отправки, включая её предварительный reconcile. Существующее чтение серверных метаданных уже известной записи для владения, обработки и очистки сохраняется после штатного удаления локального пакета: явный внутренний `reconcileServerTruth` выполняет только GET, не создаёт встречу и не разрешает последующий upload. Строгий upload/reconcile и копия клиента с проверкой не снимают свой барьер при смене контекста. Это сохранение действующих служебных путей, не исключение из допуска отправки.
- `LocalRecordingManifestService.swift`: для принятия требуется commit без fallible операций после него. Защищённый временный файл в том же каталоге полностью записывается и синхронизируется до атомарной замены manifest; после успешной замены не допускается ошибка chmod, превращающая сохранённый accepted в сообщённый отказ. Сбой до замены сохраняет прежний pending. Тестовый before-commit hook только вводит ошибку, не заменяет рабочий writer и не умеет обходить сохранение. Обрыв питания/отказ самого накопителя не объявляется доказанным тестами перезапуска процесса. Синтетические временные каталоги, никакой реальной встречи/сети.
- Порядок проверки: отрицательные тесты текущего дефекта → реализация → новые тесты → регрессии writer/recovery/queue/capture → общий F277 набор/builds → независимое review. Фиксировать время операции подтверждения; добавлено ровно одно сохранение при принятии, ноль новых операций на аудиотакт. Цель подтверждения на исправном локальном тестовом хранилище ≤100ms; превышение исследовать перед ручной приёмкой. Частоты, frame counts, непрерывность, Stop сохраняются в существующих тестах; часовой benchmark не заявляется выполненным.

Тесты сначала фиксируют новый контракт: геометрия, optional fields, repeat update/focus, start/skip/close/timeout×remember, expiry generations, dedupe/priority,0/1/5, quiet/sound/privacy, old-install cleanup, account switch. Source gate охватывает production consumers и тестовые контракты, не только отсутствие одного имени.

Quickstart содержит команды и ручную матрицу. Аудиодвижок не изменяется: регрессии capture gates/stop обязательны; часовой benchmark не требуется без изменений движка. При изменении real-time capture scope вернуться к уточнению. Native build + ContractValidation + UI evidence не заменяются source scan.

## Project Structure

```text
specs/277-compact-notifications/
  spec.md plan.md research.md data-model.md quickstart.md
  contracts/notification-ui.md contracts/settings-bridge.md checklists/ tasks.md
apps/macos/RecApp/Sources/Notifications/
apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift
apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/Shared/Tests/
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html
apps/server/tests/contract/
scripts/check_notification_retirement.py
changes/unreleased/F277.yaml
```

## Complexity Tracking

Constitution violations: none. Не добавлять второй transport, сервер истории или feature flag старого показа.
