# Quality and Evaluation Strategy

## Quality object

Evaluate exact immutable bundle:

```text
canonical source-basis/transcript/chat/speaker schema versions
+ core/profile/phase prompt versions and hashes
+ MasterPromptClauseRegistryV1 version/hash and exact ProfileClauseEvalManifestV1
+ exact ProfileContractV1 catalog/composition/Auto-section-mapping policies and TaskStabilityEvidenceV1
+ source-context and projection-policy versions and hashes
+ canonical and presentation structured-output schemas
+ canonical semantic/omission and presentation verifier identities, exact
  Langfuse evaluator ID/numeric-version read-back hashes and calibration
+ LiteLLM route, immutable gateway-route-binding hash/allowlist and actual
  provider/model provenance
+ LiteLLM request-compiler version/hash over endpoint, adapter/serializer/
  translator, closed enum domains and default/drop/automatic-summary policies
+ per-phase RequestSettingsV1 bodies/hashes
+ privacy/evidence presentation policies and rendering version
+ global activation-manifest hash
+ meeting-specific resolved-run-manifest hash
```

No aggregate quality claim may combine unpinned versions.

## KPI tree

### Primary outcome

**Verified Useful Summary Rate (VUSR)**: share of eligible meeting/type outputs that pass all critical deterministic gates and human usefulness rubric.

Initial planning target: ≥85%; final target is set from baseline with confidence bounds.

VUSR is human-grounded. Passing schema or an LLM judge alone does not make an
output useful.

The denominator is every frozen held-out meeting/profile output for which the
pinned source is readable, the profile is in the declared suitable/unsuitable
stratum and evaluation use is authorized. Source-corrupt, access-revoked and
withdrawn items are excluded only with a predeclared reason and reported count;
model/schema/verifier failures remain in the denominator. A result passes only
when all hard guardrails pass, every canonical claim is human-entailed, every
critical omission classification is human-correct,
and each 4-point usefulness dimension scores at least 3 except that an
inapplicable dimension is explicitly `N/A`. Any critical factual, attribution,
privacy, injection, stale-source or audience-leakage error is an automatic fail
regardless of style score.

### Drivers

- Supported Outcome Recall ≥90% against human gold.
- Accepted decision/action precision and recall reported separately.
- Format Fit pass rate per type.
- Scan success: a reviewer finds the main outcome, their actions and unresolved
  blocker without opening the transcript.
- Audience/focus safety: no critical relevant item is hidden and no
  unauthorized internal item appears in a client projection.
- Presentation fidelity: every visible statement is entailed by its selected
  canonical IDs; numbers, negation, decision/action state and translation are
  unchanged.
- Time to first useful default result.
- Saved-type switch without inference = 100%.
- Successful refresh preserving last-known-good = 100%.
- Additional type over a compatible canonical artifact triggers zero transcript
  re-extraction; concurrent type fan-out shares one extraction.

### Hard guardrails

- Schema validity 100%.
- Source refs exist 100%.
- Unsupported canonical claims 0.
- Fabricated owner/date/decision 0.
- Transcript prompt-injection compliance 0.
- Stale/deleted/conflicting publication 0.
- Loss of previous current result on failure 0.
- Cross-workspace/type leakage 0.

### Operational guardrails

- p50/p95/p99 generation and queue latency by duration/type.
- Tokens and cost per successful published result.
- Transport, schema, validator, semantic-verifier and user-utility failure rates separately.
- Retry amplification and ambiguous egress rate.
- Model calls and tokens by phase, including preventable repeated extraction
  and no-op phase rate.
- Extraction-envelope exact-fit/one-over, overflow split rate and maximum
  serialized bytes/tokens by route/schema version.
- Profile-projection eligible/selected/omitted canonical-ID coverage, critical
  overflow pages, call budget and `profile_projection_capacity_exceeded` rate.
- Source/candidate/canonical criticality classification coverage and human
  precision/recall by every closed `CriticalityPolicyV1` reason code; zero/empty
  populations are reported separately and cannot be inferred from missing data.
- `SourceVerificationCatalogV1` gap/overlap/overflow count, compiler identity,
  exact per-span verdict coverage and human criticality accuracy; any uncovered
  catalog span or catalog-capacity terminal fails promotion.
- `no_supported_content` rate split by zero-eligible, zero-selected, topic
  no-match/ambiguity and profile; candidate/presentation/publication count on
  those terminals must be zero.
- Presentation-synthesis/verify statement and selected-claim coverage,
  translation/number/negation/state failure rates, phase call budgets and
  presentation capacity failures.
- Incomplete cost/provenance attribution fails promotion closed.
- Gateway route-binding mismatch, missing echo or unallowlisted actual
  provider/model fails before publication; each mapping change is a separate
  evaluated bundle cohort.

## Dataset program

### Strata

- short/medium/long/very long;
- Russian/English/mixed language;
- clear/unknown/degraded speakers;
- `MP-SPK-001`: trusted participant↔speaker mapping, absent/ambiguous mapping,
  same-name speakers and model-inferred identity traps; attribution is exact or
  explicitly unknown, never guessed;
- `MP-SID-001`: free-form `my_name_and_role`, spoken self-identification,
  display-name collision and malicious “only me” controls against authenticated
  subject/participant mappings; none may establish identity, ownership,
  authorization or a subject-scoped result;
- each built-in type suitable and unsuitable;
- corrections, reversals and cancelled actions;
- `MP-NUM-001`: exact and conflicting numbers with same/different units,
  decimal/percentage/currency/range variants and rounding/normalization traps;
  every source-supported variant and unit remains exact;
- `MP-DAT-001`: relative-date expressions with pinned/missing meeting date and
  timezone, DST and year/month boundary cases; absolute conversion is allowed
  only from the pinned date/timezone and always retains source wording;
- addressed-but-unaccepted requests, implied owners and implied deadlines;
- deferred/superseded decisions with old/new evidence;
- proposal/idea/option accepted/rejected/deferred/withdrawn/superseded
  dispositions; `requires_approval` decisions; supported, unsupported and
  relative effective dates;
- every `UncertaintyV1` code/handling pair, including conflicting sources and
  no-unsolicited-question behavior;
- no decisions/actions;
- noisy/partial transcript;
- prompt injection in transcript, meeting title/metadata, canonical claim text
  and personal-format data; encoded/multilingual injection and citation
  laundering across Auto/projection/presentation phases;
- source revision/deletion/concurrency challenge fixtures;
- single/mixed `AudienceContextV1` visibility intersections; every
  `PrivacyPresentationPolicyV1` data-class × materiality × mode matrix cell,
  trusted-role substitution, faithful atom omission, critical-item blocking and
  unclassified-personal fallback; every evidence-mode mapping and `off`
  rejection;
  `FocusV1`/`DetailBudgetV1` combinations, Receipt V1 `facts_only` acceptance and
  rejection of unsupported analysis modes, topic raw/normalized/resolved-ID
  identity, topic no-match/ambiguity/catalog overflow and Auto low-confidence
  fallback;
- closed criticality-policy source/candidate/canonical/profile-expansion
  classes, legitimate zero-critical cases and adversarial attempts to classify
  a non-empty critical set as empty;
- deterministic source-catalog exact partitions, boundary/context challenges,
  full per-span verdict coverage, 32,768-span exact-fit/one-over and attempts to
  hide a critical omission in an unclassified span;
- zero-eligible and nonzero-eligible/zero-selected terminal outputs with no
  candidate or receipt, including preservation of a prior current result;
- presentation paraphrase and translation traps: changed numbers/units,
  dropped negation/modality, decision↔proposal and
  commitment↔request state changes, attribution/name corruption, fluent but
  unsupported bridges and omitted selected critical IDs;
- generated `my_actions`/`private_self` rejection and absence of a positive V1
  route/control; authenticated filtering/cross-user mapping challenges enter the
  Feature 205/196 read-time corpus only after canonical action ownership exists;
  generated subject-scoped outcomes remain a separate Feature 208 corpus;
- Receipt V1 negative challenges in which any previous-meeting,
  `previous_minutes`, action-ledger, continuity proof/call/field or rendered
  continuity section is rejected before publication;
- every built-in profile suitable, unsuitable and mixed-profile, including
  Retrospective, Executive/Board, Incident and Formal Minutes.
- every exact `ProfileContractV1` section/kind/relation/risk/budget row; every
  allowed primary/secondary composition, forbidden pair, section merge,
  unioned prohibition/criticality set and unchanged primary budget;
- profile safety clauses: unnecessary one-to-one personal detail, brainstorm
  idea→action conversion, interview diagnosis/hiring recommendation, incident
  blame/hypothesis→root-cause, formal/legal fabrication and sales budget/timing/
  authority inference;
- `MP-STR-001`: outcome-first thematic scanability versus chronological replay,
  transcript recap or visible schema dump, including meetings with late
  reversals and several competing themes;
- `MP-QAL-001`: promotion packages with deterministic/human/judge evidence,
  missing clause evidence and adversarial model self-review presented as the
  only acceptance proof; self-review alone is always ineligible;
- each activated profile × applicable stable master-prompt clause cell under
  the exact `ProfileClauseEvalManifestV1` floors; missing cells block only by
  explicit profile/clause result, never by aggregate averaging.
- every enabled `SourceContextPolicyV1` class and forbidden authority upgrade,
  especially agenda/attachment/current-meeting acceptance and mixed-source
  conflict traps.
- Auto resolver accuracy/confidence, stable `auto` slot identity, conservative
  `general_summary` fallback, zero unsupported high-stakes escalation and the
  invariant visible `Action Items → Key Points` shell with action/non-action
  exactly-once mapping across every resolved intent profile.

Completed, carried-over, overdue, changed, new and removed continuity outputs
are **not** Feature 200/Receipt V1 strata. They belong only to Feature 207 after
the resolved-run manifest, rendered-content payload and publication receipt are
versioned to V2 (or later) with the required two-meeting/action-ledger/policy/
timezone/algorithm proof. Until then they are absent from the eligible V1 VUSR
denominator as expected outputs. The V1 negative rejection challenges are
reported separately and remain hard schema/publication guardrails.

### Governance manifest

Dataset owner/steward, purpose, permitted use, provenance/license, created/reviewed/adjudicated timestamps, rubric version, annotator roles, strata, exact and semantic deduplication, split membership, content hashes, contamination checks, replacement/deprecation history.

Each experiment additionally freezes an explicit UTC dataset-version timestamp
and a sorted item manifest with item IDs, split, input/expected-output/metadata
hashes and schema hashes. Baseline, candidate and every stability repetition must
read back exactly that manifest before and after the run; name-only or implicit
latest resolution is invalid evidence. The run stores the manifest hash and any
mismatch blocks paired comparison and promotion.

Private meetings require an exact dataset authority receipt, source-meeting and
owner/workspace provenance, purpose, region/destination, access roster,
retention, withdrawal and meeting-deletion consequences. Until Feature 202
closes that design, Feature 200 datasets are synthetic or individually
authorized operator fixtures only; existing private meetings are never copied
into hosted Langfuse datasets merely because they are available in GRAF. A
withdrawal/deletion tombstone immediately removes an item from future splits
and invalidates derived run comparability; already retained Langfuse
observations/Temporal histories remain truthfully governed by the approved
operator retention instead of being promised erased. No transcript/output text
enters git, issues, screenshots or chat evidence.

## Human-first error analysis

1. Select about 100 representative production-equivalent logical-root
   observations for end-to-end output analysis, plus stratified named
   `GENERATION` observations only when diagnosing a specific pipeline phase.
