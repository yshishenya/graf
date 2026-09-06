# Requirements Checklist: AI publication lifecycle

**Purpose**: Review whether automatic publication and per-type revision requirements are complete, clear and testable

**Created**: 2026-08-23

## Requirement completeness

- [x] CHK001 Are requirements defined for initial generation, saved-type reuse, missing-type generation and same-type refresh? [Coverage, Spec §User Stories 1–3]
- [x] CHK002 Is the automatic publication gate enumerated rather than described only as «validated»? [Clarity, Spec §FR-005; Contract lifecycle §Publication gates]
- [x] CHK003 Are last-known-good requirements explicit for provider, schema, evidence, stale, deletion, timeout and conflict failures? [Coverage, Spec §FR-008]
- [x] CHK004 Is it explicit that internal candidate state does not create a mandatory user decision? [Consistency, Spec §FR-006]
- [x] CHK005 Are requirements defined for parallel generations of the same type and different types? [Coverage, Spec §FR-011–FR-012]

## Identity and revision clarity

- [x] CHK006 Is stable summary-type identity distinguished from template version? [Clarity, Spec §Key Entities; Data Model §Stable type identity]
- [x] CHK007 Is one-current-revision-per-type stated as an objective invariant? [Measurability, Spec §FR-001; SC-006]
- [x] CHK008 Is supersession constrained to the same meeting/workspace/type? [Consistency, Data Model §Invariants]
- [x] CHK009 Is the relationship between stored model calls, internal candidates and published revisions unambiguous? [Clarity, Spec §FR-013]

## Failure and recovery

- [x] CHK010 Are late-arriving older jobs, source changes and repeated idempotency keys covered? [Edge Case, Spec §Edge Cases]
- [x] CHK011 Is Temporal the sole inference retry authority, with OpenAI
  `max_retries=0`, LiteLLM `num_retries=0`, no gateway/provider/transport
  automatic resend, durable pre-egress proof for any bounded retry and
  ambiguity routed only to reconciliation? [Coverage, Research §Decision 7;
  Temporal §Retry ownership]
- [x] CHK012 Is immutable technical history retained while user/operator rollback is explicitly deferred and non-mandatory in primary UX? [Scope, Spec §FR-009; Contract lifecycle §Commands]
- [x] CHK013 Can all lifecycle success criteria be objectively measured without subjective UI judgement? [Measurability, Spec §SC-001–SC-012]

## Dependencies

- [x] CHK014 Is Feature 182 identified as a non-released prerequisite rather than assumed production evidence? [Dependency, Spec §Dependencies]
- [x] CHK015 Are prompt quality, runtime orchestration and UX clearly assigned to later slices? [Scope, Spec §Out of Scope; Program Roadmap]
- [x] CHK016 Are source-stale read, regeneration and new-egress restrictions defined without deleting the previous revision? [Coverage, Spec §FR-021]
- [x] CHK017 Are database downgrade requirements fail-closed when multiple type mappings cannot be represented by one legacy pointer? [Recovery, Plan §Migration Strategy]
- [x] CHK018 Are lost-response replay, key/payload mismatch and concurrent first-ensure semantics defined against the existing durable attempt/dispatch ledger? [Recovery, Contract lifecycle §Idempotency and replay]
- [x] CHK019 Is first-generation failure state projected from the exact attempt without requiring a slot or selecting a latest unrelated row? [Clarity, Data Model §State model]
- [x] CHK020 Are result presence, generation attempt, source state and catalog availability orthogonal, including blocked/deferred/ambiguous and retired cases? [Clarity, Spec §FR-024; Contract API §List available type states]
- [x] CHK021 Does retiring a custom type preserve its immutable saved result while denying ensure/refresh/default mutation? [Lifecycle, Spec §FR-023]
- [x] CHK022 Is the post-transcript trigger explicitly owned by Feature 197 so Feature 183 cannot create a duplicate trigger? [Boundary, Spec §Clarifications]

## Prompt, profile and evaluation program

- [x] CHK023 Is an accepted action restricted to an explicit commitment,
  explicit assignment or explicitly accepted addressed request, with negative
  fixtures for unaccepted requests and implied owners/dates? [Accuracy, Prompt
  Pipeline §Shared core; Quality Strategy §Deterministic evaluators]
- [x] CHK024 Are closed source-context, meeting-intent, mixed-audience
  intersection, privacy/focus/detail policies plus the
  Receipt V1 `facts_only` restriction
  versioned bundle members with per-run provenance rather than free-form prompt
  text? [Reproducibility, Prompt Pipeline §Bundle manifest]
