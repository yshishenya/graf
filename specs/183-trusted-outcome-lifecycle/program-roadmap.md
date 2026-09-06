# Program Roadmap: GRAF Meeting Intelligence

## North-star outcome

После встречи пользователь быстро получает полезные, доказуемые итоги в подходящем формате; переключает уже созданные типы мгновенно; обновляет один тип без потери остальных; проверяет источник одним действием; GRAF сам обрабатывает нормальные состояния и просит решение только там, где без пользователя невозможно понять намерение.

## Dependency graph

Downstream meeting-intelligence slices use repository feature numbers
`194`–`211`. Numbers `190`–`193` are already allocated to unrelated active
features, so they are not reused by this program.

```text
182 Canonical speaker turns
 ├─→ 183 Trusted per-type revisions
 └─→ 194 Canonical intelligence artifact

183 + 194
 └─→ 195 Durable verified generation runtime

194
 └─→ 198 Built-in profiles

183 + 194 + 195 + 198
 ├─→ 196 Summary workspace UX
 └─→ 197 Automatic initial generation and recovery

196 + 198
 └─→ 199 Personal formats and defaults

194 + 195 + 198
 └─→ 200 Evaluation and promotion gate

183 + 194 + 195 + 196
 └─→ 201 Version-bound feedback/corrections
       └─⋯→ optional signals for later 200 iterations; not an initial gate

202 dataset-authority gate
 └─→ 200 use of real meeting content
      (synthetic/individually authorized work may precede it)

195 ─→ 202 Privacy/security/retention closeout
183 + 196 ─→ 203 Type-pinned share/export
197 + 200 + 201 + 202 + 203 + 205 ─→ 204 Full public Summary Workspace rollout/SLO/rollback

194 ─→ 205 Canonical mutable action lifecycle
205 ─→ 196 editable action controls (`F196-11`), required for full public rollout
196 + 202 + 205
 └─→ 206 Cross-meeting Action Hub

194 + 198 + 205
 └─→ 207 Cross-meeting Continuity Summary

194 + 195 + 198 + 199 + 202
 └─→ 208 Subject-scoped generated outcomes
      (Feature 205 is additionally required for generated action-personal views)

196 + 201 + 203
 └─→ 209 Editable note-document blocks and comments

194 + 195 + 196 + 200 + 202
 └─→ 210 Grounded meeting assistant

194 + 196 + 197 + 202
 └─→ 211 Transcript correction revisions

204 + 209 + 210 + 211
 └─→ Full observed meeting-detail surface parity
```

Номера отражают независимые feature slices, а dependency order — порядок допуска
к rollout. Feature 200 не ждёт пользовательский feedback UI: human annotation,
synthetic/authorized datasets and deterministic evaluators suffice for initial
prompt calibration/promotion. Но полный публичный Summary Workspace не считается
Krisp-parity без необязательного для пользователя version-bound feedback из 201
и работающих inline action controls из 205. Это rollout prerequisites, а не
ручное принятие итогов и не циклическая зависимость начального prompt gate.
Первый trustworthy-summary rollout может предшествовать Features 209–211, но
полная observed-surface parity не заявляется, пока note-block menu, contextual
assistant и transcript-row correction controls не получили их реальные
авторизованные lifecycle-контракты.

## Feature slices

### 182 — Canonical speaker turns (prerequisite)

**Outcome**: все transcript/review/timeline/outcomes/export consumers используют одну устойчивую speaker-attributed evidence model.

**Exit**: merged/released exact SHA, text conservation, degraded-provider handling, stable segment refs. Текущий `bf53730` — база планирования, не доказательство release.

### 183 — Trusted per-type revisions

**Outcome**: один current result per meeting/type; switching reuses saved output;
the slot/read/default-egress foundation and one fail-closed publication entry
point are ready for a later verified replacement; old remains on failure.

