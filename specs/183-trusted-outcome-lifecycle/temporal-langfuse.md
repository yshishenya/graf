# Temporal, LiteLLM and Langfuse Runtime Contract

## Versioned Workflow and typed boundary contract

Feature 195 does not mutate the existing workflow incompatibly. After its
response-persistence, ambiguity, cancellation, history-budget and replay gates
pass, new pipeline runs use:

```text
MeetingOutcomePipelineV2
outcome-v2-interactive
outcome-v2-automatic
outcome-v2-background
```

The three names after the Workflow Type are dedicated V2 Task Queues. The V1
Worker continues polling only its existing queue; no V1 Worker polls a V2 queue
and no V2 Worker polls the V1 queue. New submissions switch to V2 only after a
canary. An operator recovery note is not a substitute for the executable gates
below.

### Worker Deployment V2 activation and retirement runbook

Every V2 Workflow declares `VersioningBehavior.PINNED`, and every Python Worker
on each V2 Task Queue is constructed with the equivalent of this exact
deployment contract:

```python
WorkerDeploymentConfig(
    version=WorkerDeploymentVersion(
        deployment_name="graf-outcome-v2",
        build_id=immutable_build_id,
    ),
    use_worker_versioning=True,
    default_versioning_behavior=VersioningBehavior.PINNED,
)
```

`immutable_build_id` is derived from the immutable release artifact digest and
source commit. It is never `latest`, a mutable tag, a branch name or a value
reused for different bytes. The same deployment name/build ID identifies the
candidate on all three V2 queues. Startup fails if Worker read-back does not show
`use_worker_versioning=true` and `PINNED`, or if the artifact digest previously
recorded for that build ID differs. Workflow declaration, Worker default and
per-run typed provenance must agree; no unversioned fallback is allowed.

Activation is performed in this order:

1. Freeze an activation record containing namespace, Server/SDK versions,
   deployment/build ID, artifact/commit hashes, all three Task Queues, previous
   current/ramping versions, preregistered ramp percentages and the measured
   namespace `visibility_convergence_s` bound.
2. Freeze a replay-corpus manifest. It contains every retained approved history
   for each production build that still owns an open or queryable retained
   execution, every shipped Workflow/Activity payload schema version, and
   synthetic histories for every terminal/failure branch, timer, Activity retry,
   cancellation, signal/update, continue-as-new, reset and reconciler path. Each
   entry binds Workflow ID, Run ID, Workflow Type, source build ID, history hash,
   boundary-schema inventory and expected replay result. Complete paginated
   Visibility exports and retained-history inventories are reconciled to the
   manifest by count, sorted identity list and aggregate hash; sampling or a
   representative-only corpus is not a completeness proof.
3. Replay the complete manifest against the candidate bytes with zero
   nondeterminism or payload decode failures. Register the candidate Deployment
   Version, start its pollers on all three V2 queues and read back the exact
   deployment/build/config tuple before allowing a start.
4. Set only the candidate as ramping for the first preregistered percentage.
   Advance each recorded step only while replay, provider-ambiguity, workflow
   error, schedule-to-start, backlog and fairness gates pass. A failed step sets
   the previous healthy version for new starts; already PINNED executions stay
   on their assigned build.
5. After the final ramp passes, make the candidate current and read back the
   exact current version. A single successful control-plane response is not
   stable evidence: after at least `visibility_convergence_s` from the last
   mutation, take two complete, identical Deployment/Visibility snapshots at
   least `visibility_convergence_s` apart. Each snapshot records query/filter,
   page count, observation time, sorted execution IDs and result hash.

Retiring one old V2 Deployment Version is a separate operation. First prove it
is neither current nor ramping and prevent new starts from selecting it. Keep its
pollers available while open executions remain. After the last close, wait the
declared convergence bound and collect the same two identical paginated
snapshots. Only then stop that version's pollers and collect one retirement
evidence bundle in which all of these predicates hold together:

```text
DrainageStatus = drained
open executions pinned to exact deployment/build ID = 0
pollers for exact build ID on each of the three Task Queues = 0
exact deployment/build ID is current = false
exact deployment/build ID is ramping = false
both post-convergence Visibility snapshots are complete and identical
```

`DrainageStatus`, poller description and Visibility are separate authorities;
none substitutes for another. Any non-zero, unknown, truncated page set,
`draining`/unspecified status or disagreement between the repeated snapshots
keeps the version deployed. Its image, replay manifest and evidence remain
addressable for the configured History retention even after pollers stop.

Closed PINNED executions are never sent to a Worker Query merely to display a
result. The API admits a Workflow Query only after an authoritative Describe
shows the execution is open; a close-after-check race returns a typed closed
result and reads GRAF's persisted state or retained History/Visibility instead.
No old Worker stays alive solely so a closed execution can be queried, and a
closed Query failure is not counted as an undrained open execution.

Recovery uses this closed decision matrix; every target is an already registered
immutable Deployment Version whose full affected history replays successfully:

| Situation | Recovery | Required proof and prohibition |
|---|---|---|
| Candidate harms only new starts | Move ramp/current back to the previous healthy version | Do not override, reset or migrate healthy already PINNED runs |
| One open PINNED run can replay its complete history on a compatible healthy/hotfix build | **Versioning Override** to that exact deployment/build ID | Record execution/run, old/new build, full replay PASS and operator approval; never target implicit current |
| The complete history is incompatible, but replay passes from one operator-approved pre-failure event | **Reset-with-Move** to the exact healthy build | Record reset event, new Run ID, side-effect/idempotency reconciliation and approval; preserve the old Run/history |
| Provider or Langfuse egress is completed or ambiguous | Neither until authoritative reconciliation | Override/reset must not repeat inference, provider submission or observability export |
| Execution is closed | Neither | Read persisted state/history; do not reopen it through Query, override or reset |

Reset-with-Move is allowed only when every side effect after the reset point is
classified and a completed/ambiguous GenerationCall or provider operation will
be re-read rather than emitted again. Versioning Override is preferred when the
entire history is compatible because it preserves the run and event sequence.
Neither path uses arbitrary current code.

