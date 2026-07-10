# Contract: Public Analytics

**Feature**: 093-public-landing-analytics

This contract defines the observable Phase 1 public analytics behavior.

## Scope

Included public routes:

- `/`
- `/download`

Excluded routes:

- `/login`
- `/sign-up`
- `/cabinet`
- `/cabinet/*`
- `/api/*`
- `/admin`
- `/admin/*`
- desktop embedded cabinet routes
- meeting, upload, playback, deletion, support, and diagnostic surfaces

## Runtime Configuration Contract

Analytics is active only when all required conditions pass:

1. Public analytics feature flag is enabled.
2. Environment is production-like or explicit render-only validation mode.
3. A Yandex Metrica counter ID is configured at runtime.
4. Current route is included in public scope.
5. Visitor consent state permits the provider behavior.

When inactive, rendered HTML must not contain live third-party analytics script
URLs, inline live provider initialization with real IDs, provider request
pixels, or replay enablement.

## Consent Contract

States:

| State | Meaning | Provider Behavior |
| --- | --- | --- |
| `unknown` | No current choice for the active consent copy | No provider tags; show consent control |
| `accepted_all` | Visitor selects accept all optional categories | Load approved Yandex provider behavior on public pages |
| `necessary_only` | Visitor selects necessary-only behavior | Do not load providers or replay |
| `customized` | Visitor selects specific optional categories | Load only granted optional Yandex behavior |
| `revoked` | Visitor changed a prior accepted choice | Stop future non-essential events; do not load providers on later pages |

Rules:

- Consent copy is Russian.
- Accept all, necessary-only, and customize actions are reachable without
  blocking page use.
- If user-facing copy says "reject optional analytics", that decision maps to
  the canonical `necessary_only` state.
- Optional categories are `analytics`, `advertising_attribution`, and
  `behavior_replay`; `necessary` is always on.
- A public-page control lets the visitor change the choice later.
- Session replay is never active unless consent accepts `behavior_replay`
  through accept-all or customized choice.
- No Yandex Metrica, Webvisor, advertising attribution, or other non-essential
  provider tags load before the relevant optional category is granted.
- GA4, Google Analytics, Google Ads tags, and Google Tag Manager are not part
  of Phase 1.

## Event Contract

| Event | Trigger | Safe Fields |
| --- | --- | --- |
| `public_landing_viewed` | `/` rendered and provider enabled by consent | page_path, surface, campaign fields |
| `public_landing_section_seen` | Major section enters view once per page load | section_id, page_path, surface |
| `public_landing_cta_clicked` | Public CTA clicked | cta_location, target_kind, page_path |
| `public_download_viewed` | `/download` rendered and provider enabled by consent | page_path, surface, campaign fields |
| `public_installer_download_clicked` | Installer package link clicked | cta_location, target_kind |
| `public_login_intent_clicked` | Public login link clicked | cta_location, target_kind |

Required stable labels:

| Surface | Label Class | Allowed Values |
| --- | --- | --- |
| Landing sections | `section_id` | `hero`, `platforms`, `outcomes`, `trust`, `final_cta` |
| CTA locations | `cta_location` | `header_download`, `hero_download`, `final_download`, `hero_login`, `final_login`, `download_page_installer`, `download_page_login` |
| Target kinds | `target_kind` | `download_page`, `installer_package`, `login`, `section` |

Provider mapping:

- Yandex Metrica: custom JavaScript goals map to the event names above.
- `public_installer_download_clicked` is the primary web conversion candidate
  for Yandex Direct optimization.

Deduplication:

- Each section visibility event fires at most once per page load.
- Each click emits at most one event per provider for the user action.
- Repeated installer clicks may be counted as repeated intent, but reports must
  offer session-level deduplication where providers support it.

## UTM Contract

Accepted parameters:

- `utm_source`
- `utm_medium`
- `utm_campaign`
- `utm_id`
- `utm_content`
- `utm_term`

Normalization:

- Trim whitespace.
- Lowercase source and medium.
- Keep campaign/content/term stable and readable.
- Drop unsafe values instead of sanitizing them into misleading labels.

Initial recommended values:

| Parameter | Examples |
| --- | --- |
| `utm_source` | `yandex_direct`, `vk_ads`, `telegram`, `email`, `partner` |
| `utm_medium` | `cpc`, `paid_search`, `paid_social`, `organic_social`, `referral`, `email` |
| `utm_campaign` | `2026q3_b2c_launch_ru` |
| `utm_id` | external stable campaign ID, if safe |
| `utm_content` | safe creative or placement key |
| `utm_term` | safe keyword key; no private search text copied manually |

Forbidden UTM/event values:

- email addresses
- phone numbers
- person names
- company/customer names
- account identifiers
- meeting titles
- transcript text
- raw audio or file names
- local paths
- object keys
- tokens
- signed URLs
- passcodes
- private calendar/event text
- private meeting content

## Replay Contract

- Replay/behavior recording may load only on `/` and `/download`.
- Replay requires `behavior_replay` consent through `accepted_all` or
  `customized`.
- Replay must be absent from excluded routes.
- The public landing currently contains no input fields; if fields are added
  later, replay masking and no-capture rules must be reviewed before release.

## Failure Contract

- If provider scripts fail or are blocked, the public UX still works.
- Failures do not create visible user errors.
- Validation records measurement caveats without claiming full traffic counts
  when necessary-only consent, revoked consent, or blocking prevents provider
  measurement.
