# Phase 0 Research: Canonical Speaker Turns

## Decision 1: Derive turns in the server-owned review model

- **Decision**: Build derived speaker turns on the server after transcript rows
  have been matched to diarization labels and before the review response is
  rendered or returned.
- **Rationale**: The server already owns provider credentials, result import,
  access control, playback timing, and the `TranscriptReviewState`. One
  server-side rule prevents the browser, macOS client, and each future provider
  adapter from implementing different merge behavior.
- **Alternatives considered**:
  - **Client/UI merge**: rejected because every client would need the same
    timing and boundary rules and a provider switch would become a client
    change.
  - **MediaScribe merge**: rejected because it couples the product contract to
    one provider and cannot rebuild turns for already stored transcripts.

## Decision 2: Keep raw segments and add a derived read field

- **Decision**: Keep the existing raw `transcript.segments` field unchanged and
  add `transcript.speaker_turns` as a derived, read-oriented field. The server
  rendered review uses `speaker_turns` when available; raw segments remain
  available for precise timing, playback, compatibility, and rebuilds.
- **Rationale**: No destructive rewrite or migration is needed. Existing raw
  segment consumers continue to work while the readability surface gains a
  stable contract.
- **Alternatives considered**:
  - Replace `segments` with merged rows: rejected because it would discard
    source-row identity and risk breaking existing consumers.
  - Add a new persisted table: rejected for this slice because turns are
    deterministic from existing rows and would add lifecycle/deletion work
    without user value.

## Decision 3: Use the existing processing result and source role as boundaries

- **Decision**: A turn derivation call processes one selected `ProcessingResult`
  at a time and never merges across its source role/track. The selected result
  is the current bounded diarization run for the review response.
- **Rationale**: Queries already select one latest result and the stored rows
  carry `processing_result_id` and `source_role`. This prevents cross-retry and
  cross-track joins without inventing a new run/session schema.
- **Alternatives considered**:
  - Add a new diarization-run table or migration: rejected until the product
    has more than one compatible run in a single review result.
  - Merge by wall-clock adjacency across all meeting rows: rejected because it
    can join incompatible retries or source tracks.

## Decision 4: Apply one inclusive one-second pairwise gap rule

- **Decision**: Merge a sequence only when each adjacent pair has the same
  canonical speaker and source role and a gap from 0 through 1.000 seconds
  inclusive. Join non-empty text fragments with one space in source order.
- **Rationale**: The observed fragmentation has sub-second pauses; one second
  removes that artificial fragmentation while leaving a clear pause as a
  boundary. A single decimal comparison is deterministic and easy to tune in
  one place.
- **Alternatives considered**:
  - Merge every same-speaker row regardless of pause: rejected because it hides
    meaningful silence and produces long unreadable turns.
  - Use a provider-specific threshold: rejected because it makes provider
    replacement change the product contract.

## Decision 5: Do not invent a mergeable speaker identity

- **Decision**: A row with no confirmed speaker mapping remains in raw segments
  and is not merged into a derived turn based only on the display fallback.
  Invalid timing or empty text never causes a cross-boundary merge.
- **Rationale**: A display fallback such as `SPEAKER_00` is not evidence that
  two rows came from the same person. Preserving the row is safer than silently
  changing attribution.
- **Alternatives considered**:
  - Treat all unlabeled rows as one speaker: rejected because it fabricates
    diarization evidence.
  - Drop malformed rows: rejected because raw transcript fidelity and audit
    recovery are required.

## Decision 6: No provider or storage changes

- **Decision**: Do not add a MediaScribe call, new runtime dependency, database
  table, migration, or client credential path. The existing server import and
  review pipeline remains the integration seam.
- **Rationale**: The requested behavior is a deterministic presentation model;
  the smallest safe change is in the existing server schema/view-model/render
  path.
- **Alternatives considered**: Provider-specific post-processing, persisted
  turn backfill, and a new service were all rejected as unnecessary for the
  current bounded MVP slice.