- [x] CHK025 Are deferred/cancelled/superseded decisions represented with old
  and new evidence rather than overwritten? [Completeness, Prompt Pipeline
  §Phase C]
- [x] CHK026 Does the full profile catalog cover general, project/team,
  people/learning, customer/revenue and high-stakes meetings with suitable,
  unsuitable and forbidden-inference fixtures? [Coverage, Prompt Pipeline
  §Built-in profile coverage]
- [x] CHK027 Is routine ambiguity marked in typed uncertainty fields without
  asking the user, while model-authored analysis is rejected until its own
  versioned phase/verifier/manifest/content/receipt and policy contract exists,
  and does exact `UncertaintyV1` survive candidate→canonical→projection→
  synthesis→visible receipt with verifier checks rather than only appearing in
  extract output? [CX, Prompt Pipeline §Projection policy]
- [x] CHK028 Is previous-meeting comparison isolated behind pinned two-meeting
  provenance, action identity, authorization and deterministic calendar rules?
  [Boundary, Program Roadmap §207]
- [x] CHK029 Do Langfuse experiments run the production-equivalent task,
  withhold `expectedOutput`, use exactly five separately named/read-back runs
  with per-run and exact agreement/drift gates for stability, and calibrate
  judges per class before promotion; and do end-to-end queues/evaluators target
  a logical application-root observation while phase diagnosis targets named
  generation observations, with no deprecated trace-level evaluator? [Evaluation,
  Quality Strategy; Temporal and Langfuse Contract §Experiment path]
- [x] CHK030 Are task and judge calls free of an arbitrary 4048/4096 output cap,
  with any required envelope derived from the pinned schema/profile? [Runtime,
  Prompt Pipeline §Bundle manifest]
- [x] CHK031 Is canonical-artifact reuse keyed by one extraction-layer manifest
  covering every extraction/verification-affecting prompt, schema, policy,
  normalization, validator/verifier and model setting, while projection-only
  changes remain reusable? [Identity, Temporal and Langfuse Contract §Canonical
  artifact identity]
- [x] CHK032 Is automatic publication authorized only when both immutable typed
  receipts pass: an artifact-owned `CanonicalVerificationReceipt` with exact
  verifier/repair/reverify calls, calibration, complete source/candidate
  coverage and semantic/omission verdicts; and a type-attempt-owned
  `OutcomePublicationReceipt` with exact Auto/projection plus mandatory
  presentation-synthesis/verify call set, complete
  eligible/selected/omitted coverage, relation/authorization/critical-retention
  and statement/selected-claim/fidelity gates, mutually exclusive model/no-op
  proofs, renderer version, strict nested
  outcome-content schema/hash and complete
  `VerifierCalibrationStatusSnapshotV1` body/hash with active state, event and
  drift epochs, hard deadline, freshness kind/binding and rehashed embedded
  activation-cohort or weekly-drift evidence under `FOR SHARE`? Are both external
  digests recomputed without self-reference, with canonical reuse never requiring
  verifier calls to belong to the later type attempt? [Publication, Data Model
  §Two-layer verification and publication receipts]
- [x] CHK033 Does model-based profile projection have deterministic authorized
  prefiltering, numeric object/call/context bounds, complete selected-or-omitted
  canonical-ID accounting, critical-item pagination and a fail-closed capacity
  state? [Long meeting, Prompt Pipeline §Bounded profile projection]
- [x] CHK034 Does the multi-tenant Temporal design isolate interactive,
  automatic and background queues, reserve non-borrowable automatic/background
  floors, identify Priority/Fairness as Public Preview, require effective
  self-hosted read-back of `matching.useNewMatcher`, `matching.enableFairness`
  and `matching.enableMigration` plus backlog migration, scope native
  probabilistic Fairness to one partition/deployment version, fall back to
  separate queues plus a measured custom scheduler when capability is unproven,
  test every backlogged key including the dominant tenant with sample
  floors and simultaneous confidence intervals wholly inside tolerance, use
  repeated share/p99/restart gates, and keep maximum gap
  diagnostic-only unless a custom scheduler proves it? [Operations, Temporal and
  Langfuse Contract §Multi-tenant dispatch fairness]
- [x] CHK035 Does the canonical ontology preserve `hypothesis` separately from
  fact/proposal/decision across extraction, receipts, profile allowlists and
  visible categories? [Semantics, Prompt Pipeline §Extract; Receipts §Kinds]
- [x] CHK036 Do presentation synthesis and presentation verification have closed
  success/failure schemas, exact ordering/cardinality/overflow rules, no repair
  loop and fail-closed last-known-good behavior? [Runtime, Prompt Pipeline
  §Presentation synthesis/verification]
