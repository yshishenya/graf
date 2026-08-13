# Research: Assisted Auto-Start Hardening

## Decision 1: Policy transport

**Decision**: сервер добавляет optional `assistedAutoStartPolicy` в существующий
authenticated meeting target registry response. Policy появляется только когда
runtime switch включён, текущий `tenant_scope.workspace_id` равен явно
настроенному internal workspace, все обязательные значения корректны и expiry
ещё не наступил.

**Rationale**: registry уже authenticated, device-bound, workspace-scoped,
versioned, cached и имеет ETag. Это устраняет новый network round trip и отдельный
policy service. Отсутствующее поле однозначно означает deny.

**Rejected**:

- Новая policy/acknowledgement таблица и admin CRUD: лишняя подсистема для одного
  внутреннего workspace без внешнего rollout.
- Глобально включённая policy в seeded registry: небезопасно для будущего нового
  workspace.
- Проверка `captureSession?.sourceAppEligibility`: это состояние предыдущей
  capture session, а не workspace authorization.

## Decision 2: User acknowledgement

**Decision**: хранить accepted policy reference, acknowledgement subject и
device references, acknowledgement version и timestamp в существующем atomic
`MeetingDetectionSettingsStore`. Server-generated opaque references привязаны к
user+device+workspace+policy; смена пользователя, устройства, workspace, policy
или acknowledgement version автоматически требует нового принятия.

**Rationale**: capture выполняется локально и требует device-local осознанного
разрешения. Существующий JSON store уже миграционно декодирует настройки и не
требует новой БД. Неуспешная запись не считается acceptance.

**Rejected**:

- Считать per-target checkbox подтверждением общей policy: он разрешает target,
  но не объясняет автоматический timeout.
- Считать default `.detectAndAsk` согласием: default не является действием
  пользователя.
- Server-side acknowledgement table: понадобится при multi-device/customer
  governance, но сейчас не меняет локальную trust boundary и увеличивает scope.

## Decision 3: First-run behavior

**Decision**: существующие target IDs сохраняются, но prompt/countdown и saved
target auto-start остаются неактивными до принятия текущей policy в настройках.
Настройки показывают отдельный понятный switch с policy version/expiry; отключение
удаляет acknowledgement, но не target selection.

**Rationale**: это безопасная миграция до внешних пользователей и не подменяет
явное разрешение молчаливым countdown на первой встрече.

## Decision 4: Start attribution

**Decision**: один detector-assisted decision object переносит target, stable
reason, policy snapshot и acknowledgement до общего capture start path. Scope
approval различает нажатие в prompt и prior authorization; recording evidence
использует `.user` только для button и `.assistedAutomation` для timeout/saved
target.

**Rationale**: причина выбирается один раз в месте события и не теряется при
переходе через capture controller. Это устраняет ложный generic
`meeting_detection_prompt` и `.user` для автоматических стартов.

## Decision 5: Real storage readiness

**Decision**: переиспользовать `LocalBufferService.defaultPolicy`, но подавать в
него фактический размер уже загруженной локальной upload queue и нативную
available disk capacity для volume каталога recordings. Ошибка измерения
capacity блокирует assisted start.

**Rationale**: hardcoded `.healthy` не является проверкой. Существующая policy
уже содержит thresholds и mapping в `LocalBufferRiskState`.

**Rejected**:

- Проверять только возможность создать directory: не выявляет низкий disk reserve
  или превышение buffer budget.
- Новый storage policy: дублировал бы существующий `LocalBufferService`.

## Decision 6: Countdown testability

**Decision**: вынести single-resolution countdown decision в небольшой pure Swift
state model с injected timestamps. SwiftUI остаётся владельцем animation/task,
но Start/Skip/timeout проходят через модель. Timeout перед capture повторно
вызывает общий gate evaluation.

**Rationale**: это даёт детерминированные 7.999/8.000 s и race tests без ожидания
реального времени и без UI automation framework.

## Decision 7: Offline and expiry

**Decision**: cached authenticated registry разрешает assisted start только пока
и registry, и embedded policy не истекли. Missing/expired/malformed policy не
восстанавливается локальными defaults.

**Rationale**: сохраняется ограниченная offline usability без бессрочного права
на автоматическую запись.

## Decision 8: Rollout

**Decision**: committed defaults — disabled. Production requires explicit
workspace ID, policy version, acknowledgement version and expiry plus enabled
switch. External/customer enablement исключено.

**Rationale**: пользователь подтвердил отсутствие внешних пользователей, но код
должен оставаться безопасным при их будущем появлении.
