# Program Backlog: Features 194–211

These are planning-level work items, not implementation authorization or GitHub issues. Each future feature must receive its own Spec Kit slice before code.
The range starts at the repository's current next available feature number;
`190`–`193` are already allocated to unrelated active features.

## 194 — Canonical meeting-intelligence artifact

**Outcome**: one evidence-backed knowledge model feeds every summary type.

- `F194-01` Specify a discriminated-union claim/relation graph with deterministic candidate IDs, exact evidence spans, `SourceContextPolicyV1`, kind/state/disposition matrices, `requires_approval`, evidence-backed effective time, closed `UncertaintyV1`, participant/role provenance, question/answer, option/trade-off/decision, motion/vote/resolution, event-time, metric and interview-exchange semantics; add fielded display atoms plus mode-independent closed `PrivacyDescriptorV1` data class/materiality so deterministic keep/role-substitute/omit/block policy never parses free prose; default visibility is internal and model output cannot grant external access.
- `F194-02` Define versioned strict schemas for extracted candidates and canonical intelligence, including numeric per-shard candidate/text/evidence/relation bounds, covered-source ranges and an overflow signal.
- `F194-03` Specify deterministic segmentation, overlap and complete-source coverage for long meetings.
- `F194-04` Draft compact `core`, `extract`, `resolve` and `verify` prompt modules in Langfuse-compatible form and bind them to the complete gap-free source snapshot plus requirement-atomic disposition register in `MasterPromptClauseRegistryV1` instead of one runtime master prompt. Enforce the closed phase-input inclusion matrix so profile/audience/privacy/focus/detail/output-language controls are structurally absent from canonical phases.
- `F194-05` Implement deterministic validators for schema, IDs, exact spans, typed relations, kind/state compatibility, owner/date normalization, duplicates and contradictions without pretending they prove semantic entailment.
- `F194-06` Define the exact closed `CriticalityPolicyV1` body, subhash/full-hash formulas and source/candidate/canonical/profile-expansion reason classes; compile one deterministic gap-free `SourceVerificationCatalogV1` with exact catalog/span hashes, capacities and per-span verdict coverage; require calibrated entailment for every canonical claim plus complete source→candidate and candidate→canonical critical-omission gates, make source-level omission terminal, allow one repair round only for existing canonical failures or named missing candidates, and fail closed on unavailable/invalid verifier; freeze the strict artifact-owned `CanonicalVerificationReceipt` wire schema, canonical JSON/digest vectors, criticality/calibration/canonical-call-set/coverage identities and revocation semantics from `contracts/receipts.md` so later types reuse it without repeating verification.
- `F194-07` Build synthetic fixtures for corrections, cancellations, conflicting numbers, missing owners/dates, action acceptance criteria/dependencies/status, dispositions, approval/effective-date states, every uncertainty and privacy-atom handling, source-authority escalation, free-form `my_name_and_role`/`only_me` identity/authorization traps and injection.
- `F194-08` Define the executable closed `MasterPromptClauseRegistryV1` body,
  gap-free source spans plus requirement-unit/entry coverage body/hash, external registry hash, exact
  clause-binding closure per phase, activation-manifest membership and
  revocation identity; review-owner prose is never serialized authority.
- `F194-09` Define the `MeetingIntelligenceArtifact` data/lifecycle contract:
  logical unique key, active/verified uniqueness, parent workflow ownership,
  waiter joins, failure/reconciliation/retry ordinal, RLS, expiry, deletion and
  revocation, with one extraction-layer manifest hash covering every
  extraction/verification-affecting prompt, schema, policy, normalization,
  validator/verifier, model setting and exact calibration-manifest ID/hash;
  define the composite parent key and
  restrictive artifact→attempt→outcome FKs, so a new profile reuses valid intelligence while
  source/extraction changes do not.
  Add the same-workspace `MeetingCanonicalSourcePointer`, unambiguous legacy
  backfill and runtime cutover inventory away from `latest_processing_result`
  ordering before any positive canonical publication.

**Acceptance**: 100% schema/ref validity; zero fabricated critical fields and injection compliance in challenge fixtures; canonical artifact is profile-independent.

## 195 — Durable verified generation runtime

**Outcome**: a pinned bundle runs once through the approved gateway and safely auto-publishes one type revision.

- `F195-01` Persist every response reaching GRAF before deletion/expiry/lifecycle projection.
- `F195-02` Implement the shared model-invocation barrier for every production,
  candidate and judge phase: idempotent network-free prepare; one
  `maximum_attempts=1` invoke; mandatory `prepared → sending` CAS immediately
  before gateway egress; cancellation-shielded raw-response persistence; and
  exact `response_recorded | failed_pre_egress | ambiguous` terminals.
  Configure OpenAI `max_retries=0`, LiteLLM `num_retries=0` and zero automatic
  gateway/provider/transport retries. A retry/replay/reset/stale worker that
  observes anything except `prepared` emits zero bytes. Only complete
  authenticated `ProviderNoEgressProofV1` permits one bounded new successor
  GenerationCall with an immutable predecessor link; sending/ambiguous never
  resends and any missing proof stays in reconciliation.
- `F195-03` Define cancellation, heartbeat, shielded cleanup and abandoned-child terminal rules.
- `F195-04` Enforce per-payload and aggregate Temporal History budgets with near-limit tests.
- `F195-05` After response-persistence/ambiguity/history/replay gates, implement
  `MeetingOutcomePipelineV2` on dedicated `outcome-v2-interactive`,
  `outcome-v2-automatic` and `outcome-v2-background` Task Queues. Keep V1 on its
  existing queue/Worker until replay PASS, drained V1 queue and zero open V1
  executions. Use Worker Deployments with immutable build IDs and `PINNED` V2
  behavior, explicit ramp/current/rollback evidence and keep every old V2 build
  until its pinned executions and queues drain. Configure every Python Worker
  with one `WorkerDeploymentConfig(version=WorkerDeploymentVersion(
  deployment_name, immutable_build_id), use_worker_versioning=True,
  default_versioning_behavior=PINNED)` and declare the Workflow itself PINNED.
  Freeze a replay-corpus manifest covering every shipped payload/schema version,
  terminal/failure branch, timer/retry/cancel/reset history and production build
  that still owns an execution. Retirement requires two identical
  post-convergence Visibility snapshots plus `DrainageStatus=drained`, zero open
  executions for the exact deployment version, no poller, and proof that the
  version is neither current nor ramping. Closed PINNED executions are read from
  persisted GRAF state/history, not a Worker Query. Recovery chooses explicitly
  between a documented Versioning Override to a compatible healthy build and
  Reset-with-Move at an operator-approved event for an incompatible/bad pinned
  build; neither path replays against arbitrary current code. V1 removal uses the
  same repeated visibility/poller/queue-drain proof after its replay corpus passes.
  Define one versioned Pydantic input/result object per Workflow/Activity
  boundary, pin the same `pydantic_data_converter` on client and Workers, allow
  only additive-default compatible changes and replay every shipped payload.
