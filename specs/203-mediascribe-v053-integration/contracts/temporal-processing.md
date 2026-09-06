# Temporal processing contract

- Workflow code remains deterministic and contains no provider I/O, filesystem access or wall-clock polling loops.
- Provider GET/POST/result import operations remain Activities with bounded timeout/retry policy.
- `Retry-After` and `next_retry_at` are activity outputs persisted through the existing workflow/store schedule; the workflow waits with a durable timer.
- A signal/update for manual check claims the current generation and reconciles the same provider job. It never silently creates a new business attempt.
- `workflow.patched`/existing versioning seams remain in place for changes to command shape or timer behavior; running workflows must replay.
- Workflow payloads and Search Attributes remain bounded and metadata-only for this integration; word metadata stays in GRAF result storage.
- Cancellation and deletion fences prevent a late activity from writing an imported result after meeting deletion.
