# Data Model: current revision per summary type

## Existing entities reused

### `MeetingOutcomeSet`

Immutable generated revision. Existing fields preserve meeting/workspace,
source result/revision, candidate, template snapshot, generator identity,
content hash, lifecycle/revision state and supersession link. Feature 183 reuses
this header unchanged except for the composite key required by the slot pointer;
it does not try to infer prompt/model/schema provenance from `candidate_id` or
mutable JSON.

Feature 183 retains it as the only summary-content header, adds the named target
key `(id, workspace_id, meeting_id, template_key)` for the slot FK and creates no
second revision/content table.

The following is the **Feature 195 target**, not a Feature 183 schema delta.
Feature 195 adds these provenance fields to the existing header in the same
migration family that creates the canonical parent, owner-row receipts,
GenerationCall membership and first positive publication path:

| Field | Shape | Rule |
|---|---|---|
| `generation_attempt_id` | UUID nullable for legacy only | Unique composite FK to the attempt's complete normalized workspace/meeting/type/template/source/root/activation/run tuple; required for every newly generated revision |
| `bundle_root_name` | string nullable for legacy only | Exact Langfuse root bundle prompt name |
| `bundle_root_version` | integer nullable for legacy only | Exact numeric root version; never `latest` |
| `bundle_root_hash` | string nullable for legacy only | Integrity hash of the fetched root config |
| `activation_manifest_hash` | string nullable for legacy only | Hash of the global activation manifest containing every allowed member/settings/schema/validator/renderer version |
| `resolved_run_manifest_hash` | string nullable for legacy only | Hash of the immutable attempt-owned `ResolvedRunManifestV1` body |
| `publication_receipt_schema_version` | integer nullable only while `pending_publication` or legacy | Exact type-specific publication-receipt schema version |
| `publication_receipt_digest` | string nullable only while `pending_publication` or legacy | SHA-256 of the canonical pass receipt stored on the attempt; digest is outside that payload |
| `provenance_fingerprint` | generated string nullable only while `pending_publication` or legacy | DB-generated hash of the normalized workspace/meeting/type/template/source/root/activation-manifest/run-manifest/publication-receipt tuple under serializer version 1 |
| `provenance_fingerprint_version` | integer | Persisted canonical serializer/hash contract version; initial value `1` |
| `provenance_state` | enum | `pending_publication | complete | legacy_incomplete`; only `complete` may newly become published/current or create egress; `legacy_incomplete` is readable only through an exact grandfathered migrated slot described below |

The attempt stores the same normalized `template_key`, `template_version`,
source-basis identity, root identity, activation/run manifest hashes, the
immutable `resolved_run_manifest_schema_version/json/hash`, publication
receipt digest/version and a
DB-generated `provenance_fingerprint`; mutable JSON cannot substitute for those
columns. The migration creates a unique candidate key over attempt ID plus every
normalized workspace/meeting/type/template/source/root/activation/run field and
a composite FK from the outcome header over that complete tuple; the generated
fingerprint is an audit/idempotency identity, not the sole referential check.
Negative constraints/fixtures reject same-meeting different-type,
template, source, root, activation-manifest, resolved-run or publication-
receipt substitution.

`ResolvedRunManifestV1` contains the complete immutable
`root_promotion_event_binding`; its hash is already inside the normalized
resolved-run identity and therefore inside the composite FK and provenance
fingerprint. The outcome header does not duplicate a second mutable event JSON
or add another authority column. Publication follows the attempt body through
that FK, fetches/re-hashes the typed event, and rejects a bare event digest or
current-label lookup.
Database update protection makes those normalized attempt/outcome provenance
columns immutable once attached: a `BEFORE UPDATE` trigger rejects changes to
any provenance column on the outcome and rejects the same changes on an attempt
once an outcome references it. The FK is restrictive and no cascade update is
allowed. The old reverse
`attempt.outcome_set_id` is validated for equality during transition and may
be retired later; it is never treated as sufficient provenance by itself.
Under Feature 195, an internal candidate first persists with `pending_publication`: every
non-receipt identity and the exact resolved-run body/hash is already frozen,
while receipt-dependent outcome columns and the fingerprint remain null. In the
single Feature 195 publication transaction, the sole `ai_service.py` finalizer creates the pass
receipt on the attempt, copies its schema/digest to the outcome, computes the
fingerprint and changes `pending_publication → complete` before moving the
slot. No other transition may fill those fields. Feature 183 contains only the
same entry point in an always-fail-closed state and the private slot-CAS
primitive; it cannot create these fields or run this transition. A pending row is invisible to
ordinary readers and cannot be a slot/share/export target. Legacy rows are
backfilled only when one exact same-scope attempt is provable. Otherwise they
remain `legacy_incomplete`: not selectable by ordinary publication/query
fallback and not eligible for new egress. One may remain readable only when the
Feature 183 migration proves the exact pre-migration current pointer and creates
the corresponding `migrated_legacy_read_only` slot/proof in the same transaction.

### Provenance fingerprint v1 (Feature 195 contract)

The fingerprint is an audit/checksum convenience; the composite FK still
compares every normalized column. Version `1` is SHA-256 over the domain prefix
`GRAF-PROV\0v1` followed by this exact field order:

```text
workspace_id
meeting_id
template_key
template_version
source_basis_hash
bundle_root_name
bundle_root_version
bundle_root_hash
activation_manifest_hash
resolved_run_manifest_hash
publication_receipt_schema_version
publication_receipt_digest
```

Each field is encoded as `uint32be byte_length || value_bytes`. UUIDs use 16
network-order bytes; integers use signed 64-bit big-endian bytes; hash values
are accepted only as 64-character lowercase ASCII hexadecimal and use their
decoded 32 bytes; uppercase, prefixes and whitespace are rejected; strings use
exact UTF-8 with no trim, case-fold or
Unicode normalization. Null uses length marker `0xFFFFFFFF`; complete new
provenance rejects null in every required field, while legacy fingerprints may
carry it. Empty string has length zero and is distinct from null. Migration and
model fixtures freeze field order/version and prove null/empty, Unicode,
`["ab","c"]` vs `["a","bc"]`, one-byte difference and the normative digest
vectors below.

#### Normative provenance fingerprint vectors

