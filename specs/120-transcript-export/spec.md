# Feature Specification: Canonical Transcript And Summary Export

**Feature Branch**: `120-transcript-export`

**Created**: 2026-07-21

**Status**: Implementation merged; representative pre-release study pending

**Input**: User request: "Сформировать полноценную функцию экспорта транскрипта и саммари. Поддержать TXT, хорошо сверстанный MD, CSV, XLSX, JSON и SRT; PDF и DOCX пока не делать. Продумать, как хранить и обрабатывать экспорт, а также UI, UX, IA, permissions, lifecycle, provider-neutral contract, best practices and analogous products."

## Clarifications

### Session 2026-07-22

- Q: How should the export dialog balance everyday choices with revision and lifecycle truth? → A: Keep scope, format, concise outcome, and the primary action visible; move revision and lifecycle metadata into collapsed technical details.
- Q: Where should an export from the embedded macOS client be saved? → A: Open the native macOS Save dialog with the server-suggested filename and let the reviewer choose name and location; cancellation leaves the meeting unchanged and is not an export failure.
- Q: What should change after the first compact-dialog review still felt too technical? → A: Show only two ordinary controls by default — `Что сохранить` and `Формат` — plus `Отмена` and `Сохранить`. Keep optional presentation settings and copy under `Дополнительно`; remove revision ids, readiness metadata, duration, language, lifecycle jargon, format cards, and the separate outcome summary from the user-facing dialog.

## Product Decision Summary

GRAF owns one provider-neutral, revision-pinned export snapshot. Every file
format is a projection of that snapshot; no formatter reads provider responses
directly and no formatter invents transcript content.

The source model remains immutable raw transcript segments plus derived
canonical speaker turns. A human-readable projection may group only short,
same-speaker display runs, but every canonical turn keeps its own timestamps.
Long silences remain gaps in time, not synthetic `Пауза` rows or text.

Transcript and summary are separate user-facing artifacts with separate
availability, policy, revision, and deletion truth. A combined export is
allowed only in formats that can represent both artifacts without ambiguity.

## User Scenarios & Testing

### User Story 1 - Download a Readable Transcript (Priority: P1)

As a meeting reviewer, I want to download a clean transcript with speaker
labels and timestamps so that I can read, send, and archive it outside GRAF
without seeing artificial fragmentation or technical provider data.

**Why this priority**: The current download is based on raw segments and does
not match the readable canonical transcript shown in the meeting review.

**Independent Test**: Open a ready meeting containing short same-speaker
fragments, speaker changes, long gaps, unknown attribution, and a renamed
speaker; download TXT and MD and confirm that the readable output is complete,
seekable by timestamp, deterministic, and contains no pause text.

**Acceptance Scenarios**:

1. **Given** adjacent segments have the same confirmed speaker, source, and
   result with a gap within the canonical merge rule, **When** the reviewer
   downloads TXT or MD, **Then** the output shows one readable display group
   containing separate timestamped child turns.
2. **Given** the same speaker resumes after a long gap, **When** the reviewer
   downloads the transcript, **Then** a new display block starts with the same
   speaker label and the time jump remains visible; no `Пауза` line is added.
3. **Given** the speaker changes from A to B and back to A, **When** the
   transcript is exported, **Then** the output contains three ordered speaker
   blocks and never implies one continuous A turn.
4. **Given** a manual speaker name is saved for the meeting, **When** the
   transcript is exported, **Then** human-readable formats use that display
   name while preserving the underlying canonical speaker identity internally.
5. **Given** a segment has unknown or unconfirmed attribution, **When** the
   transcript is exported, **Then** it is shown as an explicit unknown or
   unconfirmed speaker and is not silently relabeled as a confirmed speaker.

### User Story 2 - Export Structured Transcript Data (Priority: P1)

As an operator or integration developer, I want structured transcript data so
that I can process, migrate, analyze, or re-render a transcript without
depending on MediaScribe or a particular upstream segmentation policy.

**Why this priority**: GRAF must remain usable if the transcription provider
changes, and spreadsheets and automation need one row/object per canonical
turn rather than presentation-only grouping.