V1 retirement starts by permanently routing all new submissions to V2 and
freezing the exact final V1 artifact. The complete V1 replay manifest must pass;
the legacy queue must then show zero backlog/open executions in two identical
post-convergence paginated snapshots, followed by zero V1 pollers. V1 has no
invented Worker-Deployment drainage value: its evidence uses the real legacy
queue/poller/Visibility authorities, while V2 additionally requires
`DrainageStatus=drained`. The V1 start path and queue name are tombstoned only
after those gates pass. Continue-as-new, retry and reset fixtures must prove that
no surviving execution can request another V1 Workflow Task.

No rollout relies on two code versions polling one unversioned queue without
Worker Versioning.

Every Workflow and Activity boundary has one Pydantic argument object and one
Pydantic result object. The root names are
`MeetingOutcomePipelineV2InputV1` and `MeetingOutcomePipelineV2ResultV1`; each
Activity uses the corresponding `<Phase>ActivityInputV1` and
`<Phase>ActivityResultV1`. Each model contains an explicit positive
`schema_version`. Client and every V2 Worker pin the same
`temporalio.contrib.pydantic.pydantic_data_converter`. Compatible changes are
additive fields with deterministic defaults; removing/changing a field or its
meaning requires a new boundary schema and, when replay compatibility changes,
a new Workflow Type. Serialization round-trips and replay fixtures load every
previously shipped payload before rollout.

## Workflow sequence

```text
1. pin exact promoted bundle, activation manifest, complete immutable binding
   to the successful promotion event, active calibration and
   gateway-route-binding manifests; fetch/re-hash the event and its embedded
   qualification record before any model egress
2. snapshot canonical transcript/source/deletion revisions
3. reuse one compatible non-revoked canonical artifact when available, or
   reserve one shared canonical-generation identity
4. deterministically segment, compile the complete gap-free
   `SourceVerificationCatalogV1`, and calculate coverage/history budget when
   extraction is required
5. start bounded extract-shard child workflows/activities when required
6. resolve canonical intelligence; one-shard no-conflict resolve is a
   deterministic no-op
7. run deterministic verification
8. apply pinned `CriticalityPolicyV1`; run calibrated semantic entailment for
   every canonical claim plus complete source-catalog/source/candidate/canonical
   classification and source→candidate / candidate→canonical critical-omission
   verification
9. run at most one explicit bounded repair round
10. if repaired, rerun the full deterministic, semantic and omission gates
11. in its own transaction, finalize/reuse the artifact-owner-row
    CanonicalVerificationReceipt
12. resolve Auto when requested, compile and hash the one exact full
    `CompositeProfileContractV1`, and for Auto pin the exact
    `AutoSectionMappingPolicyV1` plus Auto presentation-profile body; then apply
    the pinned meeting-intent +
    mixed-audience visibility intersection + privacy + profile/focus/detail
    projection policy; text-topic resolution occurs only in projection batch zero
13. validate exclusive model/no-op proofs and the complete projection partition;
    zero eligible/selected or topic no-match/ambiguity ends as
    `no_supported_content` with terminal evidence; topic-catalog overflow is a
    distinct blocked terminal with the same non-authorizing evidence shape; both
    skip steps 14–18;
    Receipt V1 performs no cross-meeting continuity
14. deterministically map Auto actions to `Action Items` and every other
    selected ID to `Key Points` exactly once, or retain composite sections for
    non-Auto; then run bounded presentation synthesis in the requested output
    language with the same complete composite and conditional mapping bodies
15. run separate deterministic and calibrated presentation verification over
    every statement and selected critical ID with that same body/hash
16. deterministically render layout/markup and persist the frozen
    `pending_publication` candidate plus immutable resolved-run body/hash
17. reconstruct the type-attempt OutcomePublicationReceipt over exact content
18. invoke Feature 183's sole publication finalizer; in one transaction finalize
    the attempt-owner-row pass receipt, complete candidate provenance,
    auto-publish the target type slot and finalize the exact dispatch after both
    receipt layers pass
19. expose the committed attempt/dispatch terminal state
20. independently attempt retained Generation Call delivery to Langfuse and
    record confirmed or ambiguous transport truth
```

## Determinism and payload rules

- Workflow code performs no network, database, filesystem, random or wall-clock I/O.
- All I/O and LLM calls are Activities.
- Every model phase uses the shared prepare/invoke/persist/validate boundary in
  `Retry ownership`; no phase-specific Activity may call LiteLLM directly or
  configure `maximum_attempts>1` for invoke.
- The Workflow owns the immutable composite body/hash and passes it unchanged in
  `ProfileProjectionRequestV1`, `PresentationSynthesisRequestV1` and
  `PresentationVerifyRequestV1`. Each Activity recomputes the hash and clause
  closure before egress; it never resolves a profile label or accepts a
  hash-only body.
- Search Attributes/Memo contain bounded low-cardinality operational metadata only.
- Full transcript remains in Temporal History per current constitution, but deterministic chunks must fit both per-payload and aggregate serialized History budgets.
- Concurrent type generations for the same source/extraction bundle share one
  canonical-generation identity; profile fan-out cannot duplicate transcript
  extraction.
- Near-limit integration tests measure actual history/event overhead, including escaped text and failures.
- V2 uses only its dedicated queues; V1/V2 Workers never compete for the same
  unversioned Task Queue. Old V1 Workers remain until the drain/replay gate above.
- Workflow/Activity arguments and results use the pinned typed boundary and
  converter contract above; raw positional tuples and converter drift are
  rollout blockers.
- Replay gate uses exported sanitized/approved production histories plus synthetic fixtures.

## Canonical artifact identity and coalescing

Feature 194/195 adds one `MeetingIntelligenceArtifact` parent object; it is not
part of Feature 183's slot migration and is not another rendered-summary
ledger. Its logical identity is:

```text
workspace_id
+ meeting_id
+ canonical source-basis hash/revision
+ extraction-layer manifest hash over exact core/extract/resolve/semantic-
  verification prompt versions, canonical schema, source-context policy,
  deterministic segmentation/normalization, source-catalog compiler/schema/
  capacity, `CriticalityPolicyV1` canonical-rules and reason-code subhashes,
  validators/verifiers, model route/settings and exact calibration-manifest
  ID/hash; the profile-expansion/full policy hash is excluded from canonical
  identity and bound only by the resolved run
+ exact root numeric version/hash + activation-manifest hash + complete
  `root_promotion_event_binding`, outside the extraction-layer/root manifest so
  the successful event can authorize the already-hashed root without a cycle
+ canonical schema version
```

