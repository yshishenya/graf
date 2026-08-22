# macOS Release Candidate Checklist

This checklist describes the current app-owned system-audio-first recording
release surface. The active public macOS lane is Developer ID-only. Historical
owner-only/self-signed receipts below are archive evidence, not release
instructions.

## Automated Gates

- [ ] `swift build --package-path apps/macos` passes.
- [ ] `swift test --package-path apps/macos` passes.
- [ ] `swift run --package-path apps/macos ContractValidation` passes.
- [ ] `sh apps/macos/Scripts/validate-graf-aec3-artifact.sh` passes.
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
- [ ] New recordings report mandatory AEC3 metadata and never publish a raw
  microphone or render-reference artifact.
- [ ] Far-end, near-end and double-talk synthetic AEC3 thresholds pass; real
  speakerphone quality remains unclaimed until the controlled hardware matrix
  passes.

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
- [ ] `GRAF` contains both `arm64` and `x86_64`, bundles
  `AEC3-THIRD-PARTY-NOTICES.txt`, and has no WebRTC/Abseil dylib dependency.
- [ ] Developer ID Application signing is used for the app and Developer ID
  Installer signing for the package; notarization, stapling and Gatekeeper
  evidence all pass.

## In-App Update Gates

- [x] Exactly one active public release lane is declared: Developer ID
  Application/Installer with notarization, stapling and Gatekeeper. Owner-only
  self-signed material is historical or isolated-test evidence only.
- [ ] `Sparkle` is locked to `2.9.4`, embedded at
  `Contents/Frameworks/Sparkle.framework`, and reports current version `2.9.4`.
- [ ] `Contents/Resources/Sparkle-LICENSE.txt` contains the complete license
  and third-party attribution text from the pinned upstream release.
- [ ] `SUFeedURL` is the approved public credential-free HTTPS appcast URL and
  `SUPublicEDKey` is the approved base64 32-byte Ed25519 public key.
- [ ] UpdateSigningKey.json is active, contains only public metadata, and its
  keyId, trust generation and public key match the final app SUPublicEDKey.
- [ ] The named Keychain signer produced matching safe key-id evidence. Any
  disposable test proof was separate and did not activate the production
  generation.
- [ ] A local metadata-only readiness drill ran before this release, no
  more than 90 calendar days after the prior drill and immediately after any
  control-plane change; its retained evidence contains only timestamp,
  generation, key ID and channel states.
- [x] The public release never selects the historical owner-only fallback;
  historical receipts retain their exact tag/provenance and metadata-only
  evidence without becoming an active operator path.
- [ ] The release attestation binds the active generation, exact CalVer tag,
  commit, `macos-keychain` channel, `ready` state and a UTC timestamp no
  older than 24 hours before staging. A missing, stale or mismatched
  attestation blocks the attempt and leaves the prior staged/public appcast
  unchanged.
- [ ] The local signing command rejects a missing, mismatched, non-ready or
  expired Keychain attestation before generating a signed appcast.
- [x] A one-channel Keychain recovery receipt, if encountered in history, is
  treated as archive evidence only. It never authorizes a new public release;
  malformed or missing attestation blocks publication.
- [ ] Signed-feed and verify-before-extraction settings are enabled; scheduled
  checks are `86400`; automatic download/install and system profiling are off.
- [ ] All nested Sparkle code is signed inside-out before `GRAF.app`; the app
  has hardened runtime and a secure timestamp.
- [ ] The new app has a strictly increasing CalVer, stays `GRAF.app` /
  `pro.2brain.graf`, uses the same Developer ID TeamIdentifier, and satisfies
  the previous public app's designated requirement.
- [ ] Public distribution passes the Developer ID Application/Installer gate,
  notarization, stapling, `spctl --assess --type execute`, and
  `spctl --assess --type install`.
- [ ] `prepare-app-update.sh` creates a versioned archive and signed appcast in
  staging only; archive length, EdDSA signatures, `arm64`, and macOS `14.5+`
  match the final app.
- [ ] The one-time `v2026.07.26.6` Developer ID migration package is explicitly
  labelled, preserves GRAF metadata and feed/public-key continuity, passes
  notarization/package checks, and produces no appcast. It is installed
  manually; later releases use ordinary Developer ID→Developer ID updates.
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
- [ ] After the manual `.6` bootstrap, an older updater-enabled build finds the
  next staged release through both the daily scheduler and `GRAF > Check for
  Updates…`; current/offline/incompatible outcomes remain truthful.
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

## Historical T037 owner-only release closeout receipt — 2026-07-21

The following checks are an immutable historical receipt for the former
private-repository owner-only lane. They do not authorize a current release and
do not claim that the old artifact was Developer ID-signed or notarized.

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

The historical owner-only receipt is not a current migration gate. The active
Developer ID gates above are required for every new public release.

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