**Independent Test**: Export the same selected transcript revision as CSV,
XLSX, and JSON, then compare order, text, start/end timing, speaker state,
source boundaries, and revision metadata against the canonical snapshot.

**Acceptance Scenarios**:

1. **Given** a final transcript revision is selected, **When** CSV or XLSX is
   downloaded, **Then** each canonical turn is represented as one row with
   stable sequence, start/end time, display label, speaker state, text, and
   source-boundary information.
2. **Given** JSON is downloaded, **When** the file is inspected, **Then** it
   contains a versioned envelope, selected result revision, canonical turns,
   source segment references, speaker attribution state, summary references
   where available, and no credentials, signed URLs, or provider job secrets.
3. **Given** the same result revision is exported twice, **When** the content
   is compared after excluding delivery metadata, **Then** the canonical
   payload is byte-stable and has the same ordering and schema version.
4. **Given** a future provider adapter maps its payload into equivalent
   GRAF-owned canonical inputs, **When** the data is exported, **Then** the
   normalized projections remain semantically equivalent; lossless JSON still
   records that provider result's actual raw boundaries and source-derived ids.

### User Story 3 - Export Captions Without Fabricated Speech (Priority: P1)

As a reviewer who wants to reuse a recording in a video editor or player, I
want SRT subtitles with accurate timing and speaker labels so that silence is
preserved as empty time rather than shown as spoken text.

**Why this priority**: SRT is a selected product format and must not turn the
transcript readability fix into inaccurate caption timing.

**Independent Test**: Export SRT from a transcript with speaker changes,
overlaps, short gaps, and long gaps; load it into a subtitle-capable player and
verify cue order, millisecond timing, speaker labels, and absence of pause
text.

**Acceptance Scenarios**:

1. **Given** a canonical turn has a valid start and end, **When** SRT is
   generated, **Then** exactly one cue is emitted for that turn with the
   selected speaker label and millisecond timestamps.
2. **Given** there is silence between two turns, **When** SRT is generated,
   **Then** no synthetic cue is emitted for the gap.
3. **Given** turns overlap, **When** SRT is generated, **Then** the source
   overlap is preserved or surfaced as a bounded format limitation; the
   exporter does not silently shift speech into false time.
4. **Given** transcript attribution is unknown, **When** SRT is generated,
   **Then** the cue uses an explicit unknown label and does not fabricate a
   confirmed speaker identity.

### User Story 4 - Export the Meeting Summary (Priority: P1)

As a meeting owner or reviewer, I want to export the current summary, key
points, decisions, action items, follow-ups, risks, questions, and timestamped
evidence so that the useful result of a meeting can be shared without sending
the full transcript.

**Why this priority**: Summary is a separate product artifact with a different
reading job and different privacy/egress needs from the full transcript.

**Independent Test**: Open a meeting with a stored summary containing several
sections and action items; export summary-only and combined MD, TXT, XLSX, and
JSON outputs; verify section order, item text, owner/due-date truth,
transcript references, revision status, and policy behavior.

**Acceptance Scenarios**:

1. **Given** a current stored summary is available, **When** summary-only MD
   is downloaded, **Then** the file contains a clear header, readable section
   hierarchy, action-item list, and timestamped evidence links or labels where
   the source supports them.
2. **Given** the summary is unavailable, failed, deferred, or reported as
   available without stored content, **When** the reviewer opens export, **Then**
   summary formats are disabled with a truthful reason and transcript export
   remains independently available when permitted.
3. **Given** a summary has been manually edited or regenerated, **When** it is
   exported, **Then** the current saved revision is exported and the source
   transcript/result revision is recorded in structured metadata.
4. **Given** an action owner or due date cannot be inferred safely, **When**
   the summary is exported, **Then** the field is left unknown rather than
   invented.

### User Story 5 - Choose a Format Without Losing Control (Priority: P2)

As a meeting reviewer, I want a clear export surface that explains which
artifact and format I am choosing, so that I do not accidentally download a
technical file, export unavailable content, or expose data beyond my access.