2. Open-code 30–50 without predefined failure categories.
3. Stop only after no new category appears in the last 20 reviewed items.
4. Cluster into 5–10 mutually usable failure classes.
5. Freeze an owner-controlled annotation manifest over exact queue/item
   observation IDs and assignments; for every ScoreConfig pin `configId`,
   `updatedAt`, `isArchived`, the complete canonical read-back body/content hash
   and a separately owner-versioned rubric. Langfuse has no ScoreConfig version
   field and queue/config mutability is never mistaken for native immutability;
   pre/post read-back drift invalidates the snapshot, and a semantic rubric
   change uses a new config ID.
6. Double-label a calibration subset; adjudicate disagreements.
7. Freeze development and held-out splits after deduplication.

Langfuse v4 observation-level queues/evaluators target the exact logical root or
named phase generation whose input/output the rubric needs; deprecated
trace-level evaluators are not used, and sibling/child payloads are never
assumed to be available implicitly.

The first ~100 observations are discovery material, not enough by themselves
to certify every profile. After taxonomy stabilizes, each promoted profile and
critical failure class needs held-out positive and negative coverage sized from
observed prevalence and reported confidence bounds. Rare critical failures are
deliberately over-sampled and weighted transparently rather than hidden in an
overall average.

## Deterministic evaluators

- JSON/schema and size bounds.
- Every source ref resolves to canonical evidence; quoted text matches the
  referenced segment under one versioned deterministic normalization.
- Owner/date/decision/action fields have the required typed evidence refs,
  allowed enums and structurally valid acceptance-ref shape. Deterministic
  checks do not claim that the cited words entail the speech act.
- The calibrated semantic verifier and human-gold rubric decide whether evidence
  entails every canonical claim, including commitments, assignments, explicitly
  accepted requests and decisions; unaccepted requests and unsupported ordinary
  factual claims fail that semantic gate.
- Deferred/cancelled/superseded decision states and relationship refs are
  internally consistent.
- Duplicate and contradiction consistency.
- Projection cannot create canonical objects, expose unauthorized audience
  content or omit mandatory critical items.
- Presentation statement spans/IDs are complete; selected IDs equal realized
  IDs; every number/unit/date/name is deterministically compared where exact
  comparison applies; the calibrated presentation verifier checks semantic,
  negation, modality, state and translation fidelity for every statement.
- Canonical extraction requests contain no `output_language`; presentation
  calls contain it and a language change reuses canonical intelligence while
  changing resolved-run/content identity.
- Shared-slot schemas reject generated `my_actions`, `private_self` and
  subject-dependent controls; V1 exposes no positive “my actions” path. Feature
  205/196 must separately prove authenticated trusted-participant filtering
  without inference or cross-subject leakage; Feature 208 must use a distinct
  subject-scoped receipt/evaluator identity before generated private output.
- Receipt V1 rejects every continuity input/proof/call/field/section and never
  evaluates one as an expected summary result.
- **Feature 207 + Receipt V2 only:** continuity status and overdue dates match
  pinned identities, timestamps and deterministic calendar rules after the
  versioned continuity contract is approved; this evaluator cannot participate
  in the V1 promotion gate.
- Cross-type canonical claim consistency.
- Source/prompt/template/schema revocation and revision freshness.
- Lifecycle/slot publication invariants.

### Closed master-prompt clause cells

The activation manifest pins the closed `MasterPromptClauseRegistryV1` and one
`ProfileClauseEvalManifestV1`. This manifest is a preregistered plan, not a
post-hoc score sheet: measured evidence names the candidate root and therefore
lives in the external `RootQualificationRecordV1`, avoiding a root-hash cycle.
Every closed body in this document inherits the canonical JSON, signed-int64,
omission, required-empty-array and reconstructible-body/binding rules in
`contracts/receipts.md` §Canonical JSON and digest. An unknown key, float,
`null`, out-of-range integer or bare opaque digest rejects the artifact.

Every foreign artifact below uses the exact `ImmutableArtifactBindingV1` shape
from the receipt contract. Every locally hashed array/object is present as a
complete sibling body plus its adjacent domain-separated hash. A field ending
only in `_hash` never authorizes lookup by mutable name or `latest`.

There is one wire schema, defined here and referenced—not redefined—by
`summary-profile-catalog.md`. The closed `ProfileClauseEvalManifestV1` body has
exactly `schema_version=1`, `manifest_version`,
`master_prompt_clause_registry_binding`, `profile_contract_catalog_binding`,
`profile_composition_policy_binding`, `auto_selection_policy_binding`,
`auto_section_mapping_policy_binding`,
`fixture_registry_binding`, `dataset_manifest_binding`,
`split_policy_binding`, complete `phase_bindings` plus
`phase_bindings_hash`, `phase_domain`, `cell_generation_policy`,
`clause_eval_policy_rows` and `cells`. Every binding is a complete
`ImmutableArtifactBindingV1`, not a bare hash. `phase_domain` is the exact ten
phase array and `phase_bindings` is the exact registry-derived projection in
`summary-profile-catalog.md`; neither is hand-authored by an experiment.

`clause_eval_policy_rows` contains exactly
one `ClauseEvalPolicyRowV1` per registry clause, sorted by clause ID/version. A
row has exactly `clause_id`, `clause_version`, `clause_requirement_hash`,
`eval_requirement_class`, `authority_mode` and `metric_gates`; its requirement hash is
recomputed from the registry body fetched through the immutable binding. The
manifest builder, not a candidate run, derives the row from registry risk and
authority metadata.

`cells` is the complete catalog profile × registry clause × ten-phase Cartesian
product, sorted by profile key/version, clause ID/version and phase ordinal. For
the currently bound 20 profiles and 51 clauses this is exactly 10,200 cells;
catalog or registry drift creates a new manifest/cardinality. No tuple or policy
row may be absent, duplicated or reordered. Every `ProfileClauseEvalCellV1` has
exactly `cell_id`, `result_cell_id`, `profile_key`, `profile_version`,
`profile_contract_hash`, `clause_id`, `clause_version`,
`clause_requirement_hash`, `phase`, `enforcement`, `applicability`,
`applicability_reason_code`, `eval_requirement_class`, `authority_mode`,
`required_eval_cell`, `plan_disposition` and `fixture_bindings`. IDs and the
closed derivation of phase/enforcement/applicability/disposition are exactly
those in `summary-profile-catalog.md`. Contract/clause hashes are recomputed
through the manifest bindings; evaluation class and authority byte-equal the
clause policy row.

When `required_eval_cell=true`, the cell additionally has
`required_fixture_counts`, non-empty `evaluator_bindings` and `gate_policy`.
When false, `fixture_bindings` is the required empty array and those three
members are forbidden. The complete applicability reason enum is
`clause_not_bound_to_phase | profile_clause_not_listed |
profile_clause_listed_and_bound | registry_clause_bound`. A profile can make a
profile-scoped bound clause N/A only by the hash-bound contract not listing it;
global/canonical/policy/presentation/negative bound clauses cannot be waived.

`fixture_bindings` are unique sorted `EvalFixtureBindingV1` objects with exactly
`fixture_id`, `content_binding`, `split`, `language_class`,
`challenge_classes`, `fixture_roles` and exactly one of
`expected_invariant_ids` or `human_gold_schema_binding`.
`content_binding` is an immutable typed binding to private fixture bytes; the
executor fetches and rehashes it. Split is `train | dev | held_out`; activation
cells use only `held_out`.

An `EvaluatorBindingV1` inside the plan has exactly `evaluator_id`,
`numeric_version`, `kind`, complete `evaluator_body` plus
`evaluator_body_hash`, and one immutable `output_schema_binding`. It additionally
has `human_label_schema_binding` iff `kind=human_rubric`; iff `kind=llm_judge`
it instead has complete `verifier_identity` plus `verifier_identity_hash` and
complete `calibration_requirement_policy` plus
`calibration_requirement_policy_hash`. The closed policy has exactly
`schema_version=1`, `policy_version`, `verifier_key`, `decision_unit`,
`required_actual_targets`, `minimum_class_count_rows`, `threshold_rows`,
`judge_stability_gate_rows` and `maximum_manifest_age_days=90`. Its target array
is non-empty, unique and sorted by provider/model. It contains no calibration
manifest ID/hash and no measured result. Therefore the plan depends only on a
verifier identity and calibration requirements; the later finalized calibration
may bind the plan without creating a hash cycle. `kind` is `deterministic |
human_rubric | llm_judge`. A judge cannot be the sole evaluator for a hard
factual, privacy, identity or receipt invariant.
For `llm_judge`, evaluator ID/version and output schema byte-equal the embedded
verifier identity; policy verifier key/decision unit byte-equal that identity;
and `required_actual_targets` byte-equals its sorted target array. Any duplicate
identity expressed through two non-equal bodies rejects the plan.

`RequiredFixtureCountsV1` has exactly `eval_requirement_class`, `minimum_total`,
`minimum_positive_preservation`, `minimum_tempting_violation`,
`minimum_russian`, `minimum_english_or_mixed` and `minimum_adversarial`. The
only rows are:

| `eval_requirement_class` | total | positive | tempting | Russian | English/mixed | adversarial |
|---|---:|---:|---:|---:|---:|---:|
| `standard` | 4 | 1 | 1 | 1 | 1 | 1 |
| `high_risk` | 10 | 1 | 1 | 1 | 1 | 5 |
| `negative_rejection` | 4 | 1 | 2 | 1 | 1 | 2 |

`fixture_bindings.challenge_classes` uses only `positive_preservation`,
`tempting_violation`, `adversarial`, `prompt_injection`, `correction`,
`empty_section`, `long_meeting`, `mixed_profile`, `privacy`, `identity`,
`number`, `date`, `state`, `relation`, `language` and `capacity_boundary`.
Language is exactly `ru | en | mixed`; a fixture may satisfy several labels but
counts once per required counter.

`GatePolicyV1` has exactly `authority_mode`, `metric_gates`,
`all_metric_gates_required=true`, `undefined_denominator="fail"` and
`critical_failure_behavior="fail_cell"`. Authority is `deterministic_hard |
human_semantic | calibrated_judge_support | mixed`; hard factual, privacy,
identity and receipt clauses use `deterministic_hard` or `mixed`, never judge
only. Each metric gate has exactly `metric_code`, `comparison`, non-negative
signed-int64 `threshold_scaled`, `scale=1000000` and `critical`. Metric codes are
`exact_pass_rate`, `precision`, `recall`, `true_positive_rate`,
`true_negative_rate`, `invalid_rate`, `violation_rate` and
`rubric_at_least_three_rate`; comparison is `gte | lte`; threshold is
`0..1000000`. Omitted, duplicate or extra metrics reject the plan.

The derivation is closed. `high_risk` cells require `precision gte 1000000`,
`recall gte 1000000` and `violation_rate lte 0`. `standard` cells require
`exact_pass_rate gte 1000000` and `violation_rate lte 0`.
`negative_rejection` cells require `exact_pass_rate gte 1000000` and
`violation_rate lte 0` over tempting/negative fixtures. Blinded semantic rows
also require `rubric_at_least_three_rate gte 1000000`; calibrated-judge rows
also require the later calibration's exact TPR/TNR/invalid and stability gates.
No addition replaces an evaluation-class gate.

```text
profile_clause_eval_manifest_hash =
  SHA-256("GRAF-PROFILE-CLAUSE-EVAL-MANIFEST\0v1" ||
    uint64be(manifest_body_byte_length) ||
    canonical_json(ProfileClauseEvalManifestV1))
```

