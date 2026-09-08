# Implementation Plan: Верхняя панель и уведомления

**Branch**: `codex/249-notification-control-design` · **Date**: 2026-09-06 · [Spec](spec.md)

## Summary

Сохранить capture и upload, расширить CalendarTray до общей панели состояния, добавить историю уведомлений и уточнить настройки. После «продолжай» внедрение входит в область работы; начало кода после reviewer-owned проверок. HTML не является доказательством нативной записи или доставки.

Нативная доставка macOS — обязательный результат FR-019. Проверка на закрытом окне и незагруженном WKWebView обязательна. Исторический native-preview не заменяет интеграцию DesktopNotificationPresenter; его сборщик отключён. Все дальнейшие проверки — только установленный GRAF Dev.

## Technical Context

- Swift/AppKit/SwiftUI текущего проекта; Python/FastAPI/Jinja и текущий JavaScript кабинета. Существующие XCTest/pytest. Новых UI-фреймворков нет.
- PostgreSQL: серверная прочитанность и настройки. Локальная запись/очередь — существующие нативные сервисы.
- **Risk / Validation Lane**: high-risk UX / reference fidelity / capture-adjacent. Реализация; независимый UX/security review требований пройден.
- **Release Gate**: no deploy на этапе дизайна; внедрение требует текущих release-and-validation gates, governance-fast на точном SHA, capture/privacy проверок; production — dry-run, публичный Mac — notarization/stapling/Sparkle.
- macOS, web и embedded cabinet. Мобильный web — история и настройки, не захват Mac.
- Панель открывается по локальному состоянию без сети; цель p95 визуального ответа ≤200 мс. История — 30 строк, cursor pagination.
- Успешные/решённые события 30 дней; активные до разрешения. Transcript/audio не являются payload уведомлений.

## Constitution Check

До исследования и после дизайна: I/II — capture-first, 214, видимый Stop сохранены; III/IV — UI-история не меняет observability/удаление; V — дистрибуция/обновления не меняются; VI — high-risk процесс; VII — независимая реализация по наблюдениям, явные ограничения референса.

При повторном разборе уточнены идентичность карточки, порядок commit, отдельные формы и границы браузера; см. уточнения в контрактах. Это не независимое одобрение. Calendar-only ограничение 168 заменяется только в составе панели; источник/безопасность календаря сохраняются. Рецензирование требований UX/security завершено; выпуск не выполняется.

## Phase 0 — Research

[research.md](research.md): Krisp 3.15.6, код и живой GRAF. Native Tray Krisp и новая запись не доказаны; для точного сравнения нужны дополнительные наблюдения. Предложенный GRAF-контракт не использует выдуманные факты.

## Phase 1 — Design

[contracts/experience.md](contracts/experience.md) — IA, состояния, 20 событий, тексты, настройки; [data-model.md](data-model.md) — владение и прочитанность; [contracts/notifications.md](contracts/notifications.md) — интерфейсы; [quickstart.md](quickstart.md) — проверка.

## Implementation Approach / Project Structure

1. Расширить `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift` snapshot состояния и действиями из `apps/macos/RecApp/App/TwoBrainRecApp.swift`. Не создавать второй NSStatusItem или state machine записи. CalendarTrayModel остаётся календарной проекцией.
2. Расширить компактную нативную поверхность теми же командами; Stop виден при скрытом окне/строке меню. Панель 214 не превращать в постоянный виджет с активным countdown.
3. Серверная история — небольшой модуль `apps/server/src/twobrain_rec_server/notifications/inbox.py` и additive migration со свободным номером на момент внедрения. Billing outbox остаётся транспортом обязательных событий. Метаданные уведомления сохраняются атомарно с доменным изменением либо в существующем надёжном outbox; наружный показ только после commit. Стабильная карточка, read_revision и cursor следуют data-model.md; массовое чтение и отдельный счётчик sequence не вводятся. Точки источников перечислены в research.md.
4. Общий компонент в `cabinet/templates/cabinet/pages/shell.html`, `components/notification_inbox.html` (новая история; существующую `components/notifications.html` с формой не заменять), текущие CSS/JS. Новые маршруты в `cabinet/web_routes/notifications.py`. Страница истории как fallback без JS. Повторное использование route/focus/CSRF patterns.
5. Предлагаемый `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift`: UNUserNotificationCenter только для календарных напоминаний и допустимых локальных сообщений, контекстный permission; NSPanel 214 остаётся прежней. Foreground/capture/OS permission выбирают канал, Focus не обходится.
6. Расширить `billing/notification_preferences.py`, `cabinet/web_routes/settings.py` и `pages/settings_notifications_content.html` семантическими категориями с версией формы; не менять старые optional flags. Локальные настройки Mac сохраняются независимо от сервера.
7. Только после parity уточнить calendar footer и удалить доказанно недостижимую compact queue ветку `Sources/Cabinet/DesktopMeetingShellView.swift`. Сохранить миграцию autoRecordTargetIds и автономный режим.

