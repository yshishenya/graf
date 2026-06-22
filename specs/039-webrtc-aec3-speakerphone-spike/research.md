# Research: WebRTC AEC3 Speakerphone Spike

## Decision: Use A Feature-Gated AEC3 Adapter Boundary

`039` will introduce a WebRTC AEC3 adapter boundary rather than wiring WebRTC
directly into package truth. The adapter reports dependency readiness, render
reference status, capture timing status, candidate state, metrics availability,
and failure reason. It fails closed when the dependency is unavailable,
unpackaged, incorrectly licensed, unsafe for signing/notarization, or unable to
prove render/capture ordering.

**Rationale**: WebRTC AEC3 expects disciplined render/capture use. The primary
source describes 10 ms frames, lower-level 64-sample blocks, partial handling of
render/capture API jitter, and non-concurrent use except `AnalyzeRender`.
2brain Rec must preserve package truth when any of those assumptions are not
proven.

**Alternatives considered**:

- Directly replace `mic.wav` with processed output: rejected because a failed
  candidate would destroy baseline truth.
- Treat dependency availability as acceptance: rejected because build/link
  success does not prove route, quality, app status, or package lineage.
- Keep AEC3 as offline-only analysis: rejected because the user specifically
  wants a path to promotion if lab-grade and real app gates pass.

## Decision: Preserve Original Package Truth Until All Promotion Gates Pass

Original `mic.wav`, `incoming.wav`, and `manifest.json` remain traceable and
authoritative until the built-in Mac microphone plus built-in Mac speakers route
passes every immediate-promotion gate. AEC3 output can be `candidate_metadata`,
`derived_candidate`, `guidance_only`, `blocked`, or a reversible promoted route
state, but it cannot silently overwrite the original microphone evidence.

**Rationale**: Existing `020` leakage finalization, `037` microphone graph, and
`038` candidate evidence all depend on inspectable original evidence. AEC3 is a
quality candidate, not permission to lose auditability.

**Alternatives considered**:

- Persist only derived microphone audio: rejected until deletion, rollback,
  lineage, and package-readiness semantics are accepted.
- Declare original evidence obsolete after one good run: rejected because
  speakerphone echo cancellation is route, timing, and environment sensitive.

## Decision: Require Lab-Grade Corpus Plus Controlled App Recording

Immediate promotion requires at least ten files per required scenario family,
at least five slices per file, every full file, at least two 20 minute or longer
full-file runs per scenario family, varied room acoustics, varied Mac/device
profiles, varied speaker volumes, and controlled real-hardware app recording
rows. The corpus must cover far-end-only leakage, near-end-only speech,
double-talk, loud-speaker/clipping stress, route-change/timing stress, and
unsafe-reference negative controls.

**Rationale**: A small synthetic or offline-only pass is not enough for a
recording promise. The product must prove both signal cleanup and package truth
under conditions that resemble how a physical Mac leaks speaker audio into its
microphone.

**Alternatives considered**:

- Three-file smoke matrix: rejected because it is too weak for immediate
  recording/transcription promotion.
- Production-like real meetings as the first proof: rejected for privacy and
  controllability; consented test signals and synthetic fixtures are safer.

## Decision: Declare Acceptance Thresholds Before Validation

Immediate promotion requires one versioned acceptance-threshold profile declared
before validation begins. The profile covers residual leakage, speech
preservation, double-talk confidence, timing drift, clipping/dropout,
CPU/no-hang behavior, Stop/quit behavior, diagnostics safety, app-status
consistency, and rollback triggers. Changing the profile invalidates affected
promotion evidence until rerun.

**Rationale**: Echo-cancellation evidence is easy to overfit if pass/fail
criteria are adjusted after seeing the corpus. A declared threshold profile
keeps the spike auditable and keeps sliced-window, full-file, and real-hardware
results comparable.

**Alternatives considered**:

