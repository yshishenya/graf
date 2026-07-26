# Implementation Plan: Надёжная custody подписи обновлений

> Historical Sparkle trust-custody plan. It does not authorize local/self-signed
> Apple app/package signing. Feature 130 is the current and only public macOS
> Developer ID release path.

**Branch**: `codex/109-release-signing-key-custody` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

## Summary

We will replace the accidental single-local-copy release process with one active
Sparkle signing generation whose private key exists in two independent protected
channels: a protected GitHub environment secret for the normal release path and
a named macOS Keychain entry for controlled emergency recovery.  The repository
will contain only a versioned public-key manifest and safe key fingerprint.  A
release helper and a protected workflow will derive and compare the public key
before staging anything, fail before a public feed can change, and emit only
safe attestation data.

The historic Sparkle private key cannot be reconstructed. We therefore defined
one explicit manual Sparkle trust bootstrap package that preserves the GRAF
bundle identity and embeds the newly managed public key. The Apple signing
migration in `v2026.07.26.6` is a separate notarized Developer ID `.pkg`
bootstrap owned by Feature 130. This plan never authorizes a self-signed public
package or a silent key/feed change in an ordinary appcast.

## Current operating decision — 2026-07-21

The two-channel GitHub-environment design below remains the future normal
Sparkle custody path, but the current private repository cannot create the
required reviewer protection rule on its GitHub plan. The former degraded lane
used the macOS Keychain signer with an offline owner backup in Bitwarden.
Bitwarden is recovery-only and is never read by CI, the app or the public host.

That historical lane was explicitly degraded. It required exact tag/provenance,
a fresh
metadata-only Keychain attestation, explicit owner approval, unchanged public
manifest/app/feed identity, and archive-before-appcast publication. T034 is
therefore a completed scope decision rather than a claim that the unavailable
reviewer gate was configured. T037 closes historical Sparkle-custody evidence;
the protected cloud path remains a future reactivation option and is not an
Apple code-signing alternative.

## Technical Context

**Language/Version**: POSIX shell for installer/release tools; Swift 5.10
tooling already used to derive Sparkle public keys; GitHub Actions YAML; Swift
XCTest evidence tests.

**Primary Dependencies**: pinned Sparkle 2.9.4 tools (`generate_keys`,
`generate_appcast`, `sign_update`); macOS Keychain; GitHub Actions protected
environment and encrypted secrets; `gh` on approved release/CI hosts.  No new
runtime dependency is introduced.

**Storage**: macOS login Keychain (emergency signer); GitHub environment secret
(normal signer); Git repository contains a public key/fingerprint manifest only;
the existing ignored staging directory contains transient release artifacts.

