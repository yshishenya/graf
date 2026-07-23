# Research: Восстановление автозаписи встреч

**Дата**: 2026-07-23

## Decision 1 — Feature 121 удалил ранее существовавший workflow намеренно

**Finding**: В текущей ветке `35926011` (Feature 121) были удалены
`MeetingDetectionPolicyAction.autoRecord`, detector output
`autoRecordEligible`, список приложений из `MeetingDetectionSettingsView`,
сохранение `autoRecordOptIn` и countdown task из prompt. Тесты были изменены с
проверок наличия на проверки отсутствия.

**Evidence**:

- `git show --stat 35926011`
- `git diff 35926011^ 35926011 -- apps/macos/Shared/Sources/MeetingDetection/MeetingDetectionPolicy.swift apps/macos/RecApp/Sources/MeetingDetection/MacOSMeetingActivityDetector.swift apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift apps/macos/RecApp/App/TwoBrainRecApp.swift`
- текущие отрицательные assertions в `CaptureControlV5Tests.swift` и
  `AppControlAccessibilityTests.swift`.

**Decision**: Считать Feature 121 историческим временным упрощением. Feature
124 — явный superseding owner текущего контракта; историю не переписываем,
противоречащие активные указания помечаем как superseded.

## Decision 2 — Восстановить код из ближайшего рабочего предка, а не из старого routing слоя

**Finding**: Предок Feature 121 (`35926011^`) уже содержит нужные безопасные
потоки и одновременно включает актуальные на тот момент проверки:

- target-scoped policy с `.autoRecord(targetID:)`;
- detector output `.autoRecordEligible`;
- settings list из canonical registry с per-target checkbox, «Выбрать все» и
  «Снять все»;
- prompt opt-in и `saveMeetingDetectionSettings()`;
- `startManualRecording(meetingDetectionTarget:)` через текущие prerequisite и
  visible capture gates;
- остановку записи при завершении обнаруженной встречи.

**Decision**: Восстановить только удалённые куски из `35926011^`, сохранив
последующие независимые изменения в текущем `HEAD` (в частности bounded
metadata-only logging и native purge authentication). Устаревший отдельный
audio-routing implementation не возвращается.

## Decision 3 — Таймер остаётся ровно восьмисекундным и видимым

**Finding**: В раннем рабочем prompt из `5b8bc09a` есть
`countdownSeconds: TimeInterval = 8`, `TimelineView(.periodic(...))`,
отменяемый `autoStartTask` и progress-based primary button. Тот же prompt
сохраняет `Всегда писать это приложение` и вызывает `onStart(Bool)`.

**Decision**: Вернуть этот 8-секундный prompt contract. Кнопка и task используют
существующий `isStartDisabled`; при блокировке gate countdown не может
запустить запись. Manual Start и Stop остаются отдельными и доступными.

**Alternative rejected**: Удалить таймер или заменить его только на
подтверждение — именно это вызвало пользовательскую регрессию и противоречит
Feature 124.

## Decision 4 — Список берётся только из verified native prompt-capable registry

**Finding**: `MeetingTargetRegistryValidator` уже отклоняет unsafe prompt
targets, а прежний settings view фильтровал `mode == .promptEnabled`,
`platform == .macos`, `targetFamily == .nativeApp` и сортировал по display name.

**Decision**: Переиспользовать этот фильтр и `MeetingTargetRegistryStore`.
Browser, future Windows, manual-only, diagnostic-only и unknown targets не
получают auto-record checkbox и не могут быть auto-start source.

## Decision 5 — Сохранение остаётся target-scoped и обратимым

**Finding**: `MeetingDetectionSettings` уже содержит
`targetScopedAutoRecordEnabled` и `autoRecordTargetIds`, а код policy и store
сохраняет их в JSON. Feature 121 оставила поля в модели, но сделала policy
глухой к ним.

**Decision**: Не добавлять новый storage schema. Checkbox в prompt и rows в
settings меняют эти поля через существующий store и notification. При удалении
target из registry его ID не переносится на другой target.

## Decision 6 — Safety gates остаются общей точкой старта

**Finding**: `MeetingDetectionPolicy` уже блокирует prompt при
`MeetingDetectionCapturePrerequisites.allowsRecordingStart == false`; start
path вызывает `CaptureScopeApprovalService`, permission gate,
`RecordingPrerequisiteGate` и `CaptureSessionController`.

**Decision**: Auto-record and countdown both resolve into the existing
`startManualRecording(meetingDetectionTarget:)` path. No direct writer start,
no bypass of visibility/Stop/storage/permission/policy checks, and no new
parallel session.

## Decision 7 — Tests must assert presence, not only absence of unsafe behavior

**Decision**: Replace Feature 121 negative contract assertions with positive
regression assertions for settings list, policy auto-record, detector output,
prompt timer, checkbox, persistence and old labels. Keep negative assertions for
unknown targets, blocked prerequisites, duplicate active sessions, hidden
capture and removed routing.

## Decision 8 — Review follow-up closes cancellation and trigger-coalescing gaps

**Finding**: The restored prompt cancelled `Task.sleep` with `try?`, so a task
could continue into `resolveStart()` after the window disappeared. The app also
accepted every prompt/auto-record trigger from one detector-output batch and
could replace an active prompt.

**Decision**: Treat cancellation at the task boundary (`do`/`catch` plus a
main-actor cancellation check) and coalesce recording triggers in the existing
`processMeetingDetectionOutputs` function. A small transient trigger guard also
covers the scheduling window before `recordingStartInProgress` is set; it is
cleared with `defer` when the existing start path returns. No new timer service,
queue or dependency is needed. The native detector and canonical registry
remain the Feature 124 boundary: browser bundles are suppressed by the native
candidate filter and current browser targets are `manual_or_browser_only`; the
separate Feature 092 browser-evidence path is not widened by this correction.

**Regression protection**: Keep source-contract assertions for cancellation,
external disappearance and one active trigger, plus the existing detector,
policy, registry and full repository checks.

## Research Limits

This is repository/history research. It does not make claims about the current
Krisp binary or external product behavior. Runtime acceptance still requires
synthetic-safe macOS validation and the repository gates listed in the plan.