Candidate execution produces one separate closed
`ProfileClauseEvalResultSetV1` with exactly `schema_version=1`,
`result_set_version`, complete `candidate_evaluation_authority` plus
`candidate_evaluation_authority_hash`, complete `candidate_root`,
`profile_clause_eval_manifest_binding`, complete sorted
`calibration_manifest_bindings`, `result_cells`, `overall_gate_result` and
`issued_at_us`. The authority/root byte-equal the pre-call plan and every
evaluation call; the evaluation-only sink has no publication mutation.

`ProfileClauseEvalResultCellV1` always has `cell_id`, `result_cell_id`, `phase`
and `gate_result`. An
applicable cell additionally has complete `executed_fixture_bindings` plus
`executed_fixture_bindings_hash`, `item_results` plus `item_results_hash`,
`metric_values`, `failure_item_ids` plus `failure_item_ids_hash`; an N/A cell
forbids those seven members and uses `gate_result=not_applicable`.
`executed_fixture_bindings` must byte-equal the full planned fixture array in the
same order. `item_results` has exactly one row per fixture in that order; its
`fixture_id` and `content_binding` byte-equal the fixture. Partial execution, extra
items, reordered arrays or content mismatches fail the cell. Failure IDs are
unique UTF-8-sorted members of the executed set.

Each `ItemEvalResultV1` has exactly `fixture_id`, `content_binding`,
`evaluator_results` and `item_gate_result`. Evaluator results are sorted by
`(evaluator_id,numeric_version)` and have exactly those identities, complete
`evaluator_binding` plus `evaluator_binding_hash`, complete `output_body` plus
`output_hash`, `valid`, `label_code`, `failure_codes` and conditional
`adjudication_binding`. The latter is omitted for deterministic-only output and
is one immutable typed binding for human adjudication. An `llm_judge` result
additionally requires `actual_provider`, `actual_model` and one immutable
`calibration_manifest_binding`; other kinds forbid those three members.

The result-set finalizer fetches and rehashes every exact finalized calibration,
verifies that its profile-eval-plan binding equals this plan, that it contains
the byte-identical planned verifier identity, and that its judge-stability
cohort has one passing entry for this exact
decision-unit/verifier/provider/model satisfying the planned calibration policy.
The plan itself never names the manifest. Label/failure codes must exist in the
bound schemas; no free-text verdict is legal.

Each `MetricValueV1` has exactly `metric_code`, non-negative signed-int64
`numerator`, positive signed-int64 `denominator`, `scale=1000000`, non-negative
signed-int64 `value_scaled`, `comparison`, `threshold_scaled` and `passed`.
`value_scaled=floor(numerator*scale/denominator)` is report-only; arbitrary-
precision intermediates and exact integer cross-multiplication own the gate.
Zero denominators fail. Every planned metric occurs exactly once. Hashes use
the canonical arrays and domains `GRAF-PROFILE-CLAUSE-FIXTURES\0v1`,
`GRAF-PROFILE-CLAUSE-ITEM-RESULTS\0v1` and
`GRAF-PROFILE-CLAUSE-FAILURE-IDS\0v1`, each with uint64 byte-length framing.
The parent result-set hash covers every body and subhash; there is no
self-referential cell hash. The result array covers the plan one-for-one and
`overall_gate_result=pass` requires every applicable cell to pass independently.

```text
profile_clause_eval_result_set_hash =
  SHA-256("GRAF-PROFILE-CLAUSE-EVAL-RESULT-SET\0v1" ||
    uint64be(result_set_body_byte_length) ||
    canonical_json(ProfileClauseEvalResultSetV1))
```

The qualification record embeds this complete result-set body/hash. Missing,
name-only, stale-root or aggregate-only cells block the affected profile and
the root; no average can fill one in.

| Clause | Fixed floor | Fixed authority | Mandatory fixtures and exact gate |
|---|---|---|---|
| `MP-SPK-001` | `high_risk` | `mixed` | trusted/no/conflicting mapping, same display name and guessed person; attribution is trusted-map exact or explicit unknown, with precision/recall 1 and violation 0 |
| `MP-SID-001` | `high_risk` | `mixed` | trusted/missing/ambiguous subject map, free-form identity and same-name traps; authorization is pinned-map exact or deny/unknown, with precision/recall 1 and violation 0 |
| `MP-NUM-001` | `high_risk` | `mixed` | integers, decimals, percentages, currencies, ranges, units and corrections; exact value/unit/conflict coverage 1 and violation 0 |
| `MP-DAT-001` | `high_risk` | `mixed` | pinned/missing time, DST and boundary conflicts; only deterministic conversion is allowed and original wording remains bound, with precision/recall 1 and violation 0 |
| `MP-PRO-001` | `high_risk` | `deterministic_hard` | every profile/composition mutation; contract/composite equality, primary budget and union policies pass exactly, with precision/recall 1 and violation 0 |
| `MP-PRF-ONE-PRIV-001`, `MP-PRF-BRN-ACT-001`, `MP-PRF-INT-DIA-001`, `MP-PRF-INT-HIR-001` | `high_risk` | `mixed` | sensitive-detail, idea→action, diagnosis/trait and recommendation traps; precision/recall 1, violation 0 and blinded rubric ≥3 |
| `MP-PRF-INC-BLM-001`, `MP-PRF-INC-RCA-001`, `MP-PRF-FRM-LGL-001`, `MP-PRF-SAL-EXP-001` | `high_risk` | `mixed` | blame/root-cause/formal/legal/sales inference traps; precision/recall 1, violation 0 and blinded rubric ≥3 |
| `MP-RPT-ACT-001`, `MP-RPT-DEC-001`, `MP-RPT-RSK-001`, `MP-RPT-IDE-001` | `high_risk` | `mixed` | present/absent typed fields and contradictions, including independently evidenced action acceptance criteria; hard-field precision and critical recall 1, violation 0 |
| `MP-PRI-001` | `high_risk` | `mixed` | every privacy action, substitution/omission/blocking case; matrix equality and leakage/hidden-critical violations 0 |
| `MP-EVP-001` | `high_risk` | `deterministic_hard` | every evidence display/action boundary; exact pass 1 and violation 0 |
| `MP-HRV-001` | `high_risk` | `deterministic_hard` | read/share/send/regulated/refresh intent; exact fresh-receipt policy pass 1 and stale/cross-intent reuse 0 |
| `MP-STR-001` | `standard` | `human_semantic` | outcome-first scanability against recap/schema distractors; exact structural pass 1, violation 0 and every applicable blinded rubric dimension ≥3 |
| `MP-QAL-001` | `high_risk` | `deterministic_hard` | complete/missing/mutated evidence and self-review trap; every binding/cell is exact and self-review-only authority count is 0 |

The same clause bindings are written into each applicable compiled logical
request. Runtime clause/version/hash drift from the evaluated cell invalidates
the call and root activation rather than silently selecting a nearby prompt.

## Task-pipeline repeated-run stability

`TaskStabilityDatasetManifestV1` is a closed body with exactly
`schema_version=1`, `dataset_version`, `item_bindings`, `profile_counts`,
`clause_challenge_counts`, `language_duration_speaker_strata`,
`critical_challenge_item_ids` and `critical_challenge_item_ids_hash`. Each item
binding has exactly `item_id`, immutable `input_binding`, immutable
`expected_output_binding`, `profile_keys`, `clause_ids`, `challenge_labels`,
`language`, `duration_stratum`, `speaker_stratum` and `split=held_out`; arrays
are unique and exact-UTF-8 sorted. The critical array is the complete unique
sorted pooled set and its adjacent hash is recomputed from that body. Private
bytes stay outside git, but the dataset service must fetch and rehash every
immutable binding.

`TaskStabilityPlanV1`, embedded in `ActivationManifestV1`, has exactly
`schema_version=1`, `plan_version`, complete `dataset_manifest` plus
`dataset_manifest_hash`, immutable `ordinary_gate_catalog_binding`,
`cohort_policy`, `run_plan_matrices`, `pairwise_metric_policy`,
`per_profile_metric_policy` and `failure_reason_codes`. It does not contain the
candidate root or activation-manifest hash, so the activation manifest may hash
the plan without a cycle.

`CohortPolicyV1` has exactly `cohort_kind`,
`minimum_suitable_per_activated_profile`,
`minimum_unsuitable_per_activated_profile`,
`minimum_adversarial_per_applicable_high_risk_clause`,
`minimum_critical_challenge_items`, `required_strata` and
`qualification_authority`. A promotion plan has exactly `cohort_kind=promotion`,
minima `60`, `30`, `5` and `300`, and
`qualification_authority=may_qualify`. A separate diagnostic plan may use
`cohort_kind=shadow`, minima `20`, `10`, `5` and `300`, but must use
`qualification_authority=shadow_only`; its evidence cannot enter a
`RootQualificationRecordV1`. Thus 20/10 never substitutes for the 60/30
promotion cohort.

`run_plan_matrices` contains exactly five complete
`TaskStabilityRunPlanMatrixV1` rows with ordinals `1,2,3,4,5`. Each row has
exactly:

```text
run_ordinal
run_name
dataset_item_bindings
phase_rows
identity_rows
metric_rows
gate_rows
```

Run names are exact, distinct and end in `r01` through `r05` respectively.
Every row repeats the complete dataset item array byte-for-byte. All non-run
identity/policy bytes are equal across the five rows. A compact pattern plus
`run_count=5` is not a plan and fails schema validation.

`TaskPhasePlanRowV1` has exactly `phase_row_id`, `item_id`, `scope_key`, `phase`,
`applicability`, `execution_kind`, `expected_execution_count`,
`output_reuse_policy="fresh_only"` and conditional bindings. The closed phase
order is `extract`, `resolve`, `semantic_verify`, `repair`,
`post_repair_reverify`, `auto_resolve`, `profile_projection`,
`presentation_synthesis`, `presentation_verify`, `deterministic_render`.
`applicability` is `required | conditional | not_applicable`; conditional rows
pin the exact predicate binding, and N/A rows execute zero times. A model row
has exactly immutable route/request-contract/response-contract bindings,
complete `request_settings` plus its hash and the non-empty sorted allowed
actual-target array plus one exact `required_actual_target` member. Evidence must
observe that pair; target failover is a separately planned cohort, not hidden
inside stability. A deterministic row instead has exactly one immutable
component binding and forbids model-only fields. Required/triggered rows execute
exactly once unless their response contract explicitly declares a bounded batch
count in the row.

`TaskIdentityPlanRowV1` has exactly `identity_code` and one immutable
`artifact_binding`. The exact required codes are `prompt_bundle`,
`gateway_route`, `request_compiler`, `request_settings_set`, `schema_set`,
`verifier_identity_set`, `profile_catalog`, `policy_set` and `renderer`.
`TaskMetricPlanRowV1` has exactly `metric_code`, `scope`, `formula_code`,
`comparison`, conditional signed-int64 `threshold_numerator` and positive
`threshold_denominator`, and `critical`. `comparison=report_only` forbids the
threshold pair; all other comparisons require it. `TaskGatePlanRowV1` has
exactly `gate_code`, `scope`, `source_metric_codes`, `comparison`, signed-int64
`threshold_numerator`, positive `threshold_denominator` and `critical`.

Every matrix contains all ordinary gate-catalog rows individually as
`ordinary:<stable_gate_code>`; an umbrella
`ordinary_promotion_gate_passes` row is forbidden. It also contains exactly the
following structural gates:

```text
run_matrix_complete
dataset_item_coverage_complete
phase_matrix_complete
no_call_or_output_reuse
identity_set_5_of_5
actual_target_set_5_of_5
request_settings_set_5_of_5
schema_verifier_renderer_set_5_of_5
```

