# Quickstart: Validate WebRTC AEC3 Recording

This guide is the acceptance path for Feature 177. Test audio may exist only in
an ignored, access-controlled local test directory. Do not commit raw audio,
spectrograms, meeting content or private paths; committed evidence contains
bounded measurements only.

## 1. Preconditions

```sh
git branch --show-current
git status --short
swift --version
xcodebuild -version
```

Expected branch: `177-webrtc-aec3-recording`. Confirm the pinned dependency in
`apps/macos/Native/GrafAEC3/upstream.lock` before trusting any artifact.

## 2. Vendor and linkage gate

```sh
sh apps/macos/Scripts/validate-graf-aec3-artifact.sh
swift build --package-path apps/macos
swift test --package-path apps/macos
```

Expected:

- artifact hash and lock match;
- archive contains arm64 and x86_64;
- only the narrow C symbols are exported to Swift;
- C smoke processes a 480-sample pair successfully;
- no WebRTC/Abseil dylib load command exists;
- notice bundle contains every locked license component.

## 3. Deterministic framing and integrity matrix

Run the focused test filter documented by the implemented test target. It must
cover:

| Scenario | Required result |
|---|---|
| Callback partitions `1, 479, 480, 481, 1024, 4096` | Only paired 480/480 AEC calls; exact output sample count |
| Random partitions with identical PTS samples | Output matches the fixed-partition run within float tolerance |
| Final partial frame | Zero-pad/process/trim; no duration extension |
| Valid silent render | Near-end output continues; no degraded state |
| Missing render interval | Explicit degraded result; no raw-mic output |
| Callback delivery jitter with stable PTS | Same result as no jitter; no host underrun/overrun |
| Backward PTS, format/timebase or route change | One terminal integrity transition; no cross-boundary frame |
| Processor error/non-finite input | Bounded reason; only cleaned prefix retained |
| Privacy Pause/Resume | PTS stays contiguous; paused mic is zero; valid render continues; resume remains active with no raw bypass |
| Saturated microphone | Counter increments; quality row cannot pass silently |
| Historical manifests | Decode successfully with absent optional AEC fields |
| New complete manifest | Exact descriptor, completed health, one WAV and one M4A |

## 4. Synthetic quality matrix

Use independent near-end and far-end speech-like fixtures and known room impulse
responses. Record only aggregate metrics.

| Scenario | Inputs | Pass threshold |
|---|---|---|
| Far-end only | Delay `20/80/150/300 ms`; RT60 `0.2/0.5/0.8 s` | Echo reduction at least 20 dB after no more than 5 s convergence |
| Near-end only | Valid silent render | Speech RMS change no more than 1 dB; correlation at least 0.98; no gate-like gaps |
| Double-talk | Independent near/far signals | Near-end loss no more than 3 dB; echo reduction at least 10 dB; no zero speech gap over 20 ms |
| Delay drift/jump | Smooth delay then route generation change | Smooth case remains active; route change terminates once with no cross-generation frame |
| 60-minute clocks | Render/capture at plus/minus 100 ppm | No dropped/duplicated output; WAV/M4A/timeline difference no more than 100 ms |
| System integrity | Reference compared before/after mix path | System component level change no more than 1 dB and no AEC mutation |

Reject a row with clipping or an invalid/missing measurement instead of treating
it as quality evidence.

## 5. Local app and installer gate

```sh
GRAF_ALLOW_ADHOC_APP_SIGNING=1 GRAF_VERSION=2026.08.20.1 \
  sh apps/macos/Installer/Scripts/build-local-installer.sh /tmp/GRAF-177.pkg
sh infra/scripts/ci-local.sh --fast
```

Inspect the exported app/package with the repository validators. Expected:
universal executable, no WebRTC/Abseil dynamic dependency, bundled notices,
valid local signature structure and exactly the canonical recording artifacts.
An ad-hoc build is local evidence only and must never be published.

Run the synthetic C/Swift smoke natively for arm64 and under Rosetta x86_64 when
Rosetta is present. If Rosetta is unavailable, the x86_64 build/link/archive
checks remain mandatory and the missing runtime smoke is recorded as a bounded
release limitation rather than silently treated as executed.

## 6. Controlled hardware matrix

Run on at least two Apple Silicon Macs and two rooms:

- built-in microphone + built-in speakers at 25%, 50% and 75%;
- headphones (near-end preservation baseline);
- far-end-only, near-end-only and double-talk;
- loud/clipping case recorded as a rejected-quality row;
- wired and Bluetooth route changes, each requiring truthful degradation;
- one 60-minute run;
- final M4A listening check: no separately audible acoustic copy of the remote
  voice and no gate-like loss of local speech.

Store only aggregate values, device class, OS/app build, result and bounded
reason in evidence. A release remains blocked until all required rows pass.

## 7. Release-only gates

Do not execute publication from this quickstart. For an authorized release
candidate, additionally run full CI and the existing Developer ID,
notarization, stapling, `spctl`, Sparkle signature and live appcast checks from
the macOS release runbook.
