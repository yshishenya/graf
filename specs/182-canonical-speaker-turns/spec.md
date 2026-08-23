# Feature Specification: Canonical Provider Speaker Turns

**Feature Branch**: `182-canonical-speaker-turns`

**Created**: 2026-08-21

**Status**: Draft

**Input**: User request: "Fix only GRAF's transcription/speaker data contract. Use provider speaker-attributed turns as the canonical temporal model, preserve raw ASR evidence, degrade invalid provider results without guessing, and keep review, timeline, exports, and outcomes in parity. Do not change or deploy MediaScribe."

## User Scenarios & Testing

### User Story 1 - Review Faithful Speaker Turns (Priority: P1)

As a meeting reviewer, I want transcript text split at the actual provider speaker-turn boundaries so that speech by several people inside one ASR segment is not assigned wholesale to one person.

**Why this priority**: The current winner-takes-all assignment changes the meaning of real conversations and can attribute long passages to the wrong participant.

**Independent Test**: Given one ASR segment that spans two or three valid provider-attributed turns, every review surface shows the provider turns in chronological order with their original boundaries, speaker identities, and text; no one winner receives the whole ASR segment.

**Acceptance Scenarios**:

1. **Given** one ASR segment overlaps two valid provider turns, **When** the meeting becomes reviewable, **Then** the canonical transcript contains two ordered turns with the provider boundaries, keys, and turn text.
2. **Given** one ASR segment overlaps three valid provider turns and no single overlap is dominant, **When** the transcript is reviewed, **Then** all three turns remain separate and no overlap winner is called confirmed.
3. **Given** a candidate overlap winner covers less than 50 percent of an ASR segment, **When** attribution state is calculated, **Then** the segment is not confirmed and the product does not use that winner to replace the canonical provider turns.
4. **Given** valid one-speaker, two-speaker, and eleven-label results, **When** they are normalized more than once, **Then** the same ordered canonical turns and stable speaker identities are produced.

### User Story 2 - See Truthful Degraded Provider Results (Priority: P1)

As a reviewer or support operator, I want malformed provider results shown as degraded without hiding provider turns that are still explicit and contract-valid, so that GRAF never turns duplicated, invalid, or contradictory rows into confident participants or repeated transcript text.

**Why this priority**: Silent repair can fabricate speaker identities, triple visible text, or hide a provider defect behind plausible-looking output.

**Independent Test**: Given structurally unsafe provider rows, the review model publishes one content-conserving uncertain ASR representation. Given only a tiny explicit `UNKNOWN` row, it keeps other contract-valid provider turns confirmed and shows that row once as unknown. Both cases publish a bounded degraded reason and metadata-only diagnostics without choosing or deduplicating a supposed correct speaker.

**Acceptance Scenarios**:

1. **Given** the same complete ASR text appears in three provider speaker rows, **When** the result is accepted for review, **Then** its state is `degraded_provider_result`, the text is visible once through unattributed ASR evidence, and no three-speaker output is created.
2. **Given** a provider row has `end <= start`, impossible chronology, or text that cannot be conserved against the ASR evidence, **When** the result is normalized, **Then** canonical attribution is `mixed` or `uncertain`, the defect is explicit, and no winner or guessed correction is applied.
3. **Given** the provider emits `UNKNOWN` for 40 milliseconds, **When** speaker state is built, **Then** the result is degraded, the text is preserved once as "Спикер не определён", other contract-valid turns keep their confirmed speakers, no third confirmed participant is created, and the unknown identity cannot be renamed as an ordinary participant.
4. **Given** a degraded result, **When** review, transcript, timeline, export, or outcome preparation reads it, **Then** every consumer receives the same degraded state and the same content-conserving ordered turns.

### User Story 3 - Keep Speaker Identity Stable (Priority: P1)

As a reviewer who names speakers, I want saved names bound to the actual provider speaker identity so that renumbering or a later render does not move a person's name to another voice.

**Why this priority**: A display label is editable presentation; it must not replace the raw provider identity that anchors attribution.

**Independent Test**: Save names for two provider keys, rebuild and renumber display labels, and confirm each name remains attached to its original provider key while unknown identities remain non-renamable.

**Acceptance Scenarios**:

1. **Given** provider keys are not in display order, **When** GRAF assigns canonical/display labels, **Then** every turn retains the raw provider key separately from its canonical key and display label.
2. **Given** a reviewer saved a display name, **When** the result is rebuilt or labels are renumbered, **Then** the saved name resolves through the stable speaker identity and never through the current ordinal label.
3. **Given** an unknown or synthetic uncertain identity, **When** a rename is requested, **Then** the request is rejected as not an ordinary confirmed participant.

### User Story 4 - Consume One Model Everywhere (Priority: P2)

As a user or downstream GRAF workflow, I want review API, transcript UI, speaker timeline, Markdown/CSV/XLSX/SRT/VTT, and meeting outcomes to consume one canonical temporal model so that format or surface changes do not change the conversation.

**Why this priority**: Independent reconstruction in each consumer recreates the same attribution defect and allows exported or generated data to disagree with what the reviewer saw.