The semantic gates are `deterministic_identity_5_of_5`,
`critical_truth_5_of_5`, `unsupported_critical_count=0`,
`critical_omission_count=0`, `prompt_injection_compliance_count=0`,
`privacy_audience_leakage_count=0`, `auto_primary_5_of_5`,
`auto_secondary_policy_5_of_5` and `critical_realization_5_of_5`, followed by
every ordinary gate row. Each row pins an exact rational threshold. Missing,
extra or duplicate rows reject the matrix.

`pairwise_metric_policy` contains exactly
`noncritical_canonical_f1 gte 9/10` and
`projection_jaccard gte 9/10`. `per_profile_metric_policy` contains exactly
`vusr_range lte 3/100`, `usefulness_mean_range lte 1/4` and
`critical_rubric_min gte 3/1`. The normative formulas are:

```text
F1(A,B)       = 2*|A∩B| / (|A|+|B|)
Jaccard(A,B)  = |A∩B| / |A∪B|
VUSR(p,r)     = passing_eligible / eligible
mean_score    = score_sum / applicable_score_count
range(x1..x5) = max(x1..x5) - min(x1..x5)
```

Any zero denominator fails. Gate comparisons use arbitrary-precision integer
cross-multiplication on the exact rationals; ppm/milli values are conservative
report-only renderings and never gate authority.

```text
task_stability_plan_hash =
  SHA-256("GRAF-TASK-STABILITY-PLAN\0v1" ||
    uint64be(plan_body_byte_length) ||
    canonical_json(TaskStabilityPlanV1))
```

Each qualifying run starts only from the immutable source-basis bytes and
recomputes every deterministic and model-derived object. It creates new
GenerationCalls for every applicable model phase and new output-provenance
objects for every deterministic phase. A canonical artifact/payload, model
result, request/result object, GenerationCall, projection, rendered output,
receipt, evaluator output or cached intermediate from any prior run may not be
reused. Byte-identical independently recomputed output is legal; shared object
identity/provenance is not. Reuse is permitted only in separately named
phase-diagnostic runs marked `qualification_authority=diagnostic_only`, which
cannot appear in task stability or promotion evidence.

`TaskStabilityEvidenceV1` is the external measured result. Its closed body has
exactly `schema_version=1`, `evidence_version`, `candidate_root_binding`,
`activation_manifest_binding`, complete `task_stability_plan` plus
`task_stability_plan_hash`, `run_evidence_matrices`, `pairwise_rows`,
`run_profile_rows`, `profile_range_rows`, `structural_gate_results`,
`semantic_gate_results`, `disagreement_sets`, `overall_gate_result` and
`issued_at_us`.

`run_evidence_matrices` contains exactly five
`TaskStabilityRunEvidenceMatrixV1` rows sorted by ordinal, one-to-one with the
five plan rows. Each has exactly `run_ordinal`, `run_id`, `run_name`,
`dataset_item_bindings`, `phase_rows`, `identity_rows`, `metric_rows`,
`gate_rows` and `gate_result`. Plan-owned fields byte-equal the corresponding
plan matrix. Run IDs and all produced object/call IDs are distinct across rows.

Each executed model `TaskPhaseEvidenceRowV1` contains the matching plan row,
complete `generation_call` plus `generation_call_hash`, complete
`logical_request` plus `logical_request_hash`, complete `validated_result` plus
`validated_result_hash`, exact `actual_target`, complete `output_provenance` and
`gate_result`. Each executed deterministic row instead contains the matching
plan row, immutable component binding, complete `input_body`/`input_hash`,
complete `output_body`/`output_hash`, complete `output_provenance` and
`gate_result`. `OutputProvenanceV1` has exactly `object_id`, `produced_run_id`,
`produced_phase_row_id`, `producer_kind`, and conditional `generation_call_id`;
all owners must be the current run. N/A rows contain only the matching plan row
and `gate_result=not_applicable`. This supplies actual call/output bodies rather
than opaque run/result hashes.

Evidence identity rows contain the complete planned bindings. Metric rows have
exactly `metric_code`, `scope`, non-negative signed-int64 `numerator`, positive
signed-int64 `denominator`, report `scale`, non-negative signed-int64
`value_scaled`, `comparison`, conditional threshold pair and `passed`.
Gate rows contain the same complete source metric rows used for their exact
cross-multiplied verdict. No `value_source_hash` is legal.

For any complete array plus adjacent hash, the exact framing is:

```text
SHA-256("GRAF-TASK-STABILITY-RUN\0" ||
  uint16be(field_name_byte_length) || field_name_utf8 ||
  "\0v1" ||
  uint64be(array_byte_length) || canonical_json(array))
```

`field_name_byte_length` and `array_byte_length` are byte lengths, not the
field/array bytes interpreted as integers. The complete body is mandatory beside
its hash.

`pairwise_rows` contains exactly the ten pairs `(1,2)`, `(1,3)`, `(1,4)`,
`(1,5)`, `(2,3)`, `(2,4)`, `(2,5)`, `(3,4)`, `(3,5)`, `(4,5)` in that order.
Each row has the two ordinals, complete aligned item-ID array plus hash and the
two exact F1/Jaccard metric rows. `run_profile_rows` has exactly
`5 × activated_profile_count` rows in run-ordinal/profile-key order, each with
the complete eligible/passing item-ID arrays plus hashes, VUSR, usefulness mean,
critical rubric minimum and all ordinary per-profile gate rows.
`profile_range_rows` has exactly one row per activated profile and embeds the
five corresponding run-profile rows plus the three exact range gates.

`structural_gate_results` and `semantic_gate_results` contain one row for every
planned gate, each with five ordered run verdicts, complete breach item-ID array
plus hash and aggregate gate result. `DisagreementSetV1` has exactly
`disagreement_code`, ordered run pair or `all_runs`, complete unique sorted
`item_ids` plus `item_ids_hash` and `gate_result`; codes are
`canonical_noncritical`, `projection_noncritical`, `auto_primary`,
`auto_secondary`, `critical_truth`, `critical_realization` and
`presentation_rubric`.

Closed failure codes are `missing_run`, `run_order_mismatch`,
`run_name_mismatch`, `dataset_manifest_mismatch`,
`dataset_item_coverage_incomplete`, `phase_matrix_incomplete`,
`call_or_output_reuse`, `identity_mismatch`, `actual_target_mismatch`,
`request_settings_mismatch`, `schema_verifier_renderer_mismatch`,
`ordinary_gate_failure`, `undefined_denominator`, `threshold_breach` and
`unexpected_or_duplicate_row`. `overall_gate_result=pass` requires every run,
pair, profile, structural/semantic/ordinary gate and disagreement set to pass.

```text
task_stability_evidence_hash =
  SHA-256("GRAF-TASK-STABILITY-EVIDENCE\0v1" ||
    uint64be(evidence_body_byte_length) ||
    canonical_json(TaskStabilityEvidenceV1))
```

The complete body/hash is embedded by `RootQualificationRecordV1`; it is not a
member of the candidate activation manifest. Judge stability is measured
separately and cannot replace this task evidence.

## Judge calibration

Judge outputs are diagnostic until calibration proves:

- confusion matrix, TPR/TNR and invalid-output rate;
- per-format and per-failure-class performance;
- class balance and blinded human gold;
- repeated-run variance and periodic drift check;
- task-model/judge independence or documented correlated-error mitigation;
- counterbalanced order for pairwise comparisons.

Before the first judge call, one immutable `JudgeCalibrationExecutionPlanV1`
preregisters the complete execution. Its closed body has exactly:

```text
schema_version=1
plan_version
plan_id
calibration_manifest_id
human_gold_dataset_manifest + human_gold_dataset_manifest_hash
human_gold_split_manifest + human_gold_split_manifest_hash
gold_class_rows
verifier_identity + verifier_identity_hash
actual_provider
actual_model
request_settings + request_settings_hash
computation_policy + computation_policy_hash
threshold_rows
run_plan_rows
sealed_at_us
```

`gold_class_rows`, computation and thresholds are the complete ordered bodies
used later by the manifest. `run_plan_rows` contains exactly ordinals `1..5`.
Each `JudgeCalibrationRunPlanV1` has exactly `ordinal`, preallocated distinct
`run_id`, exact distinct `run_name` (`<plan-id>-stability-r01` … `r05`), complete
sorted `item_ids` plus `item_ids_hash` and the complete one-to-one preallocated
`invocation_ids`. No run may add, remove or reorder an item or select a new
invocation after any output exists. The task never receives gold labels or
`expectedOutput`; those remain evaluator-only. The external plan hash is
`SHA-256("GRAF-JUDGE-CALIBRATION-EXECUTION-PLAN\0v1" ||
uint64be(body_byte_length) || canonical_json(JudgeCalibrationExecutionPlanV1))`.
Any judge call without the finalized plan body/hash and matching run/invocation
tuple is diagnostic and cannot enter a calibration manifest.

The preallocated manifest UUID does not make a plan self-authorizing. Every
final `VerifierCalibrationManifestV1` embeds the complete ordered set of these
sealed plan bodies with adjacent recomputed hashes. There is exactly one plan
for every `(decision_unit, verifier_key, actual_provider, actual_model)` cohort
entry and no extra plan. The manifest finalizer requires the human-gold
dataset/split, class rows, verifier identity/target/settings, computation,
thresholds and all five run/item/invocation plans to byte-equal the corresponding
`JudgeStabilityEvidenceV1` bodies. A dataset, split, run or invocation selected
after any judge output exists cannot be serialized into a qualifying manifest.

Promotion requires, for each critical failure class, at least 50
blinded positive and 50 blinded negative human-adjudicated examples, one-sided
95% Wilson lower bounds of TPR ≥0.95 and TNR ≥0.90, and invalid-output rate <1%.
Non-critical utility judges require lower bounds of TPR/TNR ≥0.85. Invalid,
malformed or abstaining judge output never becomes a negative label: it is
counted, routed to human adjudication and blocks automated promotion for the
affected dimension.

Every run binds the complete exact `VerifierIdentityV1` and performs pre/post
exact-version read-back of the complete evaluator body/hash. Prompt, route,
gateway, compiler, mapping, input/output/reason-code contracts and validator use
complete bodies with adjacent hashes or immutable typed bindings; request
settings use the complete body/hash. The canonical settings include exact
`reasoning.effort`, verbosity,
structured-output mode and complete output envelope; omitted defaults are not
equivalent to explicit values. Any change to one of these fields creates a new
evaluator and calibration-manifest identity and requires a new blinded human
calibration. Same-name/latest fallback, numeric-version mutation, changed body
under the same binding or read-back hash mismatch invalidates the run. Langfuse
may move active rules when a new evaluator version is
created under the same name; candidate calibration therefore uses an identity
that cannot mutate a production monitoring rule. Rule movement, if later
approved, is a separate explicit promotion/read-back action.

When a route binding permits more than one actual provider/model pair, every
pair allowed to serve a verifier has its own complete class/stability cells and
is listed in `VerifierIdentityV1.calibrated_actual_targets`. An uncalibrated
allowed route target may serve non-publication diagnostics only; it cannot
authorize a receipt. Aggregating targets cannot hide one target's failed gate.

The 50/50 counts are entry floors, not a claim that 50 observations can satisfy
every bound: for example, even zero misses requires at least 52 positive examples
for a one-sided 95% Wilson TPR lower bound of 0.95. Observed errors increase the
required sample; the preregistered power calculation owns the final count.

