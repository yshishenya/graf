# Contract: Autorepair State Machine

## Purpose

Define allowed automatic recovery behavior for live route stability. This
contract prevents manual `Run Check` from becoming the normal recovery path and
prevents infinite repair churn.

## States

- `not_started`
- `observed`
- `classifying`
- `awaiting_os_condition`
- `repairing`
- `waiting_for_fresh_evidence`
- `healthy_after_fresh_evidence`
- `degraded_slow`
- `blocked_non_recoverable`
- `failed`
- `retry_budget_exhausted`

## Recoverable Triggers

- `coreaudiod_restart`
- `hal_reload`
- `sleep_wake`
- `physical_device_disappeared_then_returned`
- `macos_default_route_changed_to_accepted_class`
- `browser_stream_recreated`
- `stale_browser_device_id`
- `app_route_engine_restart`

## Non-Recoverable Reasons

- `permission_revoked`
- `no_accepted_physical_input`
- `no_accepted_physical_output`
- `meeting_target_no_longer_uses_virtual_devices`
- `meeting_target_intentionally_changed_away`
- `macos_default_route_bluetooth_or_airpods`
- `macos_default_route_unsupported_class`
- `would_require_independent_physical_device_selection`
- `os_or_meeting_target_refused_stream`

## Allowed Transitions

```text
not_started -> observed
observed -> classifying
classifying -> awaiting_os_condition
classifying -> repairing
classifying -> blocked_non_recoverable
awaiting_os_condition -> repairing
repairing -> waiting_for_fresh_evidence
repairing -> failed
repairing -> retry_budget_exhausted
waiting_for_fresh_evidence -> healthy_after_fresh_evidence
waiting_for_fresh_evidence -> degraded_slow
waiting_for_fresh_evidence -> failed
failed -> classifying
retry_budget_exhausted -> blocked_non_recoverable
```

## Timing Rules

- Normal recoverable disruptions must reach `healthy_after_fresh_evidence`
  within `<= 2 seconds`.
- OS/device-heavy recoverable disruptions must reach
  `healthy_after_fresh_evidence` within `<= 10 seconds` after required OS/device
  conditions are available again.
- Slower success is `degraded_slow`, not clean acceptance.
- Non-recoverable blocked states are not measured as slow recovery.

## Fresh Evidence Rules

Autorepair may report healthy only when all applicable evidence is fresh:

- meeting target still uses `2brain Rec Microphone` and `2brain Rec Speaker`;
- macOS default route resolves to built-in, wired, or USB input/output;
- virtual client activity is fresh;
- frame continuity resumes;
- recording timeline gap evidence is recorded when recording is active.

## User Action Rules

Clean autorepair acceptance requires:

- no `Run Check`;
- no app relaunch;
- no meeting settings reopen;
- no manual meeting-target device reselect;
- no required modal or blocking user action.

Manual `Run Check` remains diagnostic fallback and must be recorded as
`user_action.run_check`.