- `F195-06` Execute segment/extract/resolve/mandatory entailment and two-level omission verify/one-repair/post-repair reverify/artifact-owned canonical receipt/strict Auto assessment plus deterministic selection/bounded mandatory profile projection/mandatory presentation synthesis/mandatory presentation verification/deterministic layout render/type-specific publication-receipt pipeline with bounded fan-out. Apply `CriticalityPolicyV1` with complete source/candidate/canonical/profile-expansion coverage; source omission is terminal, while repair accepts the closed existing-canonical/missing-candidate target union. Model Auto receives one complete bounded canonical ID/kind/conditional-state/text/relation/trusted-role view and returns per-profile assessments under separate input/result schemas; the pinned policy computes profile/confidence, and an over-envelope full view falls back to `general_summary` before egress without sampling. Compile the chosen primary and optional secondary through the exact `ProfileCompositionPolicyV1`; bind the complete resulting `CompositeProfileContractV1` body/hash, every `SectionContractV1` semantic rule and compiled clause binding to `ProfileProjectionRequestV1`, `PresentationSynthesisRequestV1`, `PresentationVerifyRequestV1`, every logical-request hash, rendered-content identity and publication receipt. No per-profile Langfuse prompt exists. Union prohibitions/criticality, take maximum risk and never raise the primary B1 budget. Apply the closed privacy atom matrix before projection and exact evidence-display policy at render; an unrepresentable critical privacy item fails the type rather than disappearing. Text topic focus resolves only in projection batch zero over a complete ≤64-topic catalog and freezes final `FocusV1`; no-match/ambiguity/catalog overflow never invokes a hidden resolver or changes focus. Zero eligible/selected and topic no-match/ambiguity persist non-authorizing terminal evidence and create no synthesis call, candidate, receipt or slot mutation. Synthesis and verification use the strict closed request/result schemas, statement/selected-ID coverage, conditional visible state, reason codes, per-phase GenerationCalls, Temporal Activities, Langfuse observations and route-derived envelopes in `prompt-pipeline.md`; no projected IDs become visible without both phases passing, and the renderer writes only layout/markup. Add normalized immutable GenerationCall owner/phase columns, exclusive owner constraints, call membership/finalization triggers, exact `model_route` plus closed `RequestSettingsV1` body/hash, gateway-route-binding hash plus actual-provider/model/request binding, domain/phase-separated length-framed request/result hashes with per-phase vectors, and immutable `VerifierIdentityV1`/`VerifierCalibrationManifestV1` bodies plus separate append-only status-event/monotonic-head lookup from `contracts/receipts.md`; derive independent Auto-object, projection-object, synthesis-item/selected-ID and verifier-statement/critical-ID envelopes from maximal compiled fixtures and the exact route tokenizer, prove output and combined context-window capacity, and enforce numeric split-depth/shard/canonical/projection/presentation call/unsplittable terminal bounds with exact-fit/one-over, dense, critical-overflow, mixed-language/escaping and maximum-relation tests. Persist canonical JSON/schema/digest/finalized time only on the `MeetingIntelligenceArtifact` owner row and publication JSON/schema/digest/finalized time only on the `MeetingOutcomeGenerationAttempt` owner row; repeat only publication schema/digest on the outcome header and create no receipt table or reservation row. Implement two transactions: canonical owner-row finalization first, then publication owner-row finalization + slot CAS + exact DispatchIntent finalization. Both use the global relative order `deletion fence → current source pointer → transcript job when touched → sorted slot(s) → attempt → dispatch → candidate → artifact → deterministically sorted GenerationCalls → calibration head → prior current`, skipping classes they do not touch. Reconstruct the exact rendered-content and both receipt payloads, bind/re-read the verified canonical parent/receipt, publication receipt/outcome hash, source/extraction/criticality/route-binding identity, calibration status-event/epoch/revocation/expiry and deletion epoch, and add deadlock/race fixtures for canonical-finalizer/first-publication, call-or-dispatch-reconciler/publication, reversed multi-call input, old/new calibration identities and writers, same-type and cross-type writers; every failure leaves the old slot unchanged. Create `contracts/receipt-vectors.json` from scratch as one schema-valid conformance artifact only after it contains: positive P1–P4 plus all five resolver modes (`explicit_template`, `model_resolved`, `deterministic_low_confidence_fallback`, `single_compatible_profile`, `policy_forced_profile`) with mandatory profile projection; full closed-schema English and Russian payloads for all nine phases and both owner-row receipts; executable RFC 6901 base-vector operations with expected rejection stage/reason; Auto, projection, synthesis and presentation-verification exact-fit and one-over route-envelope vectors; every profile/composite/privacy/evidence positive and mutation vector; and a positive DB integration that reconstructs every body and proves the complete canonical-finalizer/publication/race path. Synthetic active manifests are test-only; production stays fail-closed until Feature 200 activation.
- **Normative clarification for F195-06**: “mandatory entailment” covers every
  canonical claim; criticality controls only omission/non-droppable behavior.
  The source-level gate consumes the complete deterministic
  `SourceVerificationCatalogV1`, exact per-span verdict coverage and the full/
  subhash-bound `CriticalityPolicyV1`; a partial/unclassified/overflow catalog
  cannot authorize a zero-critical result.
  Both owner-row finalizers also build the complete
  `VerifierCalibrationStatusSnapshotV1` body/hash under `FOR SHARE`: active
  status, status event/epoch, drift epoch, last PASS, hard deadline, freshness
  evidence kind and typed binding. They fetch/re-hash the bound embedded
  activation cohort or weekly-drift body; event/epoch/validity fields or an
  opaque digest alone cannot authorize either receipt.
  After all mutable locks, each finalizer's last conditional data-modifying SQL
  statement obtains one `clock_timestamp()` and uses it both as receipt
  `issued_at_us` and the hard-deadline comparison. The vector-tested database
  canonicalizer writes/returns the exact receipt bytes/digest. Transaction,
  statement, caller and earlier-read times are not authority; publication
  receipt, candidate, prior-current, slot and dispatch transitions share that
  one final CTE.
  Renderer/content conformance vectors also prove the one legal non-Auto empty-
  state shape (`pages=[]`, `empty_state_code=not_recorded`, allowlisted primary
  key), rejection of every other empty section/page, Auto-v3 omission of either
  empty shell section, and the both-empty `no_supported_content` path with zero
  candidate/receipt/slot mutation.
- `F195-07` Persist exactly one logical GenerationCall/intended observation
  identity and one stable logical `application-root` with production task input
  and exact final outcome/terminal state. Record Langfuse delivery as pending,
  confirmed or ambiguous; retry only proven pre-export failure, never inference
  or a possibly accepted span. Reconcile by `generation_call_id`, count and
  collapse any physical duplicate before evaluation/annotation, nest phase
  spans/generations below the root and keep names free of meeting/model/retry
  cardinality. Persist the exact pending→sending→confirmed|ambiguous state
  machine. A claim lease/token remains `pending`; only its owner may CAS to
  `sending` immediately before export egress and then record a terminal state. A
  stale/expired/crashed `sending` claim becomes `ambiguous`, never `pending`;
  authoritative lookup by stable GenerationCall/observation identity may append
  reconciliation evidence and move it to `confirmed`, but never emits inference
  or a blind duplicate. Validate W3C trace IDs as 32 lowercase nonzero hex and
  observation/span/parent IDs as 16 lowercase nonzero hex, bind every child to
  the same trace and one application root, and reject zero, uppercase,
  wrong-length, reused or cross-trace identities.
- `F195-08` Add one root Langfuse bundle config as the sole label-resolved selection point; pin root numeric version/hash plus exact closed `ActivationManifestV1`, child/schema/validator/renderer bindings, complete profile catalog/composition/Auto bodies, preregistered evaluation/task/calibration-requirement plans, `CriticalityPolicyV1`, source-catalog compiler/schema/capacity, calibration-registry policy and secret-free `GatewayRouteBindingV1`. The candidate activation manifest contains no finalized calibration-manifest ID/hash or measured evidence: the later immutable `VerifierCalibrationManifestV1` embeds its complete sealed `JudgeCalibrationExecutionPlanV1` set and `JudgeStabilityCohortV1`; that cohort is the only initial activation-quality authority. Production authority and last-known-good require `PromotedRootBindingV1` with the complete successful `RootPromotionEventV1` binding. Pre-promotion evaluation instead requires one finalized `CandidateEvaluationAuthorityV1` over the plan/baseline/candidate/dataset/split/run IDs and a physically evaluation-only sink; candidate calls carry no future event and cannot own artifact/attempt/slot/receipt/DispatchIntent rows. Carry production event authority through canonical parent, compiled requests/calls, resolved-run/terminal/renderer and both receipts; fetch/re-hash it before egress/finalization. A bare event hash, member/profile label or unqualified root is never runnable.
- `F195-09` Add authoritative per-user/workspace concurrency/token/cost ledgers
  and the measured dispatch contract from `temporal-langfuse.md`: dedicated
  interactive/automatic/background V2 queues; non-borrowable automatic and
  background floors of at least 10% and one Workflow/Activity slot each; opaque
  workspace fairness keys; operator weights 0.5..4.0; active/pending defaults
  4/100; and coalesced/deferred overload semantics. Scope native Fairness to one
  partition and Worker Deployment Version. Treat Priority/Fairness as Public
  Preview and require self-hosted effective read-back of
  `matching.useNewMatcher=true`, `matching.enableFairness=true` and
  `matching.enableMigration=true` plus backlog-drain proof; when any capability
  is unproven, keep the separate queues and measured custom weighted-fair
  scheduler. Run five equal-weight trials with
  every backlogged key including the dominant tenant, per-key sample floors,
  family-wise simultaneous confidence intervals wholly inside tolerance and p99
  delay, three weighted 0.5/1/2/4 trials with
  at least 10,000 starts and ratio 0.85..1.15, then repeat after a 120-second
  restart convergence window. Treat maximum gap as native diagnostic only; a
  custom fallback may claim the hard gap after deterministic proof. Continuous
  interactive backlog must not reduce automatic/background below their floors,
  and no path may duplicate inference.
