# F277 — Исследование и решения

Дата2026-09-26. База `f5cca687a06dc57ad6ccbef840a0be897eaa6336`. Выводы о реализации проверены по исходникам, не являются ручной проверкой нового интерфейса.

## R1. Собственный канал

Decision: единая AppKit-карточка; системный показ удаляется.
Rationale: нужны две команды, флажок и изменяемый отсчёт. Native actions существуют, но обычный banner не даёт нужной компоновки.
Alternatives: native-only меняет UX; hybrid оставляет два договора. Не утверждаем невозможность macOS content extensions: их UIKit-документация не основание для категорического запрета.
Sources: https://developer.apple.com/documentation/usernotifications/unnotificationaction ; https://developer.apple.com/documentation/usernotificationsui/unnotificationcontentextension

## R2. Геометрия

Decision: card380pt, padding12, icon18, gap8, radius12, close18/hit28 overlay. Short44–52pt при обычном шрифте. Buttons ниже, checkbox отдельно.
Rationale: нынешние headerLeading50+icon24+gap8 дают82pt до текста; minimum height82. Short повторяет заголовок. Уменьшение крестика само не убирает колонку.
Alternatives: pill плохо масштабируется на actions; фиксированная высота сохраняет пустоту; inline button сужает текст и меняет структуру.
Sources: `DesktopNotificationCardPresenter.swift`; https://carbondesignsystem.com/components/notification/usage/ . Krisp2.37.4 (2024, не нынешняя версия) показывает overlay close: https://whatsnew.krisp.ai/announcements/krisp-2-37-4-new-krisp-widget-and-other-improvements . Изображения не включаются в приложение.

## R3. Сроки и доступность

Decision:20s outcomes,6s preview,8s recording; hover/focus hold только informational. Повторный доступ к нейтральным результатам в меню, проблема остаётся у записи. Явная команда focus; tick без перестройки дерева.
Rationale: исчезновение не единственный шанс прочитать результат;8s — отдельный конституционный договор. Риск для медленного чтения остаётся, полное WCAG compliance не заявляется; ручная запись/Stop доступны без таймера.
Sources: https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html ; https://carbondesignsystem.com/components/notification/accessibility/ ; ConstitutionII.

## R4. Двойная календарная логика

Decision: единое расписание0/1/5min; deadline=min(due+120s,event end), refresh его не сбрасывает. Просроченное окно не воспроизводится.
Rationale: `reconcileReminders()` использует selected offset, custom `cardLeadTime`=15min. Удаление UN scheduling без переноса prefs ломает настройку.
Alternatives: fixed15min теряет выбор; два напоминания оставляют дубль.

## R5. Приватность и доставка

Decision: quiet suppresses optional popup/sound, не prompt/indicator/Stop. History memory/context-only50neutral. Lock/sleep отменяют prompt и callbacks; wake требует свежей detection, не догоняющего таймера.
Rationale: custom не наследует OS notification policy и не работает при завершённом процессе. Focus API требует разрешения и может возвращать unknown; частные API/файлы не использовать. Не обещать screen-sharing invisibility.
Sources: https://developer.apple.com/documentation/intents/infocusstatuscenter ; https://support.apple.com/guide/mac-help/get-notifications-mchle7f8a9b0/mac

## R6. Полное удаление

Decision: удалить UN scheduling/categories/delegate/permissionUI, obsolete SwiftUI prompt, `DesktopRecordingNoticePresenter`, last-notice state и rollback alias dual-write, их consumers/tests. Оставить единственную вызываемую очистку own pending/delivered OS requests без authorization/transport. Сохранить session ownership, safeURL checks, актуальный incident dedupe, capture controls; server inbox/billing и historical evidence вне удаления.
Rationale: нужны deletion map, reference scan и tests действующих invariants. Старые incident claims требуют ограниченного переноса без повтора закрытой проблемы.

## R7. Долговечное принятие запуска (2026-09-27)

Decision: пользователь разрешил узкую правку P1; pending/accepted хранится в
manifest, pending также не содержит scopeApproval. Принятие той же сессии —
синхронная операция после проверки token/context, без новой точки приостановки
MainActor; память меняется после успешного атомарного сохранения.
Rationale: существующий stop(permissionDenied) недостаточен при отказе записи
final manifest: на диске остаётся active, которое recovery могло превратить в
ready. Предварительный pending переживает такой отказ. Отсутствие scopeApproval
сохраняет запрет и при чтении старым клиентом.
Alternatives: только отмена enqueue не защищает rescan/restart; отдельный файл
запрета усложняет согласование двух файлов; новый server protocol не нужен.
Совместимость: nil у исторических пакетов сохраняет прежние проверки, но не
доказывает безопасность ранее созданного неоднозначного фрагмента. Исторические
аудиоформаты не возвращаются в отправку.
Sources: текущие startOnQueue/stopOnQueue, recoverIncompleteRecording,
isServerUploadEligible и TwoBrainRecApp.startAsync/MeetingDetectionStartCancellation.

Отдельно: существующий LocalCustodyFileProtection.write может выбросить ошибку
apply после замены данных; для manifest принятия нужен защищённый staging до
atomic commit без fallible post-commit операции. Queue cached profile также
недостаточен — чтение принятия требуется на живой границе отправки.
Основание атомарной замены в одной файловой системе:
[Apple rename(2)](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/rename.2.html).

## Unresolved questions

T035, решение 2026-09-28: выбранное владельцем сохранение относится только
к видимой карточке, не к прежнему календарному списку. Основание: реальный
CalendarTrayModel сейчас очищает events и посылает nil на503/offline;
presenter воспринимает это как удаление и завершает одноразовый claim.
Явный результат обновления сохраняет различие ошибки и недействительности.
Отклонены: сохранение всего snapshot (может породить новые старые карточки),
повторный показ после восстановления (нарушает однократность), новый120s
от сбоя (продлевает deadline), сохранение после401/403 (нарушает приватность).

Блокирующих продуктовых вопросов нет. Measurements/callbacks/migration/accessibility требуют доказательств при реализации, не считаются уже пройденными.