The base vector uses workspace UUID
`00010203-0405-0607-0809-0a0b0c0d0e0f`, meeting UUID
`10111213-1415-1617-1819-1a1b1c1d1e1f`, `template_key=auto`,
`template_version=7`, source hash `00×32`, root name
`graf/meeting-intelligence/bundle`, root version `42`, root/activation/run hashes
`11×32`/`22×32`/`33×32`, receipt schema `1` and receipt digest `44×32`.
Its complete 312-byte serialized input is:

```text
475241462d50524f5600763100000010000102030405060708090a0b0c0d0e0f00000010101112131415161718191a1b1c1d1e1f000000046175746f00000008000000000000000700000020000000000000000000000000000000000000000000000000000000000000000000000020677261662f6d656574696e672d696e74656c6c6967656e63652f62756e646c6500000008000000000000002a000000201111111111111111111111111111111111111111111111111111111111111111000000202222222222222222222222222222222222222222222222222222222222222222000000203333333333333333333333333333333333333333333333333333333333333333000000080000000000000001000000204444444444444444444444444444444444444444444444444444444444444444
```

| Vector | Exact change from base bytes | Bytes | Expected lowercase SHA-256 |
|---|---|---:|---|
| base/full | none | 312 | `bfa646333fe6918044d71cb56889cfbf5e31c8c1e2457e696961b1e3f683aeeb` |
| empty | replace framed `template_key` with `00000000` | 308 | `bc5a868573502a5e6c1bf2acdf2c0f8253f53efa0480f42ea1d128c4774be432` |
| legacy null | replace framed `template_key` with `ffffffff` | 308 | `72b36c38fbf5559946d6ffcb6aaaa7a82532f75b8adb8ac6f1ae430bd734909c` |
| Unicode | replace framed `template_key` with length `00000015` plus UTF-8 `итоги/обзор` | 329 | `0fa8a5eb4b0586d8f36c651566979611f097ef6f8b3f1ca505df4098217e9798` |
| framing A | set template/root-name bytes to framed `ab`/`c` | 279 | `dfdaed98d22b6478f668aded2febfa9cc7866ce03df86da01de50798b7414cb0` |
| framing B | set template/root-name bytes to framed `a`/`bc` | 279 | `95569ceb759987f83a99d55d1a553f019ec62e34f47697e56bf28be64000f3c1` |
| one-byte mutation | change final receipt-digest byte from `44` to `45` | 312 | `c4626054a8163277432a1db3d759823a60b5a1bd2ad54249fa70e0fa6fc9f70e` |

### Two-layer verification and publication receipts

`CanonicalVerificationReceipt` belongs to the reusable
`MeetingIntelligenceArtifact`/canonical-generation identity, never to each
type-specific attempt. The artifact owner row stores exactly one guarded,
immutable set of `canonical_verification_receipt_schema_version`,
`canonical_verification_receipt_json`,
`canonical_verification_receipt_digest` and
`canonical_verification_receipt_finalized_at` columns. Its payload binds
artifact/workspace/meeting/source/extraction-layer identities; verifier
prompt/model/schema and calibration manifest identity plus the complete
`VerifierCalibrationStatusSnapshotV1` body/hash: status event/epoch, active
state, drift epoch, last-pass time, hard freshness deadline, evidence kind and
typed freshness-evidence binding. The finalizer resolves and re-hashes the
selected embedded activation cohort or weekly-drift body under `FOR SHARE`;
the complete ordered extract/resolve/semantic-verify/
repair/reverify GenerationCall bindings and call-set hash; complete
immutable successful root-promotion-event binding shared by every canonical
call; complete
`SourceVerificationCatalogV1` identity/per-span verdicts, source-range and
candidate-ID coverage roots; the exact canonical portion of
`CriticalityPolicyV1` plus complete source/candidate/canonical classifications;
one evidence/verdict/reason entry for every canonical claim;
both omission findings; repair round and post-repair reverify; literal pass
and issued time. The digest is stored outside the hashed payload, so it is not
self-referential. Artifact reuse carries this same digest and never requires
verifier calls to belong to a new type attempt. Revoked/expired calibration or
artifact revocation blocks new projection/publication without rewriting the
historical receipt. Calibration manifest ID/hash is part of extraction/artifact
logical identity, so a replacement calibration reserves a distinct parent and
cannot be blocked by the historical verified-row unique key. Only a fully
passing canonical run finalizes these columns.
Failed/invalid/uncalibrated work remains represented by artifact lifecycle
state, GenerationCalls and findings; there is no finalized fail receipt.

The existing `MeetingOutcomeGenerationAttempt` owner row stores exactly one
guarded, immutable set of `outcome_publication_receipt_schema_version`,
`outcome_publication_receipt_json`, `outcome_publication_receipt_digest` and
`outcome_publication_receipt_finalized_at` columns. They are finalized only
after projection, presentation synthesis/verification and deterministic
layout render produce a frozen
`MeetingOutcomeSet`. The outcome header repeats only publication schema/digest
through its restrictive composite FK and provenance fingerprint; it does not
copy receipt JSON or finalization time. The strict publication payload contains:

```text
attempt/workspace/meeting/type/template/source identities
artifact ID + canonical payload hash + CanonicalVerificationReceipt digest
root + activation + resolved-run + extraction-layer hashes
complete immutable RootPromotionEventV1 binding authorizing that root/activation
gateway route-binding hash + allowlisted actual provider/model provenance
calibration manifest plus complete VerifierCalibrationStatusSnapshotV1
body/hash, hard deadline, kind-tagged typed activation-cohort/weekly-drift
binding and rehashed selected evidence
primary/optional-secondary profile versions/hashes, exact composite-profile
contract hash, projection/criticality policy versions/hashes and authorized
language/AudienceContextV1/privacy/FocusV1/DetailBudgetV1/
EvidencePresentationPolicyV1 controls plus
literal Receipt V1 analysis_mode=facts_only
ordered type-attempt Auto/projection/presentation-synthesis/presentation-verify GenerationCall IDs and call-set hash
exclusive deterministic resolver no-op proofs where applicable
eligible/selected/omitted canonical-ID coverage roots and omission reasons
relation-closure, authorization, critical-retention and capacity gate results
presentation statement/selected-claim coverage plus entailment, number,
negation, state/disposition, effective-date, uncertainty, translation and
critical-retention gates
conditional exact Auto section-mapping policy/profile binding and recomputed
action/non-action exactly-once section assignment
deterministic layout/markup renderer version
exact outcome_set_id + outcome content hash
literal pass and issued_at
```