- `F195-10` Run production-equivalent LiteLLM path on `gpt-5.6-luna` without artificial 4048/4096 output cap; require the gateway to compare/echo the expected route-binding hash before provider egress and reject any absent/mismatched hash or unallowlisted actual provider/model. Pin a versioned gateway request-compiler binding with endpoint mode, adapter/serializer/translator hash, closed effort/service-tier domains, default/drop behavior and any automatic-summary policy; include it in `GatewayRouteBindingV1`, `RequestSettingsV1`, each GenerationCall and `VerifierIdentityV1`, so a Chat/Responses bridge change cannot reuse prior evidence.
- `F195-11` Coalesce concurrent type requests onto one canonical extraction and
  skip no-op resolve/projection calls where the pinned policy permits.

**Acceptance**: zero blind repeat on ambiguous egress; replay/history/
cancellation gates pass; inference never repeats because Langfuse is down;
exact provenance is retained; the first positive receipt-backed publication uses
the Feature 183 entry point and private CAS rather than a second publisher; all
ten resolver/projection, full-schema bilingual, executable mutation, capacity
boundary and receipt/race conformance vectors pass.

## 196 — Summary Workspace UX/IA/CX

**Outcome**: users read, switch, refresh, verify and use summaries with low effort.

- `F196-01` Pin exact black-box Krisp reference screens/states and validate the
  corresponding GRAF user tasks; preserve private evidence outside git.
- `F196-02` Finalize list/search → meeting-detail IA, content hierarchy and route matrix for browser and embedded macOS.
- `F196-03` Produce a screen-by-screen fidelity specification from the approved
  Krisp reference, including layout, hierarchy, controls, copy, responsive and
  embedded-macOS behavior plus documented required deviations. Maintain a closed
  opaque control/state inventory mapping every observed control to its owner,
  behavior and states, keyboard/VoiceOver contract and release disposition
  `reproduce | deviate | out_of_scope`; this includes recent-search removal,
  search-dialog focus trap/results announcements, header/navigation/overflow/
  integration controls and contextual CTA/assistant surfaces.
- `F196-04` Implement Upcoming above history and the observed Later collection (`Отложенные` in Russian), facets for star/date/contains/company/type/tags/folders, AND-between-facets/OR-within-facet logic, date/duration/last-modified sorting with newest/oldest direction, and stable pagination/tie-break; add `⌘K` recent search over permitted indexed title/metadata/content, delayed/no-result/access-safe states, and duplicate-title disambiguation by stable identity/date/participant-or-duration context.
- `F196-05` Implement the Krisp-faithful split top control: `Итоги`/`AI Notes`
  is the main tab target, its adjacent icon+chevron is a separate summary-type
  menu button, and `Расшифровка`/`Transcript` is the peer tab. The tab and menu
  button are separate focus stops with tablist/menu semantics; ready types switch
  instantly, missing types ensure once, and ready/generating/failed/unavailable/
  retired states remain distinguishable without type/content mismatch. Include
  the full-catalog entry and preserve the selected menu/type while async work runs.
- `F196-06` Persist last successful type and `Итоги`/`Расшифровка` view per user+meeting with a presentation-intent version; reload/close during preparation resumes one durable attempt while keeping the last successful type primary unless no result or an explicit deep link requires the preparing type; background completion/failure after newer selection/navigation may update availability but never steals visible or remembered context.
- `F196-07` Implement the complete selection/Refresh/retry matrix from
  `krisp-parity-matrix.md`: selecting a missing type itself starts one ensure
  without a second `Generate` confirmation; Refresh is ready-only; retry appears
  only for typed safe-retry. Put ready Refresh in the right action cluster
  immediately left of Copy; keep that slot busy/disabled for updating/blocked/
  deferred/ambiguous states, and omit Refresh for missing types whose recovery
  belongs in the status panel. Preserve capability reasons, same-type old-content
  continuity and exact coalescing across selection/click/reload/device.
- `F196-08` On missing-type failure, restore the prior ready type automatically only while that request owns the latest presentation intent; otherwise report status without navigation. Keep transcript/player primary when no ready type exists.
- `F196-09` Implement evidence seek/return for every displayed canonical
  claim/action with evidence over pinned outcome-item/kind/canonical-segment
  anchors and preserve player time/play state, type, result scroll and focus; if
  refresh completes while evidence is open, do not navigate and return by exact
  item → same segment+kind in new current → same semantic section → summary
  heading, or remain in transcript when no current result is accessible, with
  deterministic focus and one polite update announcement.
- `F196-10` Implement orthogonal result/generation/source/catalog states for initial/loading/empty/short/transcript-failed/summary-failed/blocked/deferred/ambiguous/stale/outage/unavailable/retired/paywall/access/deletion with 300 ms/5 s thresholds and no fake cancellation; the observed `RU` surface always means transcript-language regeneration, while any later notes output-language control belongs to Feature 198 outside the reference strip.
- `F196-11` Implement action-item/decision/risk/question components over
  canonical objects; each displayed action row keeps task, assignee, due-date
  control and evidence timestamp together; route persistent inline
  completion/assignee/due edits only through the Feature 205 command path.
- `F196-12` Define state-by-state content/copy specs using the Krisp reference
  where sound, with deliberate GRAF deviations only for clarity, trust,
  accessibility, localization or missing reference states. Auto renders actions
  only under `Action Items`, every other selected outcome only under `Key Points`,
  omits either empty section and publishes nothing when both are empty. Treat the
  observed empty `Key Points` heading as a reference defect. Render the reformat
  banner exactly for ready Auto + available unsaved Meeting Minutes target,
  derive it without inference, scope dismissal to exact
  user+meeting+target-template-version and make `Try it out` one ensure+selection.
- `F196-13` Pass WCAG 2.2 AA browser plus equivalent embedded VoiceOver/keyboard matrix: tab/listbox/menu arrow/Home/End/Enter/Space/Escape model, 4.5:1/3:1 contrast, visible focus, 24px minimum targets with 44px primary touch targets where possible, polite deduplicated live regions, 390px/200% one-column reflow, reduced motion and WebView shortcut-conflict checks.
- `F196-14` Complete measurable reference-fidelity/accessibility/provenance review covering navigation, selector, content geometry, player, tokens, typography, icons, copy and every documented deviation. The player/transcript matrix is executable for play/pause, seek/scrub, speed, speaker lanes/filter, preparing/unavailable/error, keyboard/VoiceOver announcements and focus restoration in both browser and embedded macOS; a screenshot-only match cannot pass it.
- `F196-15` Implement the observed exact-revision Copy, transcript-language `RU`
  popover and reference-faithful Share header host. Copy serializes the exact
  displayed `outcome_set_id` and stays pinned if refresh completes. `RU` opens
  `Transcribe in correct language`, warns that regeneration may take up to 30
  minutes, and requires an explicit enabled `Regenerate` after a valid language
  change; it never emits summary ensure/refresh. Feature 196 owns accessible
  names, disabled/read-only/busy/error/focus states and browser/embedded parity.
  Share is always present for an accessible meeting and disabled with a reason
  until Feature 203/policy enables it; only access-loss/deleting/no-existence-
  leak states hide it. Feature 196 creates no share/export command, dialog or
  egress lifecycle; Feature 203 installs those behaviors. The `Regenerate`
  action remains disabled with a truthful dependency reason until the exact
  Feature `F197-06` transcript-regeneration command exists; Feature 196 never
  submits an ad hoc transcription job.

**Acceptance**: saved-type switch makes no inference; user completes
list/search/read/switch/refresh/evidence/action journey without instructions;
  split tabs/menu plus Feature 196-owned Copy/transcript-language actions preserve
  exact revision/type/layer and their full focus/disabled/pending/error matrix;
  the visible Share host remains capability-gated and inert until Feature 203
  owns it; no type/content
mismatch; failures preserve useful work; route persistence and all accessibility
states pass in browser and embedded macOS.