**Why this priority**: Multiple formats are useful only when the information
architecture keeps the choice understandable and policy states visible.

**Independent Test**: Exercise the export control as owner, permitted viewer,
view-only shared user, denied user, and a user viewing a processing/partial or
deleted meeting; confirm available options, disabled reasons, focus behavior,
and safe errors.

**Acceptance Scenarios**:

1. **Given** the reviewer is authorized and the artifact is ready, **When**
   they open `Экспорт`, **Then** the UI groups formats by job: reading (TXT,
   MD), tables (CSV, XLSX), integration (JSON), and captions (SRT).
2. **Given** a format cannot represent the selected artifact combination,
   **When** the reviewer chooses that combination, **Then** the option is
   disabled with a plain-language reason instead of silently producing a
   partial file.
3. **Given** a file is generated, **When** the browser or embedded macOS client
   receives it, **Then** the filename, media type, byte length, and displayed
   revision/status agree with the selected artifact and format, and the
   embedded client keeps the reviewer on the meeting detail.
4. **Given** generation fails transiently, **When** the reviewer retries,
   **Then** the original meeting content and policy state remain unchanged and
   the error does not reveal storage keys, provider URLs, or private content.
5. **Given** the reviewer opens export in the embedded macOS client, **When**
   the generated file is ready, **Then** GRAF opens the native Save dialog with
   the suggested filename and matching extension so the reviewer can choose
   the destination or cancel without treating cancellation as a failure.
6. **Given** the export dialog opens at an embedded or browser width, **When**
   no advanced details are expanded, **Then** the reviewer sees only what to
   save, the compatible format, cancel, and the primary save action without
   revision ids, lifecycle jargon, or a diagnostic preview.

### User Story 6 - Preserve Lifecycle And Provider-Neutral Truth (Priority: P2)

As a workspace owner, I want exports to remain auditable, revision-pinned, and
covered by deletion and egress policy so that a downloaded file does not create
an untracked copy inside GRAF or a false promise of universal deletion.

**Why this priority**: Transcript and summary exports are meeting-content
egress and must follow the same trust boundary as audio and existing downloads.

**Independent Test**: Export from two processing revisions, delete or expire a
meeting, and inspect metadata-only activity and lifecycle state without storing
transcript content in evidence or audit logs.

**Acceptance Scenarios**:

1. **Given** a selected result is reprocessed after an export request, **When**
   the export completes, **Then** it remains pinned to the requested result and
   does not mix old transcript turns with new summary output.
2. **Given** an export is allowed, **When** it completes, **Then** a
   metadata-only event records artifact kind, format, revision, outcome, actor,
   time, and byte length without raw meeting content.
3. **Given** a meeting deletion starts, **When** a new export is requested or
   a temporary export is fetched, **Then** the action is blocked and the UI
   states the lifecycle reason.
4. **Given** a file has already left GRAF control, **When** deletion copy is
   shown, **Then** it states that downloaded/exported files and data sent to
   approved external integrations cannot be revoked by GRAF.

### Edge Cases

- A transcript is final but diarization is missing; TXT/MD/CSV/XLSX/JSON remain
  available with explicit unknown attribution, while no confirmed speaker name
  is invented.
- Transcript processing is non-terminal or source content is incomplete; the
  default export action is unavailable. An explicitly introduced draft export
  must carry a visible `partial` status in every human and structured format.
- A meeting has no non-empty transcript text; no empty fake speaker rows are
  generated and the UI explains that there is no exportable transcript.
- A raw row has invalid timing, overlap, empty text, or missing provenance; it
  remains recoverable in structured source data, cannot become merge evidence,
  and is not silently dropped from the lossless JSON contract.
- A same visible label is used by different stable speaker keys, source roles,
  result revisions, or dual-track scopes; those boundaries are never merged.
- A same-speaker gap is exactly at the canonical threshold; inclusive threshold
  behavior is deterministic and separately testable from display grouping.
- A long recording exceeds one hour; human formats use `HH:MM:SS`, captions
  retain millisecond precision, and no timestamp wraps at 60 minutes.
- A summary has no decisions, action items, or evidence; the file keeps the
  section state explicit rather than omitting it without explanation.
