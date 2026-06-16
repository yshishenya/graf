# Research: Meeting-App Mute Truth

## Decision: Canonical MVP Truth Is Product-Owned Pause/Stop

`2brain Pause` and `2brain Stop` are the MVP source of privacy truth. The
product does not claim that third-party meeting-app mute is respected unless a
future target-specific adapter provides fresh metadata-only evidence.

Rationale:

- Third-party meeting apps and browsers do not expose one portable mute signal.
- A native product control is observable, testable, and can be represented in
  local artifact metadata.
- This preserves user trust without blocking the MVP on brittle app-specific
  integrations.

Alternatives considered:

- App-specific mute APIs: deferred because target coverage and evidence would
  be uneven and brittle.
- OS input mute or device volume state: rejected as a proxy for meeting-app mute
  because it does not prove in-app mute intent.
- Blocking all recordings on unsupported targets: rejected for MVP because the
  safer product claim is "unproven/degraded", not "no recording possible".

## Decision: Pause Writes Silence/Redaction Instead Of Dropping Timeline

When `2brain Pause` is active during a recording, the local microphone path must
not write live speech as ordinary mic audio. The implementation should preserve
timeline continuity by writing silence or equivalent redacted samples and
recording a metadata-only privacy segment.

Rationale:

- Silence/redaction protects local speech while preserving alignment with
  incoming/system audio.
- Dropping mic samples would risk duration mismatch and downstream confusion.
- A segment record makes the artifact truth auditable without storing content.

Alternatives considered:

- Stop microphone capture entirely: risks track duration mismatch and more
  complex restart failure states.
- Keep recording mic audio but mark the artifact degraded: insufficient for a
  product-owned privacy control.
- Omit local mic intervals from the file: harder to validate against current
  dual-track manifest expectations.

## Decision: Meeting-App Mute Is Unproven Unless Adapter Evidence Exists

For the first MVP matrix, Zoom native, Chrome/Telemost, and Opera/Telemost are
validated for product-owned Pause/Stop and limitation copy only. Yandex Browser
and generic/unknown targets are unsupported or deferred for direct
meeting-app-mute truth.

Rationale:

- This matches the clarified scope and prevents hidden overclaiming.
- The QA matrix can still validate visible behavior across real meeting
  surfaces.
- Future adapters can be added without changing the user-facing truth model.

Alternatives considered:

- Treat target names as supported for meeting-app mute by default: rejected
  because target presence is not mute evidence.
- Accept browser mute inference from audio samples: rejected because absence of
  audio can mean silence, routing failure, device mute, or user not speaking.

## Decision: Manifest Extension Is Local And Backward-Compatible

Add optional local manifest fields for mute truth and privacy segments instead
of changing server upload contracts in this slice.

Rationale:

- Existing local artifacts already carry manifest status, tracks, permissions,
  scope approval, capture health, and failure reasons.
- Optional metadata keeps older readers tolerant while allowing local
  validation to prove the feature.
- Server/web surfaces can later render this metadata without forcing server
  behavior into this slice.

Alternatives considered:

- New standalone evidence file only: useful for diagnostics but weaker as the
  canonical artifact truth source.
- Server-side state: explicitly out of scope and would add egress/lifecycle
  work not needed for the MVP local gate.

## Decision: Limitation Copy Is Always Visible For Unproven Meeting-App Mute

When meeting-app mute truth is unavailable, stale, contradictory, or
unsupported, the desktop app must show:

```text
2brain cannot verify mute inside this meeting app. Use Pause or Stop in 2brain to keep local speech out of the recording.
```

Rationale:

- The user needs the warning before relying on meeting-app mute.
- The copy points to the actionable local privacy control.
- The wording avoids promising universal third-party mute detection.

Alternatives considered:

- Hide limitation copy in diagnostics only: rejected because the risk is
  user-facing.
- Use stronger "not safe" copy for all targets: rejected as unnecessarily
  alarming when `2brain Pause` provides a verified control.

## Decision: Diagnostics Stay Metadata-Only

Mute-truth diagnostics may include states, timestamps, target IDs, target
families, evidence freshness, segment durations, and decisions. They must not
include raw audio, transcript text, meeting content, credentials, tokens, signed
URLs, passwords, or live secret paths.

Rationale:

- The constitution requires metadata-only diagnostics by default.
- The feature is privacy-sensitive; evidence must not recreate the data it is
  trying to protect.

Alternatives considered:

- Store waveform snippets to prove silence: rejected as raw audio content.
- Store transcript snippets around pause: rejected as meeting content.
