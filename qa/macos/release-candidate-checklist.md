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
- [ ] Both sources enter V5LocalRecordingWriter as PTS-bearing batches and
  are ordered by one shared timeline.
- [ ] Record/Stop creates exactly manifest.json, meeting-transcription.wav and
  meeting-review.m4a; no new package has separate microphone/system WAV files.
- [ ] Microphone and system-audio permissions are both enforced.
- [ ] The persistent local capture indicator and one-action `Stop` pass.
- [ ] Existing recording-directory and manifest compatibility tests pass.

## v5 Control-Period Receipt

- [ ] The contingency rollback procedure and a candidate pre-v5 reference are
  documented. Do not substitute the user-confirmed, still-in-progress parallel
  `v2026.07.16.7` work or an unverified nearby tag. Resolving and installing
  the baseline is deferred while the v5 quality gates pass.
- [ ] The selected contingency reference is the exact `v2026.07.17.6` tag at
  `4be444e82ec449a3bb5312920fb0cd6008072c56`; the parallel `v2026.07.16.7`
  line is recorded only as a non-interchangeable reference and is not a
  runtime switch.
- [ ] Candidate commit/release, date, package schema, route verdict, incoming
  level delta, timeline verdict, artifact hashes/counts/durations, processing
  status and operator decision are recorded as metadata only.
- [ ] The receipt contains no audio, decoded media, spoken marker text,
  transcript content, device name, credential, signed URL or private local
  path.
- [ ] Rollback is an operator contingency action, triggered only by a confirmed
  v5 quality failure; it reinstalls a selected baseline for a subsequent
  recording and is not a runtime switch, a silent dual fallback or a rewrite of
  an accepted v5 revision.

### Baseline, Canary and Conditional Rollback

1. Before building the candidate, record candidate SHA, schema version,
   installer artifact digest and operator date in the feature evidence receipt.
   Keep a rollback reference documented, but do not install or rehearse it
   before a v5 quality failure. Do not store a device name, local path, audio,
   transcript or secret.
2. Build and install the candidate only through the separately approved local
   test procedure. Make one controlled non-private recording and collect only
   package member names, codec/rate/channel checks, durations, hashes,
   marker-lag result, route verdict, incoming-level delta, upload-progress
   verdict, single-job count and final status.
3. A failed route, volume, timeline, package, upload or transcript verdict is
   a stop signal: do not silently retry the same accepted revision, create a
   dual fallback or repurpose the review M4A for ASR.
4. If a v5 quality failure triggers contingency rollback, reinstall the
   selected baseline for one subsequent controlled recording. The server keeps
   its additive v5 reader while any v5 record remains; accepted v5 records are
   not rewritten, re-uploaded or sent to a second provider job.
5. Record rollback as `deferred` while no v5 failure has occurred. Once
   triggered, record pass/fail and metadata only; if the exact baseline ref,
   signed candidate or installation approval is unavailable, stop rather than
   inventing a result.

## Packaging Gates

- [ ] The distribution package contains exactly one app component.
- [ ] The package contains no privileged audio component, lifecycle sidecar, or
  host-service mutation script.
- [ ] Package expansion/inspection passes without installing it.
- [ ] Signing/notarization evidence matches the intended release lane.

## In-App Update Gates

- [x] Exactly one release lane is declared: owner-only self-signed for
  controlled Macs, or public Developer ID/notarized distribution.
- [ ] `Sparkle` is locked to `2.9.4`, embedded at
  `Contents/Frameworks/Sparkle.framework`, and reports current version `2.9.4`.
- [ ] `Contents/Resources/Sparkle-LICENSE.txt` contains the complete license
  and third-party attribution text from the pinned upstream release.
- [ ] `SUFeedURL` is the approved public credential-free HTTPS appcast URL and
  `SUPublicEDKey` is the approved base64 32-byte Ed25519 public key.
- [ ] UpdateSigningKey.json is active, contains only public metadata, and its
  keyId, trust generation and public key match the final app SUPublicEDKey.
- [ ] The normal GitHub signer and named Keychain recovery signer have each
  produced matching safe key-id evidence. The disposable
  graf-release-signing-test proof was separate and did not activate the
  production generation.
