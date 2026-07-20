# T101 access and rollout boundary receipt: 2026-07-21

This metadata-only receipt records the access and rollout decision made after
the PostHog operations review. It contains no email address, invite token,
password, API key, or user payload.

## Second-operator access

- A pending organization invitation with `ADMIN` level was created for the
  second trusted operator supplied by the owner.
- The active organization membership count remains `1`; the invitation has not
  been accepted and therefore does not yet prove independent RBAC/audit review.
- PostHog email delivery is not configured (`email_available=false`), so no
  invitation email was sent. The one-time invitation URL is deliberately not
  recorded in git or printed in chat.
- The invite is not expired. The invitee must accept it, set their own password,
  and enable MFA. No password was created or stored by the operator.

## Rollout scope decision

“Enable all events” is not a single safe switch:

1. First-party PostHog autocapture is designed to cover current browser pages,
   but global delivery is still fail-closed until rollout approval and the
   credential/content suppression contract remains mandatory.
2. Yandex offline conversions are intentionally limited to the two approved
   activation goals: `desktop_account_connected` and
   `first_value_session_completed`.
3. Session replay, Webvisor, click maps, scroll maps, and form analytics are
   separate capabilities and require page-class masking, legal, QA, retention,
   and rollback evidence.

Widening all providers to every event could capture passwords, OAuth codes,
tokens, signed URLs, cookies, meeting content, or raw payloads and would make
retention, deletion, and external-provider disclosure ambiguous. No widening
was applied. Provider flags remain disabled/fail-closed.

## Operations default

The safe default remains journald metadata plus the root-owned runtime guard:
automatic analytics rollback is enabled, full-stack stop is disabled, and
normal GRAF workflows stay online. No new backup destination was invented.
The isolated restore rehearsal remains passed, but persistent backup-target and
alert-recipient review is still open because it requires an explicit storage
and ownership decision.

T101 remains open until the invitation is accepted with MFA, the rollout scope
is separately approved, and persistent backup/alert ownership is recorded.
