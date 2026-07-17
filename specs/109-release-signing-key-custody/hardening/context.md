# Hardening analysis context

## Evidence inventory

Analysis target is repository revision
`085993cf0c7289df5b4b69e864526906599843b6`.  The implementation branch has
only Spec Kit design artifacts at the time of this inventory, so source drift
for the reviewed release code is `none`.

| ID | Evidence | Type | What it establishes |
| --- | --- | --- | --- |
| E001 | Historic signer availability incident | supplied release evidence | The currently installed update line's historic private signer is unavailable, while its embedded public verifier remains immutable. No secret or local path is recorded here. |
| E002 | `apps/macos/Installer/Scripts/prepare-app-update.sh` | source | Release staging accepts one Keychain account or an arbitrary external private file, verifies key-to-app equality, and does not publish the feed. |
| E003 | `apps/macos/Scripts/validate-app-updates.sh` | source | Ordinary configured updates reject a changed feed URL or Sparkle public key and validate app/identity continuity. |
| E004 | `apps/macos/Installer/README.md` | source | Current operations document a local Keychain/file signer but not durable redundant custody or a loss-recovery drill. |
| E005 | `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` | source | Tests protect existing staging/continuity behavior but do not prove two protected channels or safe cross-channel readiness. |

The source-artifact collection digest is
`sha256:7396331047d1daa3849d5097efe04105df17d2c56041b039c8664d655b815eaa`.
It was calculated from E002--E005 at the reviewed revision.  E001 is a supplied
operational fact rather than a repository file; this analysis does not claim a
sealed incident archive.

## Constraints carried into the design

- The historical private key cannot be recreated from the application or feed.
- Existing GRAF clients must not have their verifier changed by a normal
  appcast; one manual bootstrap is acceptable and must be clearly labelled.
- The owner-only local code-signing identity remains outside this slice.
- The public download host cannot be given signing secret authority.
- No raw secret, raw audio, transcript, customer data, live local path or
  credential-bearing URL may enter feature artifacts or evidence.
