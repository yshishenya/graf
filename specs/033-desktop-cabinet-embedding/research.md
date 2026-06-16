# Research: Desktop Cabinet Embedding

## Decision: Embed the existing server-owned review surface instead of rebuilding it natively

**Rationale**: Feature `016` already owns list/detail/review product state,
content-safety behavior, processing truth, and future governance slots. A
native duplicate would create drift across desktop and browser, slow MVP
delivery, and make future `017`/`018` governance work harder.

**Alternatives considered**:

- Native Swift meeting list and transcript views. Rejected because it duplicates
  server-owned product UI and would need separate implementations for future
  platforms.
- Browser-only review. Rejected for the next MVP step because the desktop app
  would still feel disconnected after recording/upload.

## Decision: Use a native shell plus bounded WebKit host

**Rationale**: SwiftUI keeps recording/upload controls in native macOS UI while
WebKit can host the server-owned `/desktop/meetings` and detail routes. This
matches the product split: local trust shell owns capture; web cabinet owns
post-meeting review.

**Alternatives considered**:

- Open the browser externally for every meeting. Rejected because it breaks the
  desktop value loop and does not satisfy the app-embedded requirement.
- Server-driven schema rendered by Swift. Rejected for this slice because `016`
  already produced HTML routes and the first need is embedding, not schema
  renderer infrastructure.

## Decision: Add a route allowlist and explicit blocked states

**Rationale**: Embedded navigation is a trust boundary. The app must allow only
approved meeting cabinet routes and must block or bound share/export/download/
delete/capture-control destinations until their own specs are accepted.

**Alternatives considered**:

- Trust all same-origin links. Rejected because future server routes may include
  admin, risky governance, or unsupported flows that should not run inside the
  desktop shell.
- Disable all navigation after initial load. Rejected because list-to-detail
  and upload-to-detail are required for the MVP value loop.

## Decision: Configure the cabinet base URL through existing desktop configuration patterns

**Rationale**: The upload client already uses environment/UserDefaults-style
configuration for server base URL and headers. The cabinet host should follow
the same development-safe pattern while avoiding hard-coded tokens or private
account identifiers.

**Alternatives considered**:

- Hard-code `https://rec.2brain.dev`. Rejected because local development,
  self-hosting, and test servers need configurable targets.
- Store bearer/session tokens in new desktop files. Rejected because auth
  storage is not part of this slice and would risk secret leakage.

## Decision: Link upload queue items to review only when server meeting identity exists

**Rationale**: A local item may be queued, blocked, failed, retained locally, or
not yet finalized on the server. Opening review is truthful only when an item
has a server meeting identifier. Otherwise, local upload truth should remain
visible without implying server review exists.

**Alternatives considered**:

- Always show a review action for every local item. Rejected because it would
  overpromise for queued/failed/local-only recordings.
- Hide upload state once embedded meetings exists. Rejected because local upload
  truth remains native and constitutionally important.

## Decision: Keep validation screenshots sanitized and local/private references out of git

**Rationale**: The user asked to use Krisp app/web as reference, but private
meeting/account screenshots and proprietary visuals must not be committed. The
tracked evidence should describe clean-room gates, include sanitized 2brain UI
screenshots, and reference existing V8 audit docs.

**Alternatives considered**:

- Commit Krisp screenshots as reference assets. Rejected because they contain
  private account/meeting information and external product visuals.
- Skip screenshots. Rejected because the user explicitly wants UI quality and
  visual verification.
