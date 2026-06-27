# Forbidden Content Notes: Calendar Context Ingestion

Feature 060 evidence, fixtures, logs, diagnostics, screenshots, and API examples
must never contain real sensitive calendar or credential material.

## Forbidden Exact Strings And Field Patterns

- `refresh_token`
- `app_password`
- `oauth_refresh_token`
- `ews_password`
- `service_account_key`
- `credential_input`
- `sealed_payload`
- `Authorization:`
- `Bearer `
- `passcode`
- `signed_url`
- `X-Amz-Signature`
- `raw_event_payload`
- `attendee_email_dump`
- `private_event_text`
- `agenda_text`
- `transcript text`
- `live_credential_path`

## Safe Evidence Rules

- Use provider family, count, state, hash, and boolean evidence instead of raw
  calendar payloads.
- Use `example.test` synthetic identities only.
- Use redacted URL previews such as `meet.example.test/...` and URL hashes instead
  of full meeting links.
- Use limitation states when a provider does not expose data.