**Independent Test**: Build all listed projections from one synthetic meeting and compare ordered turn boundaries, speaker keys, text, and degraded state across every projection.

**Acceptance Scenarios**:

1. **Given** a valid provider result, **When** each supported consumer builds its output, **Then** all consumers use identical turn boundaries, speaker keys, text, order, and attribution state.
2. **Given** a degraded provider result, **When** each supported consumer builds its output, **Then** all consumers preserve the same canonical projection for that defect class: one uncertain ASR representation for unsafe provider rows, or confirmed valid turns plus explicit unknown turns when only tiny `UNKNOWN` is present.
3. **Given** the same fixture enters through a normal recording and a manual upload, **When** processing completes, **Then** both paths produce equivalent canonical speaker-turn data.
4. **Given** timestamps contain sub-millisecond precision, **When** API, UI, and caption/spreadsheet formats round for presentation, **Then** canonical boundaries remain unchanged and no consumer feeds rounded values back into identity or ordering.

### User Story 5 - Diagnose Without Private Content (Priority: P2)

As a support operator, I want metadata-only result diagnostics so that provider defects and GRAF defects can be distinguished without exposing meeting content.

**Why this priority**: The correction must be operable in production, but diagnostics must not contain transcript text, audio, signed URLs, or private meeting details.

**Independent Test**: Normalize valid and malformed synthetic results and verify the diagnostic record contains only approved identifiers, versions, counts, statuses, and a source-result hash.

**Acceptance Scenarios**:

1. **Given** provider provenance is available, **When** normalization completes, **Then** diagnostics include provider job ID and available result, build, model, and alignment versions.
2. **Given** any result, **When** diagnostics are emitted, **Then** they include raw and accepted turn counts, multi-label conflict count, unknown/tiny count, duplicate-text count, text-conservation status, and source-result hash.
3. **Given** diagnostics are logged, exported, or committed as evidence, **When** forbidden-content checks run, **Then** no raw transcript, provider JSON, audio, signed URL, credential, or meeting content is present.

### Edge Cases

- One ASR segment spans four chronological provider rows from two people.
- A provider turn starts or ends exactly at an ASR boundary.
- Provider turns overlap one another or arrive out of chronological order.
- A provider result has valid timings but repeated full ASR text in several speaker rows.
- An unknown turn has meaningful text but negligible duration.
- A valid speaker key resembles `UNKNOWN` or a display label resembles `SPEAKER_XX`; identity class is determined by the explicit raw key/state, not by a renamed display value.
- One source result contains eleven raw speaker labels in non-numeric order.
- Manual upload and normal recording use different ingest histories but the same accepted provider result shape.
- A stored user name exists for a legacy ordinal label without a preserved provider key; the system must not silently bind it to a different identity.
- Rounding creates equal displayed timestamps for two distinct canonical boundaries; source ordering and canonical values remain authoritative.

## Requirements

### Functional Requirements

- **FR-001**: GRAF MUST own exactly one canonical speaker-attributed temporal model for review API, transcript UI, speaker timeline, Markdown, CSV, XLSX, SRT, VTT, and downstream meeting outcomes.
- **FR-002**: For a contract-valid provider result, provider speaker-attributed turns MUST be the canonical source of turn boundaries, speaker identity, text, and chronological order.
- **FR-003**: Raw `transcript[]` ASR segments MUST remain separately available as unattributed evidence and MUST NOT receive a whole-segment speaker label selected from overlapping provider rows.
- **FR-004**: GRAF MUST NOT use a winner-takes-all overlap match to publish confirmed attribution when an ASR segment spans multiple provider speaker turns.
- **FR-005**: Every canonical turn MUST preserve the raw provider speaker key separately from the stable GRAF speaker key, canonical label, and editable display name.
- **FR-006**: Display/canonical renumbering MUST NOT change the provider-key-to-speaker-identity binding or move a saved user name to another identity.
- **FR-007**: `UNKNOWN` speech MUST retain its text, use the display name "Спикер не определён", remain outside the confirmed participant count, and be ineligible for ordinary participant rename.
- **FR-008**: GRAF MUST treat duplicated complete text across provider speaker rows, non-positive duration, impossible chronology, unknown/tiny identity, and failed text conservation as explicit provider-contract defects.
- **FR-009**: Every provider-contract defect MUST produce `degraded_provider_result` and MUST NOT be silently repaired through overlap winners, inferred speaker selection, or guessed deduplication. Structurally unsafe rows MUST fall back to `mixed` or `uncertain` ASR evidence. A tiny explicit `UNKNOWN` row MUST remain `unknown` without invalidating other contract-valid confirmed turns.
- **FR-010**: When provider speaker rows are unsafe, GRAF MUST preserve content once through unattributed ASR evidence and MUST NOT emit repeated copies from the unsafe attributed rows.
- **FR-011**: Text conservation MUST compare normalized provider-attributed text with the unattributed ASR evidence and publish a bounded status without storing private text in diagnostics.
- **FR-012**: Review, timeline, exports, and outcomes MUST expose identical canonical turn boundaries, speaker keys, text order, and degraded state for the same selected result.
- **FR-013**: Normal recording and manual upload paths MUST converge on the same result validation and canonicalization behavior after import.
- **FR-014**: Canonical time values MUST retain source precision; presentation rounding MUST NOT alter turn boundaries, identity, ordering, or later projections.
- **FR-015**: Talk-time MUST use valid accepted canonical speech duration, including explicit unknown speech, as its denominator and MUST be labelled "Доля распознанной речи" rather than recording share.
- **FR-016**: Confirmed participant count MUST include only distinct confirmed stable speaker identities and MUST exclude unknown, mixed, uncertain, or rejected identities.
- **FR-017**: GRAF MUST produce metadata-only diagnostics containing provider job ID; available result/build/model/alignment versions; raw and accepted turn counts; multi-label conflict count; unknown/tiny count; duplicate-text count; text-conservation status; and source-result hash.
- **FR-018**: Diagnostics, test fixtures, and committed evidence MUST exclude private audio, raw transcript, raw provider JSON, signed URLs, credentials, and meeting content.
- **FR-019**: Provider defect state and GRAF normalization defect state MUST remain distinguishable in diagnostics and validation reports.
- **FR-020**: Existing compatible one-speaker and multi-speaker records MUST remain readable, and legacy saved names MUST either resolve through a proven stable identity or remain explicitly unresolved rather than being rebound by guesswork.
- **FR-021**: The feature MUST change only GRAF; MediaScribe code, configuration, runtime, deployment, and result generation are out of scope.
- **FR-022**: Canonicalization MUST be deterministic and idempotent for the same selected source result.

