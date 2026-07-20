# Feature Specification: Canonical Speaker Turns for Transcript Review

**Feature Branch**: `113-transcript-speaker-turns`
**Created**: 2026-07-20
**Status**: Draft
**Input**: User description: "Объединить последовательные фрагменты одного спикера в транскрибации, выбрать правильный этап для объединения и сохранить работоспособность системы при смене облачного сервиса транскрибации."

## User Scenarios & Testing

### User Story 1 - Review Continuous Speaker Turns (Priority: P1)

As a meeting participant reviewing a transcript, I want consecutive fragments from the same speaker to appear as one continuous turn so that the transcript is readable and does not look artificially fragmented.

**Why this priority**: Fragmented rows make an otherwise correct transcript difficult to read and obscure the conversation flow.

**Independent Test**: Given adjacent transcript segments with the same canonical speaker and a short pause, a transcript review response contains one speaker turn with combined text and the complete time range.

**Acceptance Scenarios**:

1. **Given** two or more adjacent segments belong to the same diarization run and canonical speaker, **When** the transcript review model is built, **Then** they are represented by one speaker turn when the gap between each pair is at most 1 second.
2. **Given** segments are merged into one speaker turn, **When** the turn is displayed or selected for playback, **Then** its start is the first segment start, its end is the last segment end, and text order follows source time order.
3. **Given** a same-speaker gap is greater than 1 second, **When** the review model is built, **Then** a new speaker turn starts after the gap.

### User Story 2 - Keep One Provider-Agnostic Transcript Contract (Priority: P1)

As an operator who may replace the cloud transcription provider, I want GRAF to own the canonical transcript shape so that clients and downstream features do not depend on MediaScribe-specific segmentation behavior.

**Why this priority**: A provider change must not require a client rewrite or make previously stored transcripts unreadable.

**Independent Test**: Given equivalent raw transcript segments from two provider adapters, the server produces the same canonical turn rules and exposes the raw segments plus derived speaker turns without provider-specific fields.

**Acceptance Scenarios**:

1. **Given** raw segments have been imported from any supported provider, **When** the canonical transcript contract is returned, **Then** it includes raw segment fidelity and a derived `speaker_turns` representation based on canonical speaker labels and timestamps.
2. **Given** a provider changes its native segment boundaries, **When** the same words, speaker labels, and timestamps are supplied, **Then** the canonical turn output remains governed by GRAF rules rather than provider-specific UI behavior.
3. **Given** a client only understands the existing raw segment contract, **When** `speaker_turns` is added, **Then** raw segments remain available and existing consumers can continue to operate.

### User Story 3 - Preserve Safe Boundaries and Recovery (Priority: P2)

As a support or QA operator, I want speaker-turn derivation to be deterministic and non-destructive so that retries, partial results, and unusual diarization output cannot silently change source transcript data.

**Why this priority**: Transcript data is meeting content; a readability transformation must not overwrite evidence or join unrelated speech.

**Independent Test**: A fixture set covering speaker changes, long pauses, missing labels, overlaps, empty text, and repeated processing produces stable derived turns while raw segments remain unchanged.

**Acceptance Scenarios**:

1. **Given** adjacent segments have different canonical speakers, **When** turns are derived, **Then** they remain separate regardless of the gap.
2. **Given** segments belong to different diarization runs, processing results, or source tracks, **When** turns are derived, **Then** they are never merged across that boundary.
3. **Given** a segment has no usable speaker label, empty text, invalid timestamps, or overlapping timestamps, **When** turns are derived, **Then** the raw segment is retained, no unsafe cross-boundary merge occurs, and the result is marked for review without exposing raw content in diagnostics.
4. **Given** the same raw result is processed more than once, **When** the canonical transcript is rebuilt, **Then** the derived turns are identical and no duplicate turns are created.

### Edge Cases

