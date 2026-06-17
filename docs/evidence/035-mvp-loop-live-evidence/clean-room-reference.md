# Clean-Room Reference: 035 MVP Loop Live Evidence

Feature: `035-mvp-loop-live-evidence`

## Policy

Reference observations from Krisp desktop/web are used only as generic product
lessons for launch-readiness review. This file must not include private Krisp
screenshots, transcript text, account data, meeting titles, copied copy, brand
assets, icons, or layout-specific instructions.

## Allowed Lessons

- The first useful screen should be a meeting workspace, not diagnostics.
- Live recording controls should be persistent, visible, and separate from
  review content.
- Desktop capture authority should remain local and always expose one-action
  stop.
- Upload/search/filter controls should be contextual to the meeting workspace.
- Web owner review can carry denser list/detail/governance surfaces while the
  desktop app keeps capture control local.
- Transcript/playback/provenance and speaker correction belong in the review
  flow.
- Share/export/delete/lifecycle actions belong to browser/server-owned
  governance, not hidden native capture controls.

## Intentional 2brain Differences

- `2brain Rec` uses original names, copy, visual language, and native/web
  boundaries.
- The desktop app must not copy Krisp's layout, colors, icons, or brand
  expression.
- Missing product capabilities must be shown as truthful blockers or deferred
  states, not masked by reference-matching UI.
- Generated notes/actions stay a truthful planned state until a separate
  product slice implements or explicitly defers them.

## Current 035 Alignment

- Installed desktop capture proof is current: the `/Applications/2brain Rec.app`
  bundle can start, pause, resume, stop, and validate a metadata-only local
  artifact.
- The current installed desktop surface is still operational and local-mode
  heavy; it proves capture trust but does not yet deliver the accepted V8
  product workspace quality.
- Production web route truth is current: `rec.2brain.pro/meetings` exists but
  returned `401 missing_auth_context` without a commit-safe authenticated owner
  session.
- Web list/detail/governance is fixture-backed and metadata-safe, not
  live-owner proven.

## Product Polish Gaps

- Move the installed desktop first surface toward the accepted V8 meeting
  workspace while preserving native Record/Pause/Resume/Stop authority.
- Expose web cabinet entry and review status in user language, without internal
  server/API wording.
- Keep dense browser list/detail/governance in the web surface after the owner
  auth/session route is validated on `rec.2brain.pro`.
- Keep notes/actions explicitly planned or blocked until the product can prove
  generated outputs.
- Validate text fit, control sizing, and no-overlap behavior against the V8
  clean-room baseline before any broad launch claim.

## Forbidden Similarity Checks

- No committed private Krisp screenshots.
- No copied Krisp visual expression, brand assets, colors, icons, or layout.
- No copied product copy beyond short generic category labels.
- No claim that the interface is accepted merely because it resembles Krisp.

## Result

`needs_polish`: 035 proves local desktop capture and identifies the live web
auth blocker, but the product surface still needs the `036-owner-review-live-polish`
slice before a broad launch claim.