**Independent proof**: PostgreSQL lifecycle/migration/egress matrix plus
DB-only expected-current CAS fixtures. Every model-generated path remains
fail-closed: Feature 183 creates no receipt schema/producer, canonical artifact,
GenerationCall membership or successful model-publication fixture. Production
auto-publication remains unavailable until 194 defines the canonical contract
and 195 extends the same entry point with both receipts and its first positive
publication path.

### 194 — Canonical evidence-backed intelligence contract

**Outcome**: одна typed knowledge model — brief, topics, decisions, actions, risks, questions, contradictions and source refs — independent of presentation type.

**Key work**:

- compact `core` contract and discriminated-union claim/relation schemas;
- closed source-authority, decision/action/disposition/effective-date and
  `UncertaintyV1` schemas, including `requires_approval` and no guessed gaps;
- segment → extract → deduplicate/resolve → verify contract;
- deterministic identity/span/relation checks, one gap-free versioned
  `SourceVerificationCatalogV1`, mandatory calibrated semantic entailment for
  every canonical claim and source→candidate/candidate→canonical critical-
  omission gates;
- contradiction and correction precedence;
- long-meeting segmentation and merge rules;
- explicit canonical-artifact reservation/reuse/waiter/retry/RLS/deletion
  lifecycle and layer-specific invalidation across summary types;
- explicit same-workspace current-source pointer, unambiguous legacy backfill
  and runtime cutover away from newest-processing-result queries;
- one root prompt/version bundle manifest as the sole production selection point.

**Exit**: deterministic validators and synthetic challenge set pass; no runtime orchestration claim.

### 195 — Durable verified generation runtime

**Outcome**: production-equivalent LiteLLM/Langfuse/Temporal path can generate and publish safely once.

**Must fix before V2**:

- persist every response reaching GRAF before lifecycle projection;
- ambiguous egress does not blind-retry inference; OpenAI
  `max_retries=0`, LiteLLM `num_retries=0` and zero automatic
  gateway/provider/transport retries leave Temporal as the sole retry authority;
- every model phase uses idempotent network-free prepare plus one
  `maximum_attempts=1` invoke guarded by a committed `prepared → sending` CAS;
  sending/ambiguous never resends, raw response is shield-persisted before
  validation, and only authenticated `ProviderNoEgressProofV1` may authorize a
  bounded new successor GenerationCall with predecessor proof;
- cancellation and abandoned child semantics;
- aggregate Temporal History budget;
- real replay fixtures and isolated `MeetingOutcomePipelineV2` interactive,
  automatic and background Task Queues, with V1 drain ownership;
- Task Queue Priority/Fairness treated as Public Preview; self-hosted activation
  must read back `matching.useNewMatcher=true`,
  `matching.enableFairness=true`, `matching.enableMigration=true` and prove
  backlog migration, otherwise retain separate queues plus the measured custom
  weighted-fair scheduler. Flags alone never prove readiness. The rollout gate
  repeats independently for Workflow and Activity queues: five equal-weight
  trials over one dominant plus 20 small continuously ready keys, at least 500
  post-warm-up starts per key, every share ratio and simultaneous
  Bonferroni-corrected 95% Wilson bound inside `0.80..1.20`, each key's p99 no
  worse than `2 × unloaded-small-key p99 + 30s`, and both automatic/background
  lane floors at least 10%; then at least three weighted trials over
  `0.5/1/2/4`, at least 10,000 starts and 500 per key, with each weighted ratio
  and simultaneous bound inside `0.85..1.15`; after worker restart exclude a
  120-second convergence window and rerun the same gates;
- Worker Deployments with immutable build IDs, `PINNED` V2 behavior,
  explicit Python `WorkerDeploymentConfig`/`use_worker_versioning`,
  ramp/current/rollback evidence and repeated post-convergence removal proof:
  replay-corpus PASS, `DrainageStatus=drained`, zero exact-version open runs,
  no poller and not-current/not-ramping; recovery distinguishes compatible
  Versioning Override from operator-approved Reset-with-Move;
- versioned Pydantic Workflow/Activity input/result boundaries and one pinned
  client/Worker data converter;
