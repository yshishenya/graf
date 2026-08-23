# Planning Completion Audit — provisional until clean independent rerun

## Scope

This receipt is the planning closeout candidate for the GRAF
meeting-intelligence program and Feature 183. It does not close the gate until
the independent prompt and Spec Kit reruns are clean, and it never authorizes
implementation, provider calls, issue sync, commit, PR, prompt promotion,
release or deployment.

## Objective coverage

| Requested outcome | Planning authority/evidence |
|---|---|
| No routine user accept/reject decision | `spec.md`, `user-journey.md`, `contracts/lifecycle.md`, `contracts/api.md` |
| One current result per meeting/type; saved switching without inference | `spec.md` FR-001–FR-004, `data-model.md`, `tasks.md` US2 |
| Same-type refresh safely replaces only that type | `spec.md` US3/FR-007–FR-012, slot CAS contract, US3/US4 tasks |
| Old result survives waiting, failure, stale source and races; transcript source replacement stales every active saved old-source type without generating unsaved/retired types | `spec.md` FR-008/FR-021/SC-003/SC-009, `data-model.md`, `quickstart.md`, Feature 197 backlog |
| Internal immutable history without primary history UI | `spec.md` FR-009, `plan.md`, `contracts/lifecycle.md` |
| Orthogonal result/generation/source/catalog states, including transcript failure, source-empty, no-supported-content, ambiguous and retired | `spec.md` FR-024, `user-journey.md`, `contracts/api.md`, `data-model.md` |
| UX/UI/IA/CX decomposition with authorized literal observable KRISP parity | `krisp-parity-matrix.md`, `user-journey.md`, Constitution 5.0.0 and Features 196/199 in `program-backlog.md` |
| Krisp-faithful split Notes/type/Transcript controls plus exact-revision actions | `krisp-parity-matrix.md` §Executable top-control contract and `user-journey.md`; Feature 196 owns the stable ready-only Refresh slot immediately left of exact-revision Copy, the transcript-language `RU`/explicit-Regenerate surface, deterministic reformat banner and always-positioned disabled Share host, while Feature 203 owns the Share action/dialog/lifecycle |
| Executable player/transcript parity | `krisp-parity-matrix.md` `PX-01`–`PX-11` cover play/pause, seek/scrub, speed, speaker lanes/filter, preparing/unavailable/error, complete ready-player control inventory, keyboard/VoiceOver, focus restore and browser/embedded acceptance; static screenshots are explicitly not interaction proof |
| Closed observed-control inventory | `krisp-parity-matrix.md` maps every control/state visible in `KRP-183-01`–`14`, the 15-frame repeat walkthrough and current `KRP-183-C01`–`C11` challenge set to owner, behavior, accessibility acceptance and a concrete disposition. It includes Auto section mapping/empty omission, two-stage section feedback, reformat banner, assistant host, inline toolbar/block handle, transcript-row controls and five player rates; Features 209–211 prevent inert parity controls |
| Reproducible installed-reference evidence | Krisp 3.15.6 bundle/version/executable and `app.asar` integrity hashes/method in `krisp-parity-matrix.md`; exactly 14 counted JPEG images map to `KRP-183-01`–`14`, a separate 15-frame repeat walkthrough remains independent, and 11 current PNG frames map one-to-one to `KRP-183-C01`–`C11` by SHA-256. All remain private outside git; no 24-screen evidence set or claim exists |
| List/search entry, per-meeting persistence and complete loading/failure states | `krisp-parity-matrix.md`, `user-journey.md`, Feature 196 backlog |
| Template catalog/default/duplicate/delete and archived-result lifecycle | `krisp-parity-matrix.md`, Feature 183 retired-result contract, Feature 199 backlog |
| Independent capture/summary/open/title/recap settings | `user-journey.md`, Features 197 and 203 in `program-backlog.md` |
| Action completion/assignee/due and global follow-through | Feature 205 canonical mutable action ledger/commands and Feature 196 inline UI are full-public-Workspace prerequisites; Feature 206 Action Hub remains optional |
| Current GRAF UX evidence | Synthetic-only browser screenshots and findings recorded in `krisp-parity-matrix.md`; screenshots remain local outside git |
| Canonical prompt/intelligence chain | `research.md`, strict extraction/resolve/semantic+omission verification/projection/presentation-synthesis/presentation-verification/layout contracts in `prompt-pipeline.md`, Features 194/195/198; the full composite profile body/hash and clause closure are identical across all three type-phase requests, content and receipt, with no per-profile prompt authority |
| Topic focus and zero-content truth | `FocusRequestV1 → FocusV1` batch-zero contract, conditional item `state`, `CriticalityPolicyV1` profile expansion and `AttemptTerminalEvidenceV1` are synchronized across `prompt-pipeline.md`, `contracts/receipts.md`, `quickstart.md`, checklists and Features 195/198 |
| Receipt V1 truth boundary | `facts_only` only; `hypothesis` remains distinct; `contracts/receipts.md` is the normative design contract. Feature 183 intentionally ships no receipt-vector artifact; Feature 195 must create schema-valid P1–P4/full-matrix conformance vectors from scratch before any positive model publication claim |
| Per-type purpose, structure, exclusions and forbidden inferences | `summary-profile-catalog.md` embeds one exact hash-bound `SectionContractV1.semantic_rule` per section, plus closed profile/Auto/composition bodies. Auto v3 hash `b37da94d…72c9` and mapping hash `8e6e9844…5640` enforce `action → Action Items`, everything else → Key Points, omit either empty section and publish nothing when both are empty. Feature 198 backlog and Feature 200 plan/evidence matrices prove each rule |
| Prompt-source recheck and transfer/reject rationale | Codex task `01a02b3a-b966-7083-b339-709862f4346f`, `research.md` Decision 9 and `prompt-pipeline.md` |
| LiteLLM, Langfuse and Temporal runtime | `temporal-langfuse.md`, Feature 195 |
| Route and calibration identity | `GatewayRouteBindingV1`, verified numeric last-known-good bundle/no SDK fallback, exact evaluator identity and replacement-calibration finalizer/race gates in `prompt-pipeline.md`, `temporal-langfuse.md`, `quality-and-evaluation.md`, receipt contract and Features 195/200 |
| Quality, stability, judges and promotion | `quality-and-evaluation.md`, Feature 200; non-cyclic `RootQualificationRecordV1` binds measured candidate evidence and `RootPromotionEventV1` binds protected-label read-back. Calibration freshness requires a sealed weekly plan plus five distinct Langfuse evaluator runs over the frozen sentinel every seven days, with atomic PASS refresh and day-8 fail-closed expiry/revocation. The complete typed authority is propagated and rehashed; runtime never trusts a bare digest or reused judge output |
| GEPA/JEPA decision | GEPA deferred until evaluator maturity; JEPA excluded in `research.md` and `program-backlog.md` |
| Privacy, deletion, egress and retention boundaries | constitution check, `data-model.md`, `contracts/`, security/privacy checklist, Features 202–203 |
| Share permission/scope matrix and refresh-race transactional pin | `contracts/lifecycle.md`, `contracts/api.md`, Feature 203 backlog |
| Feature 183 executable order and downstream program decomposition | 48-task `tasks.md`; `program-roadmap.md` and `program-backlog.md` define 169 unique `F###-##` planning IDs across Features 194–211, each still requiring its own Spec Kit package before implementation. Raw textual occurrences may be higher where a normative clarification or ownership cross-reference repeats an ID; uniqueness is the authoritative count |