**Decision resolved**: Constitution 5.0.0 authorizes literal observable Krisp
UX/UI/IA parity. Shipping still blocks on independent implementation,
accessibility and documented rights/provenance for third-party assets, logos and
trademarks. Approved functional labels and interaction microcopy may match
literally without a brand-distance rewrite.

## 197 — Automatic first result and recovery

**Outcome**: transcript readiness leads to a default result or honest bounded recovery without user babysitting.

- `F197-01` Define eligibility and exact source-ready event; consume and mutate
  only Feature 194's explicit same-workspace `MeetingCanonicalSourcePointer`,
  never reintroducing `latest_processing_result` ordering.
- `F197-02` Resolve one versioned default at dispatch time: explicit meeting choice first, then policy-authorized owner/personal default, then workspace default; before dispatch atomically reserve the Feature 183 slot and persist its one-default marker plus resolver source/version/time. Never consult the current viewer's presentation preference; missing/retired defaults fail honestly rather than falling through to another available type.
- `F197-03` Create deterministic idempotency identity across duplicate processing events.
- `F197-04` Coalesce active intents and prevent duplicate model calls.
- `F197-05` Define retry policy for dependency failures vs ambiguous egress vs invalid result.
- `F197-06` Own one authenticated, CSRF-protected and idempotent transcript-
  regeneration command. Its request binds meeting/workspace, selected BCP-47
  language, `expected_source_revision`, access/deletion/policy epochs and an
  idempotency key; its durable business request identity binds the same tuple plus
  the exact transcription pipeline and BCP-47 normalization/allowlist versions.
  Keep that hash separate from an immutable job UUID and Temporal Workflow ID.
  The first execution has retry ordinal zero; a successor names its predecessor
  and may be created only after a terminal failure carries positive safe-retry
  proof and all fences are fresh. Start `TranscriptRegenerationV1` with Workflow
  ID derived from the job UUID and `REJECT_DUPLICATE`, never from the reusable
  business hash. Persist
  the exact submitted/sending/accepted/ambiguous/processing/succeeded/failed/
  invalidated state machine and run it through the separate PINNED
  `TranscriptRegenerationV1` Temporal workflow. The same key+identity joins one
  job, the same
  key with different identity conflicts, and a stale expected revision fails
  without work. Lost responses are reconciled against the exact job; timeout or unknown
  provider acceptance never enables blind retry. Persist a provider
  correlation/idempotency ID before egress and require the selected provider to
  support authoritative lookup or signed callback. The submit Activity has
  `maximum_attempts=1`; definitive rejection is `sending→failed`, while an
  orchestration-level successor submission is allowed only after durable proof
  that no egress occurred. Expose authenticated authorization-first `GET current`
  and `GET by job_id` recovery with the same no-existence-leak denial, monotonic
  `state_version`, ETag/conditional polling and a typed event body so reload,
  navigation and reconnect resume the exact job without another POST. Success creates one new
  canonical source revision, while failure/ambiguity preserves the old source.
- `F197-07` On successful transcript source replacement, atomically mark every
  active saved old-source type stale and create exactly one bounded coalesced
  replacement intent per active saved available type, prioritizing the persisted
  default/current type. Move the explicit current-source pointer/revision and
  use the global deletion→source-pointer→job→sorted-slot→
  sorted-dispatch lock order and invalidate a losing expected-source job. Never
  generate unsaved catalog or retired types; retired results remain stale/read-only.
- `F197-08` Project ready/preparing/blocked/failed/no-useful-content states to Feature 196.
- `F197-09` Add time-to-first-result, stuck-attempt and recovery observability.
- `F197-10` Keep auto-summary, automatically open meeting page and automatic title generation as independent policies; reuse existing capture auto-start/exclusion settings without coupling recording, summarization or sharing defaults.

**Acceptance**: every eligible meeting reaches ready or explicit terminal/recovery state; duplicate source events produce one inference. Duplicate transcript-regeneration submissions join one exact job, reload/status polling never starts work, stale expected-source requests create no work, ambiguous acceptance stays wait-only until reconciliation, a safe successor has a new job/Workflow identity and predecessor proof, and only a confirmed replacement triggers the per-saved-type stale/recovery fan-out. The job and every created/replacement transcript or ProcessingResult artifact have same-workspace ownership/RLS, GRAF-controlled tombstone/purge accounting and a truthful retained-Temporal/provider-dependency distinction.

## 198 — Built-in profiles and type catalog

**Outcome**: each built-in type gives a recognizably useful projection without changing factual truth.

- `F198-01` Confirm the launch quick list and full catalog across: Auto,
  Outline, Minutes, Project Sync, Weekly Team, Planning & Decision,
  Brainstorm/Workshop, Retrospective, 1:1, Executive/Board, Client Status,
  Sales, Customer Success, Research Interview, Hiring, Training/Q&A, Incident,
  All Hands and Formal Minutes. Publish one exact `SummaryTypeCatalogEntryV1`
  snapshot with localized name/description, group/category, stable quick/full
  ranks, availability, opaque provenance/deviation metadata and one
  `catalog_version`; state changes never reorder a visible menu.
- `F198-02` Freeze every type as the exact `ProfileContractV1` row from
  `summary-profile-catalog.md`: section/empty-state order, the complete exact
  `SectionContractV1` semantic rule for every section, allowed and required
  kind-state/relation/role sets, risk, B1 default/budgets, caveats,
  forbidden-inference and master-clause IDs. Krisp-visible naming may be retained
  where rights review permits and evidence shows it helps recognition.
- `F198-03` Define the sole `ProfileContractCatalogV1` authority and the closed deterministic
  `CompositeProfileContractV1` merge over canonical intelligence; union
  kind/relation/criticality/prohibition clauses, take maximum risk, preserve the
  primary budget and exact section merge, and reject every non-allowlisted or
  conflicting secondary. Keep
  user-visible `template_key=auto` stable while immutable revision provenance
  records resolved profile/version/confidence and low-confidence internal
  `general_summary` fallback; no independent fact extraction.
- `F198-04` Define deterministic authorized prefilter and bounded ID-only model
  projection bound to the exact composite-profile hash and privacy-filtered
  display atoms, with route-proven `N_projection_objects` where 128≤N≤256, runtime
  batches 1..N, a 128-call ceiling and complete selected-or-omitted coverage.
  For text-topic focus, only projection batch zero receives the complete
  authorized ≤64-topic catalog plus `FocusRequestV1`; it must freeze the final
  `FocusV1`, and every later batch must consume that exact value without hidden
  resolution or fallback. Require the complete `CriticalityPolicyV1`
  profile-expansion population/reason-code binding, and require visible `state`
  exactly for stateful canonical kinds while forbidding it for stateless kinds.
  Follow it with mandatory bounded presentation synthesis using independent
  `N_synthesis_items`/`N_synthesis_selected_ids`, and statement-level verification
  using independent `N_verify_statements`/`N_verify_selected_critical_ids`, each
  with its own strict schema, tokenizer fixtures, envelope and 128-call ceiling, then a
  deterministic layout/markup renderer. Every one of the three closed request
  bodies must embed and rehash the same complete composite contract and clause
  closure; tests prove a secondary profile changes projection, synthesis and
  verification semantics, not only manifest metadata. Define merge/order/empty/overflow/
  pagination behavior and exact concise/standard/detailed section/item/text
  budgets plus the exact `EvidencePresentationPolicyV1` mapping. Critical
  relevant objects paginate rather than disappear; privacy that cannot faithfully
  preserve a critical item fails the type instead of silently hiding it; any phase
  capacity failure keeps the prior revision; 1/127/128/129/256/257 and
  16,384-object fixtures pass; no hidden model call exists.
  Zero eligible IDs, zero selected IDs and topic no-match/ambiguity must take the
  closed `AttemptTerminalEvidenceV1` path. Topic-catalog overflow instead uses
  the typed fail-closed `focus_topic_catalog_capacity_exceeded` path. Neither
  path creates synthesis, presentation verification, candidate, publication
  receipt or slot mutation.