- one logical GenerationCall delivery identity with exact
  pending→sending→confirmed|ambiguous Langfuse transport truth, owner-token CAS,
  crash-after-send→ambiguous reconciliation, W3C-valid same-trace root/parent/
  child IDs and retry only after proven pre-export failure, never a claimed
  exactly-once upsert;
- persist immutable canonical/publication receipts only in their artifact/attempt
  owner rows and normalized GenerationCall owner/phase membership exactly as
  `contracts/receipts.md` defines; add no receipt table/reservation and no
  same-attempt/single-receipt compatibility path;
- carry one complete immutable `root_promotion_event_binding` through the
  canonical parent, every GenerationCall, resolved-run manifest, terminal
  evidence, deterministic renderer and both receipts; every pre-egress and
  finalizer path fetches/re-hashes the successful event and its embedded
  qualification record, while the root/activation manifest remains cycle-free;
- keep pre-promotion execution cycle-free through a complete
  `CandidateEvaluationAuthorityV1` and evaluation-only sink; candidate calls
  never require a future promotion event or gain publication owners;
- finalize canonical owner-row receipt first, then publication owner-row receipt
  + slot CAS + exact DispatchIntent in one later transaction using the shared
  lock graph including the current-source pointer before every slot, with
  deterministic GenerationCall ordering and source-replacement deadlock fixtures;
- obtain each receipt's `issued_at_us` from one `clock_timestamp()` inside the
  final conditional data-modifying SQL statement after all locks; use the same
  value for freshness and DB canonicalization/hash, never transaction/statement/
  caller time;
- prompt revocation and bundle pinning;
- per-user/workspace concurrency/token/cost budgets.
- one shared canonical extraction for concurrent type fan-out and deterministic
  no-op phase skipping where allowed by the pinned bundle.
- mandatory observed presentation-synthesis and presentation-verification
  Generation Calls/Activities with strict schemas and calibrated gates, followed
  by a deterministic layout/markup renderer that never writes factual prose;
- projection batch-zero `FocusRequestV1 → FocusV1`, complete exact-body/hash
  `CriticalityPolicyV1` profile-expansion coverage, conditional visible `state`
  and the no-publication `AttemptTerminalEvidenceV1` zero-content path;
- exact `GatewayRouteBindingV1` pre-egress/actual-provider binding and immutable
  per-phase `RequestSettingsV1`, versioned endpoint/serializer/translator/default-
  drop request-compiler binding, `VerifierIdentityV1` including Langfuse evaluator
  numeric version and calibration-manifest/separate status-event identities
  through both finalizers;
- create the first receipt-vector artifact as schema-valid positive
  P1–P4/full-schema fixtures, all five resolver modes with mandatory profile
  projection, complete English/Russian bodies, executable RFC 6901 rejection
  mutations and exact-fit/one-over envelope vectors;

**Exit**: the first receipt-backed positive publication succeeds only through
Feature 183's extended entry point; full receipt/race/conformance, fault-
injection and real dependency integration pass; no user-facing rollout.

### 196 — KRISP-parity Summary Workspace

**Outcome**: simple meeting detail experience faithfully matching the approved
Krisp UX/UI/IA reference.

**Scope**:

- `Итоги`/`Расшифровка` primary context;
- meeting list/search entry with Upcoming/Later (`Отложенные` in Russian), exact star/date/contains/company/type/tags/folders facets, deterministic date/duration/last-modified sort, recent `⌘K` search and no-result/access-safe states;
- inline quick type switcher and full catalog;
- instant saved-type switching;
- ready-only Refresh in the stable right action cluster immediately left of
  Copy; updating/blocked/deferred/ambiguous keeps that slot disabled/busy, while
  missing types omit Refresh and use the type-scoped status panel;
- Auto renders only non-empty `Action Items`/`Key Points` sections in that order,
  with actions isolated to the first and all other selected outcomes to the
  second; both empty is `no_supported_content`, not an empty published shell;
