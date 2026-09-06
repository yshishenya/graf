# Requirements Checklist: summary experience and KRISP parity

**Purpose**: Review the completeness of later UX/IA/CX requirements without testing an implementation

**Created**: 2026-08-23

## User effort and flow

- [x] CHK001 Is the removal of mandatory accept/reject consistent across spec, lifecycle contract and roadmap? [Consistency, Spec §Clarifications; Contract lifecycle §Product terminology]
- [x] CHK002 Are result, generation, source and catalog states specified independently for ready, missing, updating, blocked, deferred, ambiguous, failed, stale, empty, transcript-failed, retired, dependency-outage and access-lost cases? [Coverage, KRISP Matrix §Interaction states]
- [x] CHK003 Is the distinction between first generation of a missing type and refresh of an existing type explicit? [Clarity, Spec §User Stories 2–3]
- [x] CHK004 Is it prohibited to show one type's content under another type's selected label? [Clarity, Spec §US2 scenario 2]
- [x] CHK005 Are saved-type switch, generate-missing and update-current separate user intentions? [Consistency, KRISP Matrix §Target IA]
- [x] CHK016 Does a failed missing-type generation restore the prior ready type automatically only when that request still owns the latest presentation-intent version, while a newer selection/navigation remains untouched and no revision changes? [Recovery, User Journey §4]
- [x] CHK017 Are loading thresholds, duplicate-click coalescing, navigation-away semantics and truthful cancellation defined? [Timing, KRISP Matrix §Interaction timing]

## Information architecture

- [x] CHK006 Are meeting detail, type catalog, type details and personal-format management assigned clear locations? [Completeness, KRISP Matrix §Target IA]
- [x] CHK007 Are type selection and share/export semantics tied to exact saved result rather than generation attempts? [Consistency, Spec §FR-003 and FR-016]
- [x] CHK008 Is evidence access secondary but available from every critical claim? [Coverage, Program Roadmap §196]
- [x] CHK009 Is player/transcript parity executable for play/pause, seek/scrub,
  speed, speaker lanes/filter, preparing/unavailable/error, keyboard/VoiceOver and
  focus restoration in both browser and embedded macOS, in addition to result
  reading and source jumps? [Coverage, KRISP Matrix]
- [x] CHK018 Are meeting list, Later, filter, sort, recent search, result/no-result and access-safe entry states part of the journey? [Coverage, KRISP Matrix §Target IA]
- [x] CHK019 Is last successful type and AI Notes/Transcript view persistence scoped per user+meeting rather than meeting-global or device-global? [Clarity, KRISP Matrix §Route matrix]
- [x] CHK020 Are browser and embedded macOS route/persistence/evidence-return behaviors required to match? [Consistency, KRISP Matrix §Route matrix]
- [x] CHK021 Are custom-format autosave, one-draft idempotency, search/filter/order, unavailable, duplicate/default/delete and recovery states complete? [Coverage, User Journey §7]
- [x] CHK022 Are action completion, assignee, due-date editing and reload/global-view consistency specified? [Coverage, User Journey §5a and §9]
- [x] CHK023 Does every share flow expose exact type, recipient/access policy and stable artifact behavior before egress? [Clarity, User Journey §6]

## Accessibility and responsive behavior

- [x] CHK010 Are keyboard semantics and focus return specified for tabs, picker and catalog? [Completeness, KRISP Matrix §Accessibility]
- [x] CHK011 Are async announcements separated from actions and forbidden from stealing focus/scroll? [Clarity, KRISP Matrix §Accessibility]
- [x] CHK012 Are 390px, 200% zoom, reduced motion and non-color status requirements explicit? [Measurability, KRISP Matrix §Accessibility]
- [x] CHK024 Are icon-only controls, emoji feedback labels, shortcut conflicts and keyboard alternatives called out for implementation-level verification, and does a closed opaque inventory assign every observed search/header/navigation/overflow/integration/contextual control an owner, states, accessibility contract and reproduce/deviate/out-of-scope disposition? [Accessibility, KRISP audit evidence]

## Reference fidelity and provenance