- A summary is regenerated from a new template; the exported revision changes
  only after the new stored output is accepted.
- A viewer can read the meeting but export is disabled by owner/workspace
  policy; the UI shows the policy state without exposing a direct egress path.
- A browser refreshes or retries a large export; idempotency prevents duplicate
  lifecycle artifacts or misleading duplicate audit records.
- Text contains quotes, commas, line breaks, Markdown markers, HTML-like text,
  or spreadsheet formula prefixes; each format escapes it safely and preserves
  the visible transcript content.
- Export content includes untrusted transcript text; Markdown, SRT, and any
  rich representation must not execute or inject markup.

## Requirements

### Functional Requirements

#### Canonical source and revisions

- **FR-001**: The system MUST build every transcript export from a
  provider-neutral canonical snapshot selected from one terminal processing
  result/revision.
- **FR-002**: The snapshot MUST preserve raw transcript source rows and derived
  canonical speaker turns without changing or deleting source text, order,
  timestamps, or source references.
- **FR-003**: Every canonical turn MUST expose stable sequence, start, end,
  text, speaker key, display label, attribution state, source role, and source
  segment references to structured exporters.
- **FR-004**: Display grouping MUST remain presentation-only, MUST never merge
  across speaker, stable-key, source-role, result/revision, unknown,
  overlap, invalid-timing, or long-gap boundaries, and MUST never replace
  canonical turns in CSV, XLSX, JSON, or SRT.
- **FR-005**: The snapshot MUST record transcript revision, summary revision
  when present, derivation/schema policy versions, language, duration, and
  terminal/partial status.
- **FR-006**: The same snapshot MUST produce deterministic canonical payloads
  across repeated exports, independent of current provider availability.
- **FR-007**: Export MUST NOT call a transcription provider, request a new
  transcription, or depend on provider-specific client behavior.

#### Transcript formats

- **FR-010**: TXT MUST be a UTF-8 human-readable transcript with title/status
  header, speaker blocks, timestamped child turns, and complete source order.
- **FR-011**: MD MUST be a well-structured Markdown transcript with a readable
  heading hierarchy, speaker sections, timestamped child turns, a summary of
  source/status metadata, and safe escaping of untrusted text.
- **FR-012**: CSV MUST emit one canonical turn per row with stable sequence,
  integer or decimal machine timing, human timecodes, speaker key/label/state,
  source role, text, and boundary/provenance fields needed for analysis.
- **FR-013**: XLSX MUST present the same canonical rows in a usable workbook
  with wrapped text, filters, stable columns, and separate summary/action-item
  sheets when those artifacts are selected; it MUST NOT become a second source
  of truth.
- **FR-014**: JSON MUST emit a versioned provider-neutral envelope containing
  canonical turns, source segment fidelity, speaker attribution state,
  transcript revision, and summary references when selected; it MUST exclude
  credentials, bearer tokens, signed URLs, provider job secrets, and raw audio.
- **FR-015**: SRT MUST emit one accurately timed cue per eligible canonical turn,
  include a speaker label according to the selected option, preserve valid
  overlaps or surface a bounded limitation, and emit no synthetic pause cue.
- **FR-016**: No human, tabular, structured, or caption format MUST insert a
  literal `Пауза`, `[pause]`, or equivalent fabricated speech text.
- **FR-017**: Human formats MAY use a blank line or heading boundary to improve
  readability, but the time difference between turns MUST remain recoverable
  from timestamps.
- **FR-018**: SRT is transcript-only; summary content MUST NOT be encoded as
  subtitle cues. Summary-only and combined behavior MUST be explicit in the
  export UI.

#### Summary formats and semantics

- **FR-020**: Summary export MUST use the current stored summary/outcome
  revision and MUST NOT regenerate, rewrite, or silently repair it as part of
  downloading.
- **FR-021**: Summary projections MUST represent available sections for
  executive summary, key points, decisions, action items, follow-ups, risks,
  questions, and timestamped evidence without inventing missing sections.
