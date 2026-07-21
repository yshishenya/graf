# T101 PostHog SMTP delivery receipt: 2026-07-21

This follow-up records the production SMTP configuration used to deliver the
pending second-operator invitation. It contains status and configuration
metadata only. No recipient address, invitation URL, password, credential
value, message body, or provider payload is recorded.

## Route and credential boundary

- GRAF application mail continues to use the Postal HTTP API. PostHog uses the
  same owner-controlled Postal installation through its internal SMTP service;
  this is the same mail contour, not a second external provider.
- PostHog connects to the internal `postal-smtp:25` endpoint on the shared
  Docker network. TLS and SSL are disabled for this hop because it stays on the
  private Docker network; the Postal public SMTP hostname is not used by
  PostHog.
- A dedicated Postal SMTP credential was generated for PostHog. The key is
  stored only in the PostHog instance settings database and was not printed,
  logged, or committed. It is not the GRAF Postal API key.
- The sender domain is the Postal-owned `tutor.2brain.pro` domain. A sender
  outside a Postal-owned server domain is rejected, so the prior `rec` sender
  was corrected before retrying.

## Delivery verification

The existing pending invitation was resent; no duplicate invitation was
created. The worker completed the email task and the PostHog messaging record
has a non-null sent timestamp. Redacted Postal logs independently showed:

- SMTP authentication accepted (`235`);
- sender and recipient accepted (`250`);
- message data accepted and queued (`250`);
- connection closed normally.

GRAF readiness and the PostHog `_health` endpoint both returned HTTP `200`
after the change. The invitation remains pending until the invitee accepts it,
chooses their own password, and enables MFA; the active PostHog membership
count is therefore unchanged until that user action.

## Safety and remaining boundary

Product analytics provider flags remain disabled and fail-closed. This SMTP
change only enables PostHog account-invitation mail; it does not enable
autocapture, replay, Yandex delivery, or an “all events” rollout.

The Postal SMTP container was connected to the PostHog Docker network at
runtime. A future Postal container recreation must preserve that connection (or
declare the shared network in the reviewed Compose handoff) before PostHog mail
is retried. Until that durable Compose change is separately reviewed, the
runbook treats network reattachment as an explicit post-recreate check.

T101 remains open for invitation acceptance/MFA, independent RBAC and audit
review, dashboard freshness, deletion-enforcement evidence, and persistent
restore/alert ownership.
