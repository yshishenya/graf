# Research: Local Recording Persistence

## Decision: App-owned writer outside realtime callbacks

**Rationale**: The constitution and realtime safety gate prohibit file IO or
blocking work in Core Audio callbacks. The existing driver/app shared memory
surface already exposes mic frames and mirrored virtual speaker capture frames,
so a non-realtime app writer can poll those rings and persist files safely.

**Alternatives considered**:

- Write directly in HAL callback: rejected because file IO in callbacks risks
  `coreaudiod` hangs and violates realtime safety.
- Add backend upload first: rejected because the user is asking for local file
  presence and upload/transcription are explicitly out of scope.
- Record only mixed audio: rejected because the MVP promise requires separate
  local mic and remote speaker tracks.

## Decision: Separate local track files plus manifest

**Rationale**: Separate artifacts preserve diarization and track integrity for
future upload/transcription while giving the user a concrete local recording
location now. A manifest gives QA and future lifecycle work a metadata-only
source of truth.

**Alternatives considered**:

- Single mixed recording: rejected because it weakens the product promise.
- Manifest only: rejected because it does not answer "where is the recording?"
- UI-only saved state: rejected because it would repeat the `007` product gap.

## Decision: Development-local LPCM/WAV-compatible track artifacts

**Rationale**: The first persistence slice needs inspectable, deterministic
local files with simple duration and byte-count validation. A local PCM/WAV
style artifact fits short smoke validation and avoids encoder complexity.

**Alternatives considered**:

- Compressed M4A: deferred because encoder/finalization errors add scope.
- Proprietary buffer format only: rejected because QA needs simple local
  inspection.

## Decision: Missing required tracks degrade, not pass

**Rationale**: A recording without either local mic or remote speaker is not a
complete meeting capture. The app must show a truthful degraded/failed state and
record the track-level reason.

**Alternatives considered**:

- Accept mic-only recording: rejected for MVP acceptance because remote speaker
  capture is a core requirement.
- Block start unless speaker frames are already present: rejected because remote
  speaker frames may not appear until a meeting participant speaks.

## Decision: Safe evidence uses basenames and generated ids

**Rationale**: Diagnostics should prove artifacts exist without exposing user
home paths, meeting content, transcript text, secrets, or raw audio.

**Alternatives considered**:

- Include absolute paths in diagnostics: rejected because user names and local
  folder structures can leak.
- Hash audio content for proof: deferred because it still touches content and is
  unnecessary for this slice.
