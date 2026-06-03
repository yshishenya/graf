# ADR 001: Local Trust Shell And Server Dashboard UI Authority

**Status**: Accepted

**Date**: 2026-06-04

## Context

`2brain Rec` is a self-hosted meeting capture product with a macOS virtual audio
driver/layer, local recording, assisted meeting detection, and future
multiplatform desktop clients. The product must preserve visible capture
indicator, one-action stop, explicit policy gates, local audio route truth,
owner-controlled storage, and no silent recording.

The product also needs web-based post-meeting and admin experiences: transcript,
notes, search, sharing, retention, deletion, audit, device fleet, and workspace
policy. Future Windows support should reuse product contracts where possible
without forcing capture-critical UX into a lowest-common-denominator runtime.

Authoritative platform and security guidance shapes this decision:

- Apple and Windows expose local OS privacy/permission surfaces for microphone,
  screen/system audio, and notification-area status. Active recording truth must
  align with local platform behavior.
- Electron and WebView-style desktop apps require strict separation between
  remote content and privileged native capabilities.
- Tauri-style desktop shells still require a privileged core process and strict
  capability boundaries.
- OWASP mobile/application security guidance emphasizes minimizing sensitive
  access and protecting local data and platform interactions.
- NIST privacy guidance frames privacy as a system risk-management obligation,
  not merely a server-side notice problem.

Relevant sources reviewed:

- Apple App Sandbox and privacy permission guidance:
  <https://developer.apple.com/documentation/security/app_sandbox>
- Apple Screen & System Audio Recording permission guidance:
  <https://support.apple.com/guide/mac-help/allow-apps-to-use-screen-and-audio-recording-mchl592e5686/mac>
- Microsoft microphone privacy and Windows notification area guidance:
  <https://support.microsoft.com/en-us/windows/windows-camera-microphone-and-privacy-a83257bc-e990-d54a-d212-b5e41beba857>
  <https://learn.microsoft.com/en-us/windows/win32/shell/notification-area>
- Electron security guidance:
  <https://www.electronjs.org/docs/latest/tutorial/security>
- Tauri process model and capabilities:
  <https://tauri.app/concept/process-model/>
  <https://v2.tauri.app/security/capabilities/>
- OWASP MASVS privacy controls:
  <https://mas.owasp.org/MASVS/controls/MASVS-PRIVACY-1/>
- NIST Privacy Framework:
  <https://www.nist.gov/privacy-framework>
- Server-driven UI references for non-critical surfaces:
  <https://shopify.engineering/blogs/engineering/server-driven-ui-in-shop-app>
  <https://www.doist.dev/server-driven-ui-from-a-mobile-perspective/>

## Decision

Use a hybrid UI authority model:

1. **Local/native trust shell for capture-critical desktop surfaces.**
   The desktop app is authoritative for active capture state, visible local
   indicator, one-action stop, recording controls, assisted detection prompts,
   route readiness, driver recovery, local buffer safety, local artifact truth,
   offline pending recordings, diagnostics export, and local degraded states.

2. **Server web dashboard for post-meeting and admin surfaces.**
   The self-hosted backend/web dashboard is authoritative for uploaded meeting
   records, transcripts, notes, search, sharing, admin policy editing,
   retention/deletion dashboard, audit views, device fleet, and workspace
   management.

3. **Server-synced policy/config/content with local enforcement.**
   The server may provide workspace policy, feature flags, approved targets,
   consent/legal profile, naming policy, localization strings, help content, and
   non-critical form constraints. The desktop app must validate, cache where
   safe, and enforce these locally.

4. **No server-rendered ownership of capture-critical truth.**
   Server-rendered remote UI, remote WebView UI, or server-driven schema must
   not own or be required for active capture truth, visible indicator
   availability, Stop availability, route health truth, local storage safety,
   permission recovery, driver recovery, or capture authorization gates.

