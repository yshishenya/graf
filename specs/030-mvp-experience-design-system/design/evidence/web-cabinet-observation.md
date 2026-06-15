# Web Cabinet Observation

## Observed Facts

- Quick network probe to `https://rec.2brain.dev` did not return useful content in this execution pass.
- Repository server code exists under `apps/server`.
- Existing specs define server ingest, auth/session, email linking, upload, and MediaScribe processing foundations.
- The server data model already has meeting status, processing status,
  visibility, share policy state, and download policy state fields.
- Current backend status enums cover draft, uploading, ingested pending
  processing, degraded, failed, aborted, expired, pending processing, and
  server-mediated upload semantics.
- The web cabinet is not currently a complete implemented UI in the repository.
- Current repository scan found no separate frontend/web app. The implemented
  surfaces are `apps/server` and `apps/macos`.
- The current worktree contains `014-desktop-upload-queue`,
  `028-provider-auth-session`, `029-email-auth-account-linking`, and `030`.
  `015-mediascribe-processing-pipeline` exists in a separate local worktree and
  remote branch, so `030` treats processing states as a parallel dependency.

## Design Implications

- The web cabinet design is a target launch surface, not a screenshot of an existing production UI.
- The repo Spec Kit artifacts remain the source of truth for web cabinet IA and route/status semantics.
- Browser-only routes may exist in the full cabinet even when hidden or handed off from desktop.
- The first cabinet implementation should not invent statuses that contradict
  existing backend lifecycle language. It should map technical lifecycle states
  to readable user states.
- The web cabinet must be the full product surface, while desktop receives a
  safe subset.
- Feature 030 must produce implementation-ready screen specs and follow-up
  backlog candidates for web cabinet work instead of claiming a web UI already
  exists.

## Required Web Cabinet Surfaces

- Meetings list and empty state.
- Manual media upload.
- Upload/processing status.
- Meeting review complete and degraded states.
- Account/security basics.
- Admin, billing, team, sharing, exports, audit, help/legal as browser-only or deferred markers.

## Required First-Viewport Value

The browser cabinet home must answer:

- What meetings exist?
- Which one needs attention now?
- What is still processing?
- What can I upload?
- What is local-only, failed, deleted, or access-blocked?

It must not lead with generic dashboard cards, analytics, billing, or admin
surfaces before the meeting library and upload/review loop are useful.