When deterministic prefiltering yields zero eligible IDs, complete projection
selects zero IDs, or topic focus has no unambiguous supported match, the attempt
stores only the closed non-authorizing `AttemptTerminalEvidenceV1` from
`contracts/receipts.md` and terminal state `no_supported_content`. It creates no
candidate outcome, publication receipt or slot mutation.

Both payload schemas use the exact canonical JSON, domain-separated SHA-256,
field types, cardinalities, GenerationCall bindings, calibration registry and
digest vectors in [contracts/receipts.md](contracts/receipts.md); each digest is
stored outside its payload. Receipt V1 adds no receipt table, reservation row or
independently locked receipt entity: locking the artifact protects the
canonical columns and locking the attempt protects the publication columns.
For the type receipt, a deferred constraint trigger verifies that every Auto,
projection and presentation GenerationCall belongs to the same
workspace/meeting/type attempt;
every non-empty published result has at least one profile-projection call. Final
receipt fields are frozen by guarded owner-row transitions, and publication
digest/version are members of the outcome↔attempt composite FK and fingerprint.
Once Features 194/195 enable auto-publication, publication uses the single
global relative lock order in `contracts/receipts.md`, recomputes both digests
and rendered content, and requires a final valid non-revoked canonical receipt
plus complete projection coverage, exact outcome/content hash and final
publication pass. There is no pre-V2, single-receipt or same-attempt
compatibility mode: until Features 194/195 persist the canonical artifact, call
ownership and both final receipts, automatic publication remains fail-closed
while slot migration and reads may still be implemented and tested with
normative synthetic receipt fixtures.

The attempt-owned `ResolvedRunManifestV1` body is the immutable source for
meeting-specific resolution replay. It embeds the frozen Auto input descriptor
(including title/participant-count/duration, complete claim/relation coverage
hashes and compatible catalog), the exact full-input hash, and any validated
model-result hash plus deterministic selection proof. Every Auto manifest also
embeds the complete exact `AutoSectionMappingPolicyV1` body/hash and catalog
Auto presentation-profile v3 body/hash; all four are forbidden for non-Auto.
The complete canonical
profile view itself is reconstructed from the immutable parent artifact and is
persisted in the Auto GenerationCall logical request when model Auto runs. It
also embeds `MeetingIntentV1`, `AudienceContextV1`,
`PrivacyPresentationPolicyV1`, `FocusV1` raw and normalized query plus resolved
topic IDs, `DetailBudgetV1`, `EvidencePresentationPolicyV1`, exact primary and
optional-secondary profile identities/hashes plus the complete
`CompositeProfileContractV1` body/hash with every `SectionContractV1`,
controls, the complete immutable `root_promotion_event_binding`,
`CriticalityPolicyV1`, the complete `CanonicalKindStateMatrixV1` body/hash, the
complete gateway route-binding descriptor, child versions and phase-specific
envelopes. The publication
finalizer verifies its canonical bytes/hash and never reconstructs historical
metadata or policy from mutable meeting/workspace rows.
The same full composite body/hash is embedded in all three type-phase logical
requests, the strict rendered-content payload and the publication receipt; a
hash-only or profile-key-only representation cannot publish.

### `MeetingOutcomeItem`

Atomic evidence-backed items for one outcome revision. Unchanged in this feature.

### `MeetingOutcomeGenerationAttempt`

Attempt and internal-candidate lifecycle. `expected_current_outcome_set_id` is carried in request metadata/contract and interpreted against the target slot.

### `GenerationCall` and `DispatchIntent`

Durable provider-call ledger and dispatch idempotency. Neither can publish content by itself.

Feature 195 extends each new receipt-eligible production GenerationCall with
exactly one normalized owner (`canonical_artifact` or `outcome_attempt`), owner-compatible
phase/sequence, immutable `model_route`, `GatewayRouteBindingV1` hash, complete
`RequestSettingsV1` body/hash, canonical logical-request and validated-result
bodies/hashes, the four normalized `RootPromotionEventV1` binding members,
actual provider/model and optional provider request ID. These are
columns/immutable bodies, not mutable metadata JSON. The logical request
materializes the complete binding object; receipt descriptors and call-set
identity include it together with `model_route` and `request_settings_hash`.

Evaluation calls use the same table/state machine but a disjoint constrained
scope: exact `evaluation_run_id` plus complete
`CandidateEvaluationAuthorityV1` ID/version/body/hash, and no artifact/attempt,
receipt, slot or DispatchIntent owner. Production requires the promoted-root
event fields and forbids evaluation authority; the candidate arm requires the
cycle-free candidate root/authority and forbids promotion-event fields. These
exclusive columns and publication-sink constraints are database-enforced, not
mutable Langfuse metadata.

Model invocation and Langfuse export are two different durable machines. Every
GenerationCall is prepared without network I/O, with immutable request/route/
authority/correlation fields, then follows
`prepared → sending → response_recorded | failed_pre_egress | ambiguous`.
`ambiguous` may refine only to `response_recorded` or `failed_pre_egress` on an
authenticated exact-correlation receipt. The prepare Activity is idempotent and
retryable; the invoke Activity has `maximum_attempts=1` and all lower-layer
retries disabled. Immediately before any gateway operation, it commits one CAS
from `prepared` to `sending` with a new immutable invoke-attempt ID. A CAS loser,
retry or worker observing `sending` or any terminal state emits zero bytes.

Raw response persistence and `response_recorded` are cancellation-shielded and
precede schema validation. Crash/timeout after `sending` is ambiguous, never a
retry. `failed_pre_egress` requires the complete authenticated
`ProviderNoEgressProofV1` from the gateway proving no upstream submission for
that exact attempt/request/correlation. Only that state/proof permits one
bounded successor GenerationCall with a new ID and immutable predecessor link;
an ambiguous or sending call has no successor. Receipt membership freezes the
successful response-recorded call plus the complete failed-pre-egress
predecessor chain. The exact fields, proof schema and hash are normative in
`contracts/receipts.md`.

