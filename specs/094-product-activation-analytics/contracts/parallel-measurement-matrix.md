# Contract: Parallel Measurement Matrix

**Feature**: `094-product-activation-analytics`

This contract defines the planned event/page routing. It does not enable any
provider.

## Routing Principles

- PostHog is the primary product source of truth.
- Yandex is the parallel web/ad/Webvisor/offline-conversion surface.
- Every shared event requires a reason, allowed fields, identity rule,
  retention/deletion truth, dashboard owner, and QA evidence.
- Raw identity, meeting content, local paths, secrets, tokens, signed URLs,
  device names, transcript/audio/calendar text, and private free text are
  forbidden everywhere.
- Internal/support/smoke/test activity is counted by default and disclosed.

## Event Matrix

| Event/Page | Surface | PostHog Mode | Yandex Mode | Reason | Allowed Fields | Forbidden Fields | Identity Rule | Retention/Deletion Truth | Dashboard Owner | QA Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `public_landing_viewed` | public web `/` | anonymous event/page context | page view + existing goal/event | Acquisition context | page_path, surface, safe UTM/openstat/referrer category | raw query text, email, phone, names, account IDs, meeting data | anonymous session + optional attribution bridge | provider aggregate caveats; 093 consent rules until 094 expands | growth | rendered page + provider goal smoke |
| `public_landing_section_seen` | public web `/` | anonymous event | existing Yandex JS goal | Public engagement | section_id, page_path, surface | section text, private content | anonymous session | provider aggregate caveats | growth | browser event contract |
| `public_landing_cta_clicked` | public web `/` | anonymous event | existing Yandex JS goal | Public intent | cta_location, target_kind, page_path | visible text, private URL | anonymous session | provider aggregate caveats | growth | browser event contract |
| `public_download_viewed` | public web `/download` | anonymous event/page context | page view + existing goal/event | Download-page context | page_path, surface, safe campaign fields | unsafe UTM, private referrer | anonymous session + bridge candidate | provider aggregate caveats | growth | rendered page + provider goal smoke |
| `public_installer_download_clicked` | public web `/download` | anonymous event + bridge seed | existing Yandex primary public goal | Web download intent, not activation | cta_location, target_kind, bridge state | account identity, installer local path, raw client IDs | anonymous session + `graf_attribution_id` | public intent may survive as aggregate; deletion caveat required | growth | click test + dashboard visibility |
| `public_login_intent_clicked` | public web | anonymous event | existing Yandex JS goal | Public login intent | cta_location, target_kind | email, account ID | anonymous session | provider aggregate caveats | growth | browser event contract |
| `desktop_first_opened` | macOS desktop | identified product event or server-mediated event | none by default | Product adoption count | app_version_bucket, platform=`macos`, install_channel, bridge_present, attribution_reliability | device name, local path, raw user ID, machine ID | stable pseudonymous user if known; counted unlinked if not | PostHog/GRAF bridge deletion caveat | desktop + product analytics | desktop telemetry-gate/event test |
| `desktop_account_connected` | desktop/server auth | identified event | offline conversion default | First reliable campaign-linked product milestone | auth_method_category, account_connection_state, bridge_present, elapsed_bucket | email, OAuth tokens, raw account ID, account name | stable pseudonymous user; bridge token/`yclid`/ClientID only if approved | provider offline conversion caveat | auth/server + growth | auth handoff + Yandex offline conversion dry run |
| `desktop_autorecord_enabled` | desktop/cabinet/calendar policy | identified event | none by default | Activation setup | policy_state, surface, previous_state, source=`user_action`/`workspace_policy` | calendar event title, meeting link, participant, workspace name | stable pseudonymous user | PostHog event retention | calendar policy + desktop | policy event contract |
| `first_recording_completed` | desktop/server | identified event | none by default | First real recording milestone | duration_bucket, capture_mode, completion_state, result_pending_state | raw audio, transcript, local path, file name, meeting title | stable pseudonymous user | PostHog event retention; no audio in analytics | capture/server | recording-complete contract |
| `first_result_viewed` | cabinet/embedded webview | identified event | none by default | User sees result | result_state, surface, elapsed_bucket, useful_output_present boolean | transcript text, summary text, participants, meeting title | stable pseudonymous user | PostHog event retention | cabinet | rendered result-view contract |
| `first_value_session_completed` | cabinet/product analytics | identified event | offline conversion default | First value and ad optimization milestone | milestone booleans, elapsed_bucket, useful_result_type enum | content, names, raw IDs, text snippets | stable pseudonymous user + approved bridge identifiers for Yandex | PostHog + Yandex offline conversion caveat | product analytics + growth | first-value contract + offline conversion dry run |

## Default Yandex Offline Conversion Subset

Allowed by default:

- `desktop_account_connected`
- `first_value_session_completed`

Blocked by default:

- `desktop_first_opened`
- `desktop_autorecord_enabled`
- `first_recording_completed`
- `first_result_viewed`
- any meeting/content-bearing detail event

Expansion requires a later explicit legal/product approval.

## Required Review Columns Before Implementation

Every row in implementation tasks must include:

- owner
- surface
- PostHog destination
- Yandex destination
- Yandex mode
- reason
- allowed fields
- forbidden fields
- identity rule
- retention/deletion truth
- dashboard owner
- QA evidence
- legal status
- rollout status
