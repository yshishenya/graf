# Feature Specification: macOS Dev Channel and Native Home

**Feature Branch**: `codex/160-macos-dev-channel-shell`

**Created**: 2026-08-17

**Status**: Validated locally; pending implementation commit/PR

**Owner boundary**: functions 9 and 14 from the user goal.
Feature 095 remains the owner of historical permission continuity; Features
105/130 own public Developer ID and Sparkle publication; Features 152/153 own
local development and release process.

## Clarifications

- Production `GRAF.app` keeps its existing bundle identifier,
  Developer ID team/designated requirement, entitlements, Hardened Runtime,
  app name, data paths, and Sparkle trust contract. This slice does not change
  public production signing or feed metadata.
- The new installed channel is opt-in and separate from the disposable
  `GRAF Local` build. It is named `GRAF Dev.app`, uses a stable distinct
  bundle identifier, loopback-only configuration, a stable local signing
  identity, isolated application-support namespace, and no production Sparkle
  feed.
- The native Home control uses the existing `WKWebView` back-forward list and
  `DesktopCabinetWorkspace.defaultRoute()`/meetings URL. No parallel history
  system is introduced.

## User Scenarios & Testing

### User Story 1 - Install a distinct Dev app (Priority: P0)

As a developer, I can build, install, and update `/Applications/GRAF Dev.app`
without replacing production `GRAF.app` or silently connecting to
production.

**Independent Test**: Run the explicit Dev build/install command twice, inspect
bundle name/identifier/signature/entitlements, confirm loopback-only config and
absence of Sparkle feed keys, and verify both app bundles can coexist.

### User Story 2 - Keep Dev permissions and data isolated (Priority: P0)

As a developer, I can grant microphone and Screen & System Audio access once
to the Dev identity and retain it across same-identity rebuilds/restarts,
while understanding that production and Dev grants are separate.

**Independent Test**: Use signing and bundle metadata fixtures plus local
install/relaunch/update smoke; verify stable identity, isolated preferences,
recordings, upload queue, and meeting-detection state. No TCC database edits,
reset commands, profiles, or hidden prompt bypasses are allowed.

### User Story 3 - Navigate safely with native controls (Priority: P1)

As a user in the embedded app, I can go Back, Forward, Reload, or Home with
truthful enabled states and accessible labels.

**Independent Test**: Exercise meeting list, detail, settings, login redirect,
expired session, auth continuation, external URL, and blocked URL scenarios.
Back/Forward use safe history only; Reload reloads the current safe document;
Home opens the canonical meeting list.

## Functional Requirements

- **FR-001**: The public production app MUST retain its current bundle ID,
  Developer ID Team/designated requirement, entitlements, Hardened Runtime,
  app name, Sparkle feed URL, and trust generation.
- **FR-002**: The Dev channel MUST install as `/Applications/GRAF Dev.app`
  with a stable bundle identifier distinct from production and the disposable
  local app; repeated builds MUST use the same designated signing identity or
  fail closed.
- **FR-003**: Dev MUST accept only an explicitly supplied loopback HTTP origin
  and MUST reject production, non-loopback, and implicit fallback origins.
- **FR-004**: Dev MUST use a distinct application-support namespace for local
  recordings, upload queue, meeting-detection settings/cache/telemetry, and
  bundle-scoped preferences; production data MUST never be reused or
  overwritten.
- **FR-005**: Dev MUST omit production Sparkle feed/trust keys and MUST not
  start an updater pointed at the production feed.
- **FR-006**: The Dev app MUST declare the same microphone and system-audio
  usage explanations needed by the capture flow; first install may request
  each permission once, and same-identity updates MUST not deliberately reset
  grants.
- **FR-007**: The build/install command MUST verify the stable signing identity,
  bundle ID, loopback-only launcher, no-feed metadata, and final code signature;
  failure MUST stop before replacing any installed app.
- **FR-008**: Native Back MUST be enabled only for a safe usable previous
  history entry or existing canonical fallback; Forward only for a safe next
  entry; Reload only for a safe first-party GET document and never as a
  mutation replay.
- **FR-009**: Native Home MUST be keyboard-operable, accessible, tooltip-labeled,
  and route to the existing canonical meetings URL without permitting an
  external origin or attaching desktop headers to it.
- **FR-010**: Browser-owned external auth/payment/admin links MUST retain their
  existing route policy and MUST not inherit native desktop headers.
- **FR-011**: The slice MUST not modify TCC databases, call `tccutil reset`,
  install hidden permission profiles, restore removed audio routing, add a new
  history store, or alter public production release trust.

## Edge Cases

- Missing signing identity, ad-hoc identity, changed designated requirement,
  wrong bundle ID, invalid entitlements, or non-loopback Dev URL fails closed.
- A permission is denied, restricted, or revoked: the app reports the existing
  truthful state and does not attempt a workaround.
- Production and Dev run simultaneously; their cookies, preferences, app
  support files, updater configuration, and visible names remain distinct.
- Reload occurs on login, settings, meeting detail, an expired session, or a
  safe redirect; a POST/mutation must not be replayed.
- Home is pressed from the list, detail, settings, auth continuation, or a
  blocked route; only the allowlisted meeting list is used.

## Success Criteria

- **SC-001**: Dev build/install metadata checks pass 100% for name,
  identifier, stable signing identity, loopback-only origin, separate storage,
  no production feed, and coexistence with production.
- **SC-002**: Synthetic permission continuity checks prove same-identity
  rebuild/restart/update preserves channel identity and never runs a TCC reset
  or workaround.
- **SC-003**: Native navigation checks pass for safe Back/Forward/Reload/Home,
  auth/session recovery, settings, meeting detail, external auth continuation,
  and blocked external URLs.
- **SC-004**: Home always resolves to `DesktopCabinetWorkspace.defaultRoute()`
  and no native control permits arbitrary external navigation.

## Assumptions

- Apple TCC grants are identity-scoped and cannot be promised across a changed
  bundle ID, team, designated requirement, or user revocation.
- The existing public installer and Sparkle scripts remain canonical for
  production and are not repurposed for Dev.
- `GRAF Local Code Signing` is the local stable identity when present; the
  command fails closed if it is absent or replaced.

## Out of Scope

- Public Developer ID notarization, stapling, Gatekeeper, Sparkle publication,
  appcast mutation, or production deployment.
- Resetting or editing TCC, hidden permission profiles, legacy audio-driver
  restoration, or production bundle migration.
- Rewriting WKWebView history, auth/session, recording capture, or server routes.
