# Contract: Playback Review

## Purpose

Define how meeting review exposes retained-audio playback and transcript
timestamp seek while preserving access, retention, deletion, and evidence
boundaries.

## Review Response

Meeting detail review includes a `playback` object.

Required fields:

- `available`: whether the current viewer can play retained meeting audio.
- `duration_seconds`: non-negative duration for the retained review audio.
- `speed_options`: safe list of allowed playback speeds.
- `unavailable_reason`: safe reason when playback is unavailable.
- `playback_path`: server-owned relative path when playback is available.
- `policy_label`: short user-facing label for the current playback state.
- `source_mode`: safe label for the review audio source mode.
- `included_sources`: safe source labels represented by the review audio stream.

Rules:

- `playback_path` must be absent when `available` is false.
- `playback_path` must be relative to 2brain Rec and must not be an object
  storage URL or signed URL.
- Dual-track review responses must not silently expose only microphone or only
  incoming/system audio as if it were full meeting audio.
- The review response may include transcript text only on authorized detail
  routes that already expose transcript content. List/status responses must not
  receive transcript text because of playback.
- The review response must not include object keys, checksums, signed URLs,
  credentials, private local paths, or provider payloads.

## Playback Route

When playback is available, the review UI may request the server-owned playback
path.

Allowed behavior:

- verify viewer access for the meeting;
- verify meeting is not deleted, deleting, audio-purged, transcript-only, or
  policy-blocked;
- verify retained audio artifacts required for the review stream exist;
- return a server-mediated review stream that represents both microphone and
  incoming/system sources for normal dual-track meetings;
- record metadata-only audit for allowed and denied playback requests.

Denied behavior:

- unauthorized viewer: no existence proof beyond the existing cabinet access
  behavior;
- deleted/deleting/audio-purged/transcript-only/policy-blocked/no-audio:
  return a safe unavailable or blocked response;
- review audio cannot be safely built or retrieved: return a safe unavailable
  response;
- storage unavailable: return a retryable unavailable response.

## Transcript Seek Targets

Transcript segment views include seek metadata.

Required behavior:

- valid segment start times become seek targets when playback is available;
- invalid or out-of-range segment times remain visible as transcript rows but
  are not active seek controls;
- timestamp controls must support pointer and keyboard activation;
- activation sets playback position to the segment start time.

## Web And Desktop Parity

The web cabinet and desktop embedded cabinet must use the same review response.

Required behavior:

- playback availability matches for the same meeting and viewer;
- unavailable reasons match for the same meeting and viewer;
- timestamp seek controls match for the same transcript segments;
- desktop embedded review must not add native capture controls inside the web
  review surface.

## Evidence Rules

Allowed evidence:

- playback available/unavailable state;
- safe unavailable reason;
- duration;
- selected segment sequence;
- target seek seconds;
- observed current time after seek;
- viewport class;
- pass/fail counts.

Forbidden evidence:

- raw audio;
- transcript text from private meetings;
- object keys;
- signed URLs;
- credentials or tokens;
- private local paths;
- private meeting titles or account identifiers.