- deterministic reformat banner for ready Auto when the available target
  Meeting Minutes version is unsaved, with exact user+meeting+target-version
  dismissal and one `Try it out` ensure+selection intent;
- same-type current result remains while update runs; a missing selected type shows its own honest preparing state and never another type's content;
- failed missing-type generation restores the last ready type only if that request still owns the latest presentation intent; newer user selection/navigation is never overwritten;
- per-user/per-meeting persistence of the last successful type and `Итоги`/`Расшифровка` view across browser and embedded macOS;
- persistent player and evidence seek/return with pinned outcome/claim anchor plus type/scroll/focus/time/play-state restoration across refresh;
- read-only action items in the core summary lane with a timestamp on every
  evidenced action; inline completion/assignee/due appears only after Feature
  205, with task/assignee/due/timestamp kept in one row, model-proposed owner/due
  requiring evidence and explicit user edits retaining user provenance;
- honest orthogonal loading/short/empty/transcript-failed/summary-failed/blocked/deferred/ambiguous/stale/outage/unavailable/retired/paywall/access/deletion states; the visible Krisp-parity `RU` control is transcript regeneration only, and notes output-language policy belongs to Feature 198 outside that strip;
- exact-revision Copy and the observed transcript-language/explicit-Regenerate
  control, enabled only through Feature 197's authenticated/idempotent exact-
  source-revision command; an always-present disabled Share host for accessible meetings until
  Feature 203/policy enables it. Feature 203 alone owns the Share action, dialog,
  commands and lifecycle;
- explicit 300 ms/5 s loading thresholds, duplicate-click coalescing and no fake cancellation;
- a closed opaque inventory for every observed search/header/navigation/overflow/
  integration/contextual control and state, with owner, behavior, accessibility
  and reproduce/deviate/out-of-scope disposition;
- executable player/transcript parity for play/pause, seek/scrub, speed, speaker
  lanes/filter, preparing/unavailable/error, keyboard/VoiceOver and focus restore
  in browser and embedded macOS;
- WCAG 2.2 AA browser target plus equivalent embedded keyboard/VoiceOver, explicit control keyboard model, contrast/target-size/focus/live-region requirements, 200% zoom, 390px and reduced motion.

**Reference gate**: Constitution 5.0.0 authorizes literal observable Krisp
UX/UI/IA parity. Feature 196 must document exact reference screens/states,
deliberate deviations, accessibility proof and rights/provenance for every
third-party asset, logo or trademark; implementation code remains independent.
Approved functional labels and interaction microcopy may match literally.
Every visible reference element has the closed release state `not_applicable |
cleared | replacement_required | blocked`; the last two cannot ship.

### 197 — Automatic initial result and recovery

**Outcome**: after transcript readiness GRAF resolves default type, dispatches exactly once and reaches ready or a truthful bounded recovery state without user babysitting.

**Scope**: trigger, persisted meeting/policy default resolution, and one
authenticated/CSRF/idempotent transcript-regeneration command. The command binds
canonical BCP-47 language, expected source, access/deletion/policy epochs and
pipeline version; separates business dedupe identity from immutable job UUID and
`REJECT_DUPLICATE` Workflow ID; gives each proven-safe successor a retry ordinal
and predecessor; persists a provider correlation ID before the single-attempt
submit Activity; owns definitive rejection versus ambiguous lost-response
reconciliation through required provider lookup/signed callback; exposes
authorization-first current/by-ID status reads with monotonic state version and
conditional polling; owns the closed durable job/ambiguity state machine and
PINNED Temporal workflow; and replaces the source only through the global
fenced transaction that fans out to saved active available types. Jobs and all
replacement transcript/ProcessingResult artifacts have same-workspace RLS,
purge/tombstone accounting and a separate retained-Temporal dependency record.
Feature 197 consumes Feature 194's same-workspace
`MeetingCanonicalSourcePointer` and owns its fenced language-regeneration
mutation. Auto-summary,
open-after-meeting and automatic-title policies remain independent; capture
auto-start/exclusions and recap sharing defaults stay in their owning features.
UX state rendering belongs to 196; summary runtime safety belongs to 195.