Langfuse export is a separate durable delivery machine:
`pending → sending → confirmed | ambiguous`, with immutable export body/
hash, W3C-valid trace/span IDs, monotonic `delivery_state_version` and
`delivery_attempt_ordinal`. A publisher first CAS-claims
`claim_owner_id`, opaque `claim_token_hash`, incremented `claim_epoch` and
`lease_expires_at_us` while the delivery state remains `pending`; a crash or
expired lease at this stage is safely reclaimable because no egress is allowed
from a mere claim. Only that unexpired owner/token/epoch may CAS
`pending → sending`, set immutable `export_attempt_id`/`sending_started_at_us`,
increment the attempt ordinal and perform the first export write. That CAS occurs
immediately before egress rather than when work is picked up; losing it requires
zero emitted bytes.

The same owner/token/epoch and expected state version are required to record
`confirmed` or direct transport `ambiguous`. Once `sending` commits it never
returns to `pending`, even when no byte is known to have left GRAF, and a stale
writer cannot finalize a newer claim. An expired/crashed `sending` lease is
never reclaimed by a publisher: the sole reconciler takes its own guarded claim,
CASes it to `ambiguous` and appends bounded reconciliation evidence.
Authoritative lookup by stable
`generation_call_id`/observation identity may then CAS `ambiguous → confirmed`;
absence without authoritative no-acceptance proof leaves it `ambiguous` and
never emits a blind duplicate. No delivery transition repeats inference, and
delivery state is not a publication gate.

Feature 195 owns the registry schema, storage, exact-version lookup and
canonical/publication finalizers for immutable `VerifierIdentityV1` and
`VerifierCalibrationManifestV1` bodies/hashes, one mutable
`VerifierCalibrationStatusHeadV1` per manifest and append-only status events.
Feature 200 owns creation of human-grounded manifest instances, qualification
and promotion eligibility, plus production activation, expiry and revocation
commands that use that Feature 195 registry. Status/revocation data never
mutates or participates inside the immutable manifest body. Both finalizers bind
and re-read the exact active status event/epoch; expired/revoked manifests
remain historical and cannot authorize new receipts.

### `TranscriptRegenerationJob` (Feature 197)

One durable job owns transcript-language correction and source replacement; it
is not a summary GenerationCall/attempt. Its normalized fields are:

| Field | Shape | Rule |
|---|---|---|
| `id` | UUID | Immutable job identity and API `job_id`; never derived from request content |
| `workspace_id`, `meeting_id` | UUID | Required composite owner scope |
| `language_tag`, `language_normalization_version`, `language_allowlist_version` | string, string, string | Resolved canonical BCP-47 value and exact registry/normalizer/allowlist identities; an `auto_detect` UI request is resolved before this row exists |
| `expected_source_revision`, `expected_source_basis_hash` | positive integer, hash | Exact Feature 194 current-source fence |
| `access_policy_epoch`, `deletion_epoch`, `transcription_policy_epoch` | non-negative signed-int64 | Immutable reservation fences in `0..2^63-1`; values outside the canonical JSON range fail before reservation |
| `transcription_pipeline_version` | string | Exact provider/import/validation pipeline identity |
| `idempotency_key` | ASCII string | Route-scoped key; never a Workflow/provider identity |
| `request_identity_json`, `request_identity_hash` | canonical body, hash | Business dedupe tuple only; excludes job, retry, Temporal and provider identities |
| `retry_ordinal`, `predecessor_job_id` | uint32, UUID nullable | Initial `0/null`; every successor increments exactly one same-identity predecessor |
| `state`, `state_version` | enum, positive signed-int64 | Durable state plus monotonic client-visible CAS version in `1..2^63-1`, starting at `1`; exhaustion fails closed rather than wrapping |
| `provider_kind`, `provider_correlation_id` | enum/string, string | Immutable caller-generated provider idempotency/correlation identity, required before egress |
| `provider_submit_attempt` | uint32 | Monotonic orchestration attempt; each submit Activity itself has one attempt |
| `provider_operation_id` | string nullable | Provider-issued stable job/operation identity after acceptance or reconciliation |
| `safe_retry_proof_kind`, `safe_retry_proof_hash` | enum/hash nullable | Required together before a terminal `failed` job may have a successor |
| `raw_provider_result_ref`, `validated_transcript_artifact_id`, `replacement_processing_result_id` | scoped UUID nullable | GRAF-controlled raw/imported result chain; each target must belong to this workspace/meeting |
| `replacement_source_revision` | positive integer nullable | Set only by the successful source-pointer transaction |
| `reason_code`, `reconciliation_evidence_hash` | bounded enum/hash nullable | Metadata-only terminal/ambiguity truth outside retained provider/Temporal boundaries |
| `workflow_id`, `workflow_run_id` | string/UUID | Workflow ID derived only from job ID; exact current Temporal run identity |
| `created_at`, `updated_at`, `terminal_at` | timestamp | Transactional lifecycle times; terminal time is nullable until terminal |

State is exactly `submitted | sending | accepted | ambiguous | processing |
succeeded | failed | invalidated` with the transitions in `contracts/api.md`.
The canonical request body/hash contains workspace, meeting, resolved canonical language,
expected source revision/basis, all three epochs, exact transcription pipeline
and BCP-47 normalization/allowlist versions. It deliberately excludes
`idempotency_key`, `id`, retry lineage, Workflow/Run and provider identities so a
proven-safe successor preserves the same business identity while receiving a
new job/Workflow identity.

The database enforces:

- composite FK `(meeting_id, workspace_id) → meetings(id, workspace_id)` and
  workspace-scoped RLS before every read/write; the callback/provider lookup path
  uses the same composite owner check rather than trusting an external ID;
- unique `(workspace_id, meeting_id, idempotency_key)` bound to one immutable
  request body/hash; same key/different identity conflicts;
- a partial unique active business identity and a partial unique active source-
  replacement owner for `(workspace_id, meeting_id, expected_source_revision)`,
  so equivalent requests join and a competing language cannot create a second
  provider operation against the same current source;
- one nullable composite self-FK predecessor in the same workspace/meeting and
  business identity, unique non-null predecessor, exact
  `retry_ordinal=predecessor.retry_ordinal+1`, and reservation only from locked
  terminal `failed` plus positive safe-retry proof and fresh fences; public
  `successor_job_id` is derived from that unique reverse edge, and inserting it
  increments the locked predecessor's `state_version` in the same transaction;