The extraction-layer manifest hash is derived independently from projection,
profile and rendering members, so presentation-only changes reuse the parent
while any extraction/verification-affecting change cannot. The row carries
`reserved | extracting | verifying | verified | failed |
ambiguous | revoked`, immutable source/bundle/schema hashes, the four normalized
promotion-event binding members, canonical payload
and relation hash when verified, deletion epoch, expiry/revocation state,
Temporal workflow/run ownership and a monotonically increasing generation
ordinal. A partial unique constraint allows at most one active or verified row
for a logical identity. RLS and composite meeting/workspace/source bindings
match the meeting boundary; deletion blocks reuse and purges the GRAF-owned
artifact while retained call/History observations follow the constitution.

Every type-specific generation attempt records the exact parent artifact ID and
the migration exposes a unique parent key on `(id, workspace_id, meeting_id,
source_basis_hash, extraction_layer_manifest_hash,
root_promotion_event_id, root_promotion_event_schema_version,
root_promotion_event_version,
root_promotion_event_hash)`. Both the attempt and its
rendered outcome carry a composite restrictive FK to that key; V2 requires the
same non-null parent ID/fingerprint on both rows. They join the active parent instead of starting extraction. The first request owns
the reserved parent workflow; later waiters observe that same durable state.
Verified, non-revoked parents are reusable. `failed`/`ambiguous` parents are
never silently reopened: a reconciler proves terminal state, then a bounded new
ordinal may reserve the same logical identity. A stale active reservation must
be reconciled against Temporal workflow/run ownership and its lease deadline
before replacement. Partial shard failure, verifier failure, source change,
bundle revocation, `extraction_capacity_exceeded` and deletion have explicit
terminal reason codes; no waiter
may project or publish from an unverified parent. Canonical artifact payload and
typed relations are defined by the discriminated-union contract in
`prompt-pipeline.md`.

Expiry or revocation makes the old verified parent historical-only. A new
calibration manifest has a new ID/hash and therefore a different extraction
identity, so it can reserve a successor without rewriting the immutable parent
or colliding with the partial unique key.

Receipt V1 has no receipt tables or reservation rows. Canonical receipt JSON,
schema, digest and finalization time are immutable columns on the parent
artifact; publication receipt fields are immutable columns on the type attempt,
and the outcome header repeats only schema/digest through its restrictive
provenance FK.

Canonical finalization is an earlier Feature 195 transaction over
`meetings(id, workspace_id) FOR SHARE` → current source pointer `FOR SHARE` →
parent artifact → sorted
artifact-owned GenerationCalls → mutable calibration status head `FOR SHARE`.
It reconstructs the byte-equal promotion-event binding from the parent and
every call, re-fetches/re-hashes the passing event, and performs only the
artifact owner row's guarded pass-receipt finalization after building the
complete `VerifierCalibrationStatusSnapshotV1` body/hash from the head under
`FOR SHARE`, enforcing its hard deadline and resolving/re-hashing the
kind-tagged embedded activation cohort or weekly-drift binding; it
never locks or creates a summary slot. Its last conditional SQL write obtains a
single PostgreSQL `clock_timestamp()` after every mutable lock, injects that
exact microsecond value into the vector-tested canonical receipt body/hash and
fails at/after the locked hard deadline. Failed work finalizes no receipt.

The later V2 finalize-and-publish transaction follows the same global relative
order from `contracts/receipts.md`:
`meetings(id, workspace_id) FOR SHARE` deletion fence → current source pointer
`FOR SHARE` → target slot → attempt
→ DispatchIntent → candidate → parent artifact → GenerationCalls sorted
by owner/phase/sequence/UUID → mutable calibration status head(s) `FOR SHARE`
→ prior current
outcome. It requires `state=verified`, exact source basis/extraction manifest,
matching workspace/meeting and current deletion epoch; reconstructs both
owner-row receipts and rendered content; re-fetches/re-hashes the same complete
promotion-event binding from the parent, attempt manifest and all calls; builds
the byte-equal complete calibration snapshot/body hash under `FOR SHARE`, checks
active state, hard deadline, freshness kind and typed evidence binding and
re-hashes the selected activation cohort or weekly-drift body; then atomically performs the attempt receipt's guarded
finalization, `pending_publication → complete`, slot CAS and dispatch
finalization through Feature 183's sole publisher. Those transitions are one
last data-modifying CTE whose materialized `clock_timestamp()` is the exact
receipt `issued_at_us` and freshness comparison value returned with the stored
body/digest. `CURRENT_TIMESTAMP`, transaction/statement time, Workflow time and
caller time never authorize either receipt. Feature 195 invokes that
publisher and does not implement a duplicate finalizer. Calibration activation,
expiry-materialization and revocation writers serialize with `FOR UPDATE` on
the same status-head row; the deletion writer similarly uses `FOR UPDATE` on
the same meeting row. Source change, revocation, expiry or deletion between projection and
publish fails closed and leaves the prior type slot current.

Every attempt also persists the complete immutable `ResolvedRunManifestV1`
JSON body and hash. Auto resolution keeps the frozen metadata/catalog/coverage
descriptor, full-input hash and any validated result hash plus deterministic
selection proof, as well as the complete Auto section-mapping policy and exact
Auto presentation-profile body/hash. A model call owns the complete bounded canonical profile view
in its immutable logical request. Topic focus includes raw/normalized query and
the batch-zero resolved canonical topic IDs. The manifest also freezes the full
criticality-policy and gateway-route-binding descriptors. Publication never rebuilds historical metadata or
policy from later-mutated meeting/workspace rows.

PostgreSQL fixtures cover deletion writer versus each finalizer, canonical finalizer versus first publication,
call/dispatch reconciliation versus publication, reversed multiple-call input
order, calibration activation/revocation on both sides of the linearization
point, same-type writers, cross-type writers and parent substitution from the
same meeting or another workspace. Every run must complete with a documented
serialization winner or bounded failure and no deadlock, partial receipt,
published slot with unfinished dispatch or finalized dispatch without
publication.

## Retry ownership

Temporal is the sole retry authority for every inference route. The OpenAI
client is constructed with `max_retries=0`, the LiteLLM route has
`num_retries=0`, and gateway, HTTP-adapter and provider automatic retries are
disabled. No lower layer may reinterpret a timeout, disconnect, `429`, `5xx` or
other transport result as permission to resend.