- **FR-022**: Human summary TXT/MD MUST expose the stored revision status,
  source kind, and generator provenance. Export MUST NOT infer an `edited`
  state when the durable summary model does not record one; if a future saved
  revision records manual editing explicitly, the projection MUST preserve it.
- **FR-023**: Summary JSON and XLSX MUST preserve item order, item state,
  optional owner/due-date fields, source turn references, source transcript
  revision, summary revision, generator/template provenance, and safe status.
- **FR-024**: Combined export MUST include transcript and summary only in a
  format that can keep their boundaries clear: TXT/MD/JSON/XLSX. CSV and SRT
  MUST remain transcript-oriented unless a separate tabular summary artifact is
  explicitly selected.
- **FR-025**: Timestamped summary evidence MUST remain linked to canonical turn
  identity and time even when playback is unavailable.

#### UI, UX, and information architecture

- **FR-030**: Meeting detail MUST expose one contextual `Экспорт` action near
  the transcript/summary content and one clear artifact state in the existing
  Files/governance surface; it MUST NOT expose format choices as unrelated
  actions on every transcript row.
- **FR-031**: The export surface MUST first offer one plain-language
  `Что сохранить` control with `Расшифровка`, `Итоги`, or
  `Расшифровка и итоги`, then present only compatible formats.
- **FR-032**: Compatible formats MUST use one compact `Формат` control grouped
  by user job: reading (TXT, MD), tables (CSV, XLSX), data (JSON), and captions
  (SRT); the default dialog MUST NOT render every format as a separate card.
- **FR-033**: The default dialog MUST show only the two required choices,
  accessible progress/error text, cancel, save, and the bounded post-egress
  warning. Revision ids, readiness metadata, language, duration, response
  lifecycle, and a duplicate outcome summary MUST NOT appear in the dialog;
  those truths remain enforced by the server snapshot, policy, and audit.
- **FR-034**: Safe defaults MUST include speaker labels and timestamps, retain
  exact order, omit all pause-text markers, and use canonical turns rather than
  raw provider rows for human output.
- **FR-035**: Any optional setting that changes readability, such as displaying
  speaker names or evidence timestamps, MUST NOT change canonical source data or
  machine row boundaries.
- **FR-036**: The selected format MAY have one short plain-language hint, but
  the dialog MUST NOT add a preview card or repeat the selected values.
- **FR-037**: Processing, partial, missing, denied, deleted, failed, expired,
  and audit-unavailable states MUST disable or bound the relevant action and
  explain the reason without leaking private meeting or storage details.
- **FR-038**: Copying transcript or summary MUST use the same semantic formatter
  as the corresponding human export, preserve selection/order/timestamps, and
  show an accessible success or retryable failure state. It MUST be secondary
  inside collapsed `Дополнительно`, never a competing default footer action.
- **FR-039**: Export controls, format selection, preview, progress, success,
  failure, and disabled reasons MUST be keyboard operable, focus-visible,
  screen-reader understandable, localization-ready, and free of color-only
  meaning. In the embedded macOS client, starting a file download MUST preserve
  the current meeting route and MUST NOT treat the generated artifact as a
  cabinet navigation target. The embedded client MUST use the native macOS Save
  dialog so the reviewer can choose the filename and destination; cancelling
  that dialog MUST keep the meeting and export selections intact and MUST NOT
  be reported as generation or download failure.
- **FR-040**: Export presentation MUST use the existing GRAF design system and
  clean-room product language; competitor layouts, labels, colors, icons, and
  proprietary copy MUST NOT be copied.

#### Storage, processing, and lifecycle

- **FR-050**: Existing raw transcript, canonical turns, and stored summary
  outcomes MUST remain the durable source artifacts; export files MUST be
  reproducible or explicitly versioned derived artifacts.
- **FR-051**: Small human and structured files SHOULD be generated on demand
  from the pinned snapshot; larger XLSX or combined outputs MAY use a
  short-lived owner-controlled export artifact with explicit status and expiry.
- **FR-052**: Any persisted export artifact MUST record meeting, content kind,
  format, result/summary revisions, schema/renderer versions, byte length,
  integrity metadata, requester, creation time, expiry, and lifecycle state.