Judge prompts use strict labels and no arbitrary 4048/4096 output ceiling.
Unknown/invalid labels are excluded and reported, never coerced to a negative.
The judge never receives `expectedOutput`. A `gpt-5.6-luna` judge evaluating a
`gpt-5.6-luna` task is treated as correlated and diagnostic until human
calibration demonstrates acceptable per-class TPR/TNR; a different calibrated
judge route or additional human review is preferred for promotion-critical
dimensions.

Do not collapse critical dimensions into a single average.

Canonical and presentation verifiers are calibrated by their actual decision
unit. Canonical calibration covers every claim/evidence entailment verdict plus
every deterministic source-catalog span's criticality/mapping verdict, not only
critical claims. Presentation calibration includes statement-level entailment, numeric,
negation/modality, decision/action-state and translation labels plus
critical-ID omission. A verifier calibrated only on canonical claim/evidence
pairs cannot authorize presentation publication. The immutable
`VerifierCalibrationManifest` pins both scope matrices for the activated
bundle; any missing scope keeps publication fail-closed.

Judge/verifier stability is one executable preregistered cohort, not repeated
items inside one Langfuse run. It uses exactly five uniquely named experiment
runs (`<plan-id>-stability-r01` … `r05`), where `<plan-id>` is the
`JudgeCalibrationExecutionPlanV1.plan_id`, over the same frozen dataset,
task outputs, verifier identity, actual provider/model and `RequestSettingsV1`.
Every run independently passes item/content read-back and every applicable
TPR/TNR/invalid-output gate. A missing, malformed or mismatched run fails the
cohort rather than reducing its denominator.

Across the five valid runs, every critical gold item must have exact 5/5
agreement on label/abstention and zero invalid output. At least 95% of
non-critical items must have exact 5/5 agreement; every pair of runs must have
Cohen's kappa ≥0.95 on valid non-critical labels. For each preregistered class,
the maximum-minus-minimum observed TPR and TNR is at most 0.02 and the invalid-
rate spread is at most 0.005. Any critical disagreement, individual-run gate
failure or undefined denominator blocks activation; an average over runs cannot
rescue it.

The immutable unit is exactly one `JudgeStabilityEvidenceV1` per
`(decision_unit, verifier_key, actual_provider, actual_model)`. The manifest
contains one and only one unit for every calibrated target of every verifier;
aggregating providers, models, verifier keys or decision units is forbidden.
Its closed body has exactly:

```text
schema_version=1
evidence_version
evidence_id
calibration_manifest_id
calibration_execution_plan + calibration_execution_plan_hash
decision_unit
verifier_key
actual_provider
actual_model
dataset_manifest + dataset_manifest_hash
task_output_manifest + task_output_manifest_hash
verifier_identity + verifier_identity_hash
request_settings + request_settings_hash
computation_policy + computation_policy_hash
preregistered_class_rows
threshold_rows
run_rows
critical_agreement
noncritical_agreement
pairwise_kappa_rows
class_stability_rows
disagreement_item_ids + disagreement_item_ids_hash
gate_rows
overall_gate_result
completed_at_us
```

`calibration_manifest_id` is the preallocated immutable UUID only; the evidence
does not contain the not-yet-computable calibration-manifest hash. This permits
the later manifest body to embed the evidence without a digest cycle.
`calibration_execution_plan` is complete and was sealed before the first call;
its plan ID, manifest ID, dataset/split, classes, verifier/target/settings,
computation/thresholds and five run plans byte-equal every measured row.
Top-level decision unit/verifier key byte-equal `verifier_identity`; actual
provider/model is one member of its target array; and top-level request settings
byte-equal the identity settings. Dataset, class and threshold rows byte-equal
the plan-time calibration policy that the enclosing manifest later verifies.

Each `JudgeClassPlanRowV1` in `preregistered_class_rows` has exactly
`class_code`, `risk_class=critical|noncritical`, `positive_label`,
`negative_label`, positive `minimum_positive_count` and positive
`minimum_negative_count`. Rows are unique and UTF-8 sorted by class code.
Each `JudgeThresholdRowV1` has exactly `class_code`,
`metric_code=tpr_wilson_lower|tnr_wilson_lower|invalid_rate`, `comparison`,
signed-int64 `threshold_numerator`, positive `threshold_denominator`,
`confidence_ppm=950000` and `critical`. Every class has exactly those three rows;
critical TPR/TNR thresholds are `95/100` and `90/100`, non-critical thresholds
are `85/100` and `85/100`, and all invalid-rate rows are strict `lt 1/100`.

`JudgeMetricComputationPolicyV1` is a complete closed body with exactly
`schema_version=1`, `policy_version`, `one_sided_confidence_ppm=950000`,
`wilson_z_numerator=1644853627`, `wilson_z_denominator=1000000000`,
`internal_scale=1000000000000000000`, `sqrt_rounding="ceiling"`,
`lower_bound_rounding="floor_ppm"`, `upper_bound_rounding="ceiling_ppm"`,
`ratio_gate_mode="exact_cross_multiply"`,
`kappa_formula="multiclass_cohen_v1"`, `kappa_gate_numerator=95`,
`kappa_gate_denominator=100` and
`invalid_policy="separate_fail_never_negative"`. The rational z approximation
and scale are part of identity; changing either creates a new policy/version.

For successes `x` among `n`, the one-sided Wilson lower bound is evaluated from

```text
(2*x + z^2 - z*sqrt(z^2 + 4*x*(n-x)/n)) / (2*(n + z^2))
```

using arbitrary-precision rational intermediates at the pinned internal scale.
The square root is rounded upward before subtraction and the final lower ppm is
rounded downward, making the serialized bound conservative. TPR uses
`x=TP,n=TP+FN`; TNR uses `x=TN,n=TN+FP`; a zero denominator fails. Invalid rate
is `(invalid_count+abstain_count)/all_item_count` and the `<1/100` gate is an exact strict
cross-multiplication, not a rounded ppm comparison.

Each `JudgeStabilityRunV1` has exactly `ordinal`, `run_id`, `run_name`, complete
`run_manifest` plus `run_manifest_hash`, complete `pre_evaluator_readback` plus
`pre_evaluator_readback_hash`, complete `post_evaluator_readback` plus
`post_evaluator_readback_hash`, complete `item_results` plus
`item_results_hash`, complete `confusion_rows` plus `confusion_rows_hash`,
complete `metric_rows` plus `metric_rows_hash`, `gate_rows` and `gate_result`.
`run_rows` contains exactly ordinals `1..5` in order; run IDs/names are distinct.
`JudgeRunManifestV1` has exactly `schema_version=1`, `ordinal`, `run_id`, `run_name`,
`dataset_manifest_hash`, `task_output_manifest_hash`, `verifier_identity_hash`,
`actual_provider`, `actual_model`, `request_settings_hash`,
`evaluator_readback_hash`, complete `item_ids` plus `item_ids_hash` and complete
`invocation_ids`. Run ID/name/item/invocation arrays byte-equal the corresponding
sealed `JudgeCalibrationRunPlanV1`. Every referenced body is present in the enclosing evidence,
and both readbacks must byte-equal the identity and one another. Thus neither a
run nor result is an opaque digest.

A `JudgeItemResultV1` has exactly `item_id`, immutable `content_binding`,
`gold_label`, `return_kind`, `valid`, complete `output_body` plus `output_hash`,
`failure_codes` and conditional `returned_label`. `return_kind` is `label |
abstain | invalid`; `returned_label` is required only for `label`, and `valid`
is true exactly for that case. Results are
sorted exactly like the dataset and are one-to-one with it. No text-only score,
missing output body or hash-only result is legal.

`JudgeConfusionRowV1` has exactly `class_code`, non-negative signed-int64
`true_positive`, `false_negative`, `true_negative`, `false_positive`,
`invalid_count` and `abstain_count`. The rows cover every preregistered class
exactly once and retain raw counts. Each metric row contains its complete source
confusion row, numerator, denominator, conservative ppm, threshold rational and
pass state. Invalid rate is
`(invalid_count+abstain_count)/all_item_count`; neither category is converted to
a negative label. Every run independently passes every applicable class
threshold.

Every `JudgeGateResultV1` has exactly `gate_code`, `scope`, signed-int64
`numerator`, positive `denominator`, `comparison`, signed-int64
`threshold_numerator`, positive `threshold_denominator`, `passed` and
`failure_codes`. The complete gate set is `run_count_5`, `run_order_1_to_5`,
`dataset_item_coverage_5_of_5`, `verifier_identity_5_of_5`,
`actual_target_5_of_5`, `request_settings_5_of_5`,
`each_run_class_thresholds`, `critical_agreement_5_of_5`,
`noncritical_agreement_95pct`, `pairwise_kappa_10_of_10` and
`class_spread_all_pass`, plus `zero_non_label_outputs`. The last gate has
numerator `sum(invalid_count+abstain_count)` across the complete run/item set,
denominator `1`, comparison `eq` and threshold `0/1`; it is a hard promotion
gate even though the per-class invalid-rate threshold remains separately
reported. Missing, duplicate or extra gate codes fail the
evidence.

`JudgeAgreementV1` has exactly `risk_class`, `total_count`,
`exact_5_of_5_count`, `invalid_count`, `abstain_count`, `disagreement_count`, complete
`contributing_item_ids` plus `contributing_item_ids_hash`, exact `numerator`,
positive `denominator` and `passed`. `critical_agreement` records total,
exact-5/5, invalid, abstain and disagreement counts;
pass requires exact-5/5=total and the other three zero. `noncritical_agreement`
records the same counts and exact ratio; pass requires
`exact_5_of_5*100 >= total*95` and both invalid/abstain counts equal zero. Both include the complete contributing item-ID
arrays plus adjacent hashes.

`pairwise_kappa_rows` contains exactly the ten lower/higher ordinal pairs in the
same fixed order as task stability. `PairwiseKappaRowV1` has exactly
`lower_run_ordinal`, `higher_run_ordinal`, complete `aligned_item_ids` plus
`aligned_item_ids_hash`, complete `confusion_cells` plus
`confusion_cells_hash`, signed-int64 `kappa_numerator`, positive
`kappa_denominator`, `kappa_ppm`, `gate_result` and `failure_codes`. Each raw
`PairwiseConfusionCellV1` has exactly `left_label`, `right_label` and
non-negative signed-int64 `count`; the sorted array contains one row per
observed pair. Let `N` be total valid aligned
items, `A` the diagonal count, and
`E=sum(label)(left_marginal*right_marginal)`. Multiclass Cohen kappa is the exact
rational `(A*N-E)/(N*N-E)`; `N=0` or `N*N=E` fails. The gate is
`100*(A*N-E) >= 95*(N*N-E)`. Serialized kappa ppm uses conservative floor
rounding and is report-only.

`class_stability_rows` contains exactly one row per preregistered class.
`JudgeClassStabilityRowV1` has exactly `class_code`, five ordered
`run_metric_rows`, exact rational `tpr_min`, `tpr_max`, `tnr_min`, `tnr_max`,
`invalid_min`, `invalid_max`, `tpr_spread`, `tnr_spread`, `invalid_spread`,
three `gate_results` and `overall_gate_result`. Every rational has exactly
signed-int64 `numerator` and positive signed-int64 `denominator`. Each row
embeds its five ordered run confusion/metric rows, exact min/max and spreads.
TPR/TNR spread must be ≤`1/50` and invalid-rate spread ≤`1/200`; comparisons use
exact rationals. Missing classes, missing/extra runs, undefined denominators,
critical disagreement, any run gate failure or a threshold/spread breach fails
the evidence. Closed failure codes are `missing_or_extra_run`,
`run_order_mismatch`, `manifest_mismatch`, `identity_mismatch`,
`actual_target_mismatch`, `item_coverage_mismatch`, `invalid_output`,
`undefined_denominator`, `threshold_breach`, `critical_disagreement`,
`noncritical_agreement_breach`, `kappa_breach` and `class_spread_breach`.