Every model phase is split mechanically:

1. a retryable/idempotent **prepare** Activity compiles and persists one exact
   GenerationCall in `prepared`, including request, route, execution authority
   and provider-correlation identity; it is prohibited from network I/O;
2. one **invoke** Activity with `maximum_attempts=1` revalidates fences and
   authority, commits `prepared → sending` with one immutable invoke-attempt ID
   immediately before gateway egress, then makes at most one physical request;
3. a cancellation-shielded response transaction persists the raw body/hash and
   `sending → response_recorded` before any validation result returns;
4. retryable/idempotent validation consumes only that persisted response and
   cannot invoke the provider.

The invoke middleware performs the state/CAS check on every execution, including
manual reschedule, retry, reset and replay. Observing or losing anything other
than `prepared` means zero egress. Timeout, disconnect or crash after committed
`sending` becomes `ambiguous`; the reconciler alone may refine it by exact
authenticated correlation read-back. A search/list miss or provider 404 is not
no-egress proof.

Only an authenticated `ProviderNoEgressProofV1` for the exact call/attempt/
correlation/request may commit `failed_pre_egress`. Temporal may then reserve at
most one policy-bounded successor GenerationCall with a new ID and immutable
predecessor link; it never reopens or resends the old call. Any missing, partial
or unverifiable proof remains `ambiguous` and has no successor. Production and
candidate-evaluation calls use this identical state machine. The independently
idempotent Langfuse publisher is not an inference route and may be retried by
Temporal without repeating model work.

| Failure point | Automatic retry? | Rule |
|---|---|---|
| Prepare/invoke fails while the DB row is still `prepared` | Temporal may schedule a new one-attempt invoke | The mandatory CAS proves no egress-capable state committed; same prepared call identity |
| Gateway authenticates zero upstream egress after `sending` | Temporal only, bounded | Finalize `failed_pre_egress`; reserve a new successor call with typed predecessor proof |
| HTTP/provider outcome could have reached upstream | No inference retry | Mark ambiguous and reconcile from durable receipt if available |
| Response reached GRAF | Never lose/retry inference | Persist raw response/call state before lifecycle checks |
| Schema/semantic invalid | Optional one repair, not transport retry | Separate call/sequence and budget |
| Langfuse unavailable | Retry publisher only | Never repeat inference or block ready result |
| Source/deletion changed | No old-source retry | Cancel/stale; optional new intent on current source |

## Multi-tenant dispatch fairness

Outcome work is multi-tenant. Interactive ensure/refresh, ordinary automatic
generation and reconciliation/backfill/recovery use the three dedicated V2 Task
Queues above. A continuously backlogged interactive lane therefore cannot
starve automatic first results, and neither user-facing lane can consume the
background recovery floor. Within each lane, every Workflow and Activity uses
the opaque workspace ID as its fairness key. Allowed operator-owned weights are
`0.5..4.0`, default `1.0`; a user/workspace cannot select a weight or priority.
Priority 1 remains reserved for an audited operator incident action inside its
own lane, never as the normal interactive-versus-automatic scheduler.

For both Workflow and Activity execution, deployment reserves a non-borrowable
automatic floor and background floor of at least
`max(1, ceil(total_v2_worker_capacity * 0.10))` slots each and requires enough
capacity to satisfy both floors plus one interactive slot. Per-workspace
admission defaults to 4 active and 100 pending outcome intents and is
configurable only within `active=1..16` and `pending=10..1000`. At the bound,
identical meeting/type intents coalesce; work remains durably deferred and an
interactive caller receives typed `deferred_capacity` plus retry-after. No
request is silently dropped, and lane/fairness weight never bypasses token, cost
or concurrency ledgers.

Temporal Task Queue Priority and Fairness are Public Preview, not GA, at this
contract snapshot. Rollout therefore pins and records the exact Server/SDK
versions, current documented stability, queue partition count, Worker
Deployment Version and effective configuration, and revalidates the installed
API instead of relying on remembered field names. Self-hosted readiness requires
authoritative read-back that all three dynamic configuration flags are effective
for every V2 Task Queue and Namespace:

```text
matching.useNewMatcher=true
matching.enableFairness=true
matching.enableMigration=true
```

The migration flag is required to drain work queued before Fairness activation;
a configured value without effective read-back and a backlog-drain fixture is
not readiness evidence. Native Temporal Fairness is probabilistic and
approximate; it is not a deterministic round-robin guarantee. Native acceptance
is scoped to one Task Queue partition and one Worker Deployment Version. If the
Public Preview capability, all three effective flags, scope, partitioning or
migration cannot be proved, rollout keeps the separate queues and uses a
measured custom weighted-fair scheduler; one global FIFO or a scheduler that
ignores weights is forbidden.

The equal-weight fixed-duration fixture runs one dominant workspace at its
pending limit plus 20 continuously ready small workspaces for five independent
ten-minute trials, extending a trial to at most 60 minutes when needed to reach
the preregistered sample floor. After a 60-second warm-up, every backlogged key,
including the dominant tenant, must have at least 500 dispatch starts. For each
of all 21 keys, the dispatch-share ratio against the equal-share target must be
in `[0.80, 1.20]`, and its Bonferroni-corrected simultaneous family-wise 95%
Wilson interval, expressed as the same target ratio, must lie wholly inside that
tolerance band. Its p99 schedule-to-start delay must be no more than `2 ×` the
same fixture's unloaded-small-key p99 plus 30 seconds. With all three lanes
continuously backlogged and equal-duration tasks, automatic and background
starts must each be at least their reserved 10% floor. Missing the sample floor
is a failed/inconclusive rollout gate, never a pass by omitting that key.

The weighted fixture uses four continuously ready workspaces with weights
`0.5`, `1.0`, `2.0` and `4.0`. Each of at least three trials observes at least
10,000 post-warm-up starts and at least 500 starts for every key. Let `W=7.5`,
`N` be the accepted starts and `e_i=N*w_i/W`; every `n_i/e_i` must be in
`[0.85, 1.15]`, and every key's Bonferroni-corrected simultaneous family-wise
95% Wilson interval, expressed as `n_i/e_i`, must lie wholly inside the same
tolerance band. Counts are
dispatch starts, not concurrent executions; cancelled-before-start tasks are
excluded. The equal and weighted tests run independently for Workflow and
Activity queues. After a worker restart, a 120-second convergence window is
excluded and the same statistical/share/latency gates run again. No restart,
cancellation or transport retry may duplicate inference.