### 198 — Built-in meeting profiles

**Outcome**: built-in types have distinct, evidence-safe structures over the same canonical intelligence.

Profile coverage: Auto, Outline, Meeting Minutes, Project Sync, Weekly Team,
Planning & Decision, Brainstorm/Workshop, Retrospective, 1:1,
Executive/Board, Client Status, Sales Discovery/Demo, Customer Success,
Research Interview, Hiring Interview, Training/Q&A, Incident/Postmortem, All
Hands and Formal Minutes. The quick list may stay Krisp-sized while the full
catalog exposes specialized profiles. Krisp names/copy may be reproduced where
they are functional reference UI wording. Third-party logos, trademarks,
slogans, marketing copy and assets retain their rights gate. Every type still
requires suitable/unsuitable fixtures, forbidden-inference tests and GRAF
usefulness/accuracy validation.
The normative purpose/section/exclusion contract is
`summary-profile-catalog.md`. Every section carries an exact embedded
`SectionContractV1.semantic_rule`; the complete composed body/hash is the one
profile authority used by projection, synthesis, verification, content and
receipt. Per-profile Langfuse prompts are intentionally absent.

Audience, focus and detail are versioned projection controls, not free-form
prompts. Receipt V1 accepts only `facts_only`; routine ambiguity is marked
rather than asked. Model-authored analysis remains unavailable until a separate
versioned phase/verifier/manifest/content/receipt and policy contract exists.
Text-topic focus resolves once from `FocusRequestV1` to final `FocusV1` in
projection batch zero; later batches cannot change it. Zero eligible/selected or
topic no-match/ambiguity produces typed terminal evidence and no empty summary,
while catalog overflow fails separately without sampling. Stateful objects show
only compatible canonical state; stateless objects omit the field.

Summary output language is resolved and pinned independently from transcript
language. An authorized language choice is an explicit shared same-type refresh:
the old result remains readable, a verified replacement atomically changes only
that type, and failure restores the current revision/language. View-only users
see a read-only language label. It never starts transcript regeneration.

**Exit**: suitable/unsuitable fixtures per profile, per-format non-invention and usefulness evidence.

### 199 — Personal formats and workspace default

**Outcome**: users compose an autosaved format from supported semantic blocks, preview it, version it and choose a default without free-form runtime instructions.

**Guardrails**: custom text is data, not model authority; built-in/personal collections are distinct; built-ins are immutable but duplicable; stable type key across versions; old outcomes remain readable after retirement; keyboard reorder alternative; search/filter/order; one-draft idempotency; autosave/error recovery; duplicate/default/delete/unavailable/retired states.

### 200 — Evaluation and promotion gate

**Outcome**: no prompt/model/schema/validator bundle reaches production without reproducible paired evidence.

**Phases**:

1. dataset governance and frozen splits;
2. failure taxonomy and human gold;
3. calibrated judges with per-class TPR/TNR;
4. paired production/candidate experiments;
5. bundle-level promotion/rollback;
6. shadow/no-replacement period;
7. explicit operator promotion.

The gate freezes owner-controlled dataset, annotation-queue and evaluator
manifests instead of assuming platform immutability. A changed LiteLLM route
mapping/`GatewayRouteBindingV1` or replacement verifier calibration is a new
candidate identity and must pass the same held-out, finalizer and race gates
before root-bundle promotion.

The activation manifest contains executable definitions and preregistered
plans, not measured evidence that would create a root-hash cycle. A separate
immutable `RootQualificationRecordV1` binds the already-created candidate root
to complete profile-clause, five-run task/judge, privacy and approval evidence;
the serialized protected-label move then produces a read-back-bound
`RootPromotionEventV1` and its typed immutable artifact binding. Runtime
last-known-good is root + activation + that complete pass-event binding; a bare
event hash cannot authorize lookup, inference, rendering or publication.

