# Contract: Diagnostics And Redaction

## Purpose

Diagnostics must help debug install, route, permission, capture, and uninstall
failures without becoming hidden content or secret export.

## Default Diagnostic Bundle

Allowed fields:

- app version, driver/audio component version, installer package version
- macOS version, CPU architecture, entitlement/notarization status summaries
- virtual device availability and route status
- physical device class, not unique hardware serials unless explicitly approved
- permission status and recovery action IDs
- route verification results and failure codes
- passthrough health, dropout counts, drift summaries, and timing aggregates
- local buffer counts, sizes, threshold states, and retention deadlines
- upload readiness/failure category without upload tokens or signed URLs
- redaction engine version and diagnostic schema version

Forbidden by default:

- raw audio frames or audio snippets
- transcript text or meeting notes
- MediaScribe credentials or request payloads
- auth credentials, API keys, session tokens, refresh tokens, device tokens
- signed URLs or temporary upload/download URLs
- full local filesystem paths containing usernames when a stable redacted alias
  can be used
- contact names, meeting titles, calendar content, chat content

## Redaction States

- `redacted`: diagnostic bundle contains only allowed default fields.
- `blocked_sensitive_content`: diagnostic generation detected forbidden content
  and omitted it.
- `admin_content_enabled`: reserved for a future explicit admin policy; not
  available in this MVP feature.

## Bundle Generation Rules

- Every diagnostic bundle must declare `schemaVersion`, `createdAt`,
  `redactionState`, and `contentHash`.
- If forbidden content is detected, bundle creation should continue with the
  sensitive field omitted and `blocked_sensitive_content` recorded.
- The user-visible UI must show whether a bundle was generated, failed, or was
  redacted.
- Diagnostics for uninstall must remain available after app-managed virtual
  devices are removed where OS permits.

## Review Gate

Before production-ready release candidate, create at least one diagnostic bundle
from each failure family:

- install failure
- route verification failure
- permission failure
- physical device disconnect/profile change
- network/server outage during capture
- local buffer warning/critical state
- uninstall or rollback partial failure

Each sample must pass the forbidden-content scan.
