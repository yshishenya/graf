# Research: Canonical Provider Speaker Turns

## Decision 1: Canonical temporal source

**Decision**: Contract-valid provider diarization rows are canonical speaker
turns. `transcript[]` remains unattributed ASR evidence and is never assigned an
overlap winner.

**Rationale**: The provider rows already contain the required speaker key,
boundary, and text. Reconstructing attribution from broader ASR windows destroys
turn boundaries.

**Rejected**: Majority overlap, midpoint, minimum-confidence thresholds, and
text splitting. All require guessing which speaker owns words.

## Decision 2: Unsafe result behavior

**Decision**: If timing, chronology, duplicate-text, or text-conservation
invariants fail, reject the attributed projection as a whole and emit the
ordered ASR evidence once with `degraded_provider_result` and
`mixed`/`uncertain` attribution. A tiny explicit unknown is handled separately
by Decision 5 because its identity is already explicit and requires no guess.

**Rationale**: Partial repair of structurally unsafe rows can duplicate content
or create plausible but false attribution. Whole-result degradation for those
defects is deterministic and conserving.

**Rejected**: Dropping bad rows, picking one duplicate, merging labels, and
deduplicating by guessed similarity.

## Decision 3: Text conservation

**Decision**: Compare exact ordered lexical tokens after Unicode NFKC and
case-folding. Letters, combining marks, and numbers are conserved; punctuation
and typographic symbols are presentation differences because provider alignment
may omit them while preserving the same words. Store only `matched`,
`mismatched`, or `not_applicable`.

**Rationale**: Representation-only normalization is deterministic and does not
change, insert, reorder, or fuzzily match words or numbers. Raw ASR still keeps
the original punctuation and symbols as separate evidence.

**Rejected**: Fuzzy matching, punctuation repair, token alignment, and edit
distance thresholds because each can conceal missing or duplicated lexical
content.

## Decision 4: Chronology and duplicates

**Decision**: Reject `end <= start`, decreasing source order, and exact full-ASR
text repeated in multiple provider rows. Count multi-label ASR overlaps for
diagnostics but do not treat legitimate temporal overlap alone as a defect.

**Rationale**: These checks separate structural contradictions from legitimate
cross-talk without inventing attribution.

## Decision 5: UNKNOWN and tiny identity

**Decision**: Any explicit unknown provider key is non-confirmed and displayed
as `Спикер не определён`. A tiny unknown identity (aggregate duration at or
below 50 ms) degrades the provider attribution result, remains one explicit
unknown turn, and does not invalidate other contract-valid confirmed turns.

**Rationale**: This reproduces the supplied 40 ms defect class, prevents an
artifact from becoming a confirmed participant, and avoids replacing valid
speaker attribution with an all-unknown transcript.

## Decision 6: Stable identity and saved names

**Decision**: Build a bounded stable GRAF key from `processing_result_id` plus a
SHA-256 prefix of the raw provider key. Retain `provider_speaker_key` separately
on canonical/API/export turns. `SPEAKER_XX` is display order only.

**Rationale**: Existing tables already store the result ID and raw provider key;
the generated key fits the existing 120-character name key without migration.

**Legacy names**: Accept an old ordinal name only when the raw provider key is
the exact corresponding `SPEAKER_XX` value and the saved-name timestamp proves
that the current result already existed. An explicit rename migrates that safe
row to the stable key. Otherwise leave it unresolved; never rebind by order
after ambiguity, renumbering, or a newer result.

## Decision 7: Talk-time

**Decision**: Denominator is the duration of valid accepted canonical speech,
including explicit unknown speech. User-facing label is `Доля распознанной речи`.

**Rationale**: This measures distribution within recognized speech, not share of
the full recording. The latter needs media-duration semantics outside this fix.

## Decision 8: Diagnostics and provenance

**Decision**: Extend the GRAF adapter to retain available result/build/model/
alignment versions and an internal excluded diagnostic object. Emit a single
allowlisted audit record at import with provider job ID, source hash, counts,
statuses, and defect origin.

**Rationale**: Existing `ProcessingAuditEvent.metadata_json`, `failure_reason`,
`failure_source`, and `source_result_hash` are sufficient; no migration or new
content-bearing store is needed.

## Decision 9: Consumer convergence and VTT

**Decision**: Review, timeline, exports, and outcomes call the same canonical
function. Add VTT as the minimal sibling of the existing SRT renderer.

**Rationale**: Independent reconstruction caused the root defect. VTT is an
explicit required consumer and differs from SRT only in container syntax.

## Production baseline evidence

- Production checkout: `/opt/projects/2brain-rec`, branch `master`, clean.
- Production checkout and API/processing runtime SHA:
  `04b711bca06023772d81df165fd6a03d7142ffa0`.
- Production Alembic revision: `0077_provider_unlink_xworkspace` (`head`).
- The active uncommitted merge includes `origin/master` at
  `f0916254fe4c0a84ebe80ec2983cf4407d73b489`; its post-release closeout does not
  replace the production runtime release SHA.
- Public live and ready probes returned HTTP 200; API, processing worker, media
  worker, Temporal, Postgres, and MinIO were healthy.
- No production content or provider payload was copied into this feature.
