# Research

## Единая поверхность
Decision: кабинет — обычная точка редактирования, native окно — только резерв. Rationale: страница записи уже меняет локальный store. Alternatives: две постоянные формы сохраняют путаницу; перенос аккаунта/оплаты в SwiftUI дублирует код; автономный HTML-cache создаёт новый auth lifecycle.

## Локальные уведомления
Decision: небольшой EmbeddedCabinetNotificationSettingsBridge, без универсального framework. Rationale: DesktopNotificationPresenter уже владеет четырьмя полями, разрешением, scheduling и звуком. Research agent settings_audit независимо исследовал этот вопрос по Phase 0 speckit-plan; ничего не менял. Прямой доступ нового bridge к UserDefaults обходит privacy cleanup; перенос на сервер нарушает local scope.

Критическая деталь: уведомления принадлежат текущему аккаунту на Mac. Presenter.invalidate сбрасывает owner/context и увеличивает generation; updateContext меняет контекст. Nonce документа дополняется auth/context generation (включая A→B→A). Auth-change немедленно блокирует bridge до подтверждения нового контекста. После каждого await перепроверяются документ/поколение. Ответ не содержит user ID/cookies/календарь.

## Сохранение
Decision: patch одного поля через store/presenter; snapshot после подтверждения; read после неопределённого результата. Нужен явный Bool/Result из presenter.save, а не сравнение русской message. Полный устаревший snapshot может затирать соседнее поле. UserDefaults не доказывает fsync — новую гарантию долговременной записи не заявлять.

## Приложения
Decision: системный select/Picker на строку, полный реестр, mixed общий выбор. Три фиксированные кнопки вытесняют название. Не скрывать неустановленные/ещё не использованные приложения: это нарушает §II. Не добавлять произвольные браузеры.

## Источник и ветка
Начальное дерево чистое, detached HEAD bc41c10bf. Branch hook не оставил созданной ветки; read-only dry-run предложил 6791-unified-settings из номеров веток. Следующий каталог specs после 259 — 260; явно создана codex/260-unified-settings, записан feature.json, проверены prerequisites. История не сбрасывалась. Опциональный agent-context hook не применяется: root AGENTS должен оставаться стабильным; auto-commit hooks выключены.
