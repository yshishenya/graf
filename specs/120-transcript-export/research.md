# Phase 0 Research: Canonical Transcript And Summary Export

Research was refreshed on 2026-07-21 from public first-party help centers,
developer documentation, standards bodies, and security guidance. It is a
capability and trust-boundary study only: GRAF does not copy competitor UI,
wording, colors, icons, layouts, or private screenshots.

## Local evidence

- `cabinet/egress.py` already owns per-artifact policy, deletion blocking,
  metadata-only audit, fail-closed audit errors, server-mediated bytes, and the
  current package manifest. Reuse it instead of adding an export policy system.
- The legacy transcript download reads ordered raw `TranscriptSegment` rows and
  emits TXT. The summary download currently emits a seed placeholder; neither
  is the new canonical multi-format contract.
- Feature 113 adds `speaker_turns`, but the current view schema lacks explicit
  attribution/result/overlap fields. `_derive_speaker_turns` skips unconfirmed
  rows, while a separate diarization fallback can label absent speaker evidence
  as `SPEAKER_00`. Export cannot treat those display fallbacks as confirmed
  identity, so the shared helper must be hardened once.
- Feature 049 already stores one `MeetingOutcomeSet` per processing result and
  generator version with ordered category items, state, content hash, owner/due
  date, and raw segment evidence references. Export must read it; it must not
  call the generator.
- Feature 017's `ExportPackage` download is a truthful JSON manifest, not a
  content ZIP. Feature 120 leaves that contract unchanged and adds an explicit
  canonical file route.
- Feature 118 persists meeting-scoped speaker display names and keeps stable
  speaker keys separate from labels. Human projections may use the display
  name; structured projections retain both.

## Competitive capability matrix

