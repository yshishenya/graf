# Research: Access, Sharing, And Downloads

Feature: `017-access-sharing-downloads`
Date: 2026-06-16

## Decision: Effective Access Is Computed Server-Side For Every Surface

Use a server-side access decision function for list rows, detail payloads, share
links, download requests, export requests, and embedded desktop routes.

Rationale:

- Feature 016 currently scopes cabinet reads by `workspace_id`; 017 must add
  viewer identity, owner status, active workspace membership, team visibility,
  explicit share grants, and lifecycle policy.
- UI hiding alone would not protect direct detail or egress routes.
- A shared access service keeps browser and desktop embedded routes consistent.

Alternatives considered:

- **Client-side access filtering**: rejected because direct API/download routes
  could still leak meeting existence or artifacts.
- **Separate desktop access logic**: rejected because the spec requires
  browser/server ownership and multiplatform reuse.

## Decision: Login-Required Share Grants Only

Support owner/admin grants for authenticated users and workspace team
visibility. Do not enable anonymous or public links in this slice.

Rationale:

- Login-required sharing satisfies the first collaboration need while preserving
  the PRD's owner-controlled privacy posture.
- Public links require additional admin policy, expiration, revocation,
  external-recipient UX, legal copy, and abuse controls that belong in a later
  accepted slice.
- Authentication-before-content avoids exposing private titles, participants,
  transcript, audio, summary, or artifact existence to unauthenticated viewers.

Alternatives considered:

- **Public links with disabled defaults**: rejected for implementation because
  the UI would still need more policy surface and copy than the current MVP
  slice can safely validate.
- **Email-only invitations without account resolution**: rejected because the
  current identity model already has authenticated users and workspace
  membership, while external invitations are not yet accepted scope.

## Decision: Server-Mediated Artifact Egress

Downloads and exports are served only through Rec server routes that re-check
authorization, artifact lifecycle, and policy immediately before returning
content.

Rationale:

- Object storage keys and dependency-signed URLs are secrets in practice and
  must not appear in browser/desktop responses, logs, or screenshots.
- Server-mediated egress allows consistent audit-before-egress, rate/size
  policy later, and deletion truth around already exported files.
- The current server already owns upload artifacts and processed review data,
  so this extends existing boundaries instead of creating a new client egress
  path.

Alternatives considered:

- **Pre-signed MinIO URLs**: rejected for this slice because they would expose a
  dependency URL/token and make audit timing weaker.
- **Desktop download proxy**: rejected because desktop must not own policy or
  server credentials.

## Decision: Audit Writes Are A Required Precondition For Mutating Or Egress Actions

Share grants, share revokes, downloads, and exports fail closed if the required
metadata-only audit event cannot be persisted before the action completes.

Rationale:

- The clarified requirement FR-019 makes audit availability part of the access
  and egress safety boundary.
- A failed audit write must not create an invisible share or untracked egress.
- Metadata-only audit protects content while still proving actor, artifact
  class, policy reason, and outcome.

Alternatives considered:

- **Best-effort audit after success**: rejected because it can produce
  untracked shares/downloads during database or transaction failures.
- **Queue audit asynchronously**: rejected for MVP egress because queue failure
  would weaken evidence; it may be reconsidered with durable write-ahead
  semantics in a later infra slice.

## Decision: Extend 016 Cabinet UI In Place

Use the existing 016 server-rendered cabinet layout and reserved governance
slots, replacing planned share/export/download affordances with real policy
states.

Rationale:

- The user reference work showed Krisp's useful information architecture:
  meeting list actions, detail governance actions, share modal, filters, sort,
  and egress affordances. The implementation must use those lessons without
  copying assets, copy, iconography, or private screenshots.
- 016 already established clean-room `2brain Rec` styling and route ownership.
- Reusing server-rendered HTML/CSS avoids introducing a frontend build system
  before MVP launch.

Alternatives considered:

- **New SPA for sharing/export**: rejected as unnecessary scope and extra build
  surface.
- **Krisp-like exact modal and toolbar**: rejected by clean-room and brand
  distance rules.

## Decision: Export Packages Are Policy-Filtered Manifests Plus Allowed Files

Create exports as package requests with a manifest that lists included artifact
classes and policy reasons. The package includes only artifacts permitted for
the viewer at request time.

Rationale:

- Users need transcript plus summary together, but package contents must remain
  explicit and policy-derived.
- The manifest supports deletion/egress truth: exported files are outside later
  Rec revocation once downloaded.
- Partial package states are clearer than silently omitting artifacts.

Alternatives considered:

- **Always include all available artifacts**: rejected because per-artifact
  policy is a functional requirement.
- **No export package in 017**: rejected because the spec includes export as a
  P2 story and it shares the same egress controls as downloads.