The immutable `VerifierCalibrationManifestV1` embeds the complete
`JudgeStabilityCohortV1`; that cohort is the sole initial activation-quality
authority and initializes freshness. `VerifierDriftEvidenceV1` is forbidden as
activation evidence and exists only for subsequent weekly PASS/breach runs:
five complete distinct runs, per-run raw counts/read-backs and aggregate gates.
Each weekly execution has a sealed pre-call drift plan and five distinct
Langfuse run/result identities over the frozen sentinel; it never reuses one
judge output as five runs or changes the verifier/settings under the same
calibration identity.
Both finalizers lock and snapshot the full freshness head, follow the typed
activation-cohort or weekly-drift binding and enforce the day-8 hard deadline;
missed deadline/outage without PASS or a valid threshold breach expires/revokes
it rather than silently extending trust.

Real meeting content remains excluded until Feature 202 provides the exact
dataset authority/region/access/retention/withdrawal/deletion-invalidation
receipt. Synthetic and individually authorized operator fixtures may establish
the evaluator mechanics earlier.

GEPA is not part of the MVP gate.

### 201 — Version-bound feedback and corrections

**Outcome**: feedback attaches to exact meeting/type/outcome/prompt/model/schema
versions and an explicit result, rendered-section or canonical-claim scope,
without automatically changing production prompts. Feature 201 owns the
version-bound contract and lifecycle for the main visible section chooser and
all three scopes; Feature 196 owns only its placement and presentation.

The Krisp-parity entry is two-stage: `How were the:` offers only sections visible
in the pinned revision and writes nothing; choosing a section reveals its
five-point text-labelled radio group. The authoritative scope union is
`result | section | claim`, and each variant binds the exact immutable target.
Signals: wrong fact, missed item, wrong owner/date, duplicate, too verbose/short,
wrong format, useful. Free text is private content and follows the same boundary
rules.

### 202 — Privacy, security and retention closeout

**Outcome**: approved plaintext-observability policy is implemented truthfully with compensating controls and no accidental expansion.

Scope includes HTTPS/allowlist validation, RBAC/environment separation, prompt
mutation audit, provider-error bounds, abuse budgets, deletion disclosures,
controlled-artifact accounting, prompt revocation and real-meeting dataset
authority/withdrawal invalidation. Constitution-approved retention is not
silently contradicted; changing it requires a separate amendment.

### 203 — Type-pinned share/export

**Outcome**: every outward artifact names exact type, revision, recipient/access policy, scope and lifecycle; policy-gated edit/comment/full-view/notes-only capabilities and invite-only/workspace/team/public-link scopes are explicit; the artifact write is the transactional pin point; high-stakes profile egress carries an exact non-stale review receipt bound to the approved audience, egress purpose, recipient-or-link scope and capability class; no candidate/raw/latest fallback and later regeneration cannot silently change it.

### 204 — Production rollout, SLO and rollback

**Outcome**: staged feature flag rollout with readiness checks, observable SLOs
and tested rollback of code, workflow type and prompt bundle. Internal/shadow
stages may precede 201/205, but general availability of the full Summary
Workspace requires optional version-bound feedback and working inline action
completion/assignee/due controls.

Rollout order: operator/internal dogfood → small cohort → bounded percentage → general availability. Stop conditions include critical factual error, stale publication, data boundary violation, cost/latency regression and elevated invalid-result rate.

Feature 204 re-reads the exact installed Server/SDK/API, partition and Worker
Deployment Version and reruns the full Feature 195 fairness matrix before each
capacity-expanding stage: five equal-weight trials with all 21 keys meeting the
500-start floor, `0.80..1.20` share and simultaneous Wilson bounds, per-key p99
floor and automatic/background 10% lane floors; at least three `0.5/1/2/4`
weighted trials with 10,000 total/500 per-key starts and `0.85..1.15` ratios and
bounds; both Workflow and Activity queues; then the same gates after restart
and the 120-second convergence exclusion. Effective flags and backlog-drain
proof are prerequisites, not substitutes for measured readiness; any failed or
inconclusive row keeps the separate queues/custom scheduler or stops expansion.