- unique immutable `(provider_kind, provider_correlation_id)` from insertion and
  unique non-null provider operation identity within that provider;
- composite same-workspace/meeting FKs for raw provider evidence, validated
  transcript artifact and replacement `ProcessingResult`; no UUID-only content
  reference is accepted; and
- guarded state/version transitions: every client-visible state, reason,
  retry-proof/action, successor or replacement-revision mutation increments
  `state_version` in the same transaction, while frozen request/provider/result
  fields cannot be rewritten after their owning transition.

`workflow_id` is deterministically namespaced from immutable job `id` and uses
Temporal `WorkflowIdReusePolicy=REJECT_DUPLICATE`; it is never the reusable
`request_identity_hash`. An already-started result re-reads this row. A successor
has a new job/Workflow ID and cannot overwrite or reuse the predecessor's run.

`provider_correlation_id` is durable before `submitted → sending` and before any
network I/O. The provider must support authoritative lookup by that correlation/
returned operation identity or a signed callback carrying it; otherwise the
integration is unavailable for regeneration. The submit Activity has
`maximum_attempts=1`. The Workflow may schedule another submit Activity for the
same job/correlation only after a committed typed no-egress proof; definitive
authenticated rejection commits `sending → failed`, while timeout, crash,
connection loss or uncertain acceptance commits `ambiguous` and can advance only
through authoritative reconciliation. No `ambiguous`, `succeeded` or
`invalidated` row may acquire a successor.

The authenticated `GET current` and `GET by job_id` projections use this
composite scope and `state_version`; authorization/deletion checks precede
lookup and `If-None-Match`. Their ETag and typed post-commit event contain no
provider identity or content and cannot start/retry work.

Successful replacement locks `meeting deletion fence → current-source pointer →
transcript job → replacement source → summary slots sorted by template key →
coalesced DispatchIntents` and commits exactly one new current-source pointer,
job success and saved-type stale/fan-out set. Every slot selected for fan-out has
a current old-source outcome, active saved status and currently available type.
Unsaved or retired catalog rows cannot enter the set. A fence/source conflict
commits no pointer/stale/intent mutation and invalidates the job; retained
provider evidence remains audit-only.

#### Lifecycle and deletion accounting

`TranscriptRegenerationJob`, each raw/validated imported result, replacement
`ProcessingResult`, transcript/segment artifact, temporary object and callback/
poll evidence is registered in the existing deletion inventory with the same
workspace/meeting composite owner. RLS covers active rows and metadata-only
deletion records. Entering `deleting` invalidates or fences the job before any
new submit/import/source mutation; a late provider result remains non-publishable.

The GRAF purge removes content-bearing job/result fields, Postgres transcript/
`ProcessingResult` rows, object-store transcript artifacts and temporary/cache/
queue copies. Before removing an external-operation reference needed for
dependency cleanup, the existing deletion workflow writes a restricted
metadata-only provider tombstone; after disposition it retains only the bounded
deletion evidence required by that workflow, never readable transcript content
or a recoverable meeting result. The report records exact
`mediascribe_dependency_state` as `not_submitted |
submitted_delete_supported | delete_requested | delete_confirmed |
retention_window_pending | delete_not_supported | unknown`; unsupported or
unknown deletion remains a disclosed dependency limit.

Temporal Workflow/History is deliberately separate retained observability under
operator policy. Meeting deletion stops future useful work through the deletion
fence and may terminate the execution, but does not erase retained History. Its
dependency record is reported separately from GRAF purge/tombstone completion
and never makes History a meeting-readable artifact or a failed GRAF purge.

### `MeetingCanonicalSourcePointer` (Feature 194 foundation; Feature 197 mutation)

The current codebase often resolves transcript truth through a
`latest_processing_result` query. Language regeneration and concurrent
publication require an explicit pointer instead. Feature 194 adds one row per
`(workspace_id, meeting_id)` with `current_processing_result_id`, positive
`source_revision`, exact `source_basis_hash`, canonical transcript
`language_tag`, `source_policy_epoch`, `created_at` and `updated_at`. A composite
FK proves that the target ProcessingResult belongs to the same workspace and
meeting; a composite unique target key is added if the existing table lacks it.

All post-cutover transcript/summary reads, canonical-artifact reservations,
publication source fences and regeneration requests resolve this pointer, never
`ORDER BY result_version/created_at DESC LIMIT 1`. Legacy backfill points only to
one structurally complete, non-deleted unambiguous current ProcessingResult;
missing/ambiguous meetings retain an honest source-unavailable state until
reconciliation and are never guessed. The cutover inventory classifies every
remaining `latest_processing_result` caller as historical/admin-only or removes
it from runtime current-source truth.

Feature 197 replacement locks this pointer `FOR UPDATE`, compares both expected pointer
revision and source-basis hash, then increments `source_revision` and moves the
target in the same transaction as job success/stale fan-out. Summary finalizers
lock it `FOR SHARE` before any slot, making their source check stable through
commit.

## New entity: `MeetingSummarySlot`

Purpose: minimal explicit index from `(meeting, summary type)` to exactly one current revision.

| Field | Shape | Rule |
|---|---|---|
| `id` | UUID | Primary key |
| `workspace_id` | UUID | Required; same as meeting and outcome |
| `meeting_id` | UUID | Required; owning meeting |
| `template_key` | string(120) | Stable type identity across template versions; API/receipt limit is 1..120 UTF-8 bytes |
| `current_outcome_set_id` | UUID nullable | Exact current published revision; null only before first successful publication or after controlled purge |
| `current_binding_class` | enum nullable | `verified_complete | migrated_legacy_read_only`; present iff current pointer is present |
| `legacy_migration_proof_hash` | hash nullable | Required iff `current_binding_class=migrated_legacy_read_only`; exact domain-separated proof of the pre-migration pointer/scope/type/source snapshot |
| `is_meeting_default` | bool | At most one true slot per workspace/meeting; fixed before automatic dispatch or legacy compatibility egress |
| `default_resolution_source` | enum nullable | `explicit_meeting | owner_personal | workspace | legacy_pointer`; set only when `is_meeting_default=true` |
| `default_resolution_version` | string nullable | Opaque exact settings/template resolver version or hash used to choose the default |
| `default_resolved_at` | timestamp nullable | Transactional snapshot time |
| `created_at` | timestamp | Audit metadata |
| `updated_at` | timestamp | Pointer transition metadata |