- [x] CHK013 Is literal observable Krisp UX/UI/IA parity explicitly authorized while independent implementation and asset-rights boundaries remain clear? [Consistency, Constitution §VII; KRISP Matrix §Boundary]
- [x] CHK014 Is Constitution 5.0.0 recorded as the resolved authority for Feature 196? [Authority, KRISP Matrix §Governance decision resolved]
- [x] CHK015 Are private screenshots excluded from git/shipping assets while remaining usable as local implementation references? [Boundary, Research §Method]
- [x] CHK025 Is reference fidelity measurable across navigation, selector, component geometry, player, tokens, typography, icons, copy and interaction timing, with every deviation documented? [Measurability, KRISP Matrix §Reference-fidelity acceptance]
- [x] CHK026 Does the installed-reference evidence record exact bundle/version/hash/method and only the actually available opaque screenshot count/coverage, without overstating a larger audit or placing private content in git? [Reproducibility, KRISP Matrix §Reference metadata]
- [x] CHK049 Is every reference-derived visible element assigned exactly one closed `not_applicable|cleared|replacement_required|blocked` rights state, with the latter two blocked from release? [Rights, KRISP Matrix §Reference-fidelity acceptance]
- [x] CHK027 Can background success/failure never overwrite visible or remembered context after a newer selection/navigation? [Concurrency, User Journey §4]
- [x] CHK028 Do duplicate-title search results carry enough stable context to open the exact canonical meeting and fail closed after access loss? [Identity, User Journey §0]
- [x] CHK029 Does share/export define pending, ambiguous, success, failure, navigation-away, idempotent retry and duplicate-prevention behavior? [Lifecycle, User Journey §6]
- [x] CHK030 Are action edits and the complete share lifecycle required to match across browser and embedded macOS? [Parity, KRISP Matrix §Route matrix]
- [x] CHK031 Is one feature the explicit owner of mutable action state, authorization, idempotency, stale-edit conflicts, deletion and immutable-summary separation? [Ownership, Program Roadmap §205]
- [x] CHK032 Are exact meeting-list filters, within/between-facet logic, sort direction/tie-break and duplicate-title search identity specified? [IA, User Journey §0]
- [x] CHK033 Are reload/close during preparation and refresh-during-evidence return behaviors deterministic without duplicate work or surprise navigation? [Recovery, User Journey §4–5]
- [x] CHK034 Is the single observed `RU` affordance always identified as
  transcript-language regeneration with explicit `Regenerate` and an up-to-30-
  minute impact warning, while any later notes output-language control is kept
  outside that reference strip? [Clarity, KRISP Matrix §Transcript language]
- [x] CHK035 Are built-in/personal template actions, archived-result behavior and default lifecycle explicit? [Lifecycle, User Journey §7]
- [x] CHK036 Are auto-capture, auto-summary, open-after-meeting, auto-title, recap audience and link permission independently owned settings? [Control, Program Roadmap §196–203]
- [x] CHK037 Are WCAG 2.2 AA, keyboard model, contrast, target-size, focus and live-region requirements measurable? [Accessibility, KRISP Matrix §Accessibility]
- [x] CHK038 Are share permission capabilities and link scopes explicit and policy-gated with invite-only fail-closed behavior? [Egress UX, User Journey §6]
- [x] CHK039 Is the Krisp-faithful top strip executable as separate Notes tab,
  adjacent type-menu button and Transcript tab with independent focus targets,
  complete keyboard semantics and no type/content mismatch? [Interaction, KRISP
  Matrix §Executable top-control contract]
- [x] CHK040 Do Feature 196's exact-revision Copy and transcript-language `RU`
  action define their complete state matrix, while Share always occupies its
  accessible-meeting header position disabled until Feature 203/policy enables
  it and Feature 203 exclusively owns invocation/dialog/lifecycle? [Ownership and
  state coverage, KRISP Matrix §Executable top-control contract]
- [x] CHK041 Does successful transcript-language regeneration mark every active
  saved old-source type stale, preserve its prior readable result, block new
  egress and hand Feature 197 one coalesced replacement intent per active saved
  available type without generating unsaved/retired types? [Trust, User Journey
  §Source changed]