- [x] CHK037 Is the complete immutable `ResolvedRunManifestV1` body/hash
  cross-bound to content/publication receipts rather than trusted as a
  caller-supplied digest, with schema-valid base/mutation vectors and a positive
  reconstruction integration test explicitly required from Feature 195 before
  publication can pass? [Integrity, Receipts §Design serialization vectors and
  Feature 195 conformance gate]
- [x] CHK038 Are generated `my_actions`, `private_self` and subject-dependent
  shared formats rejected, is the positive Feature 183 path absent, and is
  authenticated zero-call/no-leak filtering deferred to Feature 205/196 after
  canonical action/mapping ownership? [Identity, Spec FR-026/SC-012]
- [x] CHK039 Does text-topic focus resolve only in projection batch zero from a
  complete bounded catalog, transforming `FocusRequestV1` into immutable
  `FocusV1` with no later re-resolution, sampling or fallback? [Focus, Prompt
  Pipeline §Bounded profile projection]
- [x] CHK040 Do zero eligible, zero selected and topic no-match/ambiguity produce
  strict non-authorizing `AttemptTerminalEvidenceV1` with no presentation call,
  candidate, publication receipt or slot mutation? [Terminal path, Prompt
  Pipeline §Zero-content terminal path]
- [x] CHK041 Does `CriticalityPolicyV1` bind and completely classify source,
  candidate, canonical and profile-expansion populations, including explicit
  legitimate-zero and adversarial non-empty→empty calibration cells? [Coverage,
  Receipts §Coverage hashes; Quality Strategy §Metrics]
- [x] CHK042 Are decision/action state, proposal/idea/option disposition,
  `requires_approval`, effective date and visible uncertainty required exactly
  where supported and forbidden/omitted where unsupported across synthesis, verification,
  content schema and conformance vectors? [Semantics, Receipts §Outcome content]
- [x] CHK043 Does every LiteLLM call bind `GatewayRouteBindingV1`, echoed actual
  provider/model and an evaluated/promoted mapping, with alias-only continuity
  and SDK fallback prompts forbidden? [Runtime identity, Prompt Pipeline
  §Gateway route binding]
- [x] CHK044 Does replacement verifier calibration create a new immutable
  manifest/extraction identity, pin Langfuse evaluator ID/numeric version, and
  pass weekly five-distinct-run drift evidence, day-7/day-8 freshness, outage,
  threshold breach, expiry, revocation, old/new writer and both-finalizer races
  without rewriting historical receipts? [Calibration,
  Receipts §Calibration registry]
- [x] CHK045 Does V2 use dedicated queues that V1 Workers cannot poll, retain V1
  until complete replay-corpus PASS, repeated Visibility plus
  `DrainageStatus=drained`, no poller, not-current/not-ramping and zero exact-
  version open executions; use explicit Python `WorkerDeploymentConfig` with
  `use_worker_versioning`, immutable build IDs, PINNED/ramp/current/rollback and
  Versioning-Override-vs-Reset-with-Move recovery; and pin versioned Pydantic
  Workflow/Activity input/result models plus the same data converter on clients and Workers?
  [Replay, Temporal and Langfuse Contract §Versioned Workflow]
- [x] CHK046 Is exactly-once Langfuse transport explicitly rejected in favor of
  one logical GenerationCall, pending→sending→confirmed|ambiguous delivery,
  a pending claim lease with owner-only pre-egress/terminal CAS,
  crash-after-sending→ambiguous reconciliation, W3C-valid nonzero same-trace
  root/parent/child IDs, no blind post-accept resend, no repeated inference and
  downstream duplicate collapse?
  [Observability, Temporal and Langfuse Contract §Trace/observation tree]
- [x] CHK047 Does every ScoreConfig snapshot pin ID, updated time, archived
  state, full canonical body/hash and an owner-versioned rubric, with pre/post
  read-back and a new ID for semantic changes rather than a nonexistent remote
  version field? [Evaluation, Quality Strategy §Human-first error analysis]
- [x] CHK048 Does every task/judge call freeze the closed phase-separated
  `RequestSettingsV1` body/hash and immutable `VerifierIdentityV1`, distinguishing
  omitted defaults from explicit values, pin endpoint mode plus
  serializer/translator/default-drop/auto-summary request-compiler identity and
  include the Langfuse evaluator ID/numeric version in call-set/calibration
  identity? [Runtime identity, Receipts §RequestSettingsV1]
