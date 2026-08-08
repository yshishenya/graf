# Contract: Page Provider Inventory

**Feature**: `096-product-analytics-provider-rollout`

This inventory is the planning baseline. Implementation tasks must keep it current as pages are added or changed.

| Page Class | Examples | PostHog Autocapture | PostHog Replay | Yandex State | Notes |
| --- | --- | --- | --- | --- | --- |
| `public_landing` | `/` | enabled | separate proof required | approved baseline from 093 | Existing public events stay live. |
| `public_download` | `/download` | enabled | separate proof required | approved baseline from 093 | Installer download goal stays live. |
| `legal` | `/privacy`, `/cookies`, `/terms`, `/analytics-consent` | enabled | disabled until proof | blocked until inventory proof | No private values expected, but Yandex needs explicit approval. |
| `login_signup` | `/login`, signup routes | enabled | disabled until proof | blocked until inventory proof | Credential fields must be suppressed. |
| `auth_callback` | OAuth callback routes | enabled after global credential suppression | unavailable | blocked | OAuth codes/tokens/cookies must be suppressed. |
| `cabinet_home` | meeting list/cabinet shell | enabled | disabled until proof | blocked or replay_unavailable | Product-visible account state may enter PostHog only. |
| `onboarding` | telemetry gate, setup states | enabled | disabled until proof | blocked until inventory proof | Good candidate for PostHog product learning. |
| `settings` | user/workspace settings | enabled | disabled until proof | blocked or replay_unavailable | Suppress credentials and private account values. |
| `recording_list` | recordings/meetings list | enabled | disabled until proof | blocked or replay_unavailable | Product-visible content may enter PostHog; not Yandex. |
| `meeting_result_detail` | meeting detail/result/playback/outcomes | enabled | unavailable until strict replay proof | blocked or replay_unavailable | PostHog first-party autocapture allowed; Yandex/replay blocked until proof. |
| `upload` | upload modal/progress | enabled | disabled until proof | blocked or replay_unavailable | Suppress local paths, filenames, object keys. |
| `playback` | review playback controls | enabled | unavailable until proof | blocked or replay_unavailable | No raw audio or signed URLs in evidence. |
| `deletion` | deletion reports/tasks | enabled | disabled until proof | blocked | Deletion truth is sensitive; Yandex blocked by default. |
| `admin` | admin dashboard/routes | enabled after global credential suppression | unavailable | blocked | PostHog first-party product analytics only. |
| `embedded_desktop_webview` | desktop embedded cabinet | enabled | unavailable until proof | blocked or replay_unavailable | Native capture controls remain outside browser analytics. |
| `error_pages` | 4xx/5xx pages | enabled | disabled until proof | blocked until inventory proof | Ensure no stack traces/secrets. |
| `future_browser_page` | any future page | enabled by default after credential suppression | disabled until proof | blocked until added | New page must update this inventory. |

## Credential Suppression Rules

Every browser-rendered page class must suppress or exclude:

- password/passcode fields;
- OAuth codes and callback parameters;
- access/refresh/id tokens;
- API keys;
- signed URLs;
- cookies;
- provider/client secrets;
- private keys;
- local paths;
- raw payload dumps.

## Provider Interpretation

- PostHog autocapture is first-party and broad.
- PostHog replay is separate and disabled unless approved.
- Yandex collection is external/ad-facing and blocked unless inventory state approves it.
- Webvisor/maps/forms are never implied by PostHog autocapture.