## Validation Plan

Дизайн: ссылки, FR→tasks, синтаксис/самопроверки прототипа, реальный браузер и ключевые переходы. Без записи/платежей/приватных мутаций.

Внедрение: XCTest CalendarTray/lifecycle/countdown/accessibility/routes; pytest preferences/read/scope/mandatory; транзакционный повтор и гонка показанной revision и нового результата; живой Mac permissions/offline/disk/hidden window; web/WKWebView keyboard/dark/light/narrow. Перед PR — repository gate на точном SHA по актуальному release guidance. Полный CI на дизайне не запускается.

## Migration / Rollback

Сначала additive server schema, совместимая со старым клиентом. Old optional false сохраняется. При недоступной новой capability Mac оставляет рабочие capture/calendar действия. При включении producer зафиксировать начальную границу событий, не показывать готовности всех старых встреч. Откат клиента сохраняет читаемость очереди; откат сервера не удаляет новые таблицы/mandatory outbox. Отказ новых баннеров не ломает запись.

## Complexity Tracking

Нарушений конституции не заявлено. Прочитанность и scope требуют истории отдельно от delivery outbox. Не нужны AI-тексты, plugin-система каналов, новая очередь, Service Worker push или глобальный лидер устройств.

## Review status

Команда продолжить получена. Независимые UX/security markers не изменены. Уточнения и оставшиеся критерии находятся в [review-preparation.md](review-preparation.md). Review, analyze и issue mapping выполнены. Legacy Impact реализации: `remove` для недостижимой embedded queue и старых обходных команд запуска; совместимые decoder сохранены.

Повторный веб-аудит: [правила внимания](web-attention-audit.md). Веб использует has_unseen_action_required и important/history; общий числовой badge и массовую кнопку read-all не реализовывать. Не добавлять планировщик обычных web-баннеров. Нативные правила выбора канала уточнены в experience.md; прежний native-preview не является доказательством их реализации.

Актуальное уточнение FR-020: [разделение поверхностей](surface-separation.md). Native server-inbox и local-event bridge не нужны. Read-all не проектируется: одиночный read_revision достаточно для веба, Mac показывает текущий health без прочитанности. Удалить из проектируемой схемы result_ready_enabled, если его отсутствие в реальном продукте повторно подтверждено; существующие optional поля не менять. Нативный макет обновлён под локальное состояние; его проверки не заменяют продуктовую приёмку.

Анализ перед кодом: [analysis.md](analysis.md); текущие источники и контекстные категории: [producer-contract.md](producer-contract.md).

## Уточнение размещения после проверки Krisp — T036/T037

Пользователь отклонил колокольчик рядом с заголовком. В установленном Krisp повторно наблюдался отдельный пункт Activity в боковой навигации и экран с Updates / Only show unread. Для GRAF: постоянный пункт «Уведомления» над профилем, значок в свёрнутом меню; на мобильном вебе тот же элемент перемещается в существующее меню навигации. Панель important/history остаётся вне заменяемого main и прокручиваемого sidebar. Точка обозначает только новое требующее действия событие; новые каналы доставки не добавляются.

Нативный popover получает явный размер не больше visibleFrame экрана кнопки меню. Управление записью остаётся над прокруткой; источники, проблемы и календарь — ниже. Ошибки действий и отсутствие аудиоданных остаются видимыми в компактном виджете. Изменение не меняет команды capture или механизм доставки.


## Блокер обновления Dev после совмещения

T038 уточняет существующий workflow единственного Dev: `dev-schema-transition.md`.
До независимого рассмотрения требований и проверки сохранности данных переход
со схемы0086 на0088 остаётся заблокированным. Это high-risk infrastructure
дополнение к текущему slice; не использовать UI-проверки как evidence его безопасности.