**Testing**: XCTest source/evidence tests; shell syntax checks; isolated
temporary-key fixture tests; workflow static/security checks; installer/update
validator tests; feature quickstart; canonical `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: high-risk feature.  It changes secret custody,
release signing, update trust, a user-visible installer/bootstrap path, and
release operations.  It requires clarify, plan, checklist, tasks, analyze,
tracker sync, focused and repository-wide validation before implementation
closeout.

**Release Gate**: no public deployment while this slice is being implemented.
The later release gate requires a green local CI, protected-channel attestation,
manual bootstrap validation, two sequential in-app update proofs, and explicit
release approval.  Versioned assets are copied and verified before the live
appcast is replaced last.

**Target Platform**: macOS 14.5+ GRAF app, GitHub Actions macOS runners, and
the existing owner-controlled HTTPS download host.

**Project Type**: native macOS desktop app plus release tooling/workflow.

**Performance Goals**: no recording-path or app runtime hot-path change;
release preflight completes before artifact publication, and update checks retain
their existing 24-hour/manual cadence.

**Constraints**: no private key, seed, secret value, live secret path, or
content-bearing release data may enter Git, app bundle, public host, issue,
artifact metadata, logs, shell history, or diagnostics.  Preserve
`pro.2brain.graf`, GRAF name, HTTPS feed, Sparkle signed-feed settings, delayed
installation during capture, and existing permission continuity.  A lost
historic key is not recoverable by design.

**Scale/Scope**: one Sparkle trust-custody line and a small release team. This
slice intentionally does not implement Apple signing migration; Feature 130
owns Developer ID/notarization and does not
modify capture, audio, transcription, or server code.

## Constitution Check

### Pre-research gate

| Applicable gate | Plan response | Status |
| --- | --- | --- |
| Capture-first integrity | No capture code or routing behavior changes. Bootstrap validation preserves permission/identity checks. | Pass |
| Visible consent and control | No capture UI or scheduling changes. Sparkle retains existing deferral during capture. | Pass |
| Data boundary and secret discipline | The secret stays only in protected Keychain/GitHub secret channels. Public manifest and attestations contain a one-way key identifier only. | Pass |
| Spec-driven delivery | High-risk sequence includes clarify, plan, checklist, tasks, analyze, GitHub task tracking, implementation, and closeout gates. | Pass |
| Release and rollback | Feed/key continuity remains strict for ordinary updates; bootstrap is explicit; archive/package precede appcast; forward-only rollback is documented. | Pass |

No constitution amendment is required: this slice strengthens existing update
and secret controls without changing product governance.

### Post-design re-check

The Phase 1 contract keeps the private material out of all app, repo and public
interfaces; retains the existing validator's strict ordinary-update key/feed
continuity; and separates manual trust migration from Sparkle publication.  The
two-channel design does not add a privileged runtime component or an audio path.
All applicable gates remain passed.

## Validation Plan

1. Run the feature [quickstart](quickstart.md) with disposable keys and
   temporary directories.  It covers correct key, missing key, mismatched key,
   protected-workflow attestation, bootstrap-only key rotation, and a normal
   post-bootstrap update.
2. Run focused macOS XCTest evidence coverage and shell syntax checks for every
   changed script/workflow.  Tests must prove that legacy arbitrary private-key
   file input is not available to a local operator, temporary CI material is
   cleaned, and a public feed is never changed by staging.
3. Review the workflow for `workflow_dispatch`/protected-environment scope,
   least `contents` permission, no untrusted PR trigger, no `set -x`, and no
   secret-bearing artifact or output.
4. Run `infra/scripts/ci-local.sh` before PR/closeout. The historical Sparkle
   bootstrap plus two sequential in-app updates belong only to archived
   evidence; current Apple publication follows Feature 130. Include
   metadata-only evidence and do not reset TCC permissions.
5. For the physical rollout, verify remote versioned files and SHA-256 values,
   replace `graf-appcast.xml` last, fetch it again, and retain the previous
   signed feed/artifacts for forward rollback.

## Project Structure

### Documentation (this feature)

```text
specs/109-release-signing-key-custody/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── release-signing-custody.md
├── hardening/
│   ├── context.md
│   ├── hardening.json
│   ├── hardening.md
│   ├── proposals/protected-dual-custody.md
│   ├── diagrams/
│   └── implementation/protected-dual-custody.md
└── tasks.md                 # Created during $speckit-tasks
```

### Source Code (repository root)

```text
.github/workflows/
├── verify-release-signing-custody.yml
└── sign-graf-app-update.yml

apps/macos/
├── Installer/
│   ├── UpdateSigningKey.json
│   ├── README.md
│   └── Scripts/
│       ├── build-local-installer.sh
│       ├── prepare-app-update.sh
│       ├── provision-release-signing-custody.sh
│       └── verify-release-signing-custody.sh
├── Scripts/
│   └── validate-app-updates.sh
└── Shared/Tests/
    └── InstallerLifecycleEvidenceTests.swift

qa/macos/
└── release-candidate-checklist.md

CHANGELOG.md
```

**Structure Decision**: This remains a native macOS release-tooling slice.  We
add no service, database, client runtime abstraction, or new package.  The
small manifest is a public trust declaration consumed by existing installer
tools, while Keychain/GitHub remain the only private-key holders.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Two protected signing channels and one protected workflow | Availability after a lost local credential must not weaken signature verification. | A single Keychain, local file, or secret manager alone recreates the observed single point of loss. |
| Explicit manual bootstrap generation | Existing installed clients trust a cryptographically unrecoverable historic public key. | An ordinary appcast cannot legitimately rotate that key and any bypass would strand or expose clients. |