- A same-speaker sequence has a gap exactly at the 1-second threshold; it follows the inclusive threshold defined in the requirements.
- A sequence has multiple short gaps; every pair must satisfy the threshold for the sequence to remain one turn.
- Text is empty or whitespace-only; timing and raw segment identity are retained, but the segment does not create visible text content by itself.
- Segments overlap in time; source order and boundaries remain deterministic, and overlapping segments are not silently reordered or discarded.
- A provider has no diarization label; the canonical contract preserves the segment and does not invent a speaker identity.
- Legacy stored transcripts have no derived turns; turns can be rebuilt from raw segments without requiring a provider re-run.
- The source transcript is unavailable or processing is incomplete; no derived turn is published as final.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST derive a canonical `speaker_turns` representation after speaker labels and timestamps are available and before transcript review consumers read the data.
- **FR-002**: GRAF MUST merge adjacent raw segments only when they share the same canonical speaker, selected processing result/diarization run, and source track, and every pairwise gap in the sequence is at most 1 second.
- **FR-003**: GRAF MUST preserve raw transcript segments, their source order, timestamps, text, and provider provenance independently of the derived turns.
- **FR-004**: Each derived speaker turn MUST expose a stable identity, canonical speaker label, first-segment start, last-segment end, ordered combined text, and source segment references.
- **FR-005**: GRAF MUST split turns at a speaker, processing-result/run, track, or gap boundary and MUST NOT merge across those boundaries.
- **FR-006**: GRAF MUST make turn derivation deterministic and idempotent for the same raw transcript input.
- **FR-007**: GRAF MUST expose derived turns through the server-owned canonical transcript contract; clients MUST NOT need direct access to MediaScribe or another transcription provider to construct turns.
- **FR-008**: GRAF MUST treat raw segments as the source of truth and MUST be able to rebuild derived turns for legacy transcripts without re-transcribing audio.
- **FR-009**: GRAF MUST retain raw segments with invalid or incomplete metadata and avoid unsafe merges; any diagnostics remain metadata-only.
- **FR-010**: GRAF MUST keep the canonical turn contract provider-neutral so replacing the transcription provider does not require a change to client-facing turn semantics.
- **FR-011**: GRAF MUST NOT publish derived turns as final while the source transcript is incomplete or the diarization result is not terminal.
- **FR-012**: The transcript review experience MUST use derived speaker turns for readable display while retaining a path to the underlying raw segments for precise timing and playback.

### Key Entities

- **Raw Transcript Segment**: Immutable or append-only source unit with text, start/end timestamps, canonical speaker label when available, diarization run, session, source track, provider provenance, and processing state.
- **Speaker Turn**: Derived readable unit containing a stable identity, canonical speaker label, time range, ordered text, and references to its raw segments.
- **Canonical Transcript Contract**: GRAF-owned representation that exposes raw segments and derived speaker turns without requiring provider-specific client logic.
- **Diarization Run**: A bounded labeling result whose identity prevents merges across retries or incompatible processing versions.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In a representative fixture set, every same-speaker sequence whose pairwise gaps are at most 1 second is rendered as one turn, with no cross-speaker or cross-run merges.
- **SC-002**: 100% of raw input segments remain recoverable after turn derivation, including segments that are not eligible for merging.
- **SC-003**: Rebuilding turns twice from identical raw input produces byte-for-byte equivalent canonical turn data and no duplicate records.
- **SC-004**: Existing raw-segment consumers continue to pass their compatibility checks when derived turns are present.
- **SC-005**: A provider-adapter fixture with equivalent canonical inputs produces identical `speaker_turns` output regardless of the upstream provider name.
- **SC-006**: Transcript review shows one readable row per derived turn for the target fragmented-speaker scenario while playback timing still covers the full source interval.

## Assumptions

- The canonical speaker label and timestamps are available after the existing diarization/import stage; this feature does not change speech recognition or diarization quality.
- A 1-second inclusive gap is the initial product rule because it removes observed micro-fragmentation without joining clearly separate utterances; the rule remains a single server-side policy point for later tuning.
- The server remains the only component that owns provider credentials and provider-specific adaptation; desktop clients and browser clients consume GRAF-owned data.
- Raw transcript rows already have lifecycle and deletion accounting; derived turns participate in the same meeting lifecycle and are deleted with the meeting.
- The MinIO playback-source access issue is a separate merged hotfix and is not part of this feature.

## Out of Scope

- Re-training, replacing, or tuning the diarization model.
- Sending audio directly from a client to MediaScribe or any future provider.
- Rewriting raw transcript text or deleting raw segment rows after turn derivation.
- New transcript search, export, summary, or translation features beyond consuming the canonical turn representation.