Maximum dispatch gap remains a diagnostic for native Fairness because its
probabilistic algorithm, partitioning, Worker versions and restart state do not
promise a finite hard gap. A custom scheduler may additionally claim the hard
bound `2 * ceil(sum(weights) / weight) + 2`, but only after deterministic tests.

Metrics record schedule-to-start p50/p95/p99 by lane and opaque-key bucket,
dispatch share and confidence interval by lane/key, active/pending counts,
coalesced/deferred admission, diagnostic maximum dispatch gap, convergence time
and reserved automatic/background capacity.
Raw workspace identity and meeting content never become metric labels.

## Cancellation

- Define pre-egress, in-egress, post-response and post-publication cancellation semantics.
- Shield required response/ledger finalization from cancellation after response arrival.
- Activities heartbeat at meaningful boundaries and check cancellation before new egress.
- Abandoned publisher/reconciler children have terminal DB predicates and bounded backoff; parent close cannot create infinite work.
- User leaving the page never cancels durable work; meeting deletion does through deletion epoch/state fences without erasing retained observability mandated by constitution.

## Transcript regeneration workflow (Feature 197)

Feature 197 uses the separate Workflow Type `TranscriptRegenerationV1` and
dedicated `transcript-regeneration-v1` Task Queue with the same pinned Pydantic
converter and Worker Deployment/PINNED rules. Workflow ID is deterministically
namespaced from the immutable random `TranscriptRegenerationJob.id` UUID and
starts with `WorkflowIdReusePolicy=REJECT_DUPLICATE`; it is never derived from
the reusable business `request_identity_hash`.

The business hash deduplicates the exact workspace/meeting/language/source/
policy/pipeline tuple before a job is reserved. The same idempotency key and
byte-equal identity, or an equivalent non-terminal identity under another key,
returns that exact database job. An already-started Temporal response causes a
re-read of that job UUID/Workflow ID and cannot join a different execution. A
proven-safe retry after terminal failure creates one successor with a new job
UUID/Workflow ID, `retry_ordinal + 1` and immutable `predecessor_job_id`; it does
not reuse or overwrite the predecessor.

Sequence:

```text
1. load and revalidate the exact job/source/access/deletion/policy identity and
   retry lineage
2. persist the job-scoped provider correlation/idempotency ID, then claim
   submitted → sending in one Activity transaction
3. submit once to the transcription provider with the exact language/pipeline
4. persist accepted provider identity, or ambiguous transport truth
5. poll/consume signed callback/reconcile the same provider operation
6. persist raw then strictly validated replacement transcript artifact
7. run the sole source-replacement + saved-type stale/fan-out transaction
8. expose succeeded/failed/invalidated terminal truth
```

Every step is a typed Activity; Workflow code performs no DB/provider I/O.
Temporal may retry read-only polling and a transaction that proves it committed
no external side effect. A new provider-submission Activity may be scheduled
only after the previous terminal Activity result durably proves no egress;
transport, SDK, gateway and provider layers themselves perform no automatic
retry. Activity timeout, worker crash or connection loss after `sending` becomes
`ambiguous` and enters reconciliation, never a second submission. Every safe
same-job submission attempt reuses the persisted provider correlation ID; each
submit Activity execution itself has `maximum_attempts=1`.
A provider callback and authoritative lookup are idempotent on the exact
job/correlation/returned operation identity. A successor has its own provider
correlation identity while preserving predecessor lineage. Replacement-
transaction retry is safe because it uses expected source,
job state and unique replacement revision/DispatchIntent constraints; a winner
is re-read rather than recreated. History, polling and ambiguity have bounded
continue-as-new/checkpoint rules, and deletion/access loss invalidates without
publishing the retained provider output.

## Langfuse prompt authority

Prompt names:

```text
graf/meeting-intelligence/bundle
graf/meeting-intelligence/core
graf/meeting-intelligence/source-context-policy
graf/meeting-intelligence/projection-policy
graf/meeting-intelligence/extract
graf/meeting-intelligence/resolve
graf/meeting-intelligence/verify
graf/meeting-intelligence/repair
graf/meeting-intelligence/auto-resolve
graf/meeting-intelligence/presentation-synthesis
graf/meeting-intelligence/presentation-verify
```

No per-profile prompt exists. The exact `ProfileContractCatalogV1` and resolved
full `CompositeProfileContractV1` are typed, hash-bound config bodies consumed
by the three generic profile/presentation prompts. Introducing
`profile/<profile>` would duplicate profile semantics and is rejected.
`AutoSectionMappingPolicyV1` is likewise typed deterministic config, never a
prompt. It keeps the visible Auto shell fixed at `Action Items → Key Points`
while the resolved intent composite controls selection, priority, criticality
and safety; changing either exact body requires a new root and evaluation.