## Final product decision

```text
meeting + summary type
→ zero or one current published revision
→ saved type opens immediately with no inference
→ missing type creates one idempotent ensure attempt
→ same-type refresh keeps current content visible
→ verified replacement atomically moves only that slot
→ failure leaves every current result unchanged
→ prior revisions remain internal and immutable
```

Result presence, generation attempt, source readiness/freshness and catalog availability are separate. A current result may therefore be `updating` or `error` without disappearing, may be `ready + stale` while new egress is blocked, or may remain `ready + retired` while future generation/default selection is disabled.

## Architecture stop rule

Feature 183 adds one pointer table only. It reuses `MeetingOutcomeSet`, `MeetingOutcomeItem`, `MeetingOutcomeGenerationAttempt`, `GenerationCall`, `DispatchIntent`, source/deletion fences and existing egress records. It does not create a second outcomes ledger, content table, request ledger or user revision-history subsystem.

## Cross-feature ownership

- 183: slot/CAS publication truth and default-type compatibility.
- 194: canonical evidence-backed intelligence and deterministic validators.
- 195: durable production-equivalent runtime, calibration-registry
  schema/storage/exact lookup/finalizers and ambiguity/retry semantics.
- 196: meeting-detail Summary Workspace UX/IA/accessibility, including only the
  placement/capability host for Share.