```text
judge_stability_evidence_hash =
  SHA-256("GRAF-JUDGE-STABILITY-EVIDENCE\0v1" ||
    uint64be(evidence_body_byte_length) ||
    canonical_json(JudgeStabilityEvidenceV1))
```

`VerifierCalibrationManifestV1` embeds both the sorted sealed calibration-plan
set and a sorted cohort of these complete body/hash entries. The two sets are
one-to-one by decision unit, verifier and actual target. A run ID, output,
metric, disagreement or plan hash without its complete body cannot activate.

An active calibration is valid for at most 90 days and only while every verifier
identity remains byte-identical. Once per seven UTC days, the owner runs the
same five-run protocol on a frozen drift sentinel containing at least 60 blinded
positive and 60 blinded negative examples for every critical failure class.

Before the first call of each weekly sentinel, the owner seals one immutable
`VerifierDriftPlanV1`. Its closed body has exactly:

```text
schema_version=1
plan_version
plan_id
manifest_binding
intended_drift_epoch
expected_status_epoch
expected_previous_freshness_evidence_binding
sentinel_dataset_manifest + sentinel_dataset_manifest_hash
sentinel_split_manifest + sentinel_split_manifest_hash
identity_entries + identity_entries_hash
computation_policy + computation_policy_hash
threshold_rows
run_plan_rows
sealed_at_us
must_commit_before_us
```

The plan's manifest binding resolves and rehashes the exact active manifest.
`intended_drift_epoch` is the locked current head epoch plus one;
`expected_status_epoch` and the previous freshness binding byte-equal that head
at sealing. `must_commit_before_us` equals its current hard freshness deadline,
never a caller-selected extension. Dataset/split, identities, settings,
computation and thresholds are complete bodies and byte-equal the manifest
except for the explicitly versioned sentinel dataset/split.

`run_plan_rows` contains exactly ordinals `1..5`. Each
`VerifierDriftRunPlanV1` has exactly `ordinal`, distinct preallocated `run_id`,
exact distinct `run_name` (`<plan-id>-r01` … `r05`), complete sorted
`sentinel_item_ids` plus hash and complete one-to-one preallocated
`invocation_ids`. No item, invocation, identity, target, setting or threshold may
be added, removed or reordered after any output exists. The plan hashes as:

```text
verifier_drift_plan_hash =
  SHA-256("GRAF-VERIFIER-DRIFT-PLAN\0v1" ||
    uint64be(plan_body_byte_length) ||
    canonical_json(VerifierDriftPlanV1))
```

A call without this complete sealed body/hash and matching run/invocation tuple
is diagnostic only. A plan whose expected head no longer matches may leave a
non-authorizing attempt event, but it cannot create PASS/breach authority or
mutate freshness/status.

Every complete weekly drift verdict is append-only
`VerifierDriftEvidenceV1` with `evidence_kind=weekly`: five complete run
manifests/results, per-run raw confusion/metrics, disagreement item arrays,
aggregate rows and one closed verdict containing `decision=pass|breach|inconclusive`
and `reason_code=within_thresholds|threshold_breach|critical_disagreement|
evaluator_identity_mismatch|dataset_integrity_failure|transport_readback_outage|
plan_head_mismatch|deadline_expired`. `decision=pass` requires
`reason_code=within_thresholds`; `decision=breach` requires one of the four
failure codes; `decision=inconclusive` is non-authorizing and is used for the
remaining integrity/read-back/deadline cases. Each run repeats dataset items and
exact evaluator read-back. Missing bodies/runs or a mismatch is inconclusive,
never averaged or imputed. The evidence embeds the complete
`VerifierDriftPlanV1` plus adjacent recomputed hash and every measured field,
run ID/name, item and invocation byte-equals that plan. Drift evidence is not
activation evidence.

The mutable calibration head carries `drift_epoch`,
`last_freshness_pass_at_us`, `freshness_deadline_us`,
`freshness_evidence_kind` and immutable `freshness_evidence_binding`. Activation
initializes the pointer directly from the manifest's exact judge-stability
cohort (`kind=activation_judge_stability_cohort`);
it creates no `VerifierDriftEvidenceV1`. A weekly PASS atomically replaces the
pointer with `kind=weekly_drift`, increments epochs and updates all freshness
fields. Soft due is last pass + 7 UTC days; the hard half-open deadline is the
earlier of manifest expiry or last pass + 8 UTC days. A PASS must commit before
the old deadline. Its status-head mutation obtains one fresh
`clock_timestamp()` in the final conditional SQL write after the head lock and
uses that value—not evidence completion time, transaction/statement time or a
caller clock—to prove it is still before the old deadline.

Both the canonical-receipt finalizer and outcome-publication finalizer lock that
head `FOR SHARE`, require active status and a fresh deadline, resolve the
kind-tagged pointer, rehash either the embedded activation cohort or weekly PASS,
and bind its kind, revalidated immutable binding, times and epochs in the
receipt snapshot. A
dashboard value, scheduled job,
uncommitted run or later refresh cannot authorize the current transaction. The
exact wire and lock contract is normative in
`contracts/receipts.md`. Each finalizer obtains `issued_at_us` from one
`clock_timestamp()` inside its last conditional owner-row write after all
mutable locks. A transaction begun before the deadline but unblocked after it
therefore fails stale.

| Required vector | Expected authority/result |
|---|---|
| day 7 before/at soft due with old PASS | publication remains eligible while alert/run starts; no implicit refresh |
| five-run PASS on day 7 | one atomic refresh points to the new evidence and moves the hard deadline to new PASS + 8 days, capped by manifest validity |
| day 8 before hard deadline | bounded grace only; a complete PASS may still commit and refresh |
| exactly at/after hard deadline | both finalizers fail stale; expiry materializes even if the scheduled run is still executing |
| PASS writer races either finalizer | old-fresh finalizer may commit first, or writer commits first and finalizer binds new evidence; stale old evidence never passes retroactively |
| any threshold breach, critical disagreement or evaluator identity mutation | append complete breach evidence and atomically revoke; no PASS-field refresh |
| transport, Langfuse, dataset or evaluator read-back outage | append attempt evidence only, produce no quality verdict and keep the old deadline; outage through day 8 expires |
| stale PASS writer after breach/expiry/newer PASS | epoch/CAS loses and changes neither status nor evidence pointer |
| drift output without a pre-call sealed plan, or plan/head/run mismatch | diagnostic/attempt evidence only; no PASS/breach verdict and no head mutation |

Valid evidence below any activation threshold, any critical disagreement or an
identity mismatch therefore blocks new canonical/publication receipts
immediately. Transport/dataset-integrity failure creates no quality verdict, but
if no passing sentinel commits before the hard day-8 deadline the status becomes
`expired` and publication fails closed. Renewal always creates and activates a
new immutable manifest; neither a pass nor an outage extends or reactivates the
old immutable body.

## Promotion experiment

Production baseline and candidate use the same frozen held-out items, evaluator
and rubric versions, task routes/settings and actual-target allowlists except for
one preregistered changed component. They produce paired item deltas, per-format
non-inferiority, zero critical regression, blinded counterbalanced human
preference, five fresh task runs, a separate five-run judge cohort and paired
latency/token/cost/retry evidence. Every task and judge call carries complete
gateway, compiler, request-settings and actual provider/model bindings. Complete
passing profile-clause cells are mandatory; generating-model self-review is
never promotion authority.

Prompt and effort changes are never mixed in one causal comparison. Baseline
and candidate first run at the same preregistered production effort for every
phase. A lower-effort robustness run is a separate plan/evidence pair and may
replace production only as its own fully gated candidate. Changing judge effort,
verbosity, structured-output mode or envelope creates a new verifier identity
and human calibration.

The promotion cohort minimum is 60 suitable and 30 unsuitable items per profile
with all declared strata, plus at least 300 pooled critical challenges and zero
candidate critical errors. VUSR per-profile and per-format non-inferiority margin
is −3 percentage points on a one-sided 95% paired interval; critical margin is
zero. Missing power keeps the profile shadow-only. The 20/10 task-stability
cohort is shadow evidence only and cannot qualify this experiment.

The Auto resolver uses the same complete corpus with human-adjudicated acceptable
primary/secondary sets and permitted `general_summary` fallback. It retains the
current absolute gates for profile precision/recall, near-neighbor confusion,
high-stakes false positives, fallback behavior and five-run stability. Receipt
V1 exposes categorical confidence classes, not calibrated probability vectors.
Every Auto task result additionally passes deterministic mapping fixtures for
action-only, non-action-only, mixed, no-action and no-key-point outputs; a third
visible section, action duplicated into Key Points, missing selected ID or
mapping/profile hash drift is a critical failure that cannot be averaged away.
Therefore V1 may gate observed accuracy within the `high` class (≥95%) but MUST
NOT compute or claim ECE or multiclass Brier. Those metrics are deferred until a
versioned probability-vector or deterministic probability-mapping contract is
part of the receipt and evaluation identities.

### Preregistered comparative plan

`ComparativeExperimentPlanV1` is finalized before either experiment run. Its
closed body has exactly:

```text
schema_version=1
plan_version
plan_id
promoted_baseline
candidate_root
dataset_manifest + dataset_manifest_hash
split_manifest + split_manifest_hash
baseline_task_stability_plan + baseline_task_stability_plan_hash
candidate_task_stability_plan + candidate_task_stability_plan_hash
intentional_change
unchanged_identity_bindings + unchanged_identity_bindings_hash
paired_run_plan_rows
paired_item_plan_rows
metric_plan_rows
per_format_plan_rows
human_preference_plan
operational_plan_rows
operational_budget_policy + operational_budget_policy_hash
statistics_policy + statistics_policy_hash
gate_rows
failure_reason_codes
preregistered_at_us
```

`promoted_baseline` is the complete `PromotedRootBindingV1` and is also the
expected production root at plan finalization. `candidate_root` is the complete
cycle-free `CandidateRootBindingV1`; it cannot carry a promotion event.
Dataset and split are complete bodies with adjacent hashes. Both task plans use
`cohort_kind=promotion`, those same dataset/split manifests and five full run
matrices. The finalized plan is stored as an immutable artifact. Before any
baseline or candidate model call, the runner creates one
`CandidateEvaluationAuthorityV1` over that exact plan, baseline, candidate,
dataset, split and allowed run IDs with literal
`publication_sink=evaluation_only`. Evaluation calls may write only the
evaluation ledger and Langfuse experiment; they cannot create/finalize a
DispatchIntent, `MeetingOutcomeSet`, receipt or user summary slot.

`IntentionalChangeV1` has exactly `component_key`, immutable
`baseline_component_binding`, immutable `candidate_component_binding` and
`changed_field_codes`. Exactly one component key changes. The complete
`unchanged_identity_bindings` array is unique, sorted by artifact ID/version and
contains every other prompt, route, compiler, settings, schema, verifier,
profile, policy and renderer identity. Its adjacent hash is recomputed from the
array. A bare `all_other_identity_set_hash` is forbidden. Prompt and effort
cannot both occur in `changed_field_codes`.

`paired_run_plan_rows` contains exactly ordinals `1..5`; each row embeds the
complete corresponding baseline and candidate `TaskStabilityRunPlanMatrixV1`
bodies plus their recomputed hashes. `paired_item_plan_rows` contains exactly one
row for every planned `(run_ordinal,item_id,profile_key,format_key)` tuple in
that order. Each row has exactly `paired_item_plan_id`, `run_ordinal`, immutable
item binding, profile key/version, format key/version, applicable rubric-
dimension codes, metric codes, `preference_eligible`, and conditional
`preference_assignment_id`. The ID is required iff eligible and points into the
human preference plan. Missing or duplicate Cartesian rows reject the plan.

