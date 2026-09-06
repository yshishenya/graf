# Contract: summary type publication lifecycle

## Product terminology

- **Тип итогов**: stable format identity.
- **Актуальная версия**: current published revision for one type.
- **Обновление**: generation of a replacement revision for that same type.
- **Внутренний кандидат**: non-user-facing pre-publication state.

UI must not ask users to accept/reject normal generations.

## Commands

### `ensure(type)`

- Existing current revision: return it; no inference.
- Equivalent active attempt: return its status; no duplicate dispatch.
- No revision/attempt: create one fenced attempt.

### `refresh(type, expected_current)`

- Keeps expected current revision visible.
- Creates at most one equivalent active attempt.
- Publishes automatically only after all gates pass.

### `publish(candidate, expected_current)`

Internal-only entry point. Feature 183 always rejects model-generated success
and exposes only its private DB-only expected-current CAS primitive. Feature
195 extends this same entry point with receipt reconstruction/finalization and
is the first feature allowed to invoke the CAS for a model-generated candidate.
It is never exposed as a user accept action, and no second publisher or CAS
implementation is permitted.

Technical history keeps a later rollback possible, but Feature 183 does not add an operator or user rollback command. If real recovery demand appears, a later scoped feature must reuse the same binding, source-policy, deletion and CAS checks without mutating revision content.

### Internal model invocation (Feature 195)

Every model phase reserves one exact GenerationCall through a network-free,
retryable prepare Activity. Its invoke Activity has `maximum_attempts=1` and may
send only after committing `prepared → sending` for its immutable attempt/
correlation identity. A retry, replay, reset or stale worker that sees anything
other than `prepared` sends nothing. Response bytes are durably recorded before
validation; crash/timeout after `sending` is `ambiguous` and wait-only.

A new bounded successor call is legal only after the exact predecessor reaches
`failed_pre_egress` with a fetched/rehashed authenticated
`ProviderNoEgressProofV1` from the gateway. `sending` and `ambiguous` never
authorize retry. This internal state projects through the existing attempt
`ambiguous`/`wait` contract and never adds a user approval step.

### `regenerate_transcript(language, expected_source_revision)` (Feature 197)

- Authenticated/authorized and CSRF-protected for cookie sessions; binds the
  canonical BCP-47 language, current source revision, access/deletion/
  transcription-policy epochs, idempotency key and exact pipeline version.
- `request_identity_hash` is the reusable business dedupe tuple, never the job
  UUID or Temporal identity. Same key plus same business identity returns one
  exact job; same key plus different identity conflicts; another key for an
  equivalent non-terminal identity coalesces.
- The first job has `retry_ordinal=0`; a retry is a new job with a new key,
  Workflow ID, incremented ordinal and exact predecessor. It may exist only
  after the locked predecessor is terminal `failed`, carries positive safe-retry
  proof and every bound fence is fresh. `ambiguous`, `succeeded` and
  `invalidated` never authorize a successor.
- Workflow ID is derived from immutable `job_id` and starts with
  `REJECT_DUPLICATE`; the reusable business hash is never a Workflow ID. An
  already-started result is resolved by re-reading the same job.
- One immutable provider correlation/idempotency ID is committed before egress.
  The submit Activity has `maximum_attempts=1`; orchestration resubmits the same
  operation only after durable proof of no egress. Definitive provider rejection
  is terminal `sending → failed`; possible acceptance becomes `ambiguous` and
  waits for required authoritative lookup or signed-callback reconciliation.
- Until confirmed success, the old source/result set remains authoritative.
- Confirmed success enters the sole source-replacement transaction. It rechecks
  every fence, moves the source pointer once, marks saved old-source slots stale
  and coalesces one replacement intent per active saved available type. Unsaved
  and retired types are never generated.
- Source/access/policy/deletion change invalidates the job; retained provider
  output cannot overwrite the winning source or trigger fan-out.

The durable job states and browser mapping are exactly those in
`contracts/api.md`; provider-internal states or errors are not product states.
Every public projection carries monotonic `state_version`. Authenticated
authorization-first `GET current` and `GET by job_id`, conditional ETag polling
and the typed post-commit event recover the exact job after reload/reconnect and
never start work. Missing, inaccessible, cross-scope and deleted targets use one
no-existence-leak denial shape; authorization runs before lookup and
`If-None-Match` evaluation.

## Publication gates

These are the complete future positive gates. Feature 183 can enforce its
slot/source/access/deletion preconditions but MUST fail closed because it does
not create or accept the Feature 194/195 canonical artifact, GenerationCall,
calibration or receipt proofs. Feature 195 owns the first test in which all
gates pass and a model-generated slot moves.

All must pass:

1. candidate and outcome exist and are structurally complete;
2. deterministic evidence refs, exact spans/normalization and source identity valid;
3. mandatory calibrated semantic entailment passes for every model-generated
   canonical claim, critical or non-critical; a matching quote/ref is necessary
   but never sufficient to prove the speech act or factual wording;
4. mandatory critical-omission checks pass at both source-shard → candidate and
   candidate → canonical levels; failed entailment of any canonical claim, any
   critical omission, or an unavailable, uncalibrated or invalid verifier blocks
   the entire candidate rather than downgrading the gate or dropping the failing
   object;
5. later explicit user edits to mutable owner/due fields are authorized user
   facts with their own audit provenance and are not rejudged as transcript
   claims;