- **FR-053**: Export generation MUST be idempotent for the same meeting,
  content selection, format, options, and pinned revisions, and retries MUST
  not duplicate content or produce conflicting revision metadata.
- **FR-054**: Generated exports MUST participate in whole-meeting retention and
  deletion accounting; expiry and deletion MUST remove controlled derived
  copies while clearly distinguishing data already downloaded outside GRAF.
- **FR-055**: Export generation MUST not put transcript text, summary text,
  raw audio, credentials, signed URLs, provider identifiers, or private paths in
  logs, diagnostics, audit records, specs, screenshots, or committed evidence.
- **FR-056**: The existing package/manifest behavior MUST remain truthful until a
  real content package is implemented; a manifest MUST NOT claim to contain
  transcript or summary bytes it does not include.

#### Access, policy, and compatibility

- **FR-060**: Every export request and download MUST re-check current meeting
  access, artifact policy, lifecycle state, and selected revision at the server
  boundary.
- **FR-061**: Transcript and summary permissions MUST remain separate and MUST
  inherit existing owner/team/shared/viewer policy semantics. Combined export
  is a separate fail-closed decision composed from both component permissions
  and readiness states; it MUST NOT reuse the broader package-export policy or
  introduce a third permissive shortcut.
- **FR-062**: A permitted export MUST create a metadata-only egress event with
  actor, meeting, artifact kind, format, result/summary revision, outcome,
  policy reason, byte length when known, and time.
- **FR-063**: If the required audit event cannot be persisted, the export MUST
  fail closed and MUST not return content.
- **FR-064**: Existing consumers of the raw transcript contract MUST continue
  to receive raw segments; canonical export is additive and MUST NOT silently
  delete or rewrite the raw representation.
- **FR-065**: The old plain-text endpoint MUST either remain compatible or be
  changed only through an explicit versioned/canonical export contract; no
  consumer-facing raw-to-canonical change may be silent.
- **FR-066**: Export format allowlisting MUST reject unsupported extensions and
  MIME types without revealing internal implementation or storage details.

### Key Entities

- **Export Snapshot**: A revision-pinned provider-neutral view containing raw
  transcript fidelity, canonical turns, summary references, status, and schema
  policy versions.
- **Canonical Speaker Turn**: A derived ordered speech unit with exact interval,
  stable speaker identity, display label, attribution state, source role, text,
  and raw source references.
- **Summary Revision**: The current stored meeting outcome set with sections,
  item states, optional owner/due-date fields, evidence references, generator
  provenance, and source transcript revision.
- **Export Selection**: The requested content scope (transcript, summary, both),
  format, options, and pinned revisions.
- **Export Artifact**: An on-demand response or short-lived generated file with
  format, content kind, byte length, integrity, expiry, and lifecycle state.
- **Export Policy Decision**: The effective owner/workspace/share permission and
  artifact readiness result for the requested content and format.
- **Export Egress Event**: Metadata-only audit record for requested, allowed,
  denied, completed, failed, expired, and deleted export actions.

## Success Criteria

### Measurable Outcomes

- **SC-001**: For the canonical fixture matrix, 100% of eligible raw rows are
  either represented in a canonical turn or explicitly retained as unknown,
  invalid, or source-only structured data; no content-bearing row disappears.
- **SC-002**: TXT and MD exports contain 100% of canonical turn text in source
  order, preserve every tested timestamp interval, and contain zero literal
  pause markers.
- **SC-003**: CSV, XLSX, JSON, and SRT preserve 100% of canonical turn order,
  text, start/end timing, speaker state, and selected revision metadata in the
  fields appropriate to each format.
- **SC-004**: Repeated export of the same pinned revision produces identical
  canonical payloads and stable filenames/content type rules, excluding delivery
  metadata explicitly documented as non-canonical.
- **SC-005**: A 60-minute transcript uses `HH:MM:SS` in human formats and does
  not wrap or reinterpret times after 59:59; SRT retains millisecond precision.
