# Security Hardening Review: GRAF update-signing custody

> Historical Sparkle-custody review. It does not authorize local/self-signed
> Apple publication; current macOS public release gates are in Feature 130.

## Evidence Basis

We reviewed the supplied historic-signer availability incident together with the
release staging helper, update validator, operational documentation and existing
macOS installer tests at `085993cf0c7289df5b4b69e864526906599843b6`.  The
evidence registry is in [context.md](context.md).  This is a design analysis,
not a claim that the issue is already fixed.

The key distinction is that the existing code already protects the client-side
trust boundary well: an ordinary update may not change its feed URL or public
key.  The observed failure sits next to that boundary in operational custody:
one valid local signer can disappear without a second independently controlled
route to produce the next valid signature.

## Constraints

We must preserve ordinary Sparkle key/feed continuity, the GRAF bundle identity,
permission continuity and archive-before-appcast publication.  We may not place
private material in Git, the app, public storage, logs or diagnostics.  The
historic unavailable key cannot be recovered, so a clearly labelled manual
bootstrap is a compatibility requirement rather than an implementation choice.

## Opportunity Portfolio

| Opportunity | Evidence | Options | Recommendation | Proposal |
| --- | --- | --- | --- | --- |
| Own Sparkle signer custody behind two protected channels | Historic signer unavailable (E001); local file/Keychain staging (E002); strict normal continuity (E003); missing redundancy proof (E004) | 1. Retain local custody<br>2. Protected dual custody<br>3. External KMS/public-signing migration | Option 2 now; Option 3 only as a separately approved identity migration | [Protected dual custody](proposals/protected-dual-custody.md) |

## Recommendation Summary

I recommend Option 2 under the historical degraded Sparkle-custody constraints.
It keeps the
strongest existing property—the installed app itself still decides what public
key can verify a normal update—while moving signer availability behind an owned,
testable control boundary.  The protected GitHub environment is the normal path;
the macOS Keychain is a deliberate recovery path; neither one is assumed to be
proof that the other holds the same material.  Public-key fingerprints and
attestations supply that proof without revealing a private key.

The attractive part is that this does not expand the app's attack surface or add
a release service.  What gives me pause is the operational ceremony: a protected
workflow and one manual bootstrap are not as frictionless as the old local
command.  That cost is proportionate because the old convenience created the
failure mode we are correcting.  Option 3 becomes preferable only when the
product is ready to fund a broader Developer ID/notarization and managed-KMS
migration with its own TCC continuity evidence.

## Next Decisions

1. Implement the selected Option 2 through the feature's ordered tasks.
2. Configure the protected environment and approved reviewers without ever
   exposing a secret value in repository artifacts.
3. Build a one-time bootstrap from the next available CalVer, then prove two
   greater ordinary in-app updates before calling the new line ready.