### Constraints

- Unique `(workspace_id, meeting_id, template_key)`.
- API, slot, attempt, outcome and receipt validation use the same exact
  `template_key` limit: 1..120 UTF-8 bytes after no normalization. PostgreSQL's
  `varchar(120)` character bound is not treated as the validator. Exact 120-byte,
  121-byte, multibyte Unicode and API/DB/receipt round-trip fixtures are required.
  `output_language` remains the existing ASCII BCP-47 field with one shared
  1..16-byte limit and exact 16/17-byte fixtures across API, outcome and receipt.
- Partial unique `(workspace_id, meeting_id)` where `is_meeting_default=true`; source/version/time are all present exactly when the marker is true.
- The migration adds the named ORM/migration parity constraint
  `uq_meetings_id_workspace_id` on `meetings(id, workspace_id)` and
  a composite FK from `(meeting_id, workspace_id)` with `ON DELETE CASCADE`, so
  even a null/empty slot cannot pair a meeting from one workspace with another
  workspace ID.
- Target outcome must match workspace, meeting and `template_key`. The migration adds a unique target key on `(id, workspace_id, meeting_id, template_key)` and a composite foreign key from the slot so a cross-workspace, cross-meeting or cross-type pointer cannot commit.
- A non-null current pointer requires one binding class. `verified_complete`
  requires `provenance_state=complete` and a null legacy proof.
  `migrated_legacy_read_only` requires `provenance_state=legacy_incomplete`, a
  valid migration proof hash and the exact pointed pre-migration row. No runtime
  publisher may create that class. Clearing the current pointer clears both
  fields; verified refresh atomically changes the class to `verified_complete`
  and clears the proof.
- Slot pointer changes only through the private `ai_service.py` CAS primitive.
  Feature 183 exercises it only with DB-only non-model fixtures; Feature 195's
  sole publication entry point invokes it after all receipt gates. Any future
  rollback must reuse the same fenced path.
- Slot contains no summary text, prompt body, transcript or model response.
- Deletion purges the slot with other GRAF-controlled meeting artifacts.

Feature 197 owns the precedence decision (`explicit meeting` → policy-authorized owner/personal choice → workspace) and atomically marks the selected slot before it creates the durable generation intent. Feature 183 owns the storage/invariant and consumes only that persisted marker. For legacy meetings with no marker, compatibility resolution may use the existing versioned workspace default exactly once, reserve/mark that slot and create egress in the same transaction; if the type/result is missing, stale, retired or unavailable, it fails without choosing another type.

## Stable type identity

- Built-in type: existing `template_key` is treated as an opaque stable identity. Legacy names that contain a suffix such as `-v1` keep that exact key when a v2 template snapshot is introduced; the version belongs only in `template_version`.
- Auto uses stable user-visible `template_key=auto`. Its immutable revision
  provenance stores the resolved profile key/version, confidence and resolver
  basis; low-confidence `general_summary` is an internal profile fallback and
  never becomes a different slot key.
- Personal type: `personal-<uuid>` key already remains stable across versioned `SummaryTemplate` rows.
- Template version is a generation snapshot, not a separate slot.
- Retiring/deleting a personal template changes catalog availability, not slot identity or immutable outcome content. A slot with a current result remains readable as an archived-format snapshot; new ensure/refresh/default selection is denied by the catalog resolver.
- An explicitly pointed legacy outcome without a trustworthy key is metadata-normalized once to the reserved `legacy-default` compatibility key before the composite pointer is created; its text, items, source basis and provenance remain unchanged. Unpointed or ambiguous rows are never normalized or selected by runtime guessing.

`SummaryTypeCatalogEntryV1` is a versioned API read model, not another content
or slot table. It joins the exact template snapshot, localized catalog policy,
availability and opaque reference/provenance metadata, then returns server-owned
`catalog_group`, semantic `category`, `quick_rank` and `full_rank`. One response
contains one `catalog_version`; state changes may update badges but never reorder
that snapshot. Feature 198 owns built-in rows, Feature 199 personal rows and
Feature 196 presentation persistence.

## State model

```text
slot absent
  └─ generate(type) → internal candidate
       ├─ invalid/failed/stale/deleted → slot remains absent
       └─ Feature 195 verified + fences pass → slot(current=R1)

slot(current=R1)
  └─ refresh(type) → internal candidate R2; R1 remains visible
       ├─ invalid/failed/stale/deleted/conflict → slot(current=R1)
       └─ Feature 195 verified + CAS(R1) → slot(current=R2), R2 supersedes R1

slot A(current=A1) + slot B(current=B1)
  ├─ refresh A → only A may change
  └─ refresh B → only B may change

exactly one slot may additionally be marked meeting-default;
changing presentation selection never changes that marker
```

Internal attempt states remain implementation-compatible (`queued`,
`generating`, `blocked_dependency`, `candidate`, `failed`, `stale`,
terminal publication state). A candidate outcome uses
`provenance_state=pending_publication` only after Feature 195 adds that schema;
it remains so until the sole publication transaction
fills receipt-dependent provenance and commits it as `complete`; the state is
never user-visible. User-facing projection uses four orthogonal dimensions:
result presence (`ready|absent`), generation attempt
(`idle|preparing|updating|blocked|deferred|error|ambiguous|no_supported_content`),
source (`not_ready|transcript_failed|empty|current|stale`) and catalog
availability (`available|unavailable|retired`). A stale current revision
therefore remains `ready + stale`; a retired type can be `ready + retired`;
neither is confused with a failed attempt.

`source_state` is derived, not stored in the slot: compare the immutable outcome source basis (processing result, media, speaker/source revisions and fingerprints) with the meeting's canonical current basis under the same read/egress fence. The slot still identifies the last-known-good revision when it becomes stale; publication and new egress require `source_state=current`.