- **SC-006**: A representative 60-minute TXT, MD, CSV, JSON, or SRT export is
  available to the reviewer within five seconds after the request when content
  is ready; XLSX or combined generation shows progress or a retryable state
  within one second and completes within thirty seconds in the supported test
  environment.
- **SC-007**: Summary-only export contains no transcript text unless the user
  explicitly selects a combined export; combined formats identify transcript
  and summary sections unambiguously.
- **SC-008**: Owner, permitted viewer, view-only shared user, denied user,
  processing meeting, partial meeting, deleted meeting, and policy-disabled
  meeting all receive the expected export action state in validation.
- **SC-009**: 100% of completed and denied export attempts in validation have
  metadata-only egress events, and no event or committed evidence contains raw
  transcript text, summary text, credentials, signed URLs, storage keys, or
  provider job identifiers.
- **SC-010**: Exported data remains pinned to the requested result/summary
  revision when a newer processing result becomes available during generation.
- **SC-011**: A provider-adapter fixture with equivalent GRAF canonical inputs
  produces semantically identical normalized TXT/MD/CSV/XLSX/JSON/SRT
  projections regardless of provider name. Lossless JSON raw rows and
  source-derived identities may differ when the provider's actual source
  segmentation differs; that difference is required raw-source fidelity, not
  provider coupling.
- **SC-012**: No critical accessibility blocker remains in keyboard,
  focus-order, accessible-name/live-region, 200% zoom, reduced-motion, or
  screen-reader-oriented semantics review of the complete export journey.
- **SC-012a**: At the supported embedded width and at 200% zoom, the default
  collapsed export view keeps the two required choices, status, and primary
  action reachable within the dialog viewport without horizontal page overflow
  and exposes no technical metadata.
- **SC-012b**: In the embedded macOS client, every generated export reaches a
  native Save dialog with the server-suggested filename and matching extension;
  choosing a writable location saves exactly one file, while cancellation saves
  none and emits no failure state.
- **SC-012c**: A first-time reviewer can understand the default dialog without
  knowing the terms revision, lifecycle, provider, canonical turn, readiness,
  or response artifact; none of those terms appear in the visible dialog copy.
- **SC-013**: No export action returns content after access is revoked, deletion
  starts, the artifact expires, or the required audit event fails.
- **SC-014**: Before general release, at least 90% of representative reviewers
  in a documented usability review can identify the correct content scope and
  format and complete a first export without assistance. This product outcome
  is not satisfied by synthetic browser automation alone.

## Assumptions

- Feature 113 remains the owner of raw-to-canonical speaker-turn derivation;
  this feature consumes and, where necessary, hardens that provider-neutral
  contract rather than changing diarization quality.
- Feature 118 remains the owner of playback/timeline interaction; export uses
  its canonical time semantics but does not create another timeline model.
- Feature 017 remains the owner of meeting access, artifact egress policy,
  audit, and truthful post-egress deletion copy.
- The current stored summary/outcome model is the source for summary export;
  export does not trigger LLM regeneration.
- TXT/MD are human projections, CSV/XLSX are tabular projections, JSON is the
  structured/provenance projection, and SRT is a caption projection.
- `XLSX` means the modern workbook format. Legacy binary `XLS` is not required.
- Human-readable exports use the user's saved speaker display names when
  available; machine formats retain stable speaker keys and attribution state.
- A terminal transcript is the default export prerequisite. Explicit draft
  export is deferred until partial-content UX and policy are separately
  approved.
- Generated exports are user-authorized meeting content and are not suitable
  for metadata-only diagnostics or analytics.

## Out of Scope

- PDF and DOCX generation.
- ZIP/content-package redesign beyond preserving truthful current manifest
  behavior.
- Batch export of many meetings.
- Public links, external-recipient invitations, or automatic external delivery
  to Slack, CRM, email, or storage integrations.
- Transcript editing, diarization retraining, speaker identity matching across
  meetings, translation, word-level captions, or provider migration itself.
- Automatic PII redaction or legal-hold editing beyond existing product policy.
- New audio export behavior; audio remains governed by existing artifact and
  playback/download policy.
- Desktop-owned export policy or direct client-to-provider access.
