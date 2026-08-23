# Data Model: Единый ввод одноразового кода

No persisted model or API contract changes.

| Field | Scope | Rule |
|---|---|---|
| `data-code-slot` | six visible HTML inputs | one digit, not submitted directly |
| `data-code-hidden` / `name=code` | existing form field | exactly the concatenated six digits before submit |
| `email`, `state`, `next`, `csrf_token` | existing hidden auth fields | unchanged and preserved per flow |

The six slots are presentation state only. The backend receives the same
single `code` string as before.