When no current revision exists, readiness comes only from the exact target/source/template generation attempt. An active attempt projects `preparing`; terminal attempts remain distinct as `blocked`, `deferred`, `error`, `ambiguous` or type-scoped `no_supported_content`. Meeting-scoped source states own transcript processing/failure/empty and prevent pointless type generation. Catalog availability owns unavailable/retired. No slot pointer, newest outcome row or unrelated attempt is used as fallback.

## Feature 195 publication transaction (downstream contract)

This section is normative for Feature 195 and deliberately not executable by
Feature 183. Feature 183 stops at the meeting/slot/prior-current CAS subset and
returns `verified_runtime_unavailable` for every model-generated candidate.

Canonical verification and outcome publication are two transactions that share
one relative row-lock order.

The earlier Feature 195 canonical-finalization transaction locks
`meetings(id, workspace_id) FOR SHARE`, the exact current
`MeetingCanonicalSourcePointer FOR SHARE`, the parent artifact, every
artifact-owned GenerationCall in deterministic order and the mutable
calibration status head `FOR SHARE`. It reconstructs the canonical payload
and the complete promotion-event binding shared by the parent and every call,
re-fetches/re-hashes the passing event and performs the artifact owner's one
allowed receipt-column transition. The
pointer must still identify the artifact's exact source revision/basis; missing,
replaced or mismatched pointers fail before receipt finalization. The transaction
does not create or lock a summary slot. After all locks and checks, its final
conditional owner-row statement obtains one PostgreSQL `clock_timestamp()`,
injects that exact microsecond value into the canonical receipt, canonicalizes/
hashes it in the versioned database finalizer, checks the locked freshness
deadline and returns the exact stored bytes. Transaction, statement, caller and
earlier-read clocks are forbidden.

The later outcome finalize-and-publish transaction:

1. Locks `meetings(id, workspace_id) FOR SHARE`; the deletion writer uses
   `FOR UPDATE` on that same row before changing deletion state/epoch.
2. Locks the exact current `MeetingCanonicalSourcePointer FOR SHARE` and proves
   it still identifies the candidate's parent artifact source revision/basis;
   source replacement uses `FOR UPDATE` on this row.
3. Reserves the target slot with `INSERT ... ON CONFLICT DO NOTHING`, then
   selects that exact slot `FOR UPDATE`; a unique conflict is re-read inside the
   transaction.
4. Asserts that the slot current pointer equals the expected pointer.
5. Locks the outcome-generation attempt, which owns the publication receipt
   columns.
6. Locks the exact `DispatchIntent` that this transaction will finalize.
7. Locks the frozen `pending_publication` candidate outcome.
8. Locks its parent canonical artifact, which owns the already-final canonical
   receipt columns.
9. Locks every referenced GenerationCall in ascending `(owner_kind ordinal,
   owner_id UUID bytes, phase ordinal, phase_sequence, generation_call_id UUID
   bytes)` order regardless of caller input order.
10. Locks each relevant mutable calibration status-head row `FOR SHARE` in
   manifest-UUID order and re-reads its exact event, epoch, active status and
   validity interval. Activation/revocation/expiry writers use `FOR UPDATE`
   on the same row; immutable manifest bodies are hash/FK checked, not locked.
11. Locks the prior current outcome if present.
12. Validates workspace/meeting/type binding, every DB-enforced normalized
    outcome↔attempt non-receipt provenance columns,
    `provenance_state=pending_publication`, exact root/activation/extraction
    identities and the immutable attempt-owned `ResolvedRunManifestV1`
    body/hash. It follows the manifest's complete promotion-event binding,
    rehashes the event and embedded qualification record and requires a passing
    target/read-back root and activation equal to this attempt. Receipt-dependent
    outcome fields and fingerprint must still be null.
13. Reconstructs the strict rendered-content payload and both receipt payloads;
    requires exact frozen outcome/content hash, same-type-attempt
    Auto/projection/presentation call set, complete eligible/selected/omitted
    and presentation statement/selected-claim coverage,
    exact Auto action→Action Items/non-action→Key Points mapping and
    exactly-once selected-ID coverage when applicable,
    relation/authorization/critical-retention/presentation-fidelity gates and
    deterministic layout renderer
    version. It follows the artifact binding to the immutable canonical
    owner-row receipt and requires valid calibration, complete source/candidate
    coverage, the byte-equal successful promotion-event binding across parent,
    calls, manifest and both receipts, final semantic-entailment and both
    critical-omission pass states plus post-repair reverify when applicable. Schema/ref/span checks, a
    canonical receipt alone or absent/unfinalized attempt receipt columns cannot
    authorize publication.
14. Re-checks latest processing/media/speaker/source hashes, deletion epoch,
    template/prompt revocation, calibration head and expiry.
15. In one last conditional data-modifying CTE, obtains one
    `clock_timestamp()` after all locks, injects it as `issued_at_us` through the
    vector-tested database canonicalizer, rejects at/after the locked freshness
    deadline, and performs the attempt owner's one allowed pass-receipt finalization, copies
    publication schema/digest to the outcome, computes its provenance
    fingerprint, changes `pending_publication → complete`, marks the prior
    current revision superseded when present, marks the candidate
    current/published, moves the slot CAS and finalizes the exact dispatch in
    this same transaction. This is the sole Feature 195 publication finalizer,
    implemented by extending the Feature 183 `ai_service.py` entry point and
    invoking its private CAS primitive; no second publisher or CAS implementation
    is allowed. `RETURNING` must equal the stored issued time/body/digest; a
    zero-row result rolls back every transition.

Any failure before commit leaves the old pointer intact.

The global order is always meeting deletion fence → current canonical-source
pointer → transcript-regeneration job when touched → target slot(s) sorted by
template key/UUID → attempt
→ dispatch intent → candidate outcome → parent canonical artifact →
deterministically sorted GenerationCall rows → calibration manifest/status
head → prior current outcome. There is no receipt-row lock. Calibration
activation/expiry/revocation writers lock that same mutable status head
`FOR UPDATE` before
appending an event and incrementing its epoch. A transaction touching only a
subset preserves the relative order and never acquires an earlier class after a
later class. Same-type writers serialize on one slot; different-type writers
may proceed independently after the shared meeting deletion check.

Canonical/publication finalizers lock the source pointer `FOR SHARE`; Feature
197 replacement locks it `FOR UPDATE`. Source replacement then locks its job,
all affected saved slots and coalesced dispatches in the global order. It never
locks a slot first and then returns to the source pointer.