`graf/meeting-intelligence/bundle` is the only label-resolved production
selection point.
Its exact numeric config version and `activation_manifest_hash` pin every allowed
child numeric version/hash, schema,
route/settings, validators/verifiers, deterministic renderer and the exact
`MasterPromptClauseRegistryV1` version/hash. The closed V1 registry includes
`MP-SRC-001`, `MP-COV-001`, `MP-SPK-001`, `MP-SID-001`, `MP-NUM-001`,
`MP-DAT-001`, `MP-INT-001`, `MP-PRO-001`, every
applicable profile-safety clause, `MP-RPT-ACT-001`, `MP-PRI-001`,
`MP-EVP-001`, `MP-HRV-001`, `MP-STR-001` and `MP-QAL-001` with their immutable
requirement hashes and required eval cells.
Prompt
variables use Langfuse `{{double_braces}}`; conditionals, loops, profile
selection and trust/source assembly remain typed compiler logic. Langfuse
documents immutable versions and movable/protected labels but not a native
expected-source CAS guarantee. Feature 200 therefore composes promotion as one
authorized writer under an operator-owned lock: read and compare the expected
root numeric version, verify evidence/candidate/rollback, move the protected
root label, then read back the exact target version/hash. Any mismatch or
out-of-band movement fails closed and alerts; member labels are never read by
runtime. GRAF never uses unpinned latest prompt and never substitutes code
prompt silently.
Every compiled logical request records the exact applicable clause
ID/version/requirement-hash set and compiler disposition. A runtime-prompt or
deterministic-policy clause missing from its owning phase fails before egress;
an unknown clause or changed requirement hash requires a new registry/root.
`MP-QAL-001` is not model self-review. The root pins the exact preregistered
evaluation plans; measured evidence binds the already-created candidate root in
an immutable external `RootQualificationRecordV1`. After promotion, runtime
requires the complete `ImmutableArtifactBindingV1` for the matching successful
`RootPromotionEventV1`, fetches/re-hashes that body and verifies its embedded
qualification record. This split avoids an
impossible evidence↔root digest cycle without allowing an unqualified root.
Last-known-good is an exact integrity-checked root version plus activation
manifest and successful promotion-event binding. Each attempt separately persists the immutable
`ResolvedRunManifestV1` canonical body and hash over meeting-specific exact
primary/optional-secondary/`CompositeProfileContractV1`, Auto/focus resolution
snapshots, conditional Auto section-mapping/presentation-profile authority,
privacy/evidence/projection/presentation controls, required
child versions, extraction-layer identity and derived envelopes; it cannot
alter the global root config or be reconstructed from mutable meeting metadata.
Langfuse's SDK-level fallback prompt is not a valid bundle and cannot authorize
egress or publication. Startup prefetch and cache are allowed only for an exact
verified numeric root/child set; without it, the worker fails closed and leaves
the saved current result unchanged.

## Trace/observation tree

Trace context follows W3C identity sizes exactly. Every GenerationCall freezes
`trace_id`, `observation_id`, `parent_observation_id` and
`root_observation_id` before export. A trace ID matches
`^(?!0{32}$)[0-9a-f]{32}$`; each observation/span/root/parent ID matches
`^(?!0{16}$)[0-9a-f]{16}$`. Uppercase, wrong-length, non-hex and all-zero
values are rejected. Meeting UUIDs, hashes and truncated UUIDs are never
substituted for W3C IDs.

The trace ID is assigned once to one logical pipeline Workflow ID/Run ID and
cannot be rebound to another run. `root_observation_id` names that trace's one
`application-root`. Every GenerationCall observation and its parent must exist
under the same trace/root; in V1 every generation is a direct child, so
`parent_observation_id == root_observation_id`. A future nested phase must bind
an existing same-trace parent and preserve the same root. An observation ID is
single-assignment to one GenerationCall and cannot be reused by another call or
under another trace; replay of the same call reuses its already persisted
identity. A cross-trace parent/root, an observation equal to its parent/root, a
second root, or identity mutation after persistence fails before any export.

```text
trace meeting-outcome-pipeline
└── span application-root (logical root: production task input/final outcome)
    ├── span pin-manifest
    ├── span snapshot-source
    ├── span segment-and-source-verification-catalog
    ├── generation extract[0..N]
    ├── generation resolve[0..N] when model merge/reconciliation is required
    ├── span resolve-noop for a deterministic one-shard/no-conflict pass
    ├── span deterministic-verify
    ├── generation semantic-entailment-and-omission-verify
    ├── generation repair[0..N] (optional, one bounded round)
    ├── generation post-repair-reverify[0..N] (required when repaired)
    ├── span finalize-canonical-verification-receipt
    ├── generation auto-resolve[0..1] when model resolution is required
    ├── span auto-resolve-noop for the pinned deterministic path
    ├── generation profile-projection[1..N] (bounded ID-only batches)
    ├── span no-supported-content-terminal (exclusive branch; no candidate/receipt)
    ├── generation presentation-synthesis[1..N]
    ├── span deterministic-presentation-verify
    ├── generation presentation-verify[1..N]
    ├── span deterministic-render
    ├── span persist-pending-publication-candidate
    ├── span finalize-outcome-publication-receipt
    ├── span publish-type-slot
    └── span finalize
```

Bracketed ranges in this diagram describe cardinality, not observation names.
Every repeated instance keeps the stable low-cardinality name (`extract`,
`repair`, `profile-projection`, and so on); batch sequence, retry ordinal,
meeting, route and model identity live in typed metadata/GenerationCall fields.

Each completed model response reaching GRAF owns exactly one logical
GenerationCall and intended deterministic `generation` identity containing the
exact logical request, pinned transcript/source, raw response and locally
validated result. The logical request and normalized call fields carry the
complete promotion-event binding pinned at Workflow start; every Activity
re-fetches/re-hashes that event before first provider egress and rejects a
different, failed or hash-only authority. Delivery state is exactly
`pending → sending → confirmed | ambiguous`, with the one monotonic refinement
`ambiguous → confirmed` after authoritative reconciliation. The immutable
export body/hash is persisted before a claim exists.

Claiming does **not** change delivery state. A publisher CAS writes
`claim_owner_id`, an opaque claim token, incremented `claim_epoch` and
`lease_expires_at_us` while the row remains `pending`. It may prepare transport
while pending. Immediately before the first operation that can emit an export
byte, the same owner performs this guarded transaction:

```text
pending
+ matching generation_call_id/body_hash
+ matching claim_owner_id/token/epoch
+ unexpired lease
→ sending + sending_started_at_us + immutable export_attempt_id
```

If that CAS loses, the publisher performs zero egress. Only the current claim
owner/token/epoch may CAS `sending` to `confirmed` after an authenticated
acceptance receipt, or to `ambiguous` after a timeout, connection loss or any
uncertain outcome. A process crash or lease expiry while still `pending` clears
or transfers only the claim and permits bounded export retry. A crash or lease
expiry in `sending` is conservatively `ambiguous` even when no byte is known to
have left: a reconciler atomically takes an expired reconciliation claim and
writes that terminal publisher state. It never returns `sending` to `pending`.
A stale publisher cannot begin egress, extend the lease or write either terminal
state after its claim has been replaced.