### 205 — Canonical mutable action lifecycle

**Outcome**: extracted action evidence becomes one authorized mutable task record without rewriting immutable summary revisions.

**Scope**:

- stable canonical action identity and source/result provenance;
- one mutable ledger for completion, assignee, due date and edit version;
- shared authenticated commands for meeting detail and future global views;
- first positive authenticated `my_actions` read capability over that ledger,
  exposed by Feature 196 only after trusted subject↔participant mapping and
  no-existence-leak tests pass;
- idempotency, expected-version stale-edit conflict recovery and audit;
- RLS/no-existence-leak, deletion/accounting and separation from prompt feedback/training.

**Exit**: one command path passes meeting/workspace authorization, duplicate submission, concurrent edit, reload, deletion and immutable-summary separation tests.

### 206 — Cross-meeting Action Hub

**Outcome**: users follow through on canonical actions across meetings without duplicate extraction or divergent task state.

**Scope**:

- one projection over canonical action records from Feature 205;
- open/completed, assignee, due-date and source-meeting filters;
- inline completion/assignee/due edits shared with meeting detail;
- exact return to meeting/type/evidence;
- truthful unavailable/paywall/permission/empty/loading/error states;
- keyboard, VoiceOver, 390px/200% zoom and no-existence-leak validation.

**Exit**: task edits remain consistent in meeting and global views, no second extraction/model call exists, and access/deletion boundaries pass. This slice is useful but not required to release the core 183–204 summary journey.

### 207 — Cross-meeting continuity summary

**Outcome**: for an authorized recurring series/project, GRAF can show what
closed, carried over, became overdue, changed, appeared or disappeared since a
pinned previous meeting without treating old prose as current truth.

**Scope**: compare current/previous canonical artifacts plus the Feature 205
ledger; stable identity first, reviewed semantic matching second; deterministic
calendar status; separate evidence per meeting; no automatic task mutation;
external `previous_minutes` remains untrusted context. Receipt V1 forbids this
path; the feature must version the resolved-run/content/publication contracts
and bind a strict two-artifact/ledger/policy/timezone/algorithm proof before any
continuity section can publish.

**Exit**: identity, authorization, deletion, changed-decision and action-status
fixtures pass; continuity can be disabled without changing the current meeting
summary. This slice is optional and does not block the core summary release.

### 208 — Subject-scoped generated outcomes

**Outcome**: an explicitly private, viewer-dependent generated result can exist
without changing a shared meeting/type slot or exposing one person's projection
to another viewer.

**Scope**: a distinct subject-scoped request, slot, rendered-content and receipt
version binding authenticated workspace user, trusted participant-mapping
snapshot/hash, access-policy epoch, owner-bound personal template, source and
root bundle. It owns RLS/no-existence-leak, consent/purpose, deletion/accounting,
cache uniqueness, revocation and egress denial by default. Feature 205/196
continues to own zero-inference read-time `my_actions`; Feature 199 rejects all
generated subject-dependent blocks and cannot approximate this feature.

**Exit**: cross-user substitution, mapping change, access loss, deletion,
refresh, duplicate dispatch and private-to-shared egress fixtures pass; no V1
shared-slot receipt or catalog path accepts the subject-scoped payload. This
slice is optional and does not block the core summary release.

### 209 — Editable note-document blocks and comments

**Outcome**: the observed block menu is functional without rewriting immutable
generated truth or turning routine regeneration into candidate review.

**Scope**: a separately versioned document/block projection pinned to exact
`outcome_set_id`; stable block provenance; the complete observed inline toolbar
(bold, italic, underline, strike, alignment, colors, nest/unnest, link and
comment/block actions) plus color/copy/duplicate/comment/delete;
expected-version/idempotent commands; comment permissions; refresh/rebase/reset,
share/export and deletion/accounting boundaries; complete keyboard/VoiceOver
menu and conflict recovery.

