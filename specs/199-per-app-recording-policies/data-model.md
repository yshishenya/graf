# Data Model: Политики автозаписи по приложениям

| Entity | Fields | Invariants |
|---|---|---|
| `AutomaticRecordingRule` | `always`, `ask`, `never` | Every eligible target resolves to exactly one rule; missing/new target defaults to `ask`. |
| `MeetingDetectionSettings` | Existing detection/upload fields; target rule map; legacy fields during migration; workspace auto-start acknowledgement | Target rules are independent of workspace/device policy acknowledgement. |
| `PromptDecision` | target ID, button outcome, checkbox state, start reason, persistence result | Timeout starts only the current meeting and never persists a rule. |
| `BulkRecordingRuleSelection` | `always`, `ask`, `never`, `mixed` presentation | Selecting a concrete value applies it to all eligible targets; `mixed` is display-only. |
| `WorkspaceAutoStartAuthorization` | Existing policy ref, subject ref, device ref, versions and expiry | Remains required for assisted automatic starts and is never copied to another target. |

## Codable migration

- Add a new target-to-rule field with a backward-compatible default.
- Read old `autoRecordTargetIds` only as a migration source; do not keep using it
  as the authoritative decision after the new field is materialized.
- Legacy selected targets become `ask` unless a future migration record contains
  explicit target-specific user intent. Legacy global acknowledgement is retained
  only for workspace policy compatibility and cannot upgrade every target to
  `always`.
- Unknown registry targets remain stored but are not rendered or acted on until
  they become verified native prompt-capable targets.
- Writes remain atomic and preserve unrelated settings.

## State transitions

```text
ask --(Start + checkbox)--> always
ask --(Skip + checkbox)----> never
ask --(Start/Skip no checkbox, timeout)--> ask
always --(settings)---------> ask | never
never --(settings)----------> ask | always
```

The timeout transition always remains `ask` for persistence, even when the
checkbox is visually checked.