- Tune thresholds per file: rejected because it would make favorable rows
  non-comparable and unsafe for product claims.
- Leave thresholds implicit in test code: rejected because reviewers and
  product owners must understand why a candidate was accepted, blocked, or
  rolled back.

## Decision: Limit Promotion Scope To Built-In Mac Mic Plus Built-In Speakers

The only route that `039` may promote or claim is built-in Mac microphone plus
built-in Mac speakers. Bluetooth, AirPods, USB headset, wired-headphone, and
browser-target evidence can support or narrow the decision but cannot broaden
the product claim without a later route-specific feature.

**Rationale**: AEC behavior varies by route topology. A truthful narrow route is
better than a broad clean-recording promise that fails on a different device.

**Alternatives considered**:

- Route-specific promotion for every passing route in `039`: rejected because
  it would multiply validation scope beyond the spike.
- Broad clean speakerphone claim after built-in route success: rejected because
  it overstates evidence.

## Decision: Treat Promotion As Reversible Runtime State

If a promoted candidate later sees route changes, missing or unsafe reference
audio, quality drops, timing uncertainty, incomplete lineage, or unsafe
diagnostics, the app returns package truth to original microphone evidence and
removes the clean-recording claim. The rollback event is metadata-only and
visible in local app status.

**Rationale**: AEC can fail during a recording even if it passed earlier gates.
The safer default is original truth plus a visible problem status, not hidden
continued promotion.

**Alternatives considered**:

- Permanent promotion after validation: rejected because runtime conditions can
  invalidate reference/capture assumptions.
- Never promote in `039`: rejected by product clarification; promotion is
  allowed when the full gate passes.

## Decision: Surface Candidate, Problem, Rollback, And Fallback-Relevant Status In The App

`039` will extend the local recording status surface so candidate evaluation,
blocked quality/topology/stability, rollback, original microphone truth, and
fallback-relevant decisions are visible without exposing private content. Copy
must be calm, route-scoped, and consistent with manifest/package truth.

**Rationale**: A silent fallback is still confusing. Users need to know whether
the app is using original microphone truth, evaluating AEC3, or has rolled back
because a gate became unsafe.

**Alternatives considered**:

- Diagnostics-only status: rejected because the user would not see problems in
  the app.
- Technical debug copy in the main UI: rejected because it is noisy and can
  leak unnecessary implementation detail.

## Decision: License And Packaging Review Blocks Promotion

Before WebRTC can move beyond spike evidence, the feature must record BSD
license notice handling, WebRTC patent grant review, redistribution readiness,
binary/package size, signing/notarization behavior, and release-note
limitations.

**Rationale**: WebRTC's FAQ describes BSD licensing and a separate patent grant.
That is compatible with product use in principle, but this repository still
needs explicit packaging and release evidence before shipping a native
dependency.

**Alternatives considered**:

- Assume WebRTC is safe because it is common: rejected because product release
  evidence must be repo-specific.
- Delay license review until release: rejected because a failed license/package
  gate could invalidate implementation tasks.

## Primary Sources And Local Evidence

- WebRTC AEC3 source:
  <https://webrtc.googlesource.com/src/+/8ba5861f7e654cf5e5683c3ba38cab3eaf6ce8ab/modules/audio_processing/aec3/echo_canceller3.h>
- WebRTC AudioProcessing implementation:
  <https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/audio_processing_impl.cc>
- WebRTC AEC3 module tree:
  <https://webrtc.googlesource.com/src/+/refs/heads/main/modules/audio_processing/aec3/>
- WebRTC FAQ, license, and patent-grant explanation:
  <https://webrtc.googlesource.com/src/+/main/docs/faq.md>
- `specs/020-speaker-to-mic-leakage/speakerphone-go-no-go.md`
- `specs/037-microphone-sample-graph-foundation/spec.md`
- `specs/038-apple-voice-processing-spike/plan.md`
- `specs/038-apple-voice-processing-spike/research.md`
