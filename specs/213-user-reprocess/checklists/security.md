# Security and Privacy Checklist: Повторная обработка записи

## Authorization

- [x] Only `Meeting.created_by_user_id` may launch reprocessing
- [x] Launch and manual retry revalidate authorization server-side
- [x] Shared recipients and unrelated workspace users cannot invoke actions
- [x] Cross-workspace/non-owner requests use non-disclosing behavior
- [x] Existing session, device and CSRF checks remain required

## Integrity

- [x] Expected workflow identity and revision are validated at the trust boundary
- [x] A stale predecessor cannot create a second successor
- [x] Meeting deletion and accepted revision are locked before admission
- [x] Exact workflow identity is checked inside the worker
- [x] Partial and stale results cannot become user-visible

## Privacy and secrets

- [x] The request contains no reason, free text or meeting content
- [x] Provider payloads/errors and credentials stay outside customer UI
- [x] MediaScribe credentials remain worker-only
- [x] Evidence and tests use synthetic or metadata-only data
- [x] No new audit retention surface is introduced
