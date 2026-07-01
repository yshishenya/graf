# Contract: Runtime Flow Evidence

Each flow in `audit/runtime-flows.md` must include:

```yaml
flow_id: stable-flow-id
plain_language_goal: "What the user or operator is trying to do"
start_event: "User/system/deploy event"
steps:
  - order: 1
    path: exact/repository/path
    responsibility: "What this step owns"
state_touched:
  - "local package, DB row, object, queue, worker state, or cabinet state"
trust_boundaries:
  - "desktop native, server API, worker, storage, third-party, admin, deploy"
validation_before_refactor:
  - "Focused proof needed before code changes"
```

## Rules

- A flow is incomplete if it stops at code structure and does not name runtime
  state or trust boundaries.
- Capture and deletion flows must include one-action stop, local visibility,
  custody, retention, and truthful deletion limits when applicable.
- MediaScribe flow evidence must keep the desktop out of direct MediaScribe
  credential handling.
- Deploy flow evidence must distinguish dry-run, execute, backup, restore, and
  smoke proof.

