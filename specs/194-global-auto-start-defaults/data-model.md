# Data Model: Глобальный автозапуск и defaults

| Entity | Fields | Lifecycle / invariant |
|---|---|---|
| AssistedAutoStartPolicy | `scope`, `policyRef`, `acknowledgementSubjectRef`, `deviceRef`, versions, issued/expiry, `noticeMode` | `scope` is `workspace` or `all_workspaces`; policy is emitted only when current time and config are valid |
| Installation defaults marker | `automaticRecordingDefaultsApplied` | Missing settings file starts false; legacy file without key decodes true; once true, registry refresh cannot rewrite targets |
| Prompt decision | target ID, bundle ID, prompt outcome, start reason, current policy/ack state | Prompt can be displayed without ack; only explicit current Start/opt-in can create ack/start; Skip/timeout without ack are terminal for prompt |
| Verified native target set | registry target IDs | Derived from `macos`, `native_app`, `prompt_enabled`; browser/unknown/diagnostic targets excluded |

Global `policyRef` is opaque and stable for scope/version. Subject/device refs are
opaque and include authenticated user/workspace/device, so a global policy never
becomes a cross-workspace acknowledgement.