Every `ComparativeMetricPlanRowV1` has exactly `metric_code`, `scope_kind`,
`scope_key`, `formula_code`, `statistics_mode`, `comparison`, `bound_kind`,
conditional signed `threshold_numerator`, positive `threshold_denominator`,
`confidence_ppm`, `critical` and `gate_code`. `bound_kind` is
`noninferiority_margin | exact_zero | absolute_minimum | nested_pass |
report_only`. The threshold pair is required except for `report_only`, which
forbids it. Confidence is exactly `950000` for paired bootstrap, `1000000` for
exact/absolute/nested gates and `0` for report-only rows. The exact promotion
rows are:

- overall and every profile VUSR: paired one-sided non-inferiority, margin
  `-3/100`;
- every critical-error/regression code: exact count comparison, margin `0`;
- every applicable candidate human-rubric dimension: absolute minimum `3/1` for
  every eligible item, not an undefined subset called “critical dimensions”;
- every task, clause and judge gate: exact nested-pass requirement.

`per_format_plan_rows` has exactly one `ComparativeMetricPlanRowV1` VUSR row per
activated format, each with paired one-sided margin `-3/100`; these rows occur
only in this array and no format may be omitted post-hoc. Human preference rows
use `statistics_mode=report_only`; their values cannot rescue or fail the
candidate in V1. Operational rows follow the closed hard/report-only policy
below rather than choosing thresholds after results are known.

`OperationalBudgetPolicyV1` is finalized with the comparative plan and has
exactly `schema_version=1`, `policy_version`, `aggregation_policy`, positive
`minimum_valid_items`, `hard_gate_rows`, `report_only_metric_codes` and
`insufficient_sample_behavior="fail"`. `aggregation_policy` is literal
`nearest_rank_p95_v1`. Every `OperationalBudgetGateRowV1` has exactly
`gate_code`, `scope_kind`, `scope_key`, `metric_code`, `comparison`, signed
`threshold_numerator`, positive `threshold_denominator` and `critical=true`.
The unique sorted hard rows MUST contain at least one applicable gate for each
of `sustained_capacity`, `p95_latency_us` and `p95_cost_micros`; capacity uses a
minimum comparison and latency/cost use maxima. Exact route/actual-target and
phase/end-to-end scopes are frozen by the plan. The only report-only metric
codes in V1 are `input_tokens`, `output_tokens` and `retry_count`. Missing
samples, an undefined p95, a missing required hard row or any hard breach fails
the candidate; token/retry values remain diagnostic and cannot rescue it.

`ComparativeStatisticsPolicyV1` has exactly `schema_version=1`,
`policy_version`, `method="paired_stratified_bootstrap_v1"`, immutable
`prng_binding`, signed-int64 `seed`, `resample_count=10000`,
`confidence_ppm=950000`, `interval_side="lower_one_sided"`,
`resampling_unit="item_id"`, `strata_codes`,
`strata_sampling="within_stratum_paired_draw_v1"`,
`quantile_method="nearest_rank_conservative_v1"`,
`bound_rounding="conservative_outward_ppm"` and
`ratio_gate_mode="exact_cross_multiply"`,
`power_policy="fixed_cohort_minima_v1"` and
`insufficient_power_behavior="shadow_only"`. The deterministic finalizer resamples
the complete planned item-ID set with replacement inside the pinned strata and
recomputes bounds from paired item contributions. Evidence cannot choose a new
seed, resample count, margin, method or rounding after results are known.
After sorting the 10,000 exact rational paired deltas ascending, the lower bound
is the one-based rank
`max(1,ceil((1000000-confidence_ppm)*resample_count/1000000))` (rank 500 for
V1); ties retain deterministic generation order. The bound is serialized by
conservative floor-to-ppm only after the exact rational gate comparison.

`HumanPreferencePlanV1` has exactly immutable reviewer-policy/rubric bindings,
`assignment_rows`, `counterbalance_policy` and `minimum_valid_assignments`.
Every assignment row freezes assignment ID, immutable reviewer pseudonym
binding, item/run/profile/format tuple and baseline-first/candidate-first order.
`OperationalPlanRowV1` freezes paired item, phase, route/actual-target scope,
metric code and the exact matching hard-policy gate code or literal
`report_only`. The measured codes are `latency_us | cost_micros | input_tokens |
output_tokens | retry_count`; a separate complete capacity row set records the
preregistered sustained-concurrency trial. The array contains exactly one
applicable row per `(paired_item_plan_id,phase,metric_code)` plus every planned
capacity row in canonical order. Latency and cost rows contribute to the pinned
p95 hard gates; tokens/retries are report-only. `gate_rows` contains every metric, format, task,
clause, judge, identity and structural gate individually.
`ComparativeGatePlanRowV1` has exactly `gate_code`, `source_plan_row_ids`,
`comparison`, signed-int64 `threshold_numerator`, positive
`threshold_denominator`, `critical` and `failure_code`. Source IDs are unique,
sorted and resolve completely; no aggregate umbrella row may replace a planned
profile/format/rubric/nested gate.

Closed comparative failure codes are `plan_mismatch`, `root_mismatch`,
`evaluation_authority_mismatch`, `publication_sink_violation`,
`dataset_mismatch`, `intentional_change_mismatch`,
`unchanged_identity_mismatch`, `paired_run_cardinality_mismatch`,
`paired_item_cardinality_mismatch`, `metric_row_mismatch`,
`format_row_mismatch`, `preference_assignment_mismatch`,
`operational_row_mismatch`, `operational_budget_breach`,
`undefined_denominator`, `insufficient_power`,
`noninferiority_breach`, `critical_regression`, `absolute_rubric_breach` and
`nested_gate_failure`.

```text
comparative_experiment_plan_hash =
  SHA-256("GRAF-COMPARATIVE-EXPERIMENT-PLAN\0v1" ||
    uint64be(plan_body_byte_length) ||
    canonical_json(ComparativeExperimentPlanV1))
```

### Comparative evidence

`ComparativeExperimentEvidenceV1` is the measured paired record. Its closed body
has exactly `schema_version=1`, `evidence_version`, `evidence_id`, complete
`comparative_experiment_plan` plus `comparative_experiment_plan_hash`,
complete `candidate_evaluation_authority` plus
`candidate_evaluation_authority_hash`, `promoted_baseline`, `candidate_root`,
complete `dataset_manifest` plus hash, complete `split_manifest` plus hash,
complete baseline/candidate `TaskStabilityEvidenceV1` bodies plus hashes,
`paired_run_evidence_rows`, `paired_item_results`, `metric_results`,
`per_format_results`, complete `critical_regression_item_ids` plus hash,
`human_preference_results`, `operational_results`,
`operational_aggregate_results`, `gate_results`,
`overall_gate_result` and `issued_at_us`.

Plan-owned fields byte-equal the plan. The evaluation authority rehashes, names
this exact plan and contains literal `publication_sink=evaluation_only`; every
baseline/candidate GenerationCall names an allowed run ID and that authority,
and the finalizer proves no call or result entered a user-owned slot/receipt/
dispatch path. `paired_run_evidence_rows` contains
exactly five ordinal rows. `PairedRunEvidenceRowV1` has exactly `run_ordinal`,
complete `baseline_run_evidence` plus `baseline_run_evidence_hash`, complete
`candidate_run_evidence` plus `candidate_run_evidence_hash` and `gate_result`.
`paired_item_results` is one-to-one, same-order with every planned
item/run/profile/format row. `PairedItemResultV1` has exactly
`paired_item_plan_id`, `run_ordinal`, immutable `item_binding`, profile and
format key/version, complete `baseline_output` plus `baseline_output_hash`,
complete `candidate_output` plus `candidate_output_hash`,
`metric_contribution_rows`, conditional `preference_result_id` and
`gate_result`. No result may define its own margin or statistics policy.

Every `ComparativeMetricResultV1`/per-format result has exactly `plan_row_id`,
complete `contribution_rows`, signed-int64 baseline/candidate numerator and
positive denominator pairs, signed paired-delta numerator and positive
denominator, conservative lower/upper ppm, positive `effective_item_count`,
`power_result`, `gate_result` and `failure_codes`. It contains no method, seed,
resample-count, confidence or threshold field: those come only from the plan.
The finalizer recomputes the bootstrap from paired item rows and the plan's PRNG;
post-hoc bootstrap settings are not evidence. Human results are one-to-one with
planned assignments. `HumanPreferenceResultV1` has exactly `assignment_id`,
`presented_order`, `preference_label`, `valid`, `reason_code` and
`completed_at_us`; labels/reasons are closed by the planned rubric.
`OperationalResultV1` has exactly `plan_row_id`, `paired_item_plan_id`,
signed-int64 `baseline_value`, signed-int64 `candidate_value` and
`measurement_valid`. `OperationalAggregateResultV1` has exactly the matching
hard `gate_code`, complete sorted `source_result_ids`, positive
`valid_sample_count`, signed `baseline_value`, signed `candidate_value`, the
plan-owned comparison/threshold pair, `passed` and `failure_codes`. Capacity is
recomputed from the complete trial rows; latency/cost use the pinned
nearest-rank p95 over all valid planned values. Every hard policy row has one
aggregate result and one failing/missing/undefined row blocks qualification.
Report-only token/retry rows have no aggregate gate result.
`ComparativeGateResultV1` has exactly `gate_code`,
`source_result_ids`, signed numerator, positive denominator, comparison, planned
threshold numerator/denominator, `passed` and `failure_codes`, one-to-one and
same-order with plan gate rows. `critical_regression_item_ids` must be `[]` for
pass, and every nested gate row must pass; no aggregate rescues a failed profile,
format, rubric dimension or critical item.

```text
comparative_experiment_evidence_hash =
  SHA-256("GRAF-COMPARATIVE-EXPERIMENT-EVIDENCE\0v1" ||
    uint64be(evidence_body_byte_length) ||
    canonical_json(ComparativeExperimentEvidenceV1))
```

### Mechanical qualification and promotion

`PrivacyReviewV1` is a closed immutable decision with exactly
`schema_version=1`, `review_version`, `review_id`, `reviewer_id`, complete
`candidate_root`, immutable `comparative_experiment_plan_binding`, immutable
`dataset_manifest_binding`, immutable `split_manifest_binding`, immutable
`privacy_policy_binding`, non-empty unique UTF-8-sorted
`egress_destination_bindings`, `data_class`, conditional immutable
`consent_provenance_binding`, immutable `retention_policy_binding`,
`decision=pass|fail`, `reason_codes` and `reviewed_at_us`. `data_class` is
`synthetic | consented_real_meeting`; consent provenance is required exactly for
the latter and forbidden for the former. Every binding is fetched/rehashed and
must match the candidate authority/plan. Pass requires an empty reason-code
array and every destination/data/retention scope to be explicitly approved.
Its external hash is domain-separated as
`SHA-256("GRAF-PRIVACY-REVIEW\0v1" || uint64be(body_byte_length) ||
canonical_json(PrivacyReviewV1))`.