**Exit**: every visible menu action has one authoritative result across browser
and embedded macOS, concurrent/offline edits preserve the last-known-good
document, and canonical claims/evidence/receipts remain byte-unchanged.

### 210 — Grounded meeting assistant

**Outcome**: the contextual assistant host answers meeting questions and useful
suggestions with evidence, without hidden inference or mutation of summary truth.

**Scope**: explicit query/session identity; authorized meeting/source/result
context; transcript-as-data boundary; query-focused extraction/synthesis/
verification; evidence links; LiteLLM/Langfuse/Temporal/receipt ownership;
reload/ambiguous/cancel/error behavior; privacy, deletion and evaluation.

**Exit**: every answer reconstructs its exact subject/source/root/calls and
evidence, unsupported questions fail honestly, and no assistant path changes a
summary slot, transcript, action ledger or prompt label.

### 211 — Transcript correction revisions

**Outcome**: the observed transcript edit/delete affordances create auditable
source revisions and safely refresh dependent summaries instead of mutating
accepted source in place.

**Scope**: text/speaker/segment-exclusion commands; immutable transcript and
canonical-source revisions; expected-version/idempotency/audit/undo; participant
mapping and RLS; source-pointer CAS; Feature 197 stale/fan-out integration;
browser/embedded accessibility and deletion/accounting.

**Exit**: correction, conflict, undo, access loss and concurrent regeneration
fixtures prove one authoritative source, no lost edit and no unsaved/retired
summary generation.

## Cross-program Definition of Done

- 100% schema validity and existing source refs.
- Zero unsupported canonical claims, critical omissions, transcript-instruction
  compliance, stale publication and loss of last-known-good in challenge sets.
- Verified Useful Summary Rate target initially ≥85% and Supported Outcome
  Recall ≥90% under preregistered denominators/one-sided 95% confidence bounds.
  Promotion challenge sets require zero critical regression with the sample
  floors in `quality-and-evaluation.md`; Critical Error-Free Rate ≥99% is the
  post-launch operational SLO, not a relaxed promotion threshold.
- All types meet per-format non-inferiority against production.
- Saved type switch performs no inference.
- Share/export pins exact revision.
- Browser and embedded routes pass keyboard/VoiceOver/zoom/reflow.
- Browser and embedded routes preserve per-meeting view/type and evidence-return context identically.
- Real `gpt-5.6-luna` LiteLLM/Langfuse/Temporal path is exercised; no artificial 4048/4096 output cap.
- Every production bundle has one exact root selection version, rollback root,
  explicit operator approval and composed expected-root read/compare + protected
  label move + read-back under one authorized writer/lock; runtime stays on
  last-known-good after mismatch.

## Explicitly deferred

- GEPA operator-only research until Feature 200 is mature.
- JEPA.
- DSPy or another runtime/evaluation stack.
- Mandatory user approval of ordinary summaries.
- User-visible revision history/undo; internal immutable history is sufficient for this program, and any later user feature requires a separate product decision.
- Extracted Krisp assets/source/binaries/private APIs/protocols/private content
  or unlicensed third-party material. Literal observable UX/UI/IA parity is
  authorized and owned by Feature 196.
- Cross-meeting Action Hub is Feature 206 and does not block the first trustworthy
  summary release. Feature 205 canonical action commands and Feature 201 optional
  feedback are required before full public Krisp-parity Summary Workspace GA, but
  not before internal/shadow prompt calibration.
- Cross-meeting continuity summary is Feature 207 and does not block the first
  trustworthy summary release.
- Generated subject-scoped outcomes are Feature 208 and do not block the first
  trustworthy summary release; read-time `my_actions` remains Feature 205/196.
- Editable note documents, grounded assistant and transcript corrections are
  Features 209–211. They are required for full observed meeting-detail parity,
  but do not block the first trustworthy generated-summary rollout.