| Product | First-party evidence | Relevant pattern | GRAF decision |
|---|---|---|---|
| Krisp | [Meetings page](https://help.krisp.ai/hc/en-us/articles/10291109632412-Meetings-page-in-account-dashboard), [recording and sharing](https://help.krisp.ai/hc/en-us/articles/11734566901788-Recording-your-meetings-with-Krisp), [notes templates](https://help.krisp.ai/hc/en-us/articles/26708055686044-Meeting-Notes-Templates) | TXT transcript includes timestamps/speakers; transcript and notes are separate surfaces; notes/action items can be edited; sharing can distinguish full meeting from summary; template regeneration replaces the current summary. | Keep transcript and saved summary as separate selectable artifacts; pin the current stored summary; show revision/readiness; do not regenerate on export. |
| Otter | [Export conversations](https://help.otter.ai/hc/en-us/articles/360047733634-Export-conversations), [Export Summary](https://help.otter.ai/hc/en-us/articles/39503855767191-Export-Summary), [captions workflow](https://help.otter.ai/hc/en-us/articles/11742706003735-Create-captions-subtitles-for-your-video) | One export dialog provides format, speaker/timestamp, paragraph grouping, preview, captions, and permission-dependent availability; summary sections are separately selectable. | Use scope-first compatible format choices, safe defaults, a concise preview, and options that affect presentation only. Keep SRT transcript-only. |
| Descript | [Export subtitles](https://help.descript.com/hc/en-us/articles/10255811669773-Exporting-subtitles), [transcript export API example](https://help.descript.com/hc/en-us/articles/47364769888525-Use-additional-Descript-API-endpoints-in-Zapier), [speaker labels](https://help.descript.com/hc/en-us/articles/10249423506061-Detect-and-label-speakers-in-your-transcript) | Transcript and subtitle exports are distinct; speaker labels/timecodes are explicit options; SRT exposes line/card constraints; synchronous transcript bytes and asynchronous jobs are separate API patterns. | Distinguish readable transcript from captions; one canonical turn per SRT cue; generate bounded meeting files synchronously and defer job storage until measured need. |
| Fireflies | [Download transcripts, summaries, and recordings](https://guide.fireflies.ai/articles/3319752033-how-to-download-transcripts-summaries-and-meeting-recordings-from-fireflies) | Transcript, summary, and recordings are separate choices; transcript supports several structured/caption formats with speaker/timestamp options; summary has its own formats/sections; availability depends on plan/permission. | Organize by artifact job and compatibility; do not mix audio or integrations into this feature; show policy/readiness reasons rather than silently omitting content. |
| Fathom | [Get a copy of your transcript](https://help.fathom.video/en/articles/296000) | Current first-party flow offers clipboard copy rather than direct transcript file download. | Treat copy and file export as related projections but keep an explicit download contract, progress, errors, and audit instead of assuming copy equals durable export. |
| Zoom | [Meeting transcript API](https://developers.zoom.us/docs/api/meetings/), [recording file formats](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0064394), [meeting summary templates](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0080366), [caption lifecycle change](https://support.zoom.com/hc/en/article?id=zm_kb&sysparm_article=KB0063899) | Transcript, recording captions, and summary are distinct lifecycle/file types; transcript download is authorized; summary template changes can regenerate stored summary; caption retention/download behavior can change independently. | Model transcript, summary, and captions as separate readiness/policy surfaces; do not infer summary/caption availability from transcript alone; version contracts and pin revisions. |

### Systematic comparison of reviewed public behavior

`Not documented` below means that the reviewed first-party pages did not make
the behavior explicit; it is not an inference that the product lacks it.

| Product | Format surface | Speaker/timestamp controls | Preview | Summary separation | Caption behavior |
|---|---|---|---|---|---|
| Krisp | Readable transcript TXT in reviewed help | Both represented in transcript output | Not documented | Notes/action items are a separate surface and can have a replaced saved revision | Not documented in reviewed pages |
| Otter | Readable, document, and caption export choices | Explicit speaker, timestamp, and paragraph controls | Export flow exposes choices before delivery | Summary export and section selection are separate | Dedicated captions/subtitles workflow |
| Descript | Transcript/API and subtitle export are distinct | Speaker labels and timecodes are explicit | Subtitle constraints are selected before export | Not documented in reviewed pages | SRT/card/line constraints are caption-specific |
| Fireflies | Transcript, summary, caption/structured, and recording choices are separated | Transcript options include speaker/timestamp behavior | Choice surface precedes download; content preview was not established by reviewed source | Summary has its own formats and sections | Caption formats belong to transcript, not summary |
| Fathom | Reviewed flow is clipboard transcript copy | Not documented | No separate file preview established | Not documented in reviewed page | Not documented |
| Zoom | Recording transcript/caption files and APIs are separate | File/API contract supplies timing; UI toggles were not established by reviewed pages | Not documented | Meeting summary/template lifecycle is separate | Caption retention/download can change independently from transcript/summary |

| Product | Permission signal | Partial/processing signal | Lifecycle/retention signal | UX information architecture |
|---|---|---|---|---|
| Krisp | Sharing can distinguish full meeting from summary | Saved meeting artifacts appear after processing; detailed partial export was not documented | Summary template regeneration replaces the saved summary | Meeting, transcript, notes, and sharing are distinct concepts |
| Otter | Export availability depends on account/permission context | Reviewed source does not define a stable partial-file contract | Export is a delivered copy outside the conversation surface | One export flow combines artifact format and presentation controls |
| Descript | Project/workspace access governs export | Sync API and asynchronous job patterns are distinct | Subtitle files are derived deliverables | Transcript export and subtitles are separate jobs |
| Fireflies | Plan and permission can gate download choices | Missing/unavailable choices are bounded by artifact readiness | Downloaded transcript/summary/recording are separate copies | Artifact-first selection separates transcript, summary, and recording |
| Fathom | Access to the meeting transcript is required | Not documented | Clipboard copy has no product-controlled post-copy lifecycle | Copy is a direct transcript action, not a multi-format package |
| Zoom | Authenticated recording/transcript access is explicit | Recording, transcript/caption, and summary readiness are separate | Recording/caption retention and summary regeneration have independent lifecycle | Recording files, captions/transcript, and summary remain separate surfaces |

GRAF therefore uses capability research only: a scope-first original dialog,
metadata-only preview, explicit readiness/policy reasons, pinned saved summary,
caption-specific SRT semantics, and truthful downloaded-copy lifecycle. No
competitor wording, layout, colors, icons, or private screenshots are reused.

## Decision 1: One scope-first export dialog

- **Decision**: Meeting detail exposes one `Экспорт` action. The dialog first
  selects `Транскрипт`, `Саммари`, or `Оба`, then shows only compatible format
  groups and presentation options.
- **Rationale**: First-party competitor flows consistently distinguish artifact
  type, format, and speaker/timestamp choices. Scope-first ordering prevents a
  user from selecting CSV/SRT and receiving a silently truncated combined file.
- **Rejected**: One button per format, format actions on transcript rows, and
  copying competitor visual patterns.

## Decision 2: Preview structure and metadata, not unauthorized content

- **Decision**: Before download, show content scope, format purpose,
  revision/readiness, language/duration, included speakers/timestamps/sections,
  and a safe structural preview. Do not fetch or render meeting text for a user
  who cannot export it.
- **Rationale**: Preview reduces format mistakes, while content-free preview
  preserves the server authorization boundary and avoids a second egress path.
- **Rejected**: Client-only permission hiding and full transcript preview from a
  metadata endpoint.

## Decision 3: Terminal-only export in this slice

- **Decision**: The default canonical export requires a terminal selected
  transcript. Partial/draft export remains disabled with a specific reason.
- **Rationale**: Competitor documentation generally frames export as a
  post-processing action. More importantly, GRAF currently publishes canonical
  turns only for ready results; inventing partial revision semantics would widen
  policy, UX, filename, and reproducibility scope.
- **Rejected**: Marking any current UI display as a stable draft snapshot.

## Decision 4: Snapshot once, serialize many

- **Decision**: Build one immutable GRAF-owned snapshot from raw rows, canonical
  turns, speaker names, and the selected stored outcome set. Every serializer
  consumes it and none queries the database or provider.
- **Rationale**: This makes cross-format comparisons deterministic, prevents
  transcript/summary revision mixing, and keeps provider replacement behind the
  canonical assembly boundary.
- **Rejected**: Format-specific queries, client grouping, provider response
  export, and UI display groups as machine data.

## Decision 5: Harden the existing canonical-turn seam

- **Decision**: Reuse feature 113 derivation but add explicit stable speaker key,
  attribution state, result id, source role, overlap/invalid flags, and source
  ids. Unknown or unconfirmed content becomes a non-mergeable singleton turn
  with an unknown key/label; it is never confirmed as `SPEAKER_00`.
- **Rationale**: A single shared rule is smaller and safer than export-specific
  patches. It also closes the current gap where unconfirmed rows disappear from
  `speaker_turns` even though raw rows remain.
- **Rejected**: Merging by visible label, dropping unknown text, or duplicating
  canonicalization inside each serializer.

## Decision 6: Generate on demand; persist nothing yet

- **Decision**: Generate all six formats inside the authorized request from the
  pinned frozen snapshot. Keep no export file, storage key, or background job.
- **Rationale**: Meeting text is bounded, current targets allow five seconds for
  text and thirty seconds for XLSX, and persistence would require a table,
  worker, expiry, deletion, RLS, storage, retry, and cleanup behavior without
  current evidence of need.
- **Upgrade trigger**: Introduce short-lived owner-controlled artifacts only if
  representative XLSX/combined fixtures exceed the time or memory budget.

## Decision 7: Use standard format writers and neutralize active content

- **Decision**:
  - CSV uses Python [`csv`](https://docs.python.org/3/library/csv.html) with
    stable columns/quoting and a UTF-8 BOM for common spreadsheet import.
  - Cells beginning with formula-trigger characters are made inert according to
    [OWASP CSV Injection](https://owasp.org/www-community/attacks/CSV_Injection).
  - Markdown follows [CommonMark escaping](https://spec.commonmark.org/current/)
    and emits no raw HTML from untrusted meeting text.
  - SRT follows the [Library of Congress format description](https://www.loc.gov/preservation/digital/formats/fdd/fdd000569.shtml):
    sequential cue, `HH:MM:SS,mmm --> HH:MM:SS,mmm`, text, blank separator.
  - JSON uses one versioned envelope, sorted object keys, stable arrays, UTF-8,
    and integer millisecond timing.
- **Rationale**: Stdlib/spec behavior is smaller and more interoperable than
  hand-rolled quoting or ad-hoc caption syntax.
- **Rejected**: CSV string concatenation, raw HTML-flavored Markdown, synthetic
  pause cues, and provider-specific JSON.

## Decision 8: Add one XLSX writer dependency

- **Decision**: Add `openpyxl` and create a write-only workbook with four fixed
  sheets: `Transcript`, `Summary`, `Action Items`, and `Metadata`. Write
  untrusted text as literal strings, with wrapped cells, stable headers,
  filters/freeze panes, and no formulas/macros/links.
- **Rationale**: XLSX is standardized by [ECMA-376](https://ecma-international.org/publications-and-standards/standards/ecma-376/)
  as a multi-part OOXML package. The [openpyxl write-only mode](https://openpyxl.readthedocs.io/en/stable/optimized.html)
  provides bounded memory and correct packaging. A custom ZIP/XML producer
  would be substantially more code and interoperability risk.
- **Rejected**: Hand-written OOXML, pandas, a full data-frame stack, legacy XLS,
  macros, and a new spreadsheet service.

## Decision 9: Preserve separate policy, audit, and deletion truth

- **Decision**: Transcript and summary decisions remain separate; combined
  requires both. Reuse feature 017 fail-closed audit and deletion checks. Record
  metadata only: content scope, format, pinned revision ids/versions, renderer
  version, outcome, actor/time, policy reason, and byte length.
- **Rationale**: Export is meeting-content egress. A UI-visible file is not proof
  of current permission, and a downloaded copy is outside later GRAF deletion.
- **Rejected**: UI-only gates, one broad `package_export` decision for all
  content, logging content hashes alongside text, or promising revocation of a
  downloaded file.

## Decision 10: Keep old routes and package manifest compatible

- **Decision**: Add canonical content-export endpoints. Do not silently change
  the raw/plain transcript consumer or claim existing export packages contain
  bytes that are not present.
- **Rationale**: Feature 113 explicitly preserved raw consumers, and feature 017
  package behavior is manifest-only. Additive versioning makes migration
  explicit and rollback safe.
- **Rejected**: Replacing `/downloads/transcript` output in place or repurposing
  the package manifest as a ZIP.

## Decision 11: Compact dialog; native save ownership on macOS

- **Decision**: Keep the default export surface compact: scope and format are
  direct choices, while presentation options and copy live under one
  `Дополнительно` disclosure. Do not expose internal revision, readiness, or
  lifecycle metadata in this common task. In the embedded macOS client, hand
  the server-suggested filename to `NSSavePanel` and let the reviewer choose
  the filename and destination before `WKDownload` writes bytes.
- **Rationale**: Current production evidence shows that an always-visible
  twelve-row metadata card pushes the primary action below the embedded
  viewport and makes a common task read like diagnostics. The existing native
  delegate also hard-codes Downloads, which removes normal macOS control over
  destination and overwrite. Progressive disclosure preserves revision truth
  without making it the primary job, while the platform save panel provides
  location, rename, directory creation, overwrite confirmation, and keyboard /
  assistive-technology behavior without a new dependency or custom file UI.
  Revision truth remains enforced by the server and audit contract rather than
  being presented as a user decision.
- **Rejected**: Weakening revision truth; a multi-step wizard; a wide
  split-pane preview; a custom folder browser; keeping automatic Downloads as
  the only embedded behavior; persisting generated artifacts to support a
  second download screen.

## Decision 12: Two plain choices beat a compact diagnostic surface

- **Decision**: The default dialog contains two labelled native selects and one
  save action. Optional presentation controls and copy remain collapsed under
  `Дополнительно`; revision/readiness/language/duration metadata, format cards,
  and the repeated outcome summary are removed from the user-facing dialog.
- **Rationale**: Direct review of the first compact implementation showed that
  progressive disclosure was not enough: the visible card grid still asked an
  ordinary reviewer to parse product-internal structure before saving a file.
  Server-side revision, policy, audit, and deletion guarantees do not require
  displaying their internal identifiers in this decision surface.
- **Rejected**: A wizard, a recommended-format quiz, a custom format picker,
  removing optional settings entirely, or weakening any server-side truth.

## UX and lifecycle conclusions

- Export settings affect projections only; speaker/timestamp switches never
  alter canonical rows or source data.
- Summary readiness is driven by the stored outcome set/category states, not by
  a broad `summary_status` flag alone.
- Captions are a transcript projection with their own timing limitations; they
  are not a summary container.
- Denied, missing, partial, deletion, audit-unavailable, and retryable serializer
  states must remain distinct in both API problems and dialog copy.
- Progress is honest: a single synchronous request can show preparing state;
  there is no fake background job or expiring artifact in this slice.
- Accessibility is part of the contract: focus trap/return, keyboard operation,
  visible focus, screen-reader names/live status, reduced motion, and no
  color-only meaning.
- Cancelling the native Save dialog is a user choice, not a generation failure;
  it writes no file, preserves the meeting route, and requires no server-side
  artifact or audit model change.