- [x] CHK049 Does Feature 197 define one authenticated/CSRF/idempotent BCP-47
  transcript-regeneration job/workflow that separates business dedupe from job/
  Workflow identity, uses retry ordinal/predecessor plus `REJECT_DUPLICATE`,
  persists provider correlation before a single-attempt submit, restores state
  through authorization-first monotonic GET/event polling, and closes provider
  ambiguity, source replacement, deletion accounting, saved-active-type-only
  fan-out and browser-state contracts?
  [Recovery, API §Regenerate transcript; Temporal §Transcript regeneration]
- [x] CHK050 Does the stable master-prompt clause registry and held-out
  complete profile×clause Cartesian manifest prove every research requirement
  is compiled, deterministic, rejected or deferred with explicit closed N/A
  cells, while plan-time judge bindings contain only complete
  `VerifierIdentityV1 + CalibrationRequirementPolicyV1` and measured result
  cells alone bind the later finalized calibration manifest without either hash
  cycle or sending the monolith?
  [Prompt coverage, Prompt Pipeline §Master-prompt clause registry]
- [x] CHK051 Does every profile embed exact section semantic rules and does the
  same complete composite body/hash reach projection, synthesis, verification,
  rendered-content identity and receipt, including a test where secondary
  emphasis changes all three model-phase semantics? [Profile binding, Summary
  Profile Catalog §Closed contract dictionaries]
- [x] CHK052 Are `AutoSelectionPolicyRowV1`, `AutoSelectionPolicyV1` and
  `ProfileCompositionPolicyV1` closed canonical bodies with non-recursive hash
  formulas, exact merge/ranking grammars and fail-closed duplicate-section
  semantics? [Policy reproducibility, Summary Profile Catalog]
- [x] CHK053 Is `MasterPromptClauseRegistryV1` independently reconstructible
  from the exact 40,861-byte snapshot, 17 gap-free provenance spans, every
  requirement-atomic unit, canonical entries and domain-separated coverage/body
  hashes, with actual phase ownership proven by compiled clause bindings rather
  than prose aliases? [Prompt provenance,
  Prompt Pipeline §Master-prompt clause registry]
- [x] CHK054 Are measured profile/task/judge results outside the candidate root
  hash in one immutable root-bound `RootQualificationRecordV1`, followed by a
  protected-label read-back `RootPromotionEventV1` plus its complete
  `ImmutableArtifactBindingV1`; is that binding propagated through parent,
  requests/calls, resolved-run/terminal/renderer authorities and both receipts
  and re-fetched/rehashed before egress/finalization, while bare hashes and
  per-profile prompt labels remain forbidden? [Promotion integrity, Quality
  Strategy §Promotion experiment]
- [x] CHK055 Does Auto V1 gate categorical confidence-class accuracy while
  explicitly forbidding ECE or multiclass Brier claims until a versioned
  probability-vector or deterministic probability-mapping contract is bound to
  receipt and evaluation identity? [Metric validity, Quality Strategy
  §Promotion experiment]
- [x] CHK056 Does judge calibration create exactly one complete
  `JudgeStabilityEvidenceV1` per decision-unit × verifier × actual-target tuple,
  one cohort entry per verifier × calibrated target, five complete ordered runs,
  ten fixed pairwise rows and full raw confusion/class/metric/read-back bodies,
  rejecting target aggregation, sparse rows and hash-only evidence? [Judge
  cardinality, Quality Strategy §Judge calibration]
- [x] CHK057 Are every judge-calibration and weekly-drift dataset/split,
  verifier/target/settings, thresholds and five run/item/invocation identities
  sealed in immutable plans before the first call, embedded one-to-one in the
  final manifest/evidence and rejected on any post-hoc selection or head
  mismatch? [Preregistration, Quality Strategy §Judge calibration]
- [x] CHK058 Does every model phase use network-free idempotent prepare, one
  `maximum_attempts=1` invoke behind `prepared → sending`, shielded response
  persistence and no resend from sending/ambiguous; and can only authenticated
  `ProviderNoEgressProofV1` authorize a bounded new predecessor-linked call?
  [Retry safety, Temporal and Langfuse Contract §Retry ownership]
- [x] CHK059 Are production and candidate-evaluation authorities disjoint and
  closed, with `PromotedRootBindingV1` required for publication and
  `CandidateEvaluationAuthorityV1` required before candidate calls, while the
  evaluation sink has no artifact/attempt/slot/receipt/DispatchIntent writer?
  [Authority, Receipts §Root execution authorities]
- [x] CHK060 Do canonical/publication and weekly-PASS conditional writes obtain
  one fresh PostgreSQL `clock_timestamp()` after all locks, reject at/after the
  hard deadline and return the exact stored issued time/body/digest, with
  transaction/statement/caller clocks forbidden? [Freshness, Receipts §Fresh
  database-time linearization]