- `F198-05` Build the sole immutable preregistered `ProfileClauseEvalManifestV1` wire plan and external candidate-root-bound `ProfileClauseEvalResultSetV1`: derive the complete 20-profile × 51-clause × 10-phase Cartesian matrix from the gap-free source registry, exact phase bindings and `ProfileContractV1.master_clause_ids`; every cell freezes phase/enforcement/applicability/disposition, evaluation class/authority, fixtures, evaluators and gate policy or an explicit generated N/A. Every LLM-judge plan binding contains only the complete `VerifierIdentityV1` plus `CalibrationRequirementPolicyV1` and MUST NOT contain a finalized calibration-manifest ID/hash. The measured result set carries the complete pre-call `CandidateEvaluationAuthorityV1`, exact phase-bound result for every preregistered ID and only then the finalized calibration bindings after verifying their embedded sealed execution plans/cohort. Cover every privacy/evidence cell and legal/illegal composite-profile pair in addition to suitable, unsuitable, mixed-profile, empty-section, correction, injection, long-meeting and mixed-language challenges. Missing/duplicate/reordered tuples, sparse N/A handling, post-hoc fixtures/runs or either calibration hash direction blocks the profile and cannot be averaged away.
- `F198-06` Add profile-fit, non-invention, coherence, redundancy and usefulness rubrics.
- `F198-07` Version the complete embedded profile-contract catalog as one bundle authority and define compatibility/rollback; do not create per-profile Langfuse prompts.
- `F198-08` Run real `gpt-5.6-luna` development experiments and record metadata-only results.
- `F198-09` Define notes output-language resolution and provenance independently
  from transcript language/regeneration. Do not reuse the Krisp `RU` top-strip
  affordance: any future authorized notes-language choice is a separately
  specified control outside that reference strip and a shared same-type refresh
  that keeps the old result/language visible while pending, atomically replaces
  only that type after verification, restores the old pair on failure and never
  retranscribes audio.
- `F198-10` Define typed audience/focus/detail/analysis projection policy,
  precedence and provenance; canonical visibility defaults to internal,
  model-only classification cannot authorize disclosure, and client projection
  requires trusted scope while prohibiting critical omission.
- `F198-11` Make `facts_only` the only Receipt V1 runtime value and routine
  uncertainty a typed marked gap rather than a user question. Defer model-authored
  analysis until a versioned phase/verifier/manifest/content/receipt and
  subject/egress policy contract exists.
- `F198-12` Add profile-specific negative fixtures for inferred owners/dates,
  unaccepted requests, personality/hiring inference, incident root-cause
  overclaim, unstated quorum/votes and client/internal leakage.
- `F198-13` Define an optional non-canonical follow-up draft assembled
  deterministically from verified visible decisions/actions/open questions with
  versioned static labels/order; it creates no new agreement and is never sent
  automatically. Any model rewrite requires a separately versioned prompt/schema/
  GenerationCall/verifier/envelope/receipt amendment.

**Acceptance**: every profile is distinguishable and useful on suitable
meetings, conservative on unsuitable meetings, and non-inferior on critical
accuracy; audience/focus never changes canonical truth or leaks unauthorized
content.

## 199 — Personal formats and defaults

**Outcome**: users assemble supported result structures without injecting arbitrary runtime authority.

- `F199-01` Define supported semantic blocks and per-block contracts.
- `F199-02` Model stable personal type identity with immutable template versions.
- `F199-03` Build safe data-to-profile compiler; personal text remains data, not system instructions.
- `F199-04` Implement one-click idempotent draft creation and autosave with saved/saving/error/offline recovery states.
- `F199-05` Separate built-in and personal collections; implement catalog search/filter/stable ordering and available/unavailable/retired states. Built-ins are immutable, may be duplicated/set default, and display default state explicitly.
- `F199-06` Implement create/edit/duplicate/delete/version/default permissions and permanent-delete confirmation; duplicate always creates a personal type, while delete retires future generation/default selection without removing historical meeting results.
- `F199-07` Implement preview and explain expected output before generation.
- `F199-08` Implement reorder with keyboard alternative, validation and recoverable draft state.
- `F199-09` Preserve old meeting results after template edit/delete and avoid bulk regeneration.
- `F199-10` Restore the prior ready result after a personal-format generation failure and hide raw provider errors.
- `F199-11` Add abuse/injection, duplicate-click, ownership, RLS and lifecycle tests.
- `F199-12` Reject `my_actions`, `private_self`, private coaching and every
  viewer-dependent block from personal shared-slot formats; point generated
  subject-scoped use cases to Feature 208 rather than adding a hidden cache key.

**Acceptance**: personal default affects future generation only; old revisions remain readable; custom content cannot override core/evidence/schema rules.

## 200 — Quality evaluation and promotion

**Outcome**: production changes require reproducible human-grounded paired evidence.

- `F200-01` Create authoritative dataset manifest schema, strata, exact/semantic deduplication and dataset authority lifecycle: source meeting/owner, purpose, region/access/retention, withdrawal/deletion invalidation and retained-observability disclosure; keep real meetings out until Feature 202 approval.
- `F200-02` Select ~100 representative logical-root observations for end-to-end open coding, plus named phase `GENERATION` observations only for phase diagnosis; use Langfuse v4 observation-level queues/evaluators, never deprecated trace-level evaluators, and open-code 30–50 into 5–10 failure classes.
- `F200-03` Freeze an owner-controlled annotation manifest over exact Langfuse
  queue/item observation IDs and assignments plus each ScoreConfig `configId`,
  `updatedAt`, `isArchived`, complete canonical read-back body/content hash and
  separately owner-versioned rubric. Langfuse has no ScoreConfig version field;
  pre/post read-back or queue/config drift invalidates the snapshot, and a
  semantic rubric change requires a new config ID. Then double-label and
  adjudicate the calibration subset.
- `F200-04` Freeze train/development/held-out splits and contamination checks.
- `F200-05` Implement deterministic evaluators and separate transport/schema/
  validator/semantic/utility rates. Calibrate and report source, candidate,
  canonical and profile-expansion `CriticalityPolicyV1` classification by every
  closed reason code, with human precision/recall, adversarial non-empty→empty
  challenges and legitimate zero-population cells reported explicitly. Validate
  complete source-span→clause coverage, every profile contract/composition,
  privacy action and evidence-display mapping with no aggregate waiver.
- `F200-06` Preregister and calibrate judges with confusion matrix, per-critical-class ≥50 positive/50 negative items, one-sided 95% lower bounds TPR≥0.95/TNR≥0.90, invalid rate <1%, per-format/class and exactly five separately named/read-back Langfuse stability runs; every run passes independently, critical items require exact 5/5 agreement, non-critical exact agreement ≥95%/pairwise kappa ≥0.95 and metric spreads obey `quality-and-evaluation.md`. Never leak `expectedOutput` or coerce invalid/abstain labels. Every run carries the complete immutable `VerifierIdentityV1` body plus adjacent recomputed hash and the complete pre/post `LangfuseEvaluatorReadbackV1` bodies plus adjacent hashes. Prompt, route, gateway/compiler, input/output/reason-code/validator artifacts are complete siblings or exact `ImmutableArtifactBindingV1` objects; request settings include their complete body/hash over exact `reasoning.effort`, verbosity, structured-output mode and complete output envelope. A change to any field creates a new evaluator/calibration-manifest identity and requires new blinded human calibration; because a new same-name evaluator version may move active Langfuse rules, candidate evaluators must not reuse a production-rule identity or mutate production monitoring before explicit promotion and read-back.
  Normative cardinality is exactly one complete `JudgeStabilityEvidenceV1` per
  `(decision_unit, verifier_key, actual_provider, actual_model)` and exactly one
  sorted `JudgeStabilityCohortV1` entry for every verifier × calibrated-target
  pair. Each unit contains five complete run bodies with ordinals `1..5`, five
  pre/post evaluator read-backs, raw per-class TP/FN/TN/FP/invalid/abstain rows,
  every metric/gate/class-stability row and exactly ten fixed pairwise-kappa
  rows. Target/verifier/decision-unit aggregation, sparse class rows, compact
  `run_count=5` or hash-only run/evaluator evidence is invalid.
  Before `F200-07` starts, this task also finalizes the immutable
  `ComparativeExperimentPlanV1`: complete frozen dataset/split binding;
  production and candidate identities/settings; exactly five expanded fresh
  task-run plan matrices per arm; all preregistered paired item/metric/format/
  preference/operational rows, exact ordering/cardinalities/statistics,
  confidence method, margins, missingness and gate policy. No measured result or
  post-hoc threshold appears in the plan, and `F200-07` may consume only this
  finalized body/hash.
