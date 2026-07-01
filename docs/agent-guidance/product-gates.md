# Product Gates

Use this file with `.specify/memory/constitution.md`,
`docs/prd-voice-layer-final.md`, and `docs/current-product-status.md`.

## Capture And Platform

- The MVP recording path is macOS system-audio-first.
- Virtual-driver routing is not required for MVP recording acceptance and must
  stay parked as future advanced-routing work until a separate spec, safety
  gate, and rollback plan exist.
- Capture-critical macOS implementation is native by default:
  Swift/Cocoa/ScreenCaptureKit/AVFoundation/Core Audio where appropriate.
- Windows and other platforms require separate future native stacks and
  architecture decisions.
- Manual `Record`/`Stop` remains available whenever workspace policy permits
  recording.
- Active capture must always have a persistent local visible indicator and a
  one-action stop path.
- No user or admin setting may make active capture invisible.

## Audio, Artifacts, And Diagnostics

- Features that touch capture, recording integrity, buffering, permissions,
  system audio, microphone capture, or future driver UX must define measurable
  latency, dropout, track alignment, authorization, recovery, degraded-state,
  and QA requirements.
- Diagnostics and evidence are metadata-only unless an approved spec explicitly
  says otherwise.
- Never include raw audio, transcript text, credentials, tokens, signed URLs,
  passwords, live local paths, or private meeting content in committed evidence.

## Server, Storage, And AI Boundaries

- GRAF-owned meeting data stays in configured owner-controlled
  infrastructure by default.
- Desktop clients never send audio directly to MediaScribe and never store
  MediaScribe credentials.
- MediaScribe credentials are server-side only.
- Langfuse traces are metadata-only by default.
- Content-bearing traces require explicit admin enablement, short retention,
  RBAC, audit logging, and deletion participation.
- External dependency features must define egress, secret, timeout, failure,
  retention, and deletion behavior.

## Deletion Truth

- Product copy must not promise universal erasure outside `GRAF` control.
- Preferred deletion wording: "Delete this meeting everywhere GRAF
  controls."
- Deletion reports must distinguish server purge, local desktop purge, backup
  expiry, Temporal/workflow payload limits, MediaScribe state, Langfuse state,
  diagnostics, post-egress limits, and unreachable clients.
- If a dependency cannot confirm deletion, the UI and admin report must say so.

## UX And Brand Distance

- UI must use an original `GRAF` design system.
- Clean-room and brand-distance review are required before production rollout.
- High-risk UX includes tray/widget, onboarding, deletion, admin policy,
  accessibility, localization, and unavailable/degraded states.

## Deployment

- MVP server target is `2brain.dev` with public URL
  `https://rec.2brain.pro`.
- MVP infrastructure runs in Docker containers.
- Dedicated Postgres and MinIO are required for `2brain_rec`.
- Temporal is the selected durable workflow engine unless the constitution is
  amended.
- Deployment features require Docker secret handling, health checks, backups,
  restore, rollback, log redaction, and disk-full behavior.