Authoritative reconciliation accepts only either the persisted authenticated
Langfuse ingest receipt for the exact `export_attempt_id`/body hash or an
owner-authenticated exact-ID read-back matching project, `generation_call_id`,
W3C trace/observation/root IDs, observation type and export body hash. The
reconciler appends that evidence and, under its own claim CAS, may refine
`ambiguous` to `confirmed`. Search/list absence, cache state, eventual-consistent
404, timeout or a mismatched object never proves non-delivery and never permits
re-export. More than one physical observation is recorded as a transport defect
and collapsed to the one logical GenerationCall before evaluation/annotation;
Langfuse v4 duplicate ingest is never treated as an upsert. None of these states
can repeat inference or block publication of an otherwise verified result.

The mandatory crash/stale-publisher corpus covers:

| Window | Expected result |
|---|---|
| claim acquired, crash before `sending` CAS | lease transfer leaves state `pending`; one later exporter may proceed |
| stale owner loses claim before `sending` CAS | CAS fails and emitted bytes remain zero |
| crash immediately after committed `sending` CAS, before known first byte | expired claim becomes `ambiguous`; no re-export |
| crash after partial/full send or after acceptance but before DB terminal write | `ambiguous`; exact receipt/read-back may refine to `confirmed` |
| stale owner writes terminal after takeover | zero-row CAS; authoritative state is unchanged |
| exact read-back missing, mismatched or duplicated | missing/mismatch stays `ambiguous`; duplicate is collapsed and alerted, never blindly resent |

The stable `application-root` observation is marked as the logical root and
stores the production-equivalent task input plus the exact final rendered
outcome (or truthful terminal state). End-to-end evaluators and annotation
queues target that observation. Phase diagnosis targets the named `generation`
observations. Observation names are versioned API surfaces and never contain
meeting IDs, retry ordinals or model names. Trace-level evaluators are not used:
Langfuse v4 evaluation is observation-first, and an evaluator cannot infer a
sibling or child observation's payload unless the application explicitly binds
the required data to its target observation.

Extract, model-resolve, verifier, repair and reverify GenerationCalls are
ordered members of the artifact-owned `CanonicalVerificationReceipt`; later type attempts reference its
digest and do not repeat canonical verification. Auto-resolver, projection,
presentation-synthesis and presentation-verify
GenerationCalls are ordered members of the type-attempt
`OutcomePublicationReceipt`, finalized only
after presentation verification and deterministic layout render freeze the
exact outcome/content hash. Publication
checks both receipt digests, their distinct ownership/call sets and complete
canonical, projection, statement and selected-claim coverage; Langfuse scores
or trace presence alone
never form either receipt.

Prose realization and translation are explicit model phases; only layout/markup
rendering is deterministic. Every synthesis and verifier batch owns a retained
GenerationCall, Activity and named Langfuse generation. Auto
resolution follows the same truth rule as every phase: a model path owns one
GenerationCall/Activity/`generation auto-resolve`, while a deterministic path
owns only `span auto-resolve-noop` plus the strict receipt proof. Profile
projection always owns at least one bounded ID-only GenerationCall/Activity for
publishable content, even when its partition is deterministic; V1 has no
projection no-op proof. Neither presentation phase has a V1 no-op path.
Model-based projection uses the numeric prefilter/batch/call/coverage contract in
`prompt-pipeline.md`; `profile_projection_capacity_exceeded` is terminal for the
type attempt and never invalidates the reusable verified canonical parent.
Zero eligible/selected, topic no-match/ambiguity and topic-catalog overflow use
the closed non-publication terminal evidence with their distinct generation
state/reason and public recovery mapping; no presentation generation is
fabricated.
Resolve follows the same truth rule: each model-based resolve batch owns a
GenerationCall, Activity and Langfuse generation; a one-shard/no-conflict
deterministic no-op is only `span resolve-noop` and creates no fake model call or
generation observation.

Receipt V1 rejects every continuity input, proof, call and rendered section.
Feature 207 must first version the resolved-run manifest, content payload and
publication receipt with pinned previous/current artifacts, action-ledger
snapshot, selection policy, timezone and algorithm identity. Only that later
contract may add a deterministic continuity span; a semantic model path must
also add its own phase/call/context budget. There is no hidden V1 continuity
path.

## LiteLLM

- GRAF calls only the owner-controlled allowlisted gateway.
- Selected route is `gpt-5.6-luna`; the root pins a complete immutable
  `GatewayRouteBindingV1` allowlist, its embedded
  `LiteLLMRequestCompilerBindingV1` and exact
  `GRAF-GATEWAY-ROUTE-BINDING\0v1` length-framed canonical-JSON hash while
  LiteLLM owns provider secrets.
- The compiler binding pins its positive version, endpoint mode, adapter,
  serializer and Chat/Responses translator hashes, closed reasoning-effort and
  service-tier domains, omitted-default policy, unsupported-parameter/drop
  policy and automatic-summary policy. V1 uses `preserve_omitted`,
  `reject_unsupported` and `disabled`; it never silently materializes an SDK
  default, drops a parameter or summarizes/compacts model input.
- Every request sends the expected route-binding and request-compiler-binding
  hashes. Gateway middleware checks both before provider egress and echoes both
  plus actual provider/model; missing/mismatched/unallowlisted values fail
  closed. A route mapping, endpoint, adapter, serializer, translator,
  default/drop or automatic-summary change requires a new binding and a
  separately evaluated/promoted root.
- Before that gateway call, the Activity resolves exactly one execution
  authority. Production resolves the compiled request's complete
  `PromotedRootBindingV1`, rehashes its promotion event and qualification bodies
  and proves the exact root/activation pair. Candidate-evaluation resolves the
  complete pre-call `CandidateEvaluationAuthorityV1`, exact allowed run/arm,
  candidate or promoted-baseline root and `evaluation_only` sink; it rejects any
  artifact/attempt/slot/receipt/DispatchIntent owner. Candidate calls do not
  require or carry the not-yet-created promotion event. The gateway route hash
  does not substitute for either local runtime-authority check.
- Every call compiles and persists the closed phase-specific `RequestSettingsV1`
  body/hash from `contracts/receipts.md` before egress. Exact reasoning effort,
  verbosity, strict structured-output schema, service-tier presence and any
  derived provider output envelope are pinned; omitted defaults remain distinct
  from explicit values. Neither task nor judge route receives a global 4048/4096
  output cap.
- Preserve selected route, request-settings hash, route/compiler-binding hashes
  and actual provider/model/request ID. `GatewayRouteBindingV1`, every
  GenerationCall and every `VerifierIdentityV1` must carry the same compiler
  hash; gateway/provider serialization cannot replace the immutable logical
  settings body.