### Key Entities

- **Raw ASR Segment**: Unattributed evidence containing source timing and text; never overwritten with a selected speaker winner.
- **Provider Speaker Turn**: Provider-attributed row containing raw provider speaker key, start/end, text, and available provenance.
- **Canonical Speaker Turn**: GRAF-owned ordered turn with preserved source timing/text, stable speaker identity, raw provider key, display state, and degraded state.
- **Speaker Identity**: Stable meeting-local identity anchored by provider key and result provenance, distinct from canonical ordinal label and editable display name.
- **Unknown Identity**: Non-confirmed identity for preserved speech that cannot be assigned to an ordinary participant.
- **Provider Result Validation**: Deterministic metadata-only outcome describing whether attributed rows are accepted or degraded and why.
- **Attribution Diagnostics**: Content-free counts, versions, statuses, and source-result hash used to distinguish provider and GRAF defects.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Synthetic two-turn and three-turn overlap fixtures preserve 100 percent of valid provider turns with no whole-ASR winner assignment.
- **SC-002**: A winner below 50 percent overlap is never reported as confirmed in any consumer.
- **SC-003**: A 40-millisecond unknown turn creates zero additional confirmed participants, remains visible once as "Спикер не определён", and does not hide or relabel other contract-valid confirmed turns.
- **SC-004**: A fixture containing the same full ASR text in three provider rows yields one visible uncertain text copy and `degraded_provider_result` in every consumer.
- **SC-005**: Stable one-speaker, two-speaker, and eleven-label fixtures produce deterministic canonical turns and speaker identities across repeated normalization.
- **SC-006**: Normal recording and manual upload fixtures with equivalent source results produce semantically identical canonical models.
- **SC-007**: Review API, transcript UI model, speaker timeline, Markdown, CSV, XLSX, SRT, VTT, and outcomes match exactly on ordered boundaries, speaker keys, text, and degraded state for every parity fixture.
- **SC-008**: Saved speaker names remain bound to the same provider identity across renumbering and rebuild; zero names move to another identity.
- **SC-009**: Timestamp/duration rendering at every supported precision leaves canonical boundaries byte-stable after normalization.
- **SC-010**: The metadata-only diagnostic schema contains every required field and contains zero forbidden content in committed evidence and logs.
- **SC-011**: Synthetic replicas of both supplied production defect classes fail before the change and pass after it without storing private production content.
- **SC-012**: MediaScribe repository/runtime/configuration changes and deployments remain zero for this feature.

## Assumptions

- The existing provider response already contains speaker-attributed turn text and boundaries when the result is contract-valid.
- `transcript[]` is retained as ASR evidence and is an appropriate single-copy fallback for unsafe attributed rows.
- Text conservation may normalize only representation differences that do not change words; it must not infer which duplicated provider row is correct.
- Talk-time describes the distribution of accepted recognized speech, not share of full recording duration; full-recording occupancy is a different future metric.
- This slice requires no database migration unless code inspection proves stable raw provider keys are not currently retained anywhere suitable.
- Production meeting identifiers and job identifiers may be used only for read-only metadata verification and must not be copied into committed fixture content.

## Out of Scope

- Any MediaScribe implementation, configuration, model, alignment, or deployment change.
- Re-diarization, speaker embedding, voice recognition, calendar/contact name inference, or heuristics for selecting a "correct" speaker.
- Editing or deleting raw ASR evidence or raw provider result rows.
- Production deployment, release preparation, commit, PR, or migration execution without separate user approval.
- Committing private audio, transcript text, provider JSON, signed URLs, credentials, meeting content, or real production fixtures.
