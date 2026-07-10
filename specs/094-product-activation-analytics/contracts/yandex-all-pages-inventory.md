# Contract: Yandex All-Pages Inventory

**Feature**: `094-product-activation-analytics`

This inventory is the required starting point for future implementation. It does
not enable Yandex beyond the approved `093` `/` and `/download` scope.

## Global Rules

- Yandex can be present only on approved browser-rendered page classes.
- URL, title, referrer, event fields, session parameters, user parameters, and
  provider-visible values must be safe before any provider collection is allowed.
- If page views/events are safe but replay proof is missing, use
  `replay_unavailable`: page views/events may proceed and Webvisor/click/scroll/
  form analytics stay disabled.
- If URL/title/referrer/events/provider parameters are unsafe, collection is
  blocked for that page class.
- Do not send identifying information to Yandex Metrica unless a provider
  feature and legal gate explicitly allow it.

## Page-Class Inventory

| Page Class | Examples | Tag Allowed | Page View | Goals/Events | Session/User Params | Webvisor | Click Map | Scroll Map | Form Analytics | Launch Status | Blocker/Caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| public landing | `/` | already approved in 093 | yes | yes | safe campaign params | yes with public consent | yes with public consent | yes with public consent | no forms today | live for 093 public scope | 094 must preserve existing consent |
| public download | `/download` | already approved in 093 | yes | yes | safe campaign params | yes with public consent | yes with public consent | yes with public consent | no forms today | live for 093 public scope | download intent is not activation |
| legal pages | `/terms`, `/privacy`, `/cookies`, `/analytics-consent` | planned | yes after legal review | safe navigation events only | page category only | likely allowed after review | allowed after review | allowed after review | off unless forms are reviewed | blocked pending 094 approval | no personal data in URL/title |
| login/signup | `/login`, `/sign-up` | planned | yes after sanitization | safe auth-step events only | auth surface category | replay unavailable by default | off by default | off by default | off | blocked pending review | no email/phone/name capture |
| auth callback | `/api/v1/auth/callback/*` or rendered callback pages | maybe no tag | no by default | no by default | no | no | no | no | no | blocked by default | tokens/state/errors must not leak |
| cabinet home | `/cabinet` | planned | yes after sanitization | safe page category events | safe user/account pseudonyms only if approved | replay unavailable until DOM proof | off until proof | off until proof | off until proof | blocked pending inventory | workspace/account names hidden |
| onboarding | cabinet/desktop onboarding web | planned | yes after sanitization | safe step events | safe step state | replay unavailable until DOM proof | off until proof | off until proof | off until proof | blocked pending proof | one-time telemetry gate copy must be approved |
| settings | cabinet settings | planned | yes after sanitization | safe settings category events | safe category only | replay unavailable by default | off | off | off | blocked pending proof | may contain account/workspace/private fields |
| recording list | cabinet meeting list | planned | yes after sanitization | safe list-view events | safe result availability buckets | replay unavailable until list DOM proof | off until proof | off until proof | off | blocked pending proof | meeting titles/participants hidden |
| meeting/result detail | cabinet detail/playback/result pages | planned | yes only after strict sanitization | safe result-view milestones | safe result state only | replay unavailable by default | off by default | off by default | off | blocked pending proof | transcript/summary/audio/participants never captured |
| upload | manual upload/product upload pages | planned | yes only after review | safe upload-step events | safe state buckets | replay unavailable by default | off | off | off | blocked pending proof | filenames/object keys/local paths forbidden |
| playback | audio playback pages | planned | yes only after review | safe playback availability events | safe state only | replay unavailable by default | off | off | off | blocked pending proof | no audio, transcript, waveform/private text |
| deletion | deletion/report pages | planned | yes only after review | safe lifecycle status events | safe status only | replay unavailable by default | off | off | off | blocked pending proof | deletion copy and dependency states may be sensitive |
| admin | `/admin/*` | no by default | no | no | no | no | no | no | no | blocked by default | admin/user/file data too sensitive for initial 094 |
| embedded desktop webview | desktop cabinet/webview routes | planned | yes after desktop/webview proof | safe page/product events | safe surface state | replay unavailable until proof | off until proof | off until proof | off | blocked pending proof | embedded route/session bridge risk |
| error pages | 4xx/5xx rendered pages | planned | maybe safe page view | safe error category only | status bucket only | no by default | off | off | off | blocked pending review | stack traces/request IDs/private URLs forbidden |

## Required Evidence Per Page Class

- sanitized URL examples
- sanitized page title examples
- referrer handling rule
- rendered HTML provider presence/absence proof
- proof that forbidden DOM text is masked or absent
- proof that replay/maps/forms are disabled where masking proof is missing
- dashboard caveat for `replay_unavailable`
- legal review status
- production smoke status

## Launch States

- `not_reviewed`: no provider collection.
- `safe_events_only`: page views/events allowed, replay/maps/forms disabled.
- `replay_unavailable`: synonym used in dashboards for user-facing caveats.
- `replay_allowed`: page views/events/replay/maps/forms allowed after proof.
- `blocked`: no provider collection.