- Per-user/workspace concurrency, token and cost budgets are database-backed and fail closed.
- Tags contain opaque IDs only; no transcript content in spend metadata.
- Direct provider endpoints/credentials in GRAF are forbidden.

## Experiment path

Langfuse experiments invoke the production-equivalent application task through
LiteLLM and the same compiler/validators, not a simplified direct prompt call.
Before either arm's first model call, GRAF finalizes the complete
`CandidateEvaluationAuthorityV1` over the preregistered plan, promoted baseline,
cycle-free candidate root, dataset/split and all allowed run IDs. Every baseline
and candidate call carries that authority, its exact arm/root and the
`evaluation_only` sink; evaluation execution has physically no slot, receipt or
DispatchIntent writer. Candidate calls never require a future promotion event,
while baseline identity still embeds and revalidates its existing successful
event. Dataset run metadata contains exact bundle/dataset/evaluator versions.
Baseline and candidate run on the same held-out items at the same explicit
per-phase `reasoning.effort`; after that cohort passes, the same frozen suite
runs at exactly one supported effort level lower as a separate robustness/cost
cohort. Prompt and effort changes are never combined in one causal comparison.
Judge request settings are pinned in evaluator and calibration-manifest
identity; changing effort, verbosity, structured-output mode or output envelope
creates a new identity and requires separate human calibration.

Production-equivalent task-run evidence embeds the complete pre-call
`CandidateEvaluationAuthorityV1` and proves zero artifact/attempt/slot/receipt/
DispatchIntent mutation. It also records the selected arm/root and, for the
promoted baseline, the complete successful promotion-event binding. A future
qualification record, Langfuse run name, prompt label or bare event digest is
never pre-promotion execution authority.

Dataset identity is never name-only or implicit `latest`. Before dispatch, GRAF
fetches the dataset with one explicit UTC version timestamp and freezes an owner-
controlled manifest containing dataset name/version, sorted item IDs, split,
input/expected-output/metadata content hashes and schema hashes. It immediately
reads that version back and recomputes the manifest. The versioned dataset object
is then used for the experiment, and the completed dataset-run items are read
back and compared with the exact item-ID/hash manifest. Missing version support,
an item mismatch, a concurrent rewrite observed by read-back or an SDK path that
silently resolves latest invalidates the run and blocks comparison/promotion.
The immutable manifest hash is stored in every baseline/candidate run.

This explicit proof is required because current Langfuse documentation is
internally inconsistent: the Datasets page documents timestamp-version fetch and
versioned experiments, while the Experiments-via-SDK page still says experiments
run on latest. GRAF relies on neither sentence alone; exact pre/post read-back is
the acceptance boundary.

Hosted Langfuse dataset items keep complete task input in `input` and human gold
only in `expectedOutput`; the task path never receives `expectedOutput`.
End-to-end discovery queues and production evaluators target the logical
`application-root` observation with exact final outcome input/output; phase
error analysis targets the relevant named `GENERATION` observation. Deprecated
trace-level evaluators are forbidden. Score configs are created before
GRAF freezes an owner-controlled annotation manifest over queue/item observation
IDs, assignments and ScoreConfig snapshots. Each snapshot contains `configId`,
`updatedAt`, `isArchived`, the complete canonical read-back body and its content
hash plus a separately owner-versioned rubric. Langfuse has no ScoreConfig
version field and its update API can mutate semantics, so pre/post read-back is
mandatory; any body/hash/timestamp/archive or queue-membership change
invalidates the manifest, and a semantic rubric change creates a new config ID.
Every experiment likewise stores the complete immutable `VerifierIdentityV1`
body beside its recomputed hash and the complete pre/post
`LangfuseEvaluatorReadbackV1` bodies beside their recomputed hashes. Every
foreign prompt/route/gateway/compiler/input/output/reason-code/validator object
is a complete sibling body or exact `ImmutableArtifactBindingV1`, never an
opaque hash. The read-backs contain exact
`evaluator_binding={id,numeric_version}`, prompt, `model_route`, gateway route,
request compiler, variable mapping, output schema and complete request settings
over exact
`reasoning.effort`, verbosity, structured-output mode and complete output
envelope. Changing any field creates a new evaluator/calibration-manifest
identity and requires new blinded human calibration. A candidate
evaluator must not reuse a production-rule identity when Langfuse would
automatically move that active rule to the new version.

There are two separate five-run families because one Langfuse experiment exposes
at most one occurrence per dataset item:

- task stability uses five production-equivalent application runs and reruns
  every model phase with fresh GenerationCalls; no task output is shared between
  repetitions;
- judge/verifier stability uses five separate evaluator runs over the exact
  frozen task-output manifest for the decision unit being calibrated.

Every repetition independently passes run-item/root/settings/actual-target
read-back. Task runs satisfy the canonical/Auto/projection/presentation,
stable Auto-shell/exactly-once mapping and human-utility invariants; judge runs satisfy per-run TPR/TNR/invalid gates and
5/5 agreement/dispersion. The two evidence bodies and hashes are distinct and
both are required by `quality-and-evaluation.md`. Missing repetitions cannot be
averaged away or replaced inside one run. Rerunning judges over the same
complete frozen task-output manifest is required for judge stability but cannot
satisfy task stability; conversely, five task outputs without five independent
judge runs cannot satisfy judge stability. A single item/partial output is never
the frozen judge manifest.

Until Feature 202 approves the exact dataset authority/region/access/retention/
withdrawal/deletion-invalidation receipt, hosted dataset items are synthetic or
individually authorized operator fixtures only. Availability of a private GRAF
meeting is not consent to copy it into a Langfuse dataset. Withdrawal removes an
item from future splits and invalidates derived experiment comparability while
already retained observations/Temporal histories remain under the truthfully
disclosed operator retention policy.

## Operational gates before rollout

- fault injection for reservation/egress/response persistence/publication;
- cancellation and abandoned-child closeout;
- aggregate history and replay evidence;
- Langfuse duplicate/read-back evidence;
- provider ambiguity and cost accounting;
- prompt revocation and rollback;
- AI dependencies outage while saved summaries remain readable;
- no production inference triggered by an observability retry.