- `F200-07` Run paired production/candidate experiments with ≥60 suitable/30 unsuitable held-out items per profile, ≥300 pooled critical challenges, one-sided 95% confidence intervals, −3pp VUSR per-format non-inferiority and zero critical-error margin; insufficient-power profiles remain shadow-only. Baseline and candidate first run with the same explicit preregistered effort for every phase. Each also runs the exact five fresh full-pipeline task-stability cohort from `quality-and-evaluation.md`; every repetition reruns extraction through presentation with new GenerationCalls, while separate five-run judge stability evaluates the resulting frozen outputs. Canonical critical IDs/states, Auto primary/unique secondary, non-droppable section assignment and presentation hard gates require 5/5 stability; non-critical pairwise F1/Jaccard and per-profile VUSR/rubric ranges meet their exact thresholds. Reusing one task output for five judges is invalid. Only after that same-effort cohort passes may the identical frozen suite run at exactly one supported effort level lower with every other setting fixed. The same-effort cohort alone determines the primary promotion; the lower-effort cohort is a separate candidate and must pass the complete gate independently. Prompt and effort never change in the same causal comparison. For Auto, additionally require ≥50 items per direction of every near-neighbor pair and ≥100 ambiguous/unsupported items, per-profile precision ≥95%/recall ≥90%, 100% high-stakes precision with zero unsafe escalation, pairwise confusion ≤5% (0% into high-stakes), high-confidence-class accuracy ≥95%, resolvable fallback ≤5% overall/≤10% per stratum, ambiguous fallback recall ≥95%, full-path repeat stability and zero sampled/partial-view path. Receipt V1 exposes categorical confidence only, so ECE and multiclass Brier are explicitly deferred until a versioned probability-vector or deterministic probability-mapping contract is bound into receipt and evaluation identity.
  Normative interpretation: the sentence about reusing one task output forbids
  claiming **task** stability from judge repeats. Judge stability itself MUST
  run five independent evaluator executions over one byte-identical complete
  frozen task-output manifest, as `JudgeStabilityEvidenceV1` requires. It never
  uses one item/partial output, and it never replaces the five fresh full-pipeline
  `TaskStabilityEvidenceV1` runs. The 60/30 plan may qualify; a separately named
  20/10 plan is `shadow_only` and cannot enter promotion evidence.
- `F200-08` Add counterbalanced blinded human preference and quality/cost/latency gates.
- `F200-09` Implement the exact non-cyclic root promotion protocol: the root embeds executable definitions and preregistered plans only; one immutable `RootQualificationRecordV1` binds that already-created candidate root/activation to the complete `ComparativeExperimentPlanV1` body/hash and complete `ComparativeExperimentEvidenceV1` body/hash, profile-clause evidence, both arms' five expanded fresh task-plan matrices and five evidence matrices, judge evidence, privacy review, operator approval, expected previous root and rollback. Its finalizer mechanically proves exact dataset/split equality, one-to-one plan/evidence run ordinals, paired-item identities/order, unchanged production/candidate identities and request settings, preregistered metric/format/preference/operational rows and statistics/margins/gates; a bare comparative hash, missing body, extra post-hoc row or unequal identity is non-qualifying. One authorized writer/lock then performs expected-root read/compare, moves only the protected root label, reads back, appends a successful `RootPromotionEventV1` and emits its exact `ImmutableArtifactBindingV1` (`artifact_id`, schema/event version and recomputed hash). Do not claim native Langfuse CAS; missing typed qualification/event binding, mismatch, unavailable protected-label capability or out-of-band movement fails closed on root+activation+event-binding last-known-good. The event binding stays outside root/activation bodies to avoid a digest cycle. Child labels never form runtime state. Treat every `GatewayRouteBindingV1` alias/allowlist or actual provider/model mapping change as a new candidate: run the same production-equivalent held-out, capacity, latency/cost and failure-path gates through LiteLLM, then promote the new root binding explicitly; alias equality alone is never continuity evidence.
- `F200-10` Add CI deterministic gates and operator-only shadow/no-replacement run.
- `F200-11` Populate the Feature 195 immutable `VerifierCalibrationManifestV1` registry from human-grounded Langfuse evidence, with mutable status head and append-only events strictly separate; activate/expire/revoke through the same locked monotonic head used by publication; bind exact event ID/epoch in both receipts, prohibit same-manifest reactivation, and require active/unexpired/non-revoked read-back at canonical receipt finalization and publication. Enforce ≤90-day validity and a five-run drift sentinel every seven days. Each drift event stores the five distinct Langfuse run IDs, frozen run/result hashes, per-run and aggregate metrics, agreement/breach verdict and evidence hash; one atomic active→active PASS refresh updates `last_pass`, day-8 deadline and evidence pointer. Both finalizers lock and verify that fresh head. Missed day-8, outage without a valid five-run PASS or a threshold/critical-agreement breach expires/revokes immediately. A replacement calibration gets a new manifest ID/hash and extraction-layer identity, never rewrites an old parent/receipt, and must pass day-7/day-8, stale-writer/race, breach/outage, expiry-before-reserve, expiry-between-finalizers, renewal, revocation, concurrent old/new writer and no-uniqueness-dead-end fixtures before activation.

**Acceptance**: zero critical regression, calibrated judges, reproducible baseline, exact rollback target and explicit operator approval; judge score alone cannot promote.

## 201 — Version-bound feedback and corrections

**Outcome**: user signals are attributable to the exact output and usable for error analysis without becoming approval friction.

- `F201-01` Model one authoritative feedback record per actor and exact workspace/meeting/type/outcome/bundle/scope. Scope is a closed `result | section | claim` union: section requires the exact immutable section key, claim requires the exact canonical claim ID, and the other discriminator fields are forbidden. Add stable client mutation ID, expected version and create/update/remove idempotency.
- `F201-02` Use one five-point helpfulness rating plus optional closed diagnostic reasons and private free text: ratings 1–3 reveal reasons, 4–5 expose them on demand. Result, section and claim scopes are explicit, version-bound and cannot alias or overwrite each other.
- `F201-03` Implement the Krisp-faithful non-blocking two-stage flow: `How were the:` first offers only sections visible in the pinned revision and writes nothing; choosing one expands that exact section's five-point emoji radio group. Use text labels, keyboard arrows, visible focus, exact result+section scope label, minimum target/reflow support, polite saved state, error association, and pending/saved/updating/failed/conflict/removing recovery. Close before first rating writes nothing; later choice updates the same section record; explicit remove clears.
- `F201-04` Preserve RLS, deletion accounting and retained-observability disclosures.
- `F201-05` Separate feedback from current revision mutation and prompt promotion.
- `F201-06` Publish the committed record server-side to deterministic source-named Langfuse scores, retrying score delivery without inference; export authorized metadata/content to curated annotation workflow with audit.
- `F201-07` Build failure-rate views by type/bundle/locale/duration without exposing private content broadly.

**Acceptance**: every signal is version-bound; duplicate/reload/offline/update/
remove/conflict fixtures converge on one authoritative record; keyboard and
screen-reader users can rate, amend, recover and remove without losing scope or
focus; feedback never auto-edits result, repeats inference or moves production
label; private data boundaries are explicit.

## 202 — Privacy, security, retention and abuse closeout

**Outcome**: the constitution-approved plaintext observability model is operated truthfully and safely.

- `F202-01` Document data-class/destination/region/retention/access matrix for GRAF, LiteLLM, Langfuse, Temporal and provider, including real-meeting dataset authority, withdrawal/deletion invalidation and what retained observations/histories cannot be erased by meeting deletion.
- `F202-02` Enforce HTTPS/approved host/CA and reject URL credentials/query/fragment for content destinations.
- `F202-03` Separate production/evaluation environments and review RBAC/service accounts/public-sharing controls.
- `F202-04` Implement prompt/bundle security revocation and authenticated operator mutation audit.
- `F202-05` Sanitize and size-bound provider/gateway errors outside constitution-retained exact-response fields.
- `F202-06` Enforce request/concurrency/token/cost budgets and rate-limit manual refresh.
- `F202-07` Audit immutable content hashes/pointers and alert on unauthorized current-revision mutation.
- `F202-08` Reconcile deletion copy/reporting with retained Generation Call/Langfuse/Temporal policy, including `TranscriptRegenerationJob`, provider operation evidence, every replacement `ProcessingResult`/transcript artifact and its MediaScribe dependency state. GRAF-controlled rows/artifacts use same-workspace composite ownership, RLS and purge/tombstone accounting; retained Temporal observability is reported separately and never presented as a still-readable meeting artifact.
- `F202-09` Threat-model cross-tenant Temporal/Langfuse access and apply deployment identity/network controls.
- `F202-10` Run adversarial injection, citation laundering, XSS/Markdown/formula and cross-scope challenge suite.

