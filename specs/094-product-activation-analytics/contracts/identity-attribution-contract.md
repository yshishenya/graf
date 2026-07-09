# Contract: Identity And Attribution

**Feature**: `094-product-activation-analytics`

## Identity Decision

Primary product analytics identity is a stable server-issued pseudonymous user
identity. It is safe to use as a PostHog `distinct_id` only after the product
telemetry gate is accepted and the identity contract is approved.

## Allowed Identifiers

- `stable_pseudonymous_user_id`
- `graf_attribution_id`
- expiring bridge token hash
- PostHog anonymous ID for public/anonymous acquisition context
- Yandex ClientID only when collected during an approved Yandex-tagged session
  and stored/used under the bridge rules
- `yclid` only when collected from approved campaign URLs and stored/used under
  the bridge rules
- safe workspace/account pseudonyms as metadata dimensions

## Forbidden Identifiers

- email
- phone
- full name
- company/organization/workspace/account name
- raw user/account/workspace/meeting IDs
- device name or machine name
- local username or local path
- OAuth/provider tokens
- cookies in committed evidence
- object keys
- signed URLs
- meeting links
- calendar IDs or text
- transcript/audio/summary content

## Attribution Reliability By Milestone

| Milestone | Counted? | Campaign-linked Reliability | Rule |
| --- | --- | --- | --- |
| `public_installer_download_clicked` | yes | public web only | Web intent, not activation |
| `desktop_first_opened` | yes | weak unless bridge/auth handoff exists | Count adoption even without campaign link |
| `desktop_account_connected` | yes | first reliable default | Bridge can link public source to authenticated product |
| `desktop_autorecord_enabled` | yes | reliable after account connection | Product setup milestone |
| `first_recording_completed` | yes | reliable after account connection | Product usage milestone |
| `first_result_viewed` | yes | reliable after account connection | Result engagement milestone |
| `first_value_session_completed` | yes | reliable after account connection | First value and default Yandex offline conversion |

## Bridge State Machine

```text
unlinked
-> public_session_seen
-> download_intent_recorded
-> auth_handoff_started
-> account_connected
-> activation_linked
```

Terminal/exception states:

```text
expired
withdrawn
deleted_in_graf_control
provider_delete_requested
not_linkable
```

## Deletion And Withdrawal

- Withdrawal stops future product analytics because normal product use is no
  longer available except account/legal/export/deletion flows.
- GRAF can delete or block its bridge records.
- Provider-held aggregates, already-imported Yandex offline conversions, and
  exported reports must be described as separate deletion domains.

## Direct Desktop Egress

Direct desktop delivery to PostHog or Yandex remains disabled until all of these
are true:

- legal/security/QA approval exists
- one-time telemetry acceptance explicitly discloses direct desktop egress
- payload schema includes only approved safe fields
- retry/buffering behavior is bounded
- provider failure is a measurement gap only
- no raw identity/content/local/device values can leave the desktop app
