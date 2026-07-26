# Research: Developer ID-only macOS release

## Decision 1: Keep the existing validator as the single trust boundary

- **Decision**: Extend `apps/macos/Scripts/validate-app-updates.sh`; do not
  create a second ordinary-update validator.
- **Rationale**: The existing script already validates bundle shape, Sparkle
  configuration, nested signatures, entitlements, signing kind, team identity,
  designated requirement, notarization staple and Gatekeeper. A second path
  would make the operator contract drift again.
- **Alternatives considered**: A documentation-only rule was rejected because
  the current script correctly blocks the `.5` local→`.6` Developer ID change,
  but does not expose the safe manual transition as a named contract.

## Decision 2: Migration is a separate manual `.pkg` bootstrap

- **Decision**: Add `GRAF_MANUAL_DEVELOPER_ID_BOOTSTRAP=1` and a thin
  `validate-developer-id-bootstrap.sh` wrapper. The mode accepts the historical
  predecessor only to prove a manual transition, requires a notarized Developer
  ID candidate/package, and forbids archive/appcast arguments.
- **Rationale**: A Sparkle update crosses a signing lineage boundary that the
  old client cannot safely treat as an ordinary update. The published `.6`
  evidence already demonstrates this exact boundary.
- **Alternatives considered**: Weakening the unconditional signing-kind check
  was rejected; it would make a local or ad-hoc predecessor eligible for an
  ordinary public update.

## Decision 3: Public build guard fails closed on identity selection

- **Decision**: When `GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1`,
  `build-local-installer.sh` requires `Developer ID Application:` and, for a
  package, `Developer ID Installer:` identities. Local/ad-hoc opt-in flags are
  rejected in this mode.
- **Rationale**: The builder is the earliest shared public release boundary and
  must not rely on a later human inspection.
- **Alternatives considered**: Checking only the finished app was rejected
  because an unsigned package could still be staged or published.

## Decision 4: Keep Sparkle key custody, clarify its meaning in guidance

- **Decision**: Retain `build-trust-bootstrap.sh` and
  `validate-manual-update-bootstrap.sh` for Ed25519 trust-generation rotation
  only. Add explicit wording that they are not Apple code-signing migration
  tools.
- **Rationale**: Sparkle trust custody is a separate control and removing it
  would weaken ordinary update signing rather than simplify the release path.
- **Alternatives considered**: Deleting the scripts was rejected because the
  existing GitHub workflow and custody tests still depend on them.

## Decision 5: Historical records remain immutable but non-operational

- **Decision**: Preserve old release/changelog facts and old test fixtures, but
  add historical/archive labels where a reader could mistake them for current
  instructions. Active README, runbook, checklist, AGENTS and Spec Kit release
  artifacts describe only Developer ID and the manual migration bootstrap.
- **Rationale**: Rewriting old receipts would corrupt release evidence; leaving
  them unlabelled would preserve the operator ambiguity the user asked to
  remove.
- **Alternatives considered**: Mass-deleting all legacy words was rejected
  because it would remove useful negative tests and historical audit evidence.