**Acceptance**: no unapproved egress, mutation or cross-tenant access; user deletion language matches actual controlled/retained artifacts; policy changes go through constitution amendment.

## 203 — Type-pinned share and export

**Outcome**: outward artifacts are explicit, stable and never leak internal or wrong-type results.

- `F203-01` Extend the Feature 183 default-type compatibility pin to explicit arbitrary-type input for public link, authenticated share and each export format.
- `F203-02` Apply the same exact resolver and denial semantics to every explicit-type path without reintroducing latest-row/global-pointer/internal-candidate fallbacks.
- `F203-03` Surface selected/default type before egress and preserve the
  approved reference-fidelity copy with truthful GRAF-specific permissions.
- `F203-04` Define a policy-gated capability matrix before creation: edit, comment, full meeting view (notes/transcript/recording) and notes-only view; invite-only is the fail-closed link scope, with workspace/team/anyone-with-link exposed only when authorized. Include disabled reasons and no-existence-leak behavior.
- `F203-05` Specify one state machine for idle/pending/succeeded/failed/ambiguous/revoked/expired/deleted share and export creation, including navigation-away and authoritative reconciliation.
- `F203-06` Implement stable idempotency, duplicate-submit coalescing and proven-safe retry without duplicate links/artifacts.
- `F203-07` Implement the user-facing create-new-artifact/share flow after refresh, type deletion and template version change without mutating an existing pinned artifact/link; resolve/validate the slot and write type/revision/permission/scope at one authoritative transaction linearization point.
- `F203-08` Apply authorization, expiration, revocation, deletion and audit requirements; for profile contracts marked `external_sensitive` or `regulated_record`, create a first-class immutable one-egress-intent review receipt and canonical digest over exact outcome/root and resolved-run manifests/projection policy/profile risk/approved audience/intended egress purpose/exact recipient or link scope/capability/policy-access-deletion epochs/reviewer/expiry/revocation. The authoritative artifact transaction locks and revalidates the receipt and current access/policy/deletion state, writes its ID/digest with the grant/artifact and atomically consumes it; refresh, recipient/scope/capability change, policy change, access loss, expiry, revocation or deletion requires a new review. Ordinary on-screen reading remains approval-free.
- `F203-09` Show bounded success confirmation with exact type/revision/recipient-or-link/permission/scope and calm failure recovery without losing current context; keep recap audience and default link permission as separate settings from auto-summary/capture policies.
- `F203-10` Add browser and embedded-macOS parity tests across pending/ambiguous/success/failure and HTML, Markdown, CSV/XLSX, JSON and supported caption/transcript bundles where summary is included. Prove dialog title/description and control labels, logical focus order/trap, initial and restored trigger focus, Escape/close semantics, disabled reasons, grouped permission/scope semantics, polite status/error association, 390px/200% reflow, target size, screen-reader state changes and no private detail after access loss.

**Acceptance**: every artifact identifies exact type/revision; duplicate/reload/ambiguous paths create at most one artifact; later refresh never changes an existing artifact silently; inaccessible/internal revisions are denied; high-stakes egress cannot bypass, race or reuse a stale/consumed review receipt, and the created artifact carries the exact receipt ID/digest; browser and embedded macOS show the same authoritative lifecycle.

## 204 — Production rollout, SLO and rollback

**Outcome**: controlled launch with observable stop conditions and tested recovery.

- `F204-01` Define feature flags and cohorts for slot lifecycle, runtime, profiles and UX independently.
- `F204-02` Define SLOs for time-to-first-result, saved switch, invalid/stale rate, critical quality, latency and cost.
- `F204-03` Build metadata-safe dashboards/alerts and stuck/ambiguous call runbooks.
- `F204-04` Prove rollback for code, database reader cutover, Workflow Type and prompt bundle.
- `F204-05` Run operator dogfood and small-cohort shadow/visible stages with stop criteria.
- `F204-06` Validate browser/embedded/macOS release compatibility,
  reference-fidelity, accessibility and third-party asset provenance.
- `F204-07` Produce release notes, migration impact, known limitations and evidence links.
- `F204-08` Expand rollout only after each stage meets quality/security/cost/SLO gates. Before every capacity-expanding stage, re-read the exact installed Temporal Server/SDK/API, one-partition/one-Worker-Deployment scope, all three effective Fairness flags and backlog-drain state, then rerun the complete `temporal-langfuse.md` matrix independently for Workflow and Activity queues: five equal-weight dominant+20-small-key trials with ≥500 post-warm-up starts per key, every ratio and simultaneous Bonferroni-corrected 95% Wilson bound in 0.80..1.20, per-key p99 ≤2× unloaded-small-key p99+30s and automatic/background ≥10% lane floors; ≥3 weighted 0.5/1/2/4 trials with ≥10,000 starts, ≥500 per key and every ratio/bound in 0.85..1.15; and the same gates after restart excluding a 120-second convergence window. Flags alone never prove readiness; any missing floor, failed/inconclusive bound, p99/lane breach or post-restart failure keeps the separate queues/custom scheduler or stops expansion.
- `F204-09` Block full public Summary Workspace general availability until
  Feature 201's optional version-bound feedback UI and Feature 205's inline
  completion/assignee/due command path pass browser/embedded accessibility,
  authorization, reload and failure tests. Neither is required to calibrate or
  promote the initial prompt bundle, and feedback remains optional per user.

**Acceptance**: rollback is rehearsed; no unresolved critical/high blocker; release evidence maps every gate to exact run/version; production promotion remains explicit.

## 205 — Canonical mutable action lifecycle

**Outcome**: one authorized mutable task state is shared by meeting detail and future global projections while summary revisions remain immutable.

- `F205-01` Specify canonical action identity, source refs, originating outcome/type/bundle provenance and immutable-vs-mutable field boundary.
- `F205-02` Add one mutable action ledger for completion, assignee, due date and expected edit version; do not copy rendered summary text into a second extraction stack.
- `F205-03` Implement one authenticated command path for completion/assignee/due edits with RLS, CSRF, no-existence-leak and audit.
- `F205-04` Add idempotency and expected-version conflict behavior for duplicate, offline replay and concurrent edits.
- `F205-05` Define user-edit precedence over future model refreshes and preserve explicit unknown owner/date until edited.
- `F205-06` Register deletion/accounting and ensure edits never mutate the immutable summary revision, feedback ledger or prompt bundle.
- `F205-07` Prove reload persistence and browser/embedded command parity in executable server and macOS contract suites, including keyboard-only checkbox/assignee/date editing, text labels and status, visible focus, busy/disabled semantics, target size, 390px/200% reflow, optimistic/pending/error/conflict announcement, focus preservation after completion or refresh, and recovery without duplicate commands.
- `F205-08` Add the first positive `my_actions` capability: authorization runs
  before filtering, trusted authenticated-subject↔participant mapping is pinned,
  only canonical Feature 205 actions are returned, missing/inaccessible/other-
  subject cases share one no-existence-leak denial, and the Feature 196 view
  creates no summary revision, attempt, dispatch or model call.

**Acceptance**: one task command path plus the downstream-gated `my_actions`
filter pass authorization, duplicate/concurrent edit, reload, deletion,
no-existence-leak and immutable-summary separation tests; no model call occurs
for a task edit or filter.

## 206 — Cross-meeting Action Hub

**Outcome**: one canonical task state is usable inside a meeting and across all meetings.

- `F206-01` Specify global projection/read model over Feature 205 canonical action records; no second extraction or summary parsing.
- `F206-02` Define open/completed, assignee, due-date and source-meeting filters, stable ordering and search.
- `F206-03` Implement inline completion/assignee/due edits through the Feature 205 command path.
- `F206-04` Implement exact meeting/type/evidence return with preserved focus and player context.
- `F206-05` Implement loading/empty/error/access/deletion/unavailable/paywall states without implying that no tasks exist.
- `F206-06` Prove reload and cross-view consistency, idempotent updates and stale-edit conflict recovery.
- `F206-07` Pass RLS/no-existence-leak, keyboard, VoiceOver, 390px and 200% zoom checks.