5. **Cross-platform reuse through contracts, not remote control of capture UI.**
   Future platforms reuse shared state contracts, API schemas, policy schemas,
   design tokens, localization keys, and dashboard surfaces. Each platform has
   its own native trust shell for capture/driver/permission behavior.

## Considered Options

### Option A: Fully Local Native UI

All product UI is implemented in each desktop app.

**Pros**:

- Strongest local trust and offline behavior.
- Best fit for OS permissions, tray/menu, widgets, driver lifecycle, and local
  recovery.
- Avoids remote UI weakening capture safety.

**Cons**:

- Duplicates meetings, transcript, notes, admin, and fleet UI across platforms.
- Slower product iteration for non-critical copy and policy surfaces.
- Larger desktop app scope.

**Result**: Accepted only for local trust-shell surfaces.

### Option B: Fully Server-Rendered Desktop UI

Desktop app is mostly a WebView or server-rendered shell.

**Pros**:

- Fast iteration.
- One UI for multiple platforms.
- Good fit for dashboard/admin surfaces.

**Cons**:

- Unsafe for active recording because network/server availability could affect
  Stop and indicator.
- Larger remote-content/native-bridge attack surface.
- Poor fit for OS permissions, driver lifecycle, local audio route truth, and
  offline behavior.

**Result**: Rejected for capture-critical surfaces.

### Option C: Server-Driven Native UI Schema

Server sends versioned schema rendered by local native components.

**Pros**:

- More flexible than hard-coded local UI.
- Safer than remote HTML/JavaScript when constrained to native components.
- Useful for non-critical settings, help, onboarding copy, and policy forms.

**Cons**:

- Requires schema versioning, cached fallbacks, and compatibility discipline.
- Old clients may not support new UI components.
- Must be heavily sandboxed to avoid capture-critical control injection.

**Result**: Allowed only for non-critical surfaces with local validation.

### Option D: Hybrid Local Trust Shell And Server Dashboard

Desktop trust shell is local/native; post-meeting/admin surfaces are server web.

**Pros**:

- Preserves local recording trust and offline Stop.
- Avoids duplicating dashboard/admin UI across desktop platforms.
- Supports future Windows through shared contracts and native trust shell.
- Keeps self-hosted server as source of truth for uploaded records and policy.

**Cons**:

- Requires disciplined shared contracts.
- Requires design-system parity between native desktop and web dashboard.
- Requires explicit server-stale/offline states.

**Result**: Accepted.

## Consequences

- macOS MVP remains Swift/SwiftUI/AppKit where appropriate for desktop trust
  surfaces and Core Audio integration.
- Windows and later platforms must define a native trust shell before capture
  implementation starts.
- The web dashboard becomes the reusable cross-platform surface for
  post-meeting and admin workflows.
- Shared contracts must define at least: `RecordingState`, `RouteState`,
  `PolicySnapshot`, `CaptureIndicatorState`, `MeetingCandidate`, `UploadState`,
  `DeletionState`, `DeviceHealth`, `FeatureFlags`, and `NamingPolicy`.
- Server outage must not remove Stop or hide active recording state.
- Stale or missing policy must be shown truthfully. New assisted auto-start must
  fail closed unless a valid cached policy explicitly authorizes it.
- Server-driven UI/schema work must include schema versioning, allowlisted
  native components, cached fallback, unknown-action rejection, and tests proving
  remote content cannot hide capture or bypass gates.

## Compliance Gates

- Active capture state and one-action stop remain visible and usable during
  server outage.
- Remote UI/schema attempts to hide active capture, remove Stop, misrepresent
  route health, or bypass local gates are rejected.
- Diagnostic bundles record policy freshness and UI authority state without raw
  audio, transcript text, meeting content, credentials, tokens, signed URLs, or
  live credential paths.
- Any future platform plan separates native trust-shell responsibilities from
  shared web/dashboard responsibilities before implementation.
