# Research: custody подписи обновлений

## Decision 1: Keep Sparkle trust immutable inside ordinary updates

**Decision**: Retain the existing requirement that an ordinary in-app update
has the same HTTPS feed and `SUPublicEDKey` as its predecessor.  Treat a trust
generation change as an explicitly labelled manual bootstrap package only.

**Rationale**: `validate-app-updates.sh` already rejects a changed public key
or feed for a configured predecessor.  This is the right fail-closed boundary:
the public key in the installed app is the verifier for the appcast and archive,
not a value an appcast may replace.  Sparkle documents that losing an EdDSA
private key normally requires key rotation/recovery planning; the private key
cannot be derived from the public application configuration.  The observed
historic-key loss therefore has no cryptographic shortcut.

**Alternatives considered**:

- Reuse or derive the historic private key: impossible from public data and
  would falsely claim a recovery capability.
- Let an appcast introduce a new key: rejected because an attacker who could
  influence the feed would gain a path to replace its own verifier.
- Disable update verification for the migration: rejected because it removes
  the guarantee at exactly the moment the trust root changes.

## Decision 2: Use protected GitHub environment plus macOS Keychain

**Decision**: Keep the active Sparkle private key in two independent protected
channels: a GitHub Actions environment secret (`graf-release-signing`) as the
normal release signer, and a named local macOS Keychain account as the
operator-controlled recovery signer.  Store only the active public key and its
SHA-256 identifier in Git.

**Rationale**: The current release helper accepts a local Keychain account or
an arbitrary external private-key file.  That permits accidental single-copy
custody and has no durable cross-channel readiness proof.  GitHub environment
secrets are supplied only to jobs that reference the protected environment and
can require manual approval; the Keychain path remains available if the cloud
channel is temporarily unavailable.  Each signer derives a public key and must
match the manifest and final app before artifact staging.

The official Sparkle documentation describes Keychain-backed key generation and
explicit export/import for recovery.  We will use export only through a
short-lived, permission-restricted provisioning pipe to an encrypted GitHub
environment secret, never as a repository file or release asset.  GitHub's
secret and environment documentation supports environment-scoped access and
approval gates, so the workflow is deliberately `workflow_dispatch` only and
uses the minimum repository permissions.

**Alternatives considered**:

- Local Keychain only: rejected; it is the exact single-point-of-loss model we
  must remove.
- A persistent external key file or encrypted repository blob: rejected;
  recovery copies are easy to leak, copy or lose and increase audit surface.
- A third-party HSM/KMS: potentially stronger at a larger operational cost,
  but unavailable in the current owner-only channel.  It remains an upgrade
  option when Developer ID/notarization work is approved.

## Decision 3: Sign a validated draft asset in the cloud, do not publish there

**Decision**: The protected workflow downloads a release-draft ZIP and Russian
notes for an exact tag, validates the extracted GRAF application and prior app,
derives the secret's public key, then uses the existing staging helper to create
the signed archive/appcast.  It uploads only reviewed artifacts back to the
draft release.  A separate owner-controlled publication procedure copies
versioned files first and the public appcast last.

**Rationale**: The Sparkle secret signs update metadata; it does not need to
own a macOS code-signing identity.  This preserves the existing controlled
local signing lineage while making Sparkle key availability independent of one
Mac.  The cloud workflow cannot trigger from a pull request and cannot publish
the live host, so a workflow error cannot atomically expose a feed whose archive
is absent.  The existing staging helper's version, app identity, archive and
signature validation remains the release choke point.

**Alternatives considered**:

- Put app code-signing certificates into GitHub too: rejected for this slice;
  it expands the secret boundary and would not improve Sparkle-key recovery.
- Let the workflow publish directly to the public host: rejected; it removes
  the independent archive-first verification step and makes rollback harder to
  inspect.
- Keep cloud verification only, while signing locally: rejected; it detects
  drift but does not provide a usable fallback signer.

## Decision 4: Represent readiness with safe attestations, not secret probes

**Decision**: Define a public `UpdateSigningKey.json` manifest and a safe
attestation schema containing a one-way key identifier, channel state, tag/run
metadata and timestamp.  The local verifier compares the Keychain-derived
public key and a downloaded workflow attestation against the app and manifest.

**Rationale**: A release operator needs proof that both channels refer to the
same active key, but neither a Keychain query nor GitHub secret APIs may reveal
secret material.  A fingerprint derived from the public key lets us compare
channels and final bundles without weakening key confidentiality.  Routine
readiness requires both channels; a one-channel release is explicit degraded
mode and still uses the same public-key checks.

**Alternatives considered**:

- List secret values or local paths in a diagnostic command: rejected by the
  product secret discipline and unsafe for logs/screenshots.
- Trust a secret-name listing as proof of key equality: rejected; existence is
  not evidence that the stored value matches the app.

## Decision 5: Prove the migration with bootstrap, then two normal updates

**Decision**: Use the next available CalVer as a manually installed bootstrap
package with the new public key, followed by two strictly greater versions
through the protected signer/appcast flow.  The first in-app update proves
new trust; the second proves continuity rather than a one-off exception.

**Rationale**: Existing pre-migration installations cannot verify an appcast
signed by a new key.  One manual package is unavoidable and honest.  Requiring
two subsequent updates catches a design that merely gets the first recovery
step working while leaving release custody or version ordering fragile.

**Alternatives considered**:

- Publish the current unreleasable candidate: rejected; its old embedded public
  key cannot produce a valid signed feed.
- Call a manual package an automatic update: rejected; users must understand
  that it is a one-time trust migration.

## Decision 6: Use the owner-only lane until protected review is available

**Decision**: Do not pretend that the current private-repository GitHub plan
provides the required reviewer gate.  Use the named macOS Keychain signer for
the current owner-controlled release lane, keep the private key as a manual
Bitwarden recovery backup, and treat cloud signing as a future reactivation.

**Rationale**: The environment, secret and branch policy exist, but GitHub
rejects the required reviewer protection rule on the current plan.  A local
Keychain signer already has the required public-key equality checks and safe
attestation path.  The fallback stays degraded and therefore requires exact
tag/provenance, fresh Keychain evidence, explicit owner approval and
archive-before-appcast publication.  Bitwarden is not an automated signer and
is never read by CI or the application.

**Consequence**: T034 is superseded as an unavailable cloud setup task.  T037
closes the owner-only release proof for the current lane; a later plan upgrade
can reopen the protected two-channel path without rotating the active public
key.

## Sources

- [Sparkle documentation](https://sparkle-project.org/documentation/) — key
  generation, Keychain storage and private-key export/import behavior.
- [GitHub Actions secrets](https://docs.github.com/en/actions/reference/security/secrets)
  and [environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
  — encrypted environment secrets and protected deployment contexts.
- [GitHub secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
  — least privilege and trust boundaries for workflow execution.
- Repository evidence at commit `085993cf0c7289df5b4b69e864526906599843b6`:
  `apps/macos/Installer/Scripts/prepare-app-update.sh`,
  `apps/macos/Scripts/validate-app-updates.sh`,
  `apps/macos/Installer/README.md`, and
  `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`.
