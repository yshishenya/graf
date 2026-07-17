# macOS Release Candidate Checklist

This checklist describes the current app-owned system-audio-first recording
release surface.

## Automated Gates

- [ ] `swift build --package-path apps/macos` passes.
- [ ] `swift test --package-path apps/macos` passes.
- [ ] `swift run --package-path apps/macos ContractValidation` passes.
- [ ] `sh apps/macos/Scripts/validate-no-legacy-audio-driver.sh` passes.
- [ ] `sh apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata` passes.
- [ ] `infra/scripts/ci-local.sh` passes.

## Recording Regression Gates

- [ ] `SystemAudioCaptureService` still produces the app-owned incoming
  sample source.
- [ ] `MicrophoneCaptureService` still produces the app-owned microphone
  sample source.
- [ ] Both sources are explicitly injected into `LocalRecordingWriter`.
- [ ] `Record`/`Stop` creates two non-empty original WAV tracks and a
  finalized manifest.
- [ ] Microphone and system-audio permissions are both enforced.
- [ ] The persistent local capture indicator and one-action `Stop` pass.
- [ ] Existing recording-directory and manifest compatibility tests pass.

## Packaging Gates

- [ ] The distribution package contains exactly one app component.
- [ ] The package contains no privileged audio component, lifecycle sidecar, or
  host-service mutation script.
- [ ] Package expansion/inspection passes without installing it.
- [ ] Signing/notarization evidence matches the intended release lane.

## In-App Update Gates

- [ ] Exactly one release lane is declared: owner-only self-signed for
  controlled Macs, or public Developer ID/notarized distribution.
- [ ] `Sparkle` is locked to `2.9.4`, embedded at
  `Contents/Frameworks/Sparkle.framework`, and reports current version `2.9.4`.
- [ ] `Contents/Resources/Sparkle-LICENSE.txt` contains the complete license
  and third-party attribution text from the pinned upstream release.
- [ ] `SUFeedURL` is the approved public credential-free HTTPS appcast URL and
  `SUPublicEDKey` is the approved base64 32-byte Ed25519 public key.
- [ ] Signed-feed and verify-before-extraction settings are enabled; scheduled
  checks are `86400`; automatic download/install and system profiling are off.
- [ ] All nested Sparkle code is signed inside-out before `GRAF.app`; the app
  has hardened runtime and a secure timestamp.
- [ ] The new app has a strictly increasing CalVer, stays `GRAF.app` /
  `pro.2brain.graf`, has the same TeamIdentifier, and satisfies the previous
  public app's designated requirement.
- [ ] The selected trust gate passes: owner-only requires the exact local
  certificate and designated-requirement continuity; public distribution
  requires Developer ID Application signing, notarization, stapling, and
  `spctl --assess --type execute`.
- [ ] `prepare-app-update.sh` creates a versioned archive and signed appcast in
  staging only; archive length, EdDSA signatures, `arm64`, and macOS `14.5+`
  match the final app.
- [ ] The private EdDSA key, Developer ID material, notarization credentials,
  and generated signed artifacts remain outside git and issue evidence.
- [ ] An older installed build finds the staged release through both the daily
  scheduler and `GRAF > Check for Updates…`; current/offline/incompatible
  outcomes remain truthful.
- [ ] Dismissing a valid offer keeps one accessible left-sidebar marker in both
  connected-cabinet and local-only layouts; skip, withdrawal, or successful
  install removes it.
- [ ] Active/paused capture, start/stop, finalization, and termination cleanup
  prevent relaunch; after protected work ends the cached offer proceeds without
  a second catalog request.
- [ ] Corrupt, unsigned, wrong-key, downgrade, wrong-identity, and incompatible
  fixtures are rejected while the previous app remains launchable.
- [ ] Two sequential same-identity in-app updates retain microphone and
  Screen/System Audio grants without `tccutil reset` or TCC mutation.
- [ ] First updater-enabled release notes state that older builds need one final
  manual `.pkg` bootstrap install.
- [ ] The archive/package contains no privileged audio component and no Core
  Audio service mutation.
- [ ] Public appcast/archive publication has explicit release approval and a
  documented stop-rollout feed restore plus higher-CalVer forward rollback for
  Macs that already updated.

## Manual Gates

- [ ] Current-build short recording smoke passes on the required browser target.
- [ ] Claimed microphone device classes pass the device matrix.
- [ ] Indicator visibility and stop behavior are observed directly.
- [ ] Long-duration acceptance is either passed with evidence or called out as
  a known limitation.

## Release Hygiene

- [ ] Russian changelog/release notes describe the architecture removal,
  compatibility impact, validation evidence, known limitations, and linked
  PR/issues.
- [ ] No secrets, raw audio, transcript text, signed URLs, or private meeting
  content are committed as evidence.
