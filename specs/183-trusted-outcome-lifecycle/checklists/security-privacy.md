# Requirements Checklist: security, privacy and deletion

**Purpose**: Review trust-boundary and lifecycle-accounting requirement quality

**Created**: 2026-08-23

## Scope and authority

- [x] CHK001 Are workspace, meeting, type and revision bindings required together for every pointer transition? [Completeness, Spec §FR-014; Data Model §Constraints]
- [x] CHK002 Are authorization, RLS, CSRF and audit boundaries preserved explicitly? [Consistency, Spec §FR-018]
- [x] CHK003 Are shared-recipient generation/refresh permissions intentionally deferred to explicit policy rather than implied? [Boundary, Contract API §Ensure/refresh]

## Deletion and retained data

- [x] CHK004 Are new slot pointers included in meeting lifecycle accounting and purge scope? [Coverage, Plan §Constitution Check]
- [x] CHK005 Are deletion-state and deletion-epoch publication fences both specified? [Completeness, Contract lifecycle §Publication gates]
- [x] CHK006 Are GRAF-controlled deletion requirements consistent with the constitution-approved Langfuse/Temporal/Generation Call retention exception? [Consistency, Program Roadmap §202]
- [x] CHK007 Is it clear that changing plaintext observability retention requires a constitution decision rather than a lower-level task? [Authority, Program Roadmap §202]

## Egress and disclosure

- [x] CHK008 Are Feature 183 share/export requirements pinned to the documented default type and exact revision, with arbitrary-type egress assigned to Feature 203? [Clarity, Spec §FR-016]
- [x] CHK009 Is newest-row/latest-attempt fallback explicitly prohibited? [Coverage, Contract lifecycle §Read contract]
- [x] CHK010 Are ordinary error/audit outputs required to exclude transcript, prompt, raw response and provider body? [Completeness, Contract API §Stable error reasons]
- [x] CHK011 Are cross-workspace/meeting/type substitution and no-existence-leak expectations included in validation scope? [Coverage, Quickstart §Security/deletion]

## Abuse and external boundaries

- [x] CHK012 Are cost/concurrency abuse budgets assigned to the runtime safety slice before rollout? [Dependency, Program Roadmap §195]
- [x] CHK013 Are prompt revocation, HTTPS/allowlist validation and operator mutation audit assigned to a release-blocking feature? [Coverage, Program Roadmap §202]
- [x] CHK014 Is private evaluation content prohibited from git, issues, screenshots and chat evidence? [Privacy, Quality Strategy §Dataset program]
- [x] CHK015 Are ordinary black-box use and metadata-only installed-app
  inspection explicitly permitted while source/code/private-API inspection,
  extraction, decompilation and protection bypass remain prohibited? [Boundary,
  Constitution §VII; Research §Method]
- [x] CHK016 Are new share/export actions from source-stale revisions explicitly denied while existing pinned artifacts remain stable? [Consistency, Spec §FR-021]
- [x] CHK017 Is cross-workspace/meeting/type pointer integrity enforced by a composite database constraint as well as service checks? [Trust boundary, Data Model §Constraints]
- [x] CHK018 Does entering `deleting` immediately deny summary read/publication/egress while preserving the constitution-mandated retained observability distinction? [Deletion, Data Model §Deletion visibility]
- [x] CHK019 Is default resolution meeting-pinned/workspace-scoped and explicitly independent from the viewer's presentation/personal preference? [Egress, Spec §FR-022]
- [x] CHK020 Is share/export resolution and the exact type/revision artifact write one transactional linearization point under refresh races? [Concurrency, Spec §FR-025; Contract lifecycle §Egress]
- [x] CHK021 Is every high-stakes egress review receipt bound to the exact
  outcome/bundle/projection policy, approved audience, egress purpose,
  recipient-or-link scope, capability class, policy and reviewer so a changed
  recipient or permission cannot reuse it? [Egress, Summary Profile Catalog
  §High-stakes profiles]
- [x] CHK022 Does the outcome↔attempt composite FK compare every normalized
  provenance column directly, with an exact versioned length-framed fingerprint
  only as audit checksum and DB-frozen receipt/provenance fields? [Integrity,
  Data Model §Provenance fingerprint v1]
- [x] CHK023 Are generated subject-dependent shared results rejected, is every
  positive Feature 183 `my_actions` route/control absent, and is downstream
  authenticated filtering explicitly owned by Feature 205/196 only after trusted
  canonical action/mapping support exists? [Privacy, Spec FR-026/SC-012]
- [x] CHK024 Does opening Copy/Share/language state pin only the authorized exact
  displayed revision and fail closed on stale source, access loss or deletion
  without retaining private cached labels/content? [Egress, KRISP Matrix
  §Executable top-control contract]
- [x] CHK025 Does the gateway compare the exact `GatewayRouteBindingV1` hash
  before provider egress, echo actual provider/model, reject every mismatch or
  unallowlisted target and keep secrets only in LiteLLM? [Egress identity,
  Prompt Pipeline §Gateway route binding]
- [x] CHK026 Are raw/normalized focus queries treated as untrusted data whose
  model resolution cannot widen audience authorization, leak unavailable topic
  identity or replace no-match/ambiguity with another type? [Disclosure,
  Prompt Pipeline §Projection controls]
- [x] CHK027 Are Langfuse cached numeric last-known-good prompts accepted only
  with the exact activation manifest and successful root-promotion event after
  hash verification, while SDK fallback/code-copy/profile-label prompts,
  unqualified roots and silently moved evaluator rules are denied as
  publication or promotion authority?
  [Prompt authority, Temporal and Langfuse Contract §Prompt structure]
- [x] CHK028 Does mixed-audience output use the least-privilege visibility
  intersection and closed privacy policy, with context text unable to grant
  access or erase a material critical owner/state? [Disclosure, Prompt Pipeline
  §Typed meeting, audience, privacy and detail controls]
- [x] CHK029 Does `SourceContextPolicyV1` prevent agenda, attachment, notes or
  previous minutes from proving a current-meeting acceptance/assignment while
  preserving each source's separate evidence authority? [Grounding, Prompt
  Pipeline §SourceContextPolicyV1]
- [x] CHK030 Is transcript regeneration authenticated/CSRF-protected, bound to
  source/access/deletion/policy epochs and safe under ambiguous provider
  acceptance, with a durable pre-egress correlation ID, required provider
  lookup/callback, one submit attempt and no raw provider/transcript body returned
  to the browser?
  [Recovery boundary, API §Regenerate transcript]
- [x] CHK031 Do summary finalizers and transcript source replacement share the
  deletion→source-pointer→job→slot lock order, with `FOR SHARE`/`FOR UPDATE`
  fencing and deadlock/race fixtures? [Concurrency, Receipts §Lock order]
- [x] CHK032 Does every reference-derived visible element have the closed
  rights state `not_applicable|cleared|replacement_required|blocked`, with no
  release path for the latter two? [Rights, KRISP Matrix §Reference fidelity]
- [x] CHK033 Are `TranscriptRegenerationJob`, every replacement
  ProcessingResult/transcript artifact and provider evidence covered by
  same-workspace composite ownership, RLS, GRAF-controlled tombstone/purge and
  deletion reporting, while retained Temporal observability is disclosed as a
  separate dependency state rather than a readable meeting artifact? [Deletion,
  Data Model §TranscriptRegenerationJob; Program Backlog F202-08]