- 197: automatic first result and bounded recovery.
- 198–199: built-in and personal type profiles/defaults.
- 200: human-grounded manifest creation, evaluation, qualification/promotion
  eligibility, production activation/revocation and serialized manual promotion.
- 201: version-bound optional feedback for the main visible section chooser and
  the result/section/claim scopes; Feature 196 owns placement/composition, while
  Feature 201 owns the contract, persistence, lifecycle and all main-section
  feedback behavior. It is required as a capability before full public
  Workspace GA but never required from a user to consume normal results.
- 202: privacy/security/retention/abuse closeout.
- 203: the only owner of arbitrary selected-type Share/export action, dialog,
  commands, lifecycle and contracts.
- 204: staged rollout, SLO and rollback; full public Workspace requires 201/205.
- 205: canonical mutable action ledger and shared command path; required before Feature 196 ships editable tasks and before full public Workspace GA.
- 206: cross-meeting canonical Action Hub; useful follow-through slice, not a blocker for the core summary rollout.
- 207: optional pinned cross-meeting continuity summary; not a blocker for the
  core summary rollout.
- 208: separately consented subject-scoped generated outcomes with their own
  authenticated-subject slot/receipt/privacy/calibration boundary; never a
  shared Feature 183 slot or the zero-inference Feature 205/196 `my_actions`
  filter, and not a blocker for the core shared-summary rollout.
- 209: human-editable note-document blocks/comments, preserving immutable
  generated result truth.
- 210: grounded meeting assistant with explicit query, evidence and independent
  call/receipt lifecycle.
- 211: non-destructive transcript correction revisions and safe dependent-summary
  stale/regeneration behavior.

## Planning validation evidence

- Spec Kit prerequisite check resolved the Feature 183 directory and tasks.
- Requirements inventory: 26 FR, 5 NFR and 12 SC.
- Task inventory: 48 sequential Feature 183 task IDs; every task has an exact
  path; every story/FR/NFR/SC has explicit task coverage. Program backlog: 169
  unique planning IDs across Features 194–211; repeated explanatory references
  do not create additional planning items.
- Local Markdown links, placeholder scans and `git diff --check` must be rerun
  after the current amendments; no earlier clean statement is treated as current
  evidence. One historical generated-installer link outside this feature may
  remain unrelated and must be reported separately if the repository-wide scan
  still finds it.
- Manual Spec Kit analysis and focused independent reviews cover UX/IA/CX,
  architecture, prompt/runtime contracts, Temporal/Langfuse, deletion/security,
  egress and requirement coverage. This receipt remains provisional until the
  final two independent reruns both report `CRITICAL 0 · HIGH 0 · MEDIUM 0`.
- The available installed-app bundle contains exactly 14 static images. The
  opaque manifest in `krisp-parity-matrix.md` records only generic surfaces:
  `KRP-183-03` shows the selector, `KRP-183-07` visible evidence timestamps and
  the persistent Share header position, `KRP-183-09` the transcript-language
  popover with explicit Regenerate/up-to-30-minute impact and ready player, and
  `KRP-183-10`/`11` the visible Share scope/permission menus. `KRP-183-12`–`14`
  cover filter, sort and recent-search controls. No image proves keyboard,
  focus trap/restore, VoiceOver, async behavior or uncaptured result/error
  states; those remain executable acceptance. Private record titles/content
  remain only in the outside-git files and are not reproduced in this package.
- A second outside-git repeat walkthrough contains 15 frames numbered
  `00`–`14`. It was used to revisit multiple records and challenge the same
  visible flow, but it is intentionally not merged into or renumbered as the
  normative `KRP-183-01`–`14` manifest. Its additional note-block menu,
  transcript-row edit/delete affordances, assistant host and exact five-rate
  player menu are assigned to Features 209–211 or Feature 196 rather than being
  silently omitted. It contributes no private title/content, hidden-prompt claim
  or additional release evidence by itself.
- A third current-state outside-git challenge set contains exactly 11 PNG frames,
  `KRP-183-C01`–`C11`, each bound by SHA-256 in the parity matrix. It captures
  the Auto `Action Items → Key Points` shell, one observed omission of an empty
  Action Items section, the inconsistent empty Key Points reference defect,
  two-stage section feedback, persistent reformat banner, three assistant-host
  labels, current transcript/player states and the inline toolbar/block handle.
  The frame set does not prove the universal empty-section rule or any unseen
  combination; those are executable acceptance requirements. Findings are now
  assigned to explicit product owners and contracts, and the frames remain
  private without proving keyboard, VoiceOver or async behavior.