- [ ] A two-channel metadata-only readiness drill ran before this release, no
  more than 90 calendar days after the prior drill and immediately after any
  control-plane change; its retained evidence contains only timestamp,
  generation, key ID and channel states.
- [x] If this private-repository release uses the current owner-only fallback,
  the receipt explicitly records degraded approval, exact tag/provenance,
  fresh Keychain attestation and archive-before-appcast ordering; Bitwarden is
  recovery-only and no workflow or public host reads it automatically.
- [ ] The protected signing environments require independent reviewer approval,
  permit the protected master branch only, and have no public-host write path.
  Every external workflow action is pinned to a full immutable SHA.
- [ ] The release attestation binds the active generation, exact CalVer tag,
  commit, `github-environment` channel, `ready` state and a UTC timestamp no
  older than 24 hours before staging. A missing, stale or mismatched
  attestation blocks the attempt and leaves the prior staged/public appcast
  unchanged.
- [ ] The exact draft release also contains a fresh metadata-only
  `macos-keychain` attestation for the same generation/tag/commit. The signing
  workflow rejects its absence, mismatch, non-ready state or age over 24 hours
  before generating a signed appcast.
- [x] A one-channel Keychain recovery release, if unavoidable, has a recorded
  owner approval identifier and explicit degraded-fallback flag; it still
  passes manifest/app/signer/Keychain-attestation/tag checks. A malformed cloud
  attestation is never silently treated as a fallback.
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
- [ ] The one manual trust-bootstrap package is explicitly labelled, preserves
  GRAF identity and permission continuity, changes only the permitted signing
  generation, and produces no appcast. It is followed by two strictly higher
  ordinary in-app updates with the same new public key.
- [x] Production update artifacts were staged from a clean commit published at the exact release tag
  and matching `origin/master`, with
  `GRAF_REQUIRE_RELEASE_PROVENANCE=1` enabled.
- [x] ZIP, package, checksums, and Russian notes are present as GitHub Release
  assets; the archive/package were published before the appcast, and every
  public SHA-256 matches the reviewed local release artifact.
- [ ] The private EdDSA key, Developer ID material, notarization credentials,
  and generated signed artifacts remain outside git and issue evidence.
- [ ] The custody fixture/secret-pattern guard passes without suppressing a
  real value. A safe false positive is corrected in the pattern or fixture,
  never excepted by adding a production secret.
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
- [x] Public appcast/archive publication has explicit release approval and a
  documented stop-rollout feed restore plus higher-CalVer forward rollback for
  Macs that already updated.

## T037 owner-only release closeout receipt — 2026-07-21

The following checks are the completed receipt for the current private-repository
owner-only lane. They do not claim that the future protected reviewer or
Developer ID/notarization lane is configured.

- [x] `v2026.07.21.3` is an immutable exact tag at the staged `origin/master`
  commit `9a17dde2e6938d352cbf38aff7e034a9ad52fad6`.
- [x] Fresh metadata-only Keychain evidence matches the active manifest:
  `channel=macos-keychain`, `state=ready`, `trustGeneration=1`,
  `keyId=sha256:63c373b20f82851a6b4443bad2100eede5d50d897ed2aaf9fa8c94db56e4ecce`.
- [x] The degraded fallback is explicit: approval id
  `t037-owner-20260721-3` and
  `GRAF_RELEASE_SIGNING_APPROVED_DEGRADED_FALLBACK=1`; the helper reported
  `signer=keychain`, `custody=degraded`, `published=no` before publication.
- [x] The owner-only app, Sparkle archive and appcast passed the strict
  owner-only validator, signature checks, ZIP integrity and package expansion;
  no package installation was used as a substitute for these checks.
- [x] Public publication order is proven: ZIP, pkg and checksum were copied and
  SHA-256 checked before `graf-appcast.xml`; the prior appcast was retained as
  a recoverable backup, and the final public fetch rechecked version, length,
  checksums and signatures.
- [x] GitHub Release `v2026.07.21.3` retains the Russian notes and safe
  Keychain attestation. The private key, Bitwarden recovery copy and any
  secret-bearing material remain outside Git, issues and the public host.

The remaining unchecked protected-cloud and Developer ID items are future
migration gates, not blockers for this explicitly approved owner-only receipt.

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
