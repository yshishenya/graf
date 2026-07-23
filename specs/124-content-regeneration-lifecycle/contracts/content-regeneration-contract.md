# Contract: Content Regeneration and Accepted Current

This contract defines user-visible and server-visible behavior. It is
implementation-neutral; concrete route names may reuse the existing cabinet
API paths as long as these semantics remain true.

## Actors

- **Owner**: may request, preview, accept, reject and retry candidates for a
  meeting the owner can manage.
- **Shared viewer**: may read only accepted current content permitted by ACL.
- **Automatic system actor**: may create the bounded initial baseline candidate
  under product/workspace policy, but never silently accept it.
- **Worker/reconciler**: advances durable processing/generation without changing
  published current unless an explicit accept operation passes its fence.

## Request idempotency

Every generation request carries or derives an idempotency key from:

```text
meeting + media_revision + processing_result_hash + template_version
  + generator/config fingerprint + explicit request intent
```

The same key returns the existing active/terminal candidate. A same-format
manual refresh must supply a new explicit intent; selector focus and page load
are not intents.

## Candidate response states

| State | Owner view | Shared view | Next action |
|---|---|---|---|
| queued/dispatching | `Готовим вариант «<формат>»…` | hidden | return later |
| generating | `Готовим вариант «<формат>»…` | hidden | return later |
| ready | format name + owner-only preview | hidden | `Использовать`, `Оставить текущие` |
| retryable failure | `Не удалось подготовить вариант` | hidden | `Повторить` |
| terminal failure | concrete bounded impact | hidden | open support/recovery |
| stale/conflict | `Итоги уже изменились` | hidden | `Обновить` |
| expired | `Вариант больше недоступен` | hidden | request again |
| blocked | concrete policy/input reason | hidden | fix prerequisite |
| accepted | current accepted projection | accepted projection only | no candidate action |

Current accepted text remains rendered while every non-accepted state changes.

## Preview

Owner-only preview is read-only and contains:

- safe format display name;
- source/result timestamp or revision label suitable for a human;
- generated category items with truth labels and evidence refs allowed by the
  current detail policy;
- bounded provenance summary (not provider credentials, raw request, prompt
  secrets or internal signed URLs);
- explicit distinction from current accepted content.

Preview content never changes `current_outcome_set_id` and is not returned by
shared/public/export paths.

## Accept

`Использовать` must atomically validate:

1. owner authorization and workspace access;
2. candidate is ready, unexpired and not deleted/blocked;
3. candidate source/result hash equals the current accepted source fence expected
   by the request;
4. candidate expected current pointer still equals the stored current pointer;
5. meeting deletion epoch is unchanged and active.

On success, exactly one candidate becomes accepted/current and the previous
accepted outcome becomes superseded. On any conflict, response is 409 with no
pointer or content mutation.

## Reject/dismiss

Reject, dismiss, close and failed generation leave current unchanged. They may
  mark candidate terminal and retain metadata-only lineage. They do not erase
  historical accepted outcomes.

## Automatic policy

- Trigger only after an eligible terminal transcript/result and only once for
  the idempotency key.
- Bounded retries for timeout, 429 and transient 5xx; no automatic retry for
  missing input, permission, deletion, policy, invalid template or unsupported
  payload.
- New source revision may create an unaccepted candidate only where the
  workspace policy allows automatic follow-up; no silent replacement.
- Reopen, view, refresh, deployment or polling never triggers a new request.