- The latest pre-remediation audits found missing `hypothesis` ontology coverage,
  strict presentation call schemas, a legal V1 analysis path, runtime/roadmap
  drift, FR-026/SC-012 coverage, executable top-control states, language
  semantics and full-public feedback/action prerequisites. Those findings were
  incorporated; only the fresh reruns may close them.
- The most recent compiler/profile audit additionally found that opaque section
  names, undefined Auto-row/composition bodies, profile-key-only type requests
  and measured evidence embedded into its own candidate root could not prove
  executable semantics. The package now defines exact section/Auto/composition
  bodies, complete projection/synthesis/verification requests and external
  root-bound qualification/promotion records. Fresh reruns, not this statement,
  must close those findings.
- Current GRAF browser audit used only synthetic fixtures. Installed Krisp black-box research used private records only in the local outside-git evidence directory; no private transcript/output or screenshot was added to git.
- The complete Feature 183 implementation matrix has not been run because 43
  of 48 implementation tasks remain open. The current partial branch was
  nevertheless rechecked independently: the valid focused PostgreSQL helper
  and the fast repository gate results are recorded in the fresh recheck
  section below.
- The 2026-08-23 final prompt and Spec Kit reviewers initially returned NO-GO
  (`0/9/3/0` and `0/3/6/2` by CRITICAL/HIGH/MEDIUM/LOW). The documents were
  amended for mandatory semantic/omission gates, typed canonical relations,
  canonical-parent lifecycle, one atomic Langfuse root bundle, immutable
  outcome-attempt provenance, statistical/privacy gates, high-stakes review,
  null-slot scope integrity, mandatory presentation synthesis/verification,
  deterministic layout rendering and the remaining UX/WCAG inconsistencies.
  This receipt remains provisional until both reviewers rerun against the final
  synchronized package.
- The final official Langfuse documentation recheck covered prompt data/config,
  version/label/cache/fallback behavior, composability, datasets and timestamp
  versions, experiment data/run semantics, annotation queues, v4 observation
  data and tracing best practices. It exposed mutable queue membership,
  same-name evaluator rule movement, one-item-per-run repetition and conflicting
  dataset latest/versioned wording; the owner-controlled queue/evaluator/dataset
  manifests, stable observation names, numeric last-known-good-only runtime and
  read-back gates now make those platform behaviors explicit.

## Fresh source and validation recheck — 2026-08-24