- [x] CHK042 Are optional version-bound feedback and Feature 205 inline action
  controls prerequisites for full public Summary Workspace GA while remaining
  independent from initial prompt calibration and without forcing user review?
  [Rollout, Program Roadmap §Dependency graph]
- [x] CHK043 Does the ready/missing × blocked/deferred/ambiguous/
  no-supported-content action matrix state exactly when Switch, Copy,
  ready-only Refresh, Share, safe retry, wait and Open transcript are available;
  place ready Refresh immediately left of Copy with a stable busy/disabled slot,
  omit it for missing types whose recovery belongs in the status panel, and prove
  missing-type selection itself owns one ensure and no second `Generate`
  confirmation, without hiding an old ready result or offering ambiguous retry?
  [Recovery, KRISP Matrix §Executable top-control contract]
- [x] CHK047 Does a selected `no_supported_content` type stay selected with its
  own empty state (or explicitly selected Transcript/player recovery), while all
  other ready types remain switch targets rather than substituted primary
  content? [Type/content integrity, KRISP Matrix §Interaction states]
- [x] CHK044 Does feedback first offer only sections visible in the exact pinned
  revision without writing, then create/update/remove one result+section-scoped
  five-point record, while pending/error/offline/conflict/removing recovery
  preserves the authoritative prior value, scope and focus?
  [Feedback UX, Quality and Evaluation §User feedback; Feature 201]
- [x] CHK045 Does the Share dialog define accessible title/description,
  initial/logical/trapped/restored focus, Escape/close behavior, grouped
  permission/scope semantics, disabled reasons, status/error association,
  target size and 390px/200% reflow across browser and embedded macOS?
  [Egress accessibility, Program Backlog F203-10]
- [x] CHK046 Do inline completion/assignee/due controls provide keyboard-only
  editing, text labels and state, visible focus, busy/disabled semantics,
  optimistic/error/conflict announcements, focus preservation and idempotent
  recovery without mutating the immutable summary revision? [Action
  accessibility, Program Backlog F205-07]
- [x] CHK048 Does a topic-focus no-match/ambiguity/catalog-overflow keep the
  requested type and typed focus visible, avoid silently showing another type or
  `all_material`, map to public `next_action=open_transcript`, keep an authorized
  focus editor as a normal control/new request identity, and never serialize
  internal `change_focus`/`wait_for_source_change`? [Focus recovery, Prompt Pipeline
  §Zero-content terminal path; KRISP Matrix §Interaction states]
- [x] CHK050 Does the repeat walkthrough's note-block menu have an explicit
  Feature 209 owner for color/copy/duplicate/comment/delete, with no inert menu
  and no mutation of immutable generated claims, evidence or receipts?
  [Repeat reference coverage, KRISP Matrix §Observed-control inventory]
- [x] CHK051 Is the contextual assistant host assigned to Feature 210 with one
  explicit grounded query intent, evidence, complete runtime/receipt ownership
  and no hidden inference or product-state mutation? [Repeat reference coverage]
- [x] CHK052 Are transcript-row edit/delete controls assigned to Feature 211 and
  does the observed speed menu freeze the five visible rates, while correction
  creates a source revision and deterministic stale/fan-out rather than in-place
  mutation? [Repeat reference coverage, KRISP Matrix `PX-04`]
- [x] CHK053 Does Auto map each selected action only to `Action Items` and every
  other selected outcome only to `Key Points`, omit either empty section, and use
  `no_supported_content` with no publication when both are empty? [Current-state
  challenge set, Auto profile v3]
- [x] CHK054 Is the reformat banner mandatory only for ready Auto + available
  unsaved Meeting Minutes target version, inference-free on paint, dismissed for
  exact user+meeting+target-version and activated by one ensure+selection intent?
  [KRISP Matrix §Executable top-control contract]
- [x] CHK055 Does the evidence boundary enumerate all three private sets—14-image
  baseline, 15-frame repeat and SHA-bound `KRP-183-C01`–`C11` current challenge—
  without merging their counts or treating screenshots as keyboard/async proof?
  [KRISP Matrix §Reproducible reference metadata]