Feature 195 race/deadlock fixtures cover deletion writer versus each finalizer, canonical
finalization versus first publication,
publication versus call/dispatch reconciliation, reversed caller ordering for
multiple calls, calibration activation/revocation on both sides of the
linearization point, same-type writers and cross-type writers. Each fixture
must end with one documented serialization winner or bounded failure, never a
deadlock, partial receipt, finalized dispatch without publication or published
slot with an unfinished dispatch.

## Existing egress records reused

- `MeetingShareGrant.metadata_json` records the compatibility `template_key` and exact `outcome_set_id` in the same transaction that activates the summary-bearing grant.
- `ExportPackage.manifest_json` and generated export selection record the same exact pair in the artifact-creation transaction.
- Egress readers validate the recorded pair against meeting/workspace/type and access/deletion policy; they never resolve a newer attempt or another type.
- The successful grant/artifact write is the egress linearization point. A refresh committed before the resolver locks/validates the slot may be selected; a refresh committed after that write cannot mutate the recorded pair.
- Feature 203 may replace JSON-backed compatibility pins with first-class arbitrary-type UX/contracts if evidence justifies it; Feature 183 adds no second share/export ledger.

## Deletion visibility

The meeting deletion state/epoch is checked before every summary read, publication and egress action. As soon as the meeting enters `deleting`, slot content is unavailable to users and no new publication/share/export can begin; physical slot/outcome purge follows the existing deletion workflow. Retained `GenerationCall`, Langfuse observations and Temporal History remain outside that GRAF purge exactly as the constitution requires.

## Legacy migration

| Legacy state | Result |
|---|---|
| Explicit meeting pointer to valid same-scope `complete` outcome with key | Create/update one `verified_complete` slot to that exact outcome |
| Explicit meeting pointer to same-scope `legacy_incomplete` outcome with key | Create one `migrated_legacy_read_only` slot plus proof; exact result is readable but cannot create new egress |
| Explicit meeting pointer to valid same-scope legacy outcome without key | Normalize only that pointed outcome to reserved `legacy-default`, then create the exact `migrated_legacy_read_only` compatibility slot/proof |
| Explicit pointer target missing/cross-scope | Do not guess; report metadata-only failure |
| No pointer, one or more historical rows | Do not infer a current result or create a slot; report metadata-only `missing_explicit_legacy_pointer` (and row count/classification for operators without content) |
| Deleted/deleting meeting | No publication/backfill |

Migration is idempotent and never rewrites outcome text or source snapshots. The
legacy proof is
`SHA-256("GRAF-LEGACY-SLOT-PROOF\0v1" || uint64be(byte_length) ||
canonical_json({workspace_id,meeting_id,template_key,outcome_set_id,
source_basis_hash,pre_migration_pointer_kind}))`. It is created only by the
migration from the locked pointer and target; a second run must reproduce the
same bytes. A `legacy_incomplete` row without that exact slot/proof is invisible
to ordinary reads. New share/export from a migrated legacy slot is denied; an
already pinned historical artifact remains governed by its existing access and
deletion contract. A later successful same-type refresh publishes a new
`complete` revision and replaces the slot class/proof atomically.

Database downgrade fails closed once multiple type slots or otherwise non-representable mappings exist; a single legacy pointer cannot safely encode them. Code rollback may leave the table intact and unused until forward recovery.

## Invariants

- One current revision per slot.
- One slot per meeting/type.
- At most one persisted meeting-default slot with complete resolver provenance.
- A current revision belongs to the same meeting/workspace/type.
- An empty slot belongs to the same workspace as its meeting even before first publication.
- Feature 183 has no successful model-generated transition; Generation Call or
  candidate existence never implies publication and the fail-closed entry point
  cannot move a slot or finalize a DispatchIntent.
- After Feature 195, every newly generated revision has one same-scope immutable attempt and one exact root/manifest bundle identity; legacy gaps remain explicitly incomplete.
- `legacy_incomplete` can be current/readable only through one exact
  `migrated_legacy_read_only` slot and migration proof; it can never be newly
  published or create new egress, and verified refresh replaces rather than
  upgrades that immutable row.
- After Feature 195, a `pending_publication` candidate is internal, has a complete immutable
  resolved-run body/hash, null receipt-dependent outcome provenance and cannot
  be current/read/shared/exported; the publication transaction alone may make
  all dependent fields `complete` atomically.
- A supersession edge connects revisions of the same slot and is acyclic.
- Generation failure never changes a slot.
- Generation Call retention never implies publication.
- Summary-bearing grants/exports pin exact type and slot revision in their existing metadata/manifest records.
- Shared-slot Receipt V1 rejects generated `my_actions`, `private_self` and
  every other subject-dependent projection. Feature 199 rejects those fields;
  a future Feature 208 subject-scoped slot must
  include authenticated subject and trusted participant-mapping/policy identity
  in its unique key and receipt before such generation is enabled.

## Downstream canonical intelligence parent (Features 194–195)

Feature 183 does not create this table, but the program no longer leaves reuse
as an implied cache. Features 194–195 add one
`MeetingIntelligenceArtifact` parent with the logical identity, active/verified
uniqueness, lifecycle states, workflow ownership, waiter joins,
failure/reconciliation/retry ordinal, RLS, expiry, revocation and deletion rules
specified in [temporal-langfuse.md](temporal-langfuse.md#canonical-artifact-identity-and-coalescing),
including one extraction-layer manifest hash over every extraction- or
verification-affecting component and exact calibration-manifest ID/hash rather
than one prompt-member identity. Expired/revoked parents remain historical;
replacement calibration produces a distinct identity and reservable successor.
When that pipeline is enabled, both `MeetingOutcomeGenerationAttempt` and its
rendered `MeetingOutcomeSet` carry the same non-null
`meeting_intelligence_artifact_id` and extraction-layer identity through a
composite same-workspace/meeting/source/manifest FK. Publication locks that
artifact and revalidates `verified`, source/deletion epoch, expiry and revocation
inside the slot transaction. No type projection may reread the transcript or
publish from a reserved/failed/ambiguous/revoked parent; source change,
revocation or deletion between projection and publication leaves the old slot
unchanged.