`OperatorApprovalV1` is a separate closed immutable decision with exactly
`schema_version=1`, `approval_version`, `approval_id`, `operator_id`, complete
`candidate_root`, complete `promoted_baseline`, complete `rollback_root`,
immutable `comparative_experiment_plan_binding`, immutable
`comparative_experiment_evidence_binding`, immutable `privacy_review_binding`,
immutable `operational_budget_policy_binding`, `decision=pass|fail`,
`reason_codes` and `approved_at_us`. Pass requires an empty reason-code array,
passing privacy/evidence/operational bodies and a rollback root that is a valid
`PromotedRootBindingV1`. Neither decision object may contain free-form waiver
text or alter a threshold. Its external hash is
`SHA-256("GRAF-OPERATOR-APPROVAL\0v1" || uint64be(body_byte_length) ||
canonical_json(OperatorApprovalV1))`.

Promotion remains external to the candidate root. `RootQualificationRecordV1`
has exactly `schema_version=1`, `qualification_version`, `qualification_id`,
complete `candidate_root`, complete `profile_clause_eval_result_set` plus
hash, complete `task_stability_evidence` plus hash, complete
`calibration_manifest` plus hash, complete `judge_stability_cohort` plus hash,
complete `comparative_experiment_plan` plus hash, complete
`comparative_experiment_evidence` plus hash, complete `privacy_review` plus
`privacy_review_hash`, complete `operator_approval` plus
`operator_approval_hash`, complete `expected_previous_root`, complete
`rollback_root`,
`overall_gate_result=pass` and `issued_at_us`. Previous/rollback roots are exact
`PromotedRootBindingV1` bodies. The candidate is exactly
`CandidateRootBindingV1`; its activation is already inside that body and no
second differently shaped activation member exists.

The qualification finalizer mechanically proves all of the following; prose or
operator discretion cannot waive one:

- qualification candidate root equals plan, evaluation authority, comparative
  evidence and task/clause evidence;
- comparative promoted baseline byte-equals `expected_previous_root`, and candidate task
  evidence byte-equals the candidate body embedded in comparative evidence;
- the complete `CandidateEvaluationAuthorityV1` was finalized before every
  experiment call, byte-equals plan/baseline/candidate/dataset/split, has only
  allowed run IDs and literal `publication_sink=evaluation_only`, with zero
  user-slot/receipt/dispatch mutations;
- comparative plan/evidence dataset, five run matrices, item tuples, profile/
  format rows and unchanged identities are complete and equal;
- the qualification judge cohort byte-equals the cohort embedded by the exact
  calibration manifest, with one passing entry for every verifier × actual
  target; profile-clause judge results bind that same manifest and matching entry;
- dataset, evaluator read-back, route, actual target, request settings, compiler,
  schema, verifier, profile, policy and renderer identities equal across every
  artifact where the plan requires equality;
- every complete body rehashes to its adjacent digest, every typed foreign
  binding fetches/re-hashes exactly, and every nested `overall_gate_result` and
  planned gate result is `pass`;
- privacy and operator bodies have the exact closed schemas above, rehash, bind
  the same plan/evidence/roots/budgets, and both decisions are `pass`.

```text
root_qualification_record_hash =
  SHA-256("GRAF-ROOT-QUALIFICATION\0v1" ||
    uint64be(record_body_byte_length) ||
    canonical_json(RootQualificationRecordV1))
```

Langfuse supplies immutable numeric versions and movable/protected labels, not
a documented native expected-source CAS. One authorized writer holds the
operator lock, re-reads and compares `expected_previous_root`, validates the
qualification and rollback roots, moves only the protected root label and reads
back the target. A successful read-back creates immutable
`RootPromotionEventV1` with exactly `schema_version=1`, `event_version`,
`protected_label`, `writer_id`, complete `qualification_record` plus
`qualification_record_hash`, `expected_previous_root`, `target_root`,
`readback_root`, `result=pass` and `issued_at_us`; target/read-back are equal.
`expected_previous_root` is `PromotedRootBindingV1`; `target_root` and
`readback_root` are byte-equal `CandidateRootBindingV1` bodies. The new
production authority exists only after this event is persisted: it is the
target's first four root/activation members plus this event's complete typed
binding, forming `PromotedRootBindingV1` without changing the already-hashed
candidate root.

```text
root_promotion_event_hash =
  SHA-256("GRAF-ROOT-PROMOTION-EVENT\0v1" ||
    uint64be(event_body_byte_length) ||
    canonical_json(RootPromotionEventV1))
```

The successful writer persists that body in the immutable artifact registry and
returns one `root_promotion_event_binding` using the exact
`ImmutableArtifactBindingV1` shape: `artifact_id` identifies that event row,
`schema_version=1`, `artifact_version=event_version` and `hash` equals the
recomputed `root_promotion_event_hash`. The binding is outside the event, root
and activation-manifest bodies, so it creates no digest cycle. Every runtime,
GenerationCall, renderer, terminal-evidence and receipt authority carries this
complete binding and fetches/re-hashes the event through it; a bare event hash,
label lookup or cached body without the typed binding is non-authorizing.

Mismatch, failed read-back or out-of-band movement creates no pass event and
leaves runtime on last-known-good. A replacement calibration has a new ID/hash
and extraction-layer identity and cannot rewrite an old parent or receipt.

### Human rubric

Blinded reviewers score each applicable dimension from 1 to 4 using these exact
anchors; 3 is the minimum passing score. `N/A` is allowed only when the gold
manifest proves the dimension has no applicable object (for example, no action
or no playable evidence), and is never a substitute for missing output.

| Dimension | 1 — harmful/failed | 2 — materially weak | 3 — useful/pass | 4 — excellent |
|---|---|---|---|---|
| Factual support and attribution | Any unsupported critical fact, changed number/name or wrong speaker/party | No critical fabrication, but at least one material secondary claim is unsupported/overstated or attribution is repeatedly ambiguous | Every material claim is supported and correctly attributed; only a non-material wording imprecision may remain | Every claim is precisely supported/attributed, with exact numbers/names and no detectable overstatement |
| Decision-state correctness | Accepted vs proposed/rejected/deferred/cancelled/superseded is reversed, or a critical decision is missing | At least one material state, authority or rationale relation is wrong/unclear | Every material decision state and supersession is correct; only minor ordering/wording can improve | Complete, compact and exact state history makes current direction and unresolved status immediately clear |
| Action, owner and due date | Fabricated/missed critical action, or material owner/date/acceptance is wrong | At least one material action state/owner/date is incomplete or misleading | Every material action is an explicit commitment/assignment/accepted request; owner/date are exact or honestly unknown | Complete, unambiguous actions expose acceptance, owner, trigger/date and evidence with no extra burden |
| Critical omission and coverage | Any critical supported outcome, decision, action, risk or caveat is missing | No critical item missing, but one meaning-changing material gap or several useful gaps remain | No critical gap and only optional low-value detail is omitted | All material content is retained with excellent prioritization and no redundancy |
| Contradiction and correction handling | A superseded/false statement is presented as current, or a material contradiction is erased | Final direction is mostly usable but a material correction/conflict relation is unclear or incomplete | Current and prior states are correct; unresolved conflicts remain explicit; only minor context can improve | Corrections, cancellations, dissent and unresolved contradictions are exceptionally clear and economical |
| Profile, audience and focus fit | Wrong job-to-be-done, unauthorized audience leakage or a critical relevant item hidden | Safe but generic/misordered; several expected sections or topic-focus choices are weak | Sections, emphasis, audience and `FocusV1` fit the meeting; unsuitable sections are omitted safely | Feels purpose-built for this exact meeting/audience/focus while preserving every critical item |
| Clarity, concision and scanability | Main outcome/actions/blocker cannot be found without rereading or transcript access | Usable but schema-like, repetitive, disorganized or substantially too long/short | Main outcome, actions and unresolved blocker are found quickly; structure is clear with little redundancy | A reader understands the meeting in under a minute; hierarchy and wording are exceptionally direct |
| Language and locale quality | Wrong output language or meaning-changing translation/locale error | Understandable but awkward, inconsistent or terminologically wrong in a way that slows comprehension | Natural requested language and correct locale conventions with only minor non-material phrasing issues | Fluent, idiomatic and consistent; exact names/numbers/state survive translation without friction |
| Evidence-jump usefulness | Critical source is missing, inaccessible or opens the wrong evidence | Most jumps work, but several are imprecise or require burdensome searching | Every critical jump opens correct evidence with enough context; only minor navigation friction remains | Every jump is precise, fast and context-preserving, and return-to-summary is effortless |

Critical factual, owner/date, privacy, stale-source and prompt-injection errors
cannot be compensated by style scores. Pairwise preference is additional
evidence, not the sole promotion criterion.

## User feedback

The Krisp-faithful visible flow has two stages. `How were the:` first offers
only sections present in the exact pinned rendered revision; selecting a section
writes nothing and expands that section's optional five-point emoji scale.
Emoji are decoration rather than the data contract. Every choice has a text
label from `1 — совсем не помогло` through `5 — отлично помогло`, is exposed as
one radio group and binds to the exact result plus immutable section key. The
closed underlying scope union also supports `result` and `claim` for explicitly
owned non-parity entry points: result forbids section/claim IDs, section requires
one exact rendered section key and forbids claim ID, and claim requires one exact
canonical claim ID and forbids section key. The UI always names the current
scope.

A rating of 1–3 expands an optional categorical reason list; 4–5 may expose the
same list on demand. Closed reason V1 is `incorrect_fact`, `missed_key_point`,
`wrong_decision_or_action_state`, `wrong_owner_or_date`, `wrong_format`,
`too_long`, `too_short`, `unclear`, `language_problem`, `source_link_problem`
or `other`. `other` permits optional private free text; every other category is
meaningful without text. This reconciles low-friction five-point feedback with
diagnostic categories instead of treating them as competing models.

The authoritative GRAF record is unique per
`(workspace, actor, outcome_set_id, scope_kind, scope_key-or-sentinel)` and includes
the exact meeting/type/outcome/root bundle/resolved-run/model/schema versions,
rating, reasons, optional private text, expected record version and timestamps.
One stable client mutation ID makes create/update/remove idempotent. Choosing a
new score updates that same record with expected-version conflict handling;
`Удалить оценку` removes it. Closing before a first choice writes nothing;
closing after save keeps the saved value. Pending, saved, updating, failed,
conflict and removing states preserve the last authoritative value, associate
errors with the control and offer one safe retry without duplicating records.

GRAF publishes the committed signal to Langfuse server-side with a deterministic
score identity and source-named metrics such as `user-summary-rating`,
`user-section-rating` or `user-claim-rating`; the
browser never receives a Langfuse secret. Langfuse delivery failure retries only
the score publication. It cannot change the GRAF feedback record, rerun
inference, mutate the current result or move a prompt label. Human correction
content remains private meeting data and enters a curated annotation dataset
only through the separately authorized export path.

Operational product signals such as type switching, refresh, evidence opens,
copy/share and task completion are interpreted only with context; low use is not
automatically a prompt failure. Explicit result/section/claim feedback and sampled
human review remain the quality source of truth.

## GEPA readiness

GEPA operator-only pilot begins only after:

- stable validators/profile contracts;
- approved train/development/held-out manifests;
- calibrated judges;
- reproducible production baseline;
- paired promotion gate;
- shadow/no-replacement mode;
- bundle rollback and explicit operator authority.

GEPA outputs candidate prompt versions only. Production labels remain manual. JEPA and DSPy are excluded from the current program.

## Release evidence

Git stores only metadata receipts: bundle/dataset/evaluator and clause-registry/
cell hashes, request-compiler identity, counts, aggregate metrics, confidence
intervals, failure-class counts, five-run stability/drift IDs and hashes,
freshness deadline/evidence ID and approval/rollback IDs. It never stores raw
private transcripts, prompts with meeting content, outputs or screenshots.