6. exact meeting/workspace/type plus immutable attempt/root-bundle binding;
7. processing/media/speaker/source revisions current;
8. deletion state/epoch current;
9. prompt/template/schema/model bundle not revoked;
10. candidate not expired;
11. slot pointer equals expected current;
12. authorization/audit context valid.

## Failure semantics

| Failure | Slot effect | User result |
|---|---|---|
| Provider/dependency unavailable | None | Current version if present; otherwise honest unavailable/preparing state with bounded automatic recovery |
| Invalid schema/evidence/canonical claim or critical omission | None | Current version if present; otherwise no published result and a calm type-scoped explanation |
| Source changed | None | Every active saved old-source slot is labelled stale; old revisions remain readable, new egress is blocked and Feature 197 creates one bounded coalesced replacement intent per active saved available type, default/current first; unsaved/retired types are not generated |
| Same-type conflict | None | Show the newer current revision |
| Different-type concurrent success | Own slot only | Both types become available |
| Custom type retired after publication | None | Saved revision remains read-only; ensure/refresh/default mutation denied |
| Meeting deleting/deleted | None | Content unavailable according to deletion contract |
| Langfuse delivery unavailable after retained call | Not a publication gate | Publisher retries independently; no repeated inference |
| Transcript regeneration failed/ambiguous | None; old source and summaries remain | Failed with proven-safe retry or wait-only ambiguous state |
| Transcript replacement confirmed | Saved old-source slots become stale; no immediate pointer loss | Default/current saved type recovers first, then other saved available types |

## Read contract

- Explicit type → exact slot current revision.
- No explicit type → exact slot marked as the persisted meeting default. Feature 197 writes its resolver source/version/time before dispatch. Only legacy meetings without a marker may run and persist the documented workspace resolution once; the requesting user's selected/personal presentation preference never changes compatibility reads or egress.
- No current revision → honest state; never newest outcome fallback.
- Saved revision remains readable without AI dependencies.
- Saved revision from a retired custom type remains readable under its immutable snapshot, but cannot be ensured/refreshed or made a new default.
- A revision based on an older canonical source is returned only with explicit `stale` state; it is not presented as current-source truth.

Generation attempt, source readiness/freshness, result presence and type availability are independent lifecycle dimensions. `transcript_failed`, meeting-level `source_empty`, type-level `no_supported_content`, `retired`, `unavailable`, `deferred`, `blocked` and provider-`ambiguous` are never aliases for each other.

## Idempotency and replay

- Existing `MeetingOutcomeGenerationAttempt.idempotency_key` and `DispatchIntent` remain the durable request ledger; no second request table is added.
- Request identity includes workspace, meeting, type, source basis, template/bundle version, intent and expected current revision. Reusing a key with different identity fails closed.
- Reusing the same key after a lost response returns the same terminal attempt plus the slot's current revision. It never repeats inference or publication, including when that revision was later superseded.
- Concurrent first `ensure` calls serialize through the target slot reservation. Different keys for the same equivalent active identity coalesce to one attempt; a unique-conflict is re-read, not treated as permission to dispatch again.
- Transcript regeneration uses its separate durable job identity because it
  replaces the canonical source rather than one summary slot. Replay resumes the
  exact job/provider operation and source transaction; it cannot reinterpret a
  timeout as permission to submit again. A terminal retry is an explicit
  successor job, never a reused Workflow execution or overwritten predecessor.

## Transcript regeneration privacy and deletion

- `TranscriptRegenerationJob` owns a composite workspace/meeting FK and RLS;
  every referenced provider result, replacement `ProcessingResult`, transcript
  artifact and canonical-source target repeats the same workspace/meeting scope
  in its FK. Cross-workspace, cross-meeting and callback/provider-ID substitution
  fail before state changes and expose no existence detail.
- Entering `deleting` wins every reservation, submit, callback/poll, result
  import and source-replacement race. Public reads/events stop immediately; a
  retained provider response cannot restore the meeting or move its source.
- The existing deletion lifecycle registers the job, GRAF callback/result
  metadata, temporary processing state, every created/replacement
  `ProcessingResult` and transcript artifact. GRAF-controlled content and active
  references are purged; only the existing metadata-only deletion/provider
  tombstone needed to prove dependency disposition remains under RLS.
- The deletion report carries exact `mediascribe_dependency_state` as
  `not_submitted | submitted_delete_supported | delete_requested |
  delete_confirmed | retention_window_pending | delete_not_supported | unknown`.
  Unsupported or unknown provider deletion is a dependency limit, never a claim
  of complete end-to-end erasure.
- Temporal execution/History is a separate retained observability dependency
  under operator policy. Deletion may signal/terminate future workflow work and
  purge GRAF rows/artifacts, but it does not erase retained History or expose it
  as a readable meeting artifact; the deletion report discloses that retention
  separately rather than counting it as a failed GRAF purge.

## Egress contract

Feature 183 compatibility share/export resolves the persisted meeting-default slot (or performs the one-time legacy workspace resolution), then records exact `template_key` and `outcome_set_id` in the existing grant/audit or export manifest. Default-marker write when needed, revision validation and artifact/grant write form one transaction and the successful write is the linearization point: a refresh committed before it may be selected; a refresh committed after it cannot alter the artifact/link. Creation of new egress from a source-stale or retired default revision is blocked until an available current-source default revision is published. Feature 203 later adds arbitrary selected-type egress and the complete user-facing share/export workflow.