- `git fetch origin master` resolved `origin/master` to `65d46da9`
  (`v2026.08.24.5`). Feature 183 is based directly on that commit; `HEAD` is
  `90fe2b6c`, and the branch contains five Feature 183 commits after master.
  The active worktree is the separate
  `183-trusted-outcome-lifecycle` worktree; the older
  `181-meeting-summary-experience` worktree is not an evidence source for this
  feature.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks
  --include-tasks` resolved `specs/183-trusted-outcome-lifecycle` and the
  required task/supporting documents.
- The valid focused PostgreSQL helper run passed **64 tests**. A direct pytest
  invocation without the helper is not valid evidence: it passed the
  environment-independent tests but produced setup errors because
  `TWOBRAIN_DATABASE_URL` was intentionally absent.
- `infra/scripts/ci-local.sh --fast` passed **1223 tests**. `git diff --check`
  passed. These are current-branch regression signals, not proof that all 48
  Feature 183 tasks are implemented.
- The fresh runtime recheck found and fixed the previously recorded artificial
  output caps: outcome/judge prompt configs no longer contain
  `max_completion_tokens`, `PromptSnapshot.litellm_request()` does not send it,
  Langfuse seed/observation metadata does not advertise it, and the optimizer
  uses only its database-backed run budget for reservation accounting. The
  focused prompt/gateway tests passed **20/21**; the remaining failure is the
  environment's missing `langfuse.api.prompts` v4 SDK module, not an assertion
  failure in the changed behavior.

## Current implementation blockers

The current code is intentionally not represented as a completed Feature 183
or production-ready prompt runtime:

- The artificial `4096/2048` caps are removed in the active working tree, but
  the changed runtime has not yet been promoted or exercised through a real
  `gpt-5.6-luna` LiteLLM/Langfuse/Temporal run. The missing v4 Langfuse SDK
  module must be resolved in the authoritative project environment before that
  contract test can be green.
- Legacy meeting-global pointer and newest-row owners remain in the current
  runtime, including cabinet API/egress/query/browser paths and the operational
  reconciliation script. T035/T036/T043 still own the verifier, closed
  allowlist and final cutover; no strict slot-only completion claim is valid
  until those tasks pass.
- No real LiteLLM, Langfuse or Temporal generation/evaluation was executed in
  this recheck. No prompt was promoted and no production state was changed.
- The current-source link recheck returned HTTP 200 for the cited OpenAI,
  Langfuse, Temporal, MeetingBank, QMSum and GitHub sources after updating the
  Temporal Worker Versioning URL to its current production-deployment path.
  The Krisp Help URL remains access-restricted (HTTP 403); installed-app
  black-box evidence remains the authoritative reference for the observable
  UX claims and no Help-page claim is treated as verified.
- The installed Krisp metadata recheck still found version `3.15.6` and the
  recorded executable hash, but its current stable `app.asar` hash is
  `d247c922e78ea432779aedc7d1e7378281f08aeec9452a37191cf9a3e24f3ec0`, while
  the 2026-08-23 frame set was captured from the historical hash recorded in
  `krisp-parity-matrix.md`. This does not invalidate the frame manifest, but a
  future visual re-audit must bind new screenshots to the current package hash;
  this metadata-only pass adds no new interaction claim.
- A current read-only accessibility/screenshot spot-check of one authenticated
  meeting-detail view was captured outside git and inspected. It confirms the
  visible Notes/Transcript, Copy, RU, Share, Connect, reformat, timestamp,
  feedback and assistant surfaces, but intentionally does not prove keyboard,
  async, mutation or second-record behavior.

## Independent follow-up contract audit — 2026-08-24

The follow-up was run against `HEAD=90fe2b6c`, not the older subagent snapshot.
The following findings were confirmed and corrected in the planning package:

- `AutoSelectionPolicyV1` now records the recomputed digest
  `99ca480ffa81e6085037a822bb29cc3a3c6533b9d57f1729fa6a87e4c94bdcb5`; the
  canonical JSON body is 20,087 UTF-8 bytes and the profile-catalog digest and
  all embedded profile/row digests independently recompute successfully.
- Model request/result hashes now have one `GenerationCall` authority and one
  phase-separated `GRAF-GENERATION-CALL` formula; the stale parallel
  `GRAF-MODEL-*` family was removed from the pipeline wording.
- Model execution authority is now an explicit production/candidate union:
  production re-fetches a complete promoted-root/promotion-event binding,
  candidate evaluation re-fetches its complete evaluation authority and does
  not require a future promotion event.
- `RendererInputV1` now carries the complete immutable promotion-event binding,
  not a bare digest. The canonical kind/state matrix is required for every
  renderer/content type; only the Auto mapping/profile bodies remain
  conditional.
- Auto resolver cardinality now explicitly requires the policy's complete
  `all_policy_rows` assessment set while ranking only the compatible subset.
- Summary state updates now have a monotonic per-meeting/type `state_version`,
  opaque `event_id`, ETag/304 behavior and gap-triggered same-type refetch;
  Temporal transcript delivery now has a closed chunk manifest, descriptor
  hashes and complete reassembly/ordering/size checks.

The consistency pass also confirms 26 FR, 5 NFR, 12 SC and 48 task IDs with all
requirements mentioned by tasks; no unresolved placeholder markers were found.
These are documentation/contract corrections only. No runtime path, provider
call, Langfuse object, Temporal workflow or production state was changed.

The planned `validation/focused.md`, `validation/regression.md`,
`validation/privacy.md` and `validation/closeout.md` artifacts remain absent
until their implementation-owned tasks run. Creating them now from the
current regression signals would falsely imply that T041–T045 and T043 are
complete.

## Gates before implementation or release

- Feature 182 is a planning base/prerequisite, not merged/released evidence.
- Implementation requires explicit approval, then issue sync and the Feature 183 task sequence.
- Feature 183 is independently testable but not independently releasable; production rollout remains blocked by the program gates in `program-roadmap.md`.
- Constitution 5.0.0 authorizes literal observable KRISP UX/UI/IA parity for
  Feature 196. Independent code, accessibility, privacy/security truth and
  third-party asset, logo and trademark rights remain release gates; approved
  functional UI labels and interaction microcopy may match literally.