**Acceptance**: meeting and global projections converge on one task state, no model call occurs, and inaccessible meeting/task identity is not disclosed.

## 207 — Cross-meeting continuity summary

**Outcome**: recurring work gains a trustworthy delta without making previous
minutes a second source of current truth.

- `F207-01` Define authorized previous-meeting/series selection and exact pinned
  previous/current canonical artifact identities.
- `F207-02` Compare stable decision/action IDs first and create reviewable
  semantic match candidates only when identity is unavailable.
- `F207-03` Derive completed/carried-over/overdue deterministically from Feature
  205 state, meeting date and timezone.
- `F207-04` Preserve separate previous/current evidence and represent changed,
  superseded, new and removed decisions without inventing causality.
- `F207-05` Treat external `previous_minutes` as untrusted context that cannot
  close or mutate a task and cannot override either canonical artifact.
- `F207-06` Apply workspace/RLS/no-existence-leak, deletion and source-revision
  fences to both meetings.
- `F207-07` Render continuity as an optional section/profile projection; failure
  never blocks or rewrites the current-meeting summary.
- `F207-08` Evaluate identity, semantic matching, calendar status, access loss,
  changed decisions and absent previous meeting on held-out fixtures.
- `F207-09` Keep stable-ID continuity deterministic by default, but before any
  continuity output can publish, version the resolved-run manifest,
  rendered-content payload and publication receipt and add a strict proof over
  previous/current artifact and canonical-receipt identities, Feature 205
  ledger snapshot, selector/authorization policy, timezone, algorithm and
  delta/evidence coverage. Before a semantic model call, also version the phase
  enum, define call ownership and numeric batch/context/call ceilings, and add
  exact-fit/one-over plus failure-isolation fixtures.

**Acceptance**: every delta has a validated versioned proof with pinned
two-meeting/action-ledger/policy/timezone/algorithm provenance bound into the
exact rendered outcome; task state is not mutated by prose; unauthorized or
deleted prior context fails closed; disabling continuity leaves the current
summary unchanged. Receipt V1 accepts no continuity field or section.

## 208 — Subject-scoped generated outcomes

**Outcome**: explicitly private generated content is isolated by authenticated
subject and can never reuse or contaminate a shared meeting/type slot.

- `F208-01` Define allowed product purposes, explicit audience/consent policy and
  forbidden sensitive-trait/private-coaching cases before enabling generation.
- `F208-02` Define `SubjectScopedOutcomeRequestV1` over exact workspace, meeting,
  authenticated user, trusted participant-mapping snapshot/hash, access-policy
  epoch, owner-bound personal template version, source basis and root bundle.
- `F208-03` Add a separate subject-scoped slot/cache uniqueness contract; never
  add subject fields to, fall back to or alias a shared Feature 183 slot.
- `F208-04` Version the projection/synthesis/verifier schemas, resolved-run
  manifest, rendered-content payload and publication receipt; Receipt V1 rejects
  every one of these fields.
- `F208-05` Prove authorization-before-existence, RLS, cross-user substitution,
  mapping change, revocation, deletion/accounting, duplicate dispatch and stale
  source/policy races.
- `F208-06` Keep results private and new egress disabled by default; any later
  share/export requires an explicit subject/audience/purpose-bound review receipt
  and cannot be promoted to meeting default.
- `F208-07` Build a separately consented/calibrated held-out corpus and evaluators
  for subject attribution, privacy leakage, critical omission and wrong-viewer
  exposure; shared-slot evaluator identities cannot be reused.

**Acceptance**: every published result reconstructs one exact subject-scoped
identity/receipt, a different viewer or mapping cannot read/reuse it, deletion
and revocation fail closed, and Feature 199/Receipt V1/shared slots remain unable
to represent it. Feature 205/196 read-time `my_actions` remains zero-inference
and independent.

## 209 — Editable note-document blocks and comments

**Outcome**: every observed note-block action works against a human-editable
document revision without mutating the generated result.

- `F209-01` Define document/revision/block/comment identities pinned to exact
  meeting, type and source `outcome_set_id`, with generated/human provenance.
- `F209-02` Implement the complete observed inline-selection toolbar and block
  handle as real authorized operations: bold, italic, underline, strike,
  left/center/right alignment, text and highlight colors, nest/unnest, link,
  comment and block actions, plus block color/copy/duplicate/comment/delete.
  Every rendered command has a stable operation, selection/block identity and
  no canonical-result mutation; unsupported commands are absent rather than
  inert icons.
- `F209-03` Add idempotency, expected-version conflict, offline replay and
  concurrent editor/commenter recovery with one authoritative document.
- `F209-04` Bind comment visibility and edit rights to Feature 203 capabilities;
  authorization precedes existence and no hidden block/thread leaks.
- `F209-05` Define refresh/rebase/reset, history, share/export pinning and
  deletion/accounting so a new generated result never overwrites human edits.
- `F209-06` Reproduce the observed menu geometry/copy and pass keyboard,
  VoiceOver, target-size, focus-restore, non-color and destructive-action checks.
- `F209-07` Prove browser/embedded parity, reload, conflict, access loss,
  deletion and immutable generated receipt/content in executable fixtures.

**Acceptance**: every visible action persists exactly once or fails without
data loss; generated claims/evidence/receipts remain immutable and provenance is
always visible.

## 210 — Grounded meeting assistant

**Outcome**: contextual questions and suggested tasks return evidence-backed
meeting answers without hidden inference or product-state mutation.

- `F210-01` Define explicit query/session/request identity, authenticated subject,
  authorized context selection and transcript/note data-instruction boundary.
- `F210-02` Specify query-focused extraction, synthesis and semantic/omission
  verification with strict unsupported-answer and evidence contracts.
- `F210-03` Version assistant prompts/schemas/settings/route/calibration and bind
  complete LiteLLM, Langfuse, Temporal, GenerationCall and receipt provenance.
- `F210-04` Reproduce the compact host and contextual suggestions with explicit
  submit, busy, cancel-only-when-real, reload, ambiguous, error and source-jump states.
- `F210-05` Enforce RLS/no-existence-leak, privacy/audience, deletion/accounting,
  retention, rate/cost limits and zero mutation of summary/source/action truth.
- `F210-06` Build human-grounded held-out query/answer/evidence, injection,
  unsupported, mixed-language, long-meeting and access-boundary evaluations.
- `F210-07` Prove browser/embedded accessibility and exact session recovery;
  assistant availability never makes the meeting or saved summaries unusable.

**Acceptance**: every answer is reconstructable and supported, unknown stays
unknown, and no open/type/suggestion action starts inference before explicit submit.

## 211 — Transcript correction revisions

**Outcome**: text, speaker and segment-exclusion corrections produce one audited
canonical source and deterministic dependent-summary recovery.

- `F211-01` Define immutable transcript revision, segment operation, actor/audit
  and canonical-source pointer contracts over accepted media.
- `F211-02` Implement authorized idempotent expected-version text edit, speaker
  correction and reversible segment exclusion; never edit accepted bytes in place.
- `F211-03` Integrate source-pointer CAS with Feature 197 so confirmed correction
  stales active saved old-source types and coalesces only eligible regeneration.
- `F211-04` Preserve participant mapping, evidence offsets/segment identity and
  explicit invalidation/rebinding semantics for downstream canonical artifacts.
- `F211-05` Reproduce visible transcript-row controls with keyboard alternatives,
  confirmation, focus, conflict/offline/error and undo/restoration states.
- `F211-06` Enforce RLS/no-existence-leak, deletion/accounting, concurrent
  language regeneration and access-loss behavior across server and local cache.
- `F211-07` Pass browser/embedded correction, race, undo, stale-summary, egress,
  unsaved/retired-type and immutable-history fixtures.

**Acceptance**: every accepted correction creates one exact source revision,
old results remain readable/stale as authorized, and no race overwrites a newer
source or dispatches an unrequested type.

## Later operator-only GEPA pilot

- Freeze a synthetic-only optimization scope and budget.
- Use Feature 200 evaluators and development split only; held-out remains untouched until finalist.
- Produce candidate numeric prompt versions without production labels.
- Compare against manual iteration and baseline on quality/cost/latency Pareto frontier.
- Stop on judge gaming, evaluator drift, contamination or critical regression.
- Require the ordinary Feature 200 promotion path; GEPA never auto-promotes.

JEPA is not part of this backlog because it does not solve prompt optimization for the product pipeline.
