# Contract: Replay Masking

**Feature**: `094-product-activation-analytics`

This contract applies to PostHog Session Replay, Yandex Webvisor, click maps,
scroll maps, and form analytics.

## Default Rule

Authenticated, cabinet, product, embedded desktop, meeting/result, upload,
playback, deletion, settings, and admin-adjacent surfaces are private by default.
Replay is disabled until the page class has masking proof.

## Allowed Replay State

A page class may enable replay only when all of these pass:

- URL, title, and referrer contain no raw identity, meeting, file, token, signed
  URL, local path, search text, object key, passcode, or content-bearing values.
- Inputs, textareas, editors, search fields, auth fields, upload controls,
  transcript/result text, summaries, meeting titles, participant names,
  workspace/account names, calendar text, payment/contact fields, object keys,
  signed URLs, local paths, and free-text regions are hidden or suppressed.
- Safe UI allowlist is documented.
- PostHog masking/blocking selectors are documented.
- Yandex `ym-disable-keys`/`ym-hide-content` or stronger controls are
  documented where applicable.
- Browser QA proves masked rendered DOM and replay state.
- Legal review approves the page class.
- Dashboard/owner understands replay limits.

## Replay-Unavailable State

Use this state when safe page views/events can launch but replay proof is not
ready.

Behavior:

- page view: allowed if URL/title/referrer are safe
- safe events/goals: allowed if event fields are safe
- PostHog Session Replay: disabled
- Yandex Webvisor: disabled
- click map: disabled
- scroll map: disabled
- form analytics: disabled
- dashboard caveat: required
- launch evidence: required

This state does not block the whole 094 rollout.

## Blocked State

Use this state when the page class cannot safely sanitize URL, title, referrer,
event fields, session/user parameters, or provider-visible values.

Behavior:

- all provider collection: disabled
- rendered provider snippet: absent
- dashboard caveat: required
- implementation task: must fix route/title/DOM/parameter safety before launch

## Forbidden Replay Payloads

Replay must never include:

- raw audio or playback content
- transcript text
- generated summaries/outcomes if they contain meeting content
- meeting title
- participant names
- calendar event text
- meeting links
- email
- phone
- full name
- account/workspace/company name
- raw user/account/workspace/meeting/device IDs
- device name
- local path
- filename if user-provided or content-bearing
- object key
- signed URL
- OAuth/provider token
- API key
- cookie
- passcode/password
- payment/contact fields
- free-text support/private notes

## Provider-Specific Controls

### PostHog

Required before replay:

- opt-in only after telemetry gate accepts
- autocapture/replay disabled for blocked page classes
- masking/blocking selectors for private regions
- no network payload/header/body capture for private product traffic unless a
  later gate approves a metadata-only subset
- replay status diagnostics included in smoke evidence

### Yandex

Required before Webvisor/maps/forms:

- field recording disabled by default for private pages
- `ym-disable-keys` on fields that must never record
- `ym-hide-content` on private DOM containers
- no `ym-record-keys` or `ym-show-content` on private fields/containers unless
  separately approved for neutral UI
- form analytics off for auth/settings/upload/deletion/meeting/result pages
  unless a page-specific proof exists
- IP masking status recorded in provider readiness

## QA Evidence

Every approved replay page class needs:

- fixture route with synthetic safe data
- rendered HTML screenshot or DOM proof showing private regions are hidden
- browser/provider debug proof that replay is enabled only on approved class
- negative proof on at least one replay-unavailable class
- negative proof on one blocked class
- no screenshots/logs with real visitor/account data

## Failure Rule

If replay is uncertain, disable replay/maps/forms for that page class and keep
safe page views/events only when their own sanitization proof passes.
