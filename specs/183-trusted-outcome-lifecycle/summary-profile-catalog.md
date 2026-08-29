# Summary Profile Catalog Contract

This catalog is the product/prompt contract for Feature 198. Profiles select
and render one canonical intelligence artifact; they never independently infer
facts from the transcript. User-facing names may follow the approved Krisp
reference, while stable keys below remain internal and versioned.

## Universal profile rules

- Every visible factual object preserves canonical claim ID and evidence.
- Unsupported optional sections are hidden; no profile invents content to fill
  its layout.
- Unknown owner/date remains unknown. An unaccepted request is not an action.
- Proposal/idea/option disposition remains `open | accepted | rejected |
  deferred | withdrawn | superseded`; a profile cannot flatten it into a
  decision. Decision `requires_approval` remains visibly distinct from accepted,
  and an effective date is shown only with its own evidence.
- Every visible ambiguity uses the closed `UncertaintyV1` handling; a profile may
  omit an uncertain field or preserve alternatives but cannot replace uncertainty
  with smooth prose.
- Receipt V1 accepts only `facts_only`. Model-authored analysis is unavailable
  until a versioned analysis phase, verifier, manifest/content/receipt contract
  and subject/egress policy exist; profiles cannot smuggle it into prose.
- Shared `AudienceContextV1`, privacy policy and `FocusV1` may change ranking and
  depth, never factual
  state. V1 rejects `my_actions` and every generated subject-dependent result.
  Feature 205/196 may later add authenticated read filtering after canonical
  action/mapping ownership exists; only Feature 208 may add a generated
  subject-scoped result and receipt. Feature 199 must reject that capability.
- A text-topic `FocusRequestV1` is resolved only once, in projection batch zero
  over the complete bounded authorized topic catalog. The final `FocusV1` is
  immutable for later batches; no-match/ambiguity is terminal and never falls
  back to another focus or summary type.
- A visible item carries `state` only when every supporting canonical claim has
  one compatible stateful projection. Stateless items omit it; an item that
  merges incompatible states is rejected rather than losing or inventing status.
- A profile unsuitable for the source returns a concise useful subset or
  terminal `no_supported_content`; it does not hallucinate profile-specific
  fields. Zero eligible/selected IDs create no candidate, presentation calls,
  publication receipt or slot mutation.
- Each profile ships with suitable, unsuitable, mixed-profile, empty-section,
  correction, injection and long-meeting fixtures.
- Mixed-audience output is the authorization intersection across every requested
  audience, never a union. Empty intersection produces no supported content.

Every versioned `ProfileContractV1` is a closed body with exactly
`schema_version=1`, `profile_key`, `profile_version`, `provenance`,
`risk_class`, `profile_semantic_rule`, `sensitive_class_allowlist`,
`default_detail_level`, `budget_policy_key`, `section_order`,
`section_contracts`, `empty_state_section_keys`, `allowed_kind_set`,
`allowed_relation_set`, `required_kind_state_pairs`,
`required_relation_types`, `required_trusted_role_groups`,
`safety_caveat_codes`, `forbidden_inference_clause_ids` and
`master_clause_ids`, plus conditional `auto_policy_row_hash`. The conditional
field is present exactly for every `auto_eligible=yes` row and the
`general_summary` fallback row in `AutoSelectionPolicyV1`; it is absent for
`auto`, `outline` and `meeting_minutes`. This presence rule is catalog-stable
and does not change when a user selects a profile explicitly.

The body never contains its own digest. Its adjacent external digest is:

```text
profile_contract_hash = SHA-256("GRAF-PROFILE-CONTRACT\0v1" ||
  uint64be(profile_contract_body_byte_length) ||
  canonical_json(ProfileContractV1))
```

`ProfileContractCatalogV1` is the sole activated catalog authority. Its closed
body has exactly `schema_version=1`, `catalog_version=3` and
`profile_bindings`. `profile_bindings` contains one object with exactly
`profile_key`, `profile_version`, `profile_contract` and
`profile_contract_hash` for every row in this document, sorted by exact
`profile_key` UTF-8 bytes. The embedded contract is the complete body, including
`section_contracts`; no hash-only or Langfuse-profile-prompt entry is legal.

```text
profile_contract_catalog_hash =
  SHA-256("GRAF-PROFILE-CONTRACT-CATALOG\0v1" ||
    uint64be(profile_contract_catalog_body_byte_length) ||
    canonical_json(ProfileContractCatalogV1))
```

`auto_policy_row_hash`, when present, is likewise the domain-separated hash of
the exact closed Auto row body, not of rendered Markdown:

```text
auto_policy_row_hash = SHA-256("GRAF-AUTO-SELECTION-POLICY\0row\0v1" ||
  uint64be(auto_policy_row_body_byte_length) ||
  canonical_json(AutoSelectionPolicyRowV1))
```

`provenance` is the literal `built_in` for every row in this catalog. A
personal/owner-authored format must version the contract before introducing a
different provenance shape. Unchanged contracts remain `profile_version=1`;
the corrected `all_hands` and seven decision-section contracts are
`profile_version=2`; the Auto shell is `profile_version=3` after aligning empty-
section behavior with the observed reference. Changing purpose, section semantics,
exclusions, risk, budget, clause bindings or Auto row identity requires a new
profile version. Set-like arrays are unique exact
UTF-8 ascending; section, predicate-group and other order-semantic arrays retain
their canonical body order. Unknown fields, keys, kinds, states, relations,
clauses, ordering or caveats reject activation.

`risk_class` is exactly `ordinary | external_sensitive | regulated_record`.
Workspace policy may require stricter review but cannot downgrade the contract
class. Every profile has an exact `B1` budget row for each allowed detail level;
the numeric values are shared intentionally, while the hash includes profile
key/version and selected detail so one profile cannot borrow another contract.
Default per-page limits are:

| Detail | Non-critical items per section | Non-critical chars per item | Visible chars per page |
|---|---:|---:|---:|
| `concise` | 8 | 360 | 8,000 |
| `standard` | 20 | 600 | 20,000 |
| `detailed` | 50 | 1,000 | 50,000 |

The same policy adds whole-result non-critical limits (critical overflow is
separately retained behind deterministic `has_more` pages):

| Detail | Overview target/max | Non-critical items total | Non-critical UTF-8 bytes total |
|---|---:|---:|---:|
| `concise` | 3 / 7 | 24 | 4,000 |
| `standard` | 3 / 7 | 80 | 12,000 |
| `detailed` | 3 / 7 | 200 | 30,000 |

The target never forces filler: one or two supported overview claims produce
one or two items. Evaluators fail an over-budget non-critical payload, hidden
critical item, wrong `has_more` boundary or overview above seven; they do not
penalize evidence-backed critical overflow for exceeding the non-critical total.

The activated `B1:<profile_key>:<profile_version>:<detail>` row compiles to the closed `DetailBudgetV1` in
`prompt-pipeline.md`, including the separately versioned overview-item values.
The independent `EvidencePresentationPolicyV1` binds requested evidence display.
Projection, synthesis, verification and rendering bind
the same body/hash. Non-critical prose must remain within every bound; critical
content deterministically paginates and is never dropped to satisfy the table.

Every `ProfileContract` also declares the closed kind/state, relation, trusted
role-group and safety-caveat additions consumed by `CriticalityPolicyV1`.
Canonical-critical plus profile-expanded IDs are never silently dropped to meet
a presentation budget.
Overflow is deterministically grouped/paginated with `has_more` and stable
claim IDs. Extract/resolve/verify envelopes depend only on their phase schemas,
numeric extraction bounds, tokenizer and route; they are part of the
`extraction_layer_manifest_hash` and never vary by selected profile. A separate
profile-projection envelope depends on the bounded canonical input, selected
`ProfileContract`, projection controls and route and belongs only to the
`resolved_run_manifest_hash`. Presentation synthesis and presentation
verification each have their own strict schema, route-proven envelope and
128-call ceiling. The deterministic renderer has no provider envelope and owns
layout/markup only. All model envelopes use the maximal-fixture/context formula
and boundary suite in `prompt-pipeline.md`; projection uses its deterministic
authorized prefilter, route-proven batches of 1..N where 128≤N≤256, a 128-call
ceiling and complete selected/omitted canonical-ID coverage. Synthesis realizes
exactly the selected IDs in the requested language; verification covers every
statement, number, negation, decision/action state, translation and critical
selected ID.
No hidden global token constant is used. A boundary hit
or `overflow_detected` splits the shard and reruns it before canonicalization
rather than truncating the response.

`DetailBudgetPolicyV1` is the single closed authority behind `B1`. Its body has
exactly `schema_version=1`, `policy_version=1`, `budget_family_key="B1"`,
`detail_rows` and `critical_overflow_mode="has_more_pages"`. `detail_rows`
contains exactly three objects in `concise`, `standard`, `detailed` order; each
has exactly `detail_level`, `overview_target_min=3`, `max_overview_items=7`,
`max_noncritical_items_total`, `max_noncritical_utf8_bytes_total`,
`max_noncritical_items_per_section`, `max_noncritical_utf8_bytes_per_item` and
`max_visible_utf8_bytes_per_page`, using the numeric values in both tables
above. The body contains no digest. Its adjacent hash is:

```text
detail_budget_policy_hash =
  SHA-256("GRAF-DETAIL-BUDGET-POLICY\0v1" ||
    uint64be(detail_budget_policy_body_byte_length) ||
    canonical_json(DetailBudgetPolicyV1))
```

The per-run `DetailBudgetV1` repeats the selected row plus primary profile
key/version and this external policy version/hash. Exact 300/800/1,500-word
limits from the research prompt are deliberately not runtime authority: words
tokenize inconsistently across Russian, English and mixed text. The closed byte,
item, page and schema-derived provider envelopes above replace them and receive
exact-fit/one-over tests.

## Exact activated Auto and profile authorities

The canonical JSON blocks in this section are the only V1 Auto/profile
authority. Each block is already serialized as exact UTF-8 canonical JSON:
object keys are code-point sorted, set-like arrays are unique UTF-8 ascending,
and order-semantic arrays retain the declared order. Runtime embeds and rehashes
these bodies; it never resolves a dictionary key, Markdown row, section label,
Langfuse profile prompt or product-readable restatement. A different byte,
missing row/body or second prose authority rejects activation.

### Exact AutoSelectionPolicyV1 body

```json
{"assessment_validation":{"malformed_result_behavior":"fail_type_attempt","required_assessment_profile_set":"all_policy_rows","source_segment_diversity_source":"AutoClaimEvidenceIndexV1","supporting_claim_id_policy":"must_exist_and_satisfy_row_predicates","trusted_role_source":"trusted_workspace_or_meeting_metadata_only"},"confidence":{"fallback":"low","high_min_lead_over_every_eligible":2,"high_min_score":10,"high_requires_fit_class":"strong","otherwise_selected":"medium"},"contraindication_code_sets":{"C0":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"CH":["conflicting_profile_signals","high_stakes_evidence_incomplete","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"CR":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"]},"eligibility":{"contraindication_behavior":"exclude","high_stakes_fit_classes":["strong"],"ordinary_fit_classes":["plausible","strong"],"score_bonus_cap_per_distinctive_dimension":2},"fallback_profile_key":"general_summary","fit_points":{"contraindicated":0,"plausible":4,"strong":8,"weak":0},"policy_version":1,"primary_selection":{"high_stakes_near_neighbor_margin":3,"insufficient_margin_behavior":"low_confidence_general_fallback","no_eligible_behavior":"low_confidence_general_fallback","ordinary_near_neighbor_margin":2,"require_unique_highest_score":true,"tie_behavior":"low_confidence_general_fallback"},"ranking_serialization":"primary_then_other_eligible_score_desc_utf8_then_ineligible_utf8_then_fallback","relation_type_domain":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"row_schema_version":1,"rows":[{"allowed_secondary_profile_keys":["training_qa","weekly_team"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["executive_board","training_qa","weekly_team"],"optional_support_predicates":[],"positive_reason_codes":["all_hands_announcement"],"profile_key":"all_hands","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":2,"values":["decision","event","fact","metric"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision","question"]}],[{"kind":"trusted_role_group","role_group_key":"all_hands_host"}],[{"kind":"authorized_participant_count","min":5}]],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":false,"contraindication_codes":[],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":0,"min_distinct_source_segment_ids":0,"near_neighbor_profile_keys":[],"optional_support_predicates":[],"positive_reason_codes":[],"profile_key":"auto","required_predicate_groups":[],"schema_version":1},{"allowed_secondary_profile_keys":["planning_decision","research_interview","retrospective"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["planning_decision","research_interview","retrospective"],"optional_support_predicates":[],"positive_reason_codes":["brainstorm_ideation"],"profile_key":"brainstorm_workshop","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":2,"values":["idea","option","proposal"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["question","requirement","topic"]}]],"schema_version":1},{"allowed_secondary_profile_keys":["customer_success","project_sync","sales_discovery_demo"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["customer_success","project_sync","sales_discovery_demo"],"optional_support_predicates":[],"positive_reason_codes":["client_status_update"],"profile_key":"client_status","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["blocker","fact","feedback","metric","requirement","risk"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision","question"]}],[{"kind":"trusted_role_group","role_group_key":"customer_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["client_status","project_sync","sales_discovery_demo"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["client_status","project_sync","sales_discovery_demo"],"optional_support_predicates":[],"positive_reason_codes":["customer_adoption_or_renewal"],"profile_key":"customer_success","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["blocker","fact","feedback","metric","requirement","risk"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision"]}],[{"kind":"trusted_role_group","role_group_key":"customer_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["all_hands","planning_decision"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","high_stakes_evidence_incomplete","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":true,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":3,"near_neighbor_profile_keys":["all_hands","formal_minutes","incident_postmortem","planning_decision"],"optional_support_predicates":[],"positive_reason_codes":["executive_strategy_or_resource"],"profile_key":"executive_board","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["fact","metric","requirement","risk"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["decision","resolution"]}],[{"kind":"relation_type_any","values":["constraint_on","option_for","rationale_for"]},{"kind":"relation_type_any","values":["motion_for","resolves","vote_on"]}],[{"kind":"trusted_role_group","role_group_key":"board"}]],"schema_version":1},{"allowed_secondary_profile_keys":["planning_decision"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","high_stakes_evidence_incomplete","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":true,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":3,"near_neighbor_profile_keys":["executive_board","incident_postmortem","planning_decision"],"optional_support_predicates":[],"positive_reason_codes":["formal_motion_vote_or_resolution"],"profile_key":"formal_minutes","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["motion"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["resolution","vote"]}],[{"kind":"relation_type_any","values":["motion_for"]}],[{"kind":"relation_type_any","values":["resolves"]},{"kind":"relation_type_any","values":["vote_on"]}],[{"kind":"trusted_role_group","role_group_key":"formal_governance"}]],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":false,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence"],"fallback_only":true,"high_stakes":false,"min_distinct_claim_ids":0,"min_distinct_source_segment_ids":0,"near_neighbor_profile_keys":[],"optional_support_predicates":[],"positive_reason_codes":["general_mixed_content"],"profile_key":"general_summary","required_predicate_groups":[],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["one_on_one","research_interview"],"optional_support_predicates":[],"positive_reason_codes":["hiring_interview_exchange"],"profile_key":"hiring_interview","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["interview_exchange"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["fact","feedback","question"]}],[{"kind":"relation_type_any","values":["interview_question"]}],[{"kind":"relation_type_any","values":["interview_answer"]}],[{"kind":"trusted_role_group","role_group_key":"hiring_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["project_sync","retrospective"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","high_stakes_evidence_incomplete","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":true,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":3,"near_neighbor_profile_keys":["executive_board","formal_minutes","retrospective"],"optional_support_predicates":[],"positive_reason_codes":["incident_impact_timeline_or_cause"],"profile_key":"incident_postmortem","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["event"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["blocker","correction","fact","hypothesis","risk"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision"]}],[{"kind":"relation_type_any","values":["causes","contributes_to","mitigates","precedes"]}],[{"kind":"trusted_role_group","role_group_key":"incident"}]],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":false,"contraindication_codes":[],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":0,"min_distinct_source_segment_ids":0,"near_neighbor_profile_keys":[],"optional_support_predicates":[],"positive_reason_codes":[],"profile_key":"meeting_minutes","required_predicate_groups":[],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["hiring_interview","research_interview"],"optional_support_predicates":[],"positive_reason_codes":["one_to_one_mutual_commitment"],"profile_key":"one_on_one","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":2,"values":["action","feedback","question","requirement"]}],[{"kind":"trusted_role_group","role_group_key":"one_to_one_pair"}],[{"kind":"authorized_participant_count","max":2,"min":2}]],"schema_version":1},{"allowed_secondary_profile_keys":[],"auto_eligible":false,"contraindication_codes":[],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":0,"min_distinct_source_segment_ids":0,"near_neighbor_profile_keys":[],"optional_support_predicates":[],"positive_reason_codes":[],"profile_key":"outline","required_predicate_groups":[],"schema_version":1},{"allowed_secondary_profile_keys":["brainstorm_workshop","project_sync"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["brainstorm_workshop","executive_board","formal_minutes","project_sync"],"optional_support_predicates":[],"positive_reason_codes":["explicit_planning_or_tradeoff"],"profile_key":"planning_decision","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["option","proposal","tradeoff"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["decision","question"]}],[{"kind":"relation_type_any","values":["benefit_of","constraint_on","cost_of","option_for","rationale_for"]}]],"schema_version":1},{"allowed_secondary_profile_keys":["client_status","customer_success","planning_decision","weekly_team"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["client_status","customer_success","planning_decision","weekly_team"],"optional_support_predicates":[{"kind":"relation_type_any","values":["blocks","depends_on"]}],"positive_reason_codes":["project_movement"],"profile_key":"project_sync","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","blocker","decision","dependency","event","metric","requirement"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","blocker","dependency","event","metric"]}]],"schema_version":1},{"allowed_secondary_profile_keys":["brainstorm_workshop","sales_discovery_demo"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["brainstorm_workshop","hiring_interview","one_on_one","sales_discovery_demo","training_qa"],"optional_support_predicates":[],"positive_reason_codes":["research_interview_exchange"],"profile_key":"research_interview","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["interview_exchange"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["fact","feedback","hypothesis","requirement"]}],[{"kind":"relation_type_any","values":["interview_question"]}],[{"kind":"relation_type_any","values":["interview_answer"]}],[{"kind":"trusted_role_group","role_group_key":"research_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["brainstorm_workshop","weekly_team"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["brainstorm_workshop","incident_postmortem","weekly_team"],"optional_support_predicates":[{"kind":"relation_type_any","values":["cancels","supersedes"]}],"positive_reason_codes":["retrospective_reflection"],"profile_key":"retrospective","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["correction","feedback","learning"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision","proposal"]}]],"schema_version":1},{"allowed_secondary_profile_keys":["client_status","customer_success","research_interview"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["client_status","customer_success","research_interview"],"optional_support_predicates":[],"positive_reason_codes":["sales_need_or_criterion"],"profile_key":"sales_discovery_demo","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["fact","feedback","option","question","requirement","tradeoff"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","decision","question"]}],[{"kind":"trusted_role_group","role_group_key":"customer_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["all_hands"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal","untrusted_role_only"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":2,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["all_hands","research_interview"],"optional_support_predicates":[],"positive_reason_codes":["training_qa"],"profile_key":"training_qa","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["learning","topic"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["fact","question","requirement"]}],[{"kind":"relation_type_any","values":["answers"]},{"kind":"trusted_role_group","role_group_key":"training_pair"}]],"schema_version":1},{"allowed_secondary_profile_keys":["all_hands","project_sync","retrospective"],"auto_eligible":true,"contraindication_codes":["conflicting_profile_signals","insufficient_distinctive_evidence","missing_required_signal"],"fallback_only":false,"high_stakes":false,"min_distinct_claim_ids":3,"min_distinct_source_segment_ids":2,"near_neighbor_profile_keys":["all_hands","project_sync","retrospective"],"optional_support_predicates":[],"positive_reason_codes":["weekly_team_cadence"],"profile_key":"weekly_team","required_predicate_groups":[[{"kind":"claim_kind_any","min_distinct_claims":2,"values":["action","blocker","event","fact","metric","topic"]}],[{"kind":"claim_kind_any","min_distinct_claims":1,"values":["action","blocker","decision"]}]],"schema_version":1}],"schema_version":1,"score_formula":{"base_points_source":"fit_points","below_row_minimum_behavior":"ineligible_before_scoring","bonus_cap_source":"eligibility.score_bonus_cap_per_distinctive_dimension","distinct_claim_bonus_operator":"bounded_excess_above_row_minimum","distinct_source_segment_bonus_operator":"bounded_excess_above_row_minimum"},"secondary_selection":{"allowed_fit_classes":["plausible","strong"],"effect":"emphasis_only","high_stakes_allowed":false,"min_novel_supporting_claim_ids":1,"require_unique_highest_score":true,"score_source":"score_formula","tie_behavior":"none"},"trusted_role_groups":[{"distinct_participants_required":false,"required_alternative_role_sets":[["all_hands_host","executive"]],"role_group_key":"all_hands_host"},{"distinct_participants_required":false,"required_alternative_role_sets":[["board_chair","board_member","executive"]],"role_group_key":"board"},{"distinct_participants_required":true,"required_alternative_role_sets":[["account_owner","customer_success_manager","project_owner","seller"],["client","customer","prospect"]],"role_group_key":"customer_pair"},{"distinct_participants_required":false,"required_alternative_role_sets":[["chair","secretary","voting_member"]],"role_group_key":"formal_governance"},{"distinct_participants_required":true,"required_alternative_role_sets":[["candidate"],["interviewer"]],"role_group_key":"hiring_pair"},{"distinct_participants_required":false,"required_alternative_role_sets":[["incident_commander","incident_responder"]],"role_group_key":"incident"},{"distinct_participants_required":true,"required_alternative_role_sets":[["direct_report"],["manager","team_lead"]],"role_group_key":"one_to_one_pair"},{"distinct_participants_required":false,"required_alternative_role_sets":[["project_manager","project_member","project_owner"]],"role_group_key":"project"},{"distinct_participants_required":true,"required_alternative_role_sets":[["research_participant"],["researcher"]],"role_group_key":"research_pair"},{"distinct_participants_required":false,"required_alternative_role_sets":[["manager","team_lead","team_member"]],"role_group_key":"team"},{"distinct_participants_required":true,"required_alternative_role_sets":[["attendee","learner"],["instructor","trainer"]],"role_group_key":"training_pair"}]}
```

```text
auto_selection_policy_hash =
  SHA-256("GRAF-AUTO-SELECTION-POLICY\0v1" ||
    uint64be(auto_selection_policy_body_byte_length) ||
    canonical_json(AutoSelectionPolicyV1))
```

The adjacent `auto_selection_policy_hash` is
`99ca480ffa81e6085037a822bb29cc3a3c6533b9d57f1729fa6a87e4c94bdcb5`. The row ledger below is a
derived conformance vector, not a second policy authority:

| Profile key | `auto_policy_row_hash` |
|---|---|
| `all_hands` | `664575f82445c058f2d34b8fe4c908324ad591a586b02b99e2d5d5927a936bf0` |
| `auto` | `5b2d75f821e8e98a7dcb9b730936c343bd162c80c4b04bc415da259fc8e1e2bd` |
| `brainstorm_workshop` | `edeef141e6478f1baeb8c2fabc95443b92359fa7c7a7bac9a07880f0237f2cce` |
| `client_status` | `56674e3e4573e6eab33317523146324cd72d1fc2420d25c2c723d4dcc70c0606` |
| `customer_success` | `c21e068fd0c6114a5670496624aebde24c3a5a6cba2632680600973fe53ef08f` |
| `executive_board` | `f6b227c6d72c32738002160d73d2075cf5653a4487fed8a02d3c7caa3dde5c79` |
| `formal_minutes` | `1307da9e55eb737f587ed8505dd205230ba44fa4ebf27952b7af8880b1878ac5` |
| `general_summary` | `5e6c81d1009b89030cfd2680e20c5c95d20a5c1ebed9c4e52b231a36ccb3f497` |
| `hiring_interview` | `9f755ca514aa740474bc78b9fb32c187043976755cf6b41f6195d4dce1b3d92e` |
| `incident_postmortem` | `fd3641af0451a0cc28c22f3119fcb1ae29abe6f029879809f5269a85f0126772` |
| `meeting_minutes` | `35cd68da86ecec4497f6ffc0642149f23342d90b999b9bf3ac84123832b698ef` |
| `one_on_one` | `7e6432c0e5dd82d5c2b2fb8c61b69f677a616662cfca8bd749169d7eff4e2dc7` |
| `outline` | `001dd8b0a3da0ae8d9294fa4d11d2569cf6743d803913a6c49ea34e5e41ba7f7` |
| `planning_decision` | `f2793630e0e74ffab5380b91f0696242aa23dbde4c1ee467be9f1cee72661c72` |
| `project_sync` | `2cc11db3adbbbe692f116b32d1a0a8fa055fac9be6cd24907550735d0756882e` |
| `research_interview` | `9d9d17f2d5faaab47d8b7178fc330aa4413c31d92cc66a92c483ca537f4415cd` |
| `retrospective` | `9d342f61b61f4d20d6af168ab0dbeb17d5674a7cf87fcc6f9ca1c43ea2fc489c` |
| `sales_discovery_demo` | `287a334bc8e24ff0b4570814b36fefd038a325bafeb9405e093530e3d341f309` |
| `training_qa` | `285387b1eda0a36d152e7478470a044a5fc40018e3a97b3c21ecb7080b10e579` |
| `weekly_team` | `43e06b0c8009ac250ef6ec045ab4dafa270609f65323823d04fe9670c4a741b8` |

Every embedded row is a closed `AutoSelectionPolicyRowV1`. The
policy body owns the complete relation domain, trusted-role groups, reason
codes, predicate groups, row-specific D/S minima, scoring, confidence,
fallback, ranking and directional secondary eligibility. All three high-stakes
rows have exact minima 3/3. No prose algorithm or runtime expression parser may
change the canonical body.

### Exact ProfileContractCatalogV1 body

```json
{"catalog_version":3,"profile_bindings":[{"profile_contract":{"allowed_kind_set":["action","decision","event","fact","feedback","metric","question","resolution","risk","topic"],"allowed_relation_set":["answers","blocks","cancels","depends_on","precedes","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"664575f82445c058f2d34b8fe4c908324ad591a586b02b99e2d5d5927a936bf0","budget_policy_key":"B1","default_detail_level":"concise","empty_state_section_keys":["actions_followups"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"all_hands","profile_semantic_rule":"Present supported headline announcements, authorized business or product updates, decisions, employee questions and follow-ups for the broad audience; never widen confidential content or invent company conclusions.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*","event:*","fact:*","metric:*","question:*"],"required_relation_types":["answers"],"required_trusted_role_groups":["all_hands_host"],"risk_class":"ordinary","safety_caveat_codes":["no_audience_widening"],"schema_version":1,"section_contracts":[{"section_key":"headline_announcements","semantic_rule":"Include the highest-impact explicit announcements in concise form, without extrapolating implications."},{"section_key":"business_product_team_updates","semantic_rule":"Include source-supported business, product and team updates appropriate to the authorized audience; omit speculation and confidential widening."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"employee_q_and_a","semantic_rule":"Pair employee questions with only source-supported answers and preserve unanswered or partially answered status."},{"section_key":"actions_followups","semantic_rule":"Include only explicit actions or promised follow-ups, preserving owner, due condition and state exactly when evidenced."}],"section_order":["headline_announcements","business_product_team_updates","decisions","employee_q_and_a","actions_followups"],"sensitive_class_allowlist":[]},"profile_contract_hash":"002c972d51e6bfa233c98069533c144fc1426918506eec39cc617c84d912f876","profile_key":"all_hands","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","feedback","hypothesis","idea","interview_exchange","learning","metric","motion","option","proposal","question","requirement","resolution","risk","topic","tradeoff","vote"],"allowed_relation_set":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":[],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-ACT-001","MP-PRF-001","MP-PRO-001"],"profile_key":"auto","profile_semantic_rule":"Render the stable Auto shell with Action Items first and Key Points second; use the resolved intent composite only to select, rank and constrain supported content, never to change canonical truth or visible section names.","profile_version":3,"provenance":"built_in","required_kind_state_pairs":[],"required_relation_types":[],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":[],"schema_version":1,"section_contracts":[{"section_key":"action_items","semantic_rule":"Include only explicit accepted assignments, personal commitments or accepted addressed requests; preserve source-backed status, owner and due condition when evidenced, and never invent work."},{"section_key":"key_points","semantic_rule":"Include the most material remaining source-supported outcomes selected under the resolved intent composite, preserving exact decision and proposal states, risks, questions and corrections without duplicating Action Items."}],"section_order":["action_items","key_points"],"sensitive_class_allowlist":[]},"profile_contract_hash":"b37da94da0ebe54af4025864fd24809942c3dcdaba51d3981398bb50a9b672c9","profile_key":"auto","profile_version":3},{"profile_contract":{"allowed_kind_set":["action","decision","idea","learning","option","proposal","question","requirement","risk","topic","tradeoff"],"allowed_relation_set":["cancels","depends_on","option_for","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"edeef141e6478f1baeb8c2fabc95443b92359fa7c7a7bac9a07880f0237f2cce","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":[],"forbidden_inference_clause_ids":["MP-PRF-BRN-ACT-001"],"master_clause_ids":["MP-PRF-BRN-ACT-001","MP-PRO-001"],"profile_key":"brainstorm_workshop","profile_semantic_rule":"Preserve the problem, idea clusters, stated evaluation criteria, selected experiments and exact deferred or rejected dispositions; never turn an idea into an action without separate acceptance evidence.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*","idea:accepted","idea:deferred","idea:rejected","idea:superseded","idea:withdrawn"],"required_relation_types":["option_for","rationale_for"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["no_idea_to_action"],"schema_version":1,"section_contracts":[{"section_key":"problem_statement","semantic_rule":"Include the problem or opportunity explicitly framed for the workshop; preserve competing framings when unresolved."},{"section_key":"idea_clusters","semantic_rule":"Group semantically related ideas without changing their wording, disposition or authorship and without declaring a preferred idea."},{"section_key":"evaluation_criteria","semantic_rule":"Include criteria explicitly proposed or accepted for evaluating ideas; do not create scoring, weights or a winner."},{"section_key":"selected_experiments","semantic_rule":"Include only experiments explicitly selected or accepted, with stated hypothesis, owner and success condition when evidenced."},{"section_key":"deferred_rejected_ideas","semantic_rule":"Include ideas explicitly deferred, rejected, withdrawn or superseded and only the reasons actually stated."}],"section_order":["problem_statement","idea_clusters","evaluation_criteria","selected_experiments","deferred_rejected_ideas"],"sensitive_class_allowlist":[]},"profile_contract_hash":"da325e2d63068e3ffc59eebbc9132c913138574ca2454f551e1ff1e510b79493","profile_key":"brainstorm_workshop","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","decision","dependency","event","fact","feedback","metric","question","requirement","risk","topic"],"allowed_relation_set":["blocks","depends_on","rationale_for","resolves"],"auto_policy_row_hash":"56674e3e4573e6eab33317523146324cd72d1fc2420d25c2c723d4dcc70c0606","budget_policy_key":"B1","default_detail_level":"concise","empty_state_section_keys":["commitments","next_checkpoint"],"forbidden_inference_clause_ids":["MP-PRF-SAL-EXP-001"],"master_clause_ids":["MP-PRF-SAL-EXP-001","MP-PRO-001"],"profile_key":"client_status","profile_semantic_rule":"Produce an authorized client-safe account of shared outcome, evidenced progress, requirements or issues, decisions, commitments, risks and next checkpoint; exclude internal-only concerns and inferred client sentiment or commitment.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","blocker:*","decision:*","feedback:*","requirement:*","risk:*"],"required_relation_types":["blocks","depends_on"],"required_trusted_role_groups":["customer_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["no_audience_widening","sales_explicit_only"],"schema_version":1,"section_contracts":[{"section_key":"overview","semantic_rule":"Present the most important source-supported outcome, decisions and unresolved constraints for this profile in a compact scan."},{"section_key":"delivered_progress","semantic_rule":"Include delivered work and progress explicitly evidenced; never invent completion percentage, schedule status or acceptance."},{"section_key":"requirements_issues","semantic_rule":"Include explicit customer requirements and reported issues, separating accepted obligations from requests and observations."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"commitments","semantic_rule":"Include only explicit commitments by either side and preserve which side, owner, condition and due date when evidenced."},{"section_key":"risks","semantic_rule":"Include explicit or evidence-supported risks, preserving hypothesis and uncertainty; do not invent probability, impact or mitigation."},{"section_key":"next_checkpoint","semantic_rule":"Include the next checkpoint only when date or trigger, purpose and required preparation are source-supported; unknown fields remain unknown."}],"section_order":["overview","delivered_progress","requirements_issues","decisions","commitments","risks","next_checkpoint"],"sensitive_class_allowlist":[]},"profile_contract_hash":"1b0208cabf1cf43ad6595aa920a356e8d1e54551d0f0f0acd88f6b8a7a8be585","profile_key":"client_status","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","blocker","decision","dependency","event","fact","feedback","metric","question","requirement","risk","topic"],"allowed_relation_set":["blocks","depends_on","rationale_for","resolves"],"auto_policy_row_hash":"c21e068fd0c6114a5670496624aebde24c3a5a6cba2632680600973fe53ef08f","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["commitments","next_checkpoint"],"forbidden_inference_clause_ids":["MP-PRF-SAL-EXP-001"],"master_clause_ids":["MP-PRF-SAL-EXP-001","MP-PRO-001"],"profile_key":"customer_success","profile_semantic_rule":"Track source-supported customer goals, adoption evidence, risks, product requests, commitments and next checkpoint; never infer health score, renewal likelihood or an unstated product promise.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","blocker:*","decision:*","feedback:*","metric:*","requirement:*","risk:*"],"required_relation_types":["blocks","depends_on"],"required_trusted_role_groups":["customer_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["no_audience_widening","sales_explicit_only"],"schema_version":1,"section_contracts":[{"section_key":"customer_goal_state","semantic_rule":"Include the customer's stated goal and source-supported current state; do not synthesize a health or success judgement."},{"section_key":"adoption_evidence","semantic_rule":"Include source-supported product usage, adoption or outcome evidence; never infer a health score, satisfaction or renewal likelihood."},{"section_key":"risks_blockers","semantic_rule":"Separate risks from blockers and preserve each item's typed state and relation; never collapse a concern into a blocker."},{"section_key":"product_requests","semantic_rule":"Include explicit product requests and their disposition; never convert a request into a promise or roadmap commitment."},{"section_key":"commitments","semantic_rule":"Include only explicit commitments by either side and preserve which side, owner, condition and due date when evidenced."},{"section_key":"next_checkpoint","semantic_rule":"Include the next checkpoint only when date or trigger, purpose and required preparation are source-supported; unknown fields remain unknown."}],"section_order":["customer_goal_state","adoption_evidence","risks_blockers","product_requests","commitments","next_checkpoint"],"sensitive_class_allowlist":[]},"profile_contract_hash":"03483d546246d552783b30a985c709b3c96aa2dccb687392f749955b9cdc3e5b","profile_key":"customer_success","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","decision","fact","metric","motion","option","question","requirement","resolution","risk","topic","tradeoff","vote"],"allowed_relation_set":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"auto_policy_row_hash":"f6b227c6d72c32738002160d73d2075cf5653a4487fed8a02d3c7caa3dde5c79","budget_policy_key":"B1","default_detail_level":"concise","empty_state_section_keys":["leadership_actions"],"forbidden_inference_clause_ids":["MP-PRF-FRM-LGL-001"],"master_clause_ids":["MP-PRF-FRM-LGL-001","MP-PRO-001"],"profile_key":"executive_board","profile_semantic_rule":"Surface the smallest source-faithful executive brief, strategic or resource facts, exact resolutions and decision states, material risks, dissent and leadership actions; never invent approval, budget, authority, vote or legal conclusion.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["decision:*","metric:*","motion:*","resolution:*","risk:*","vote:*"],"required_relation_types":["motion_for","rationale_for","resolves","vote_on"],"required_trusted_role_groups":["board"],"risk_class":"external_sensitive","safety_caveat_codes":["no_unproved_formal_or_legal_claim"],"schema_version":1,"section_contracts":[{"section_key":"executive_brief","semantic_rule":"Present the smallest source-faithful set of material outcomes, decisions and risks needed by leadership; add no strategic conclusion."},{"section_key":"strategic_financial_resource_facts","semantic_rule":"Include exact source-supported strategic, financial and resource facts; preserve units and exclude inferred forecasts or conclusions."},{"section_key":"resolutions_decisions","semantic_rule":"Include source-supported resolutions and decisions while preserving formal versus ordinary status and requires-approval state."},{"section_key":"material_risks","semantic_rule":"Include source-supported risks material to leadership, preserving likelihood or impact only when explicitly stated."},{"section_key":"dissent","semantic_rule":"Include material, explicitly expressed dissent and its stated basis without inferring motives or resolving it by majority."},{"section_key":"leadership_actions","semantic_rule":"Include only explicit actions requiring leadership ownership or approval, preserving preliminary and requires-approval states."}],"section_order":["executive_brief","strategic_financial_resource_facts","resolutions_decisions","material_risks","dissent","leadership_actions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"401b0f98ead495feb8aea60fc678e8ead3f6fa096bcc334374986e8b08945acc","profile_key":"executive_board","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","decision","fact","motion","question","resolution","topic","vote"],"allowed_relation_set":["cancels","motion_for","resolves","supersedes","vote_on"],"auto_policy_row_hash":"1307da9e55eb737f587ed8505dd205230ba44fa4ebf27952b7af8880b1878ac5","budget_policy_key":"B1","default_detail_level":"detailed","empty_state_section_keys":["actions","motions","resolutions"],"forbidden_inference_clause_ids":["MP-PRF-FRM-LGL-001"],"master_clause_ids":["MP-PRF-FRM-LGL-001","MP-PRO-001"],"profile_key":"formal_minutes","profile_semantic_rule":"Create a source-faithful draft protocol containing only evidenced meeting facts, agenda, quorum, motions, votes, dissent, resolutions and actions; mark gaps for human review and never claim legal compliance or invent formal facts.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","motion:*","resolution:*","vote:*"],"required_relation_types":["motion_for","resolves","vote_on"],"required_trusted_role_groups":["formal_governance"],"risk_class":"regulated_record","safety_caveat_codes":["no_unproved_formal_or_legal_claim"],"schema_version":1,"section_contracts":[{"section_key":"meeting_facts","semantic_rule":"Include date, time, place, participants and purpose only when source-supported; no attendance, authority or legal status is inferred."},{"section_key":"agenda","semantic_rule":"Include only agenda items explicitly stated in the source and preserve their source order when known."},{"section_key":"quorum","semantic_rule":"Include quorum only when explicitly established by trusted formal evidence; otherwise record a verification gap, never a conclusion."},{"section_key":"motions","semantic_rule":"Include only formally stated motions with exact wording, proposer and state when evidenced; never infer a motion from ordinary discussion."},{"section_key":"votes_abstentions_dissent","semantic_rule":"Include only evidenced votes, abstentions and dissent with exact counts or participants when known; never infer unanimity."},{"section_key":"resolutions","semantic_rule":"Include only formally evidenced resolutions with exact state and relation to motions or votes; ordinary decisions are not upgraded."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."}],"section_order":["meeting_facts","agenda","quorum","motions","votes_abstentions_dissent","resolutions","actions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"d568f8362cb6d52dbe23ff4081d6b43228cd9cfd0d634bcc3c17505fce89fd29","profile_key":"formal_minutes","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","feedback","hypothesis","idea","interview_exchange","learning","metric","motion","option","proposal","question","requirement","resolution","risk","topic","tradeoff","vote"],"allowed_relation_set":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"auto_policy_row_hash":"5e6c81d1009b89030cfd2680e20c5c95d20a5c1ebed9c4e52b231a36ccb3f497","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["actions","decisions","open_questions"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"general_summary","profile_semantic_rule":"Present the supported meeting outcome for quick internal understanding, then decisions, actions, risks or blockers, open questions and compact themes; exclude chronology, filler and generic recommendations.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":[],"required_relation_types":[],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":[],"schema_version":1,"section_contracts":[{"section_key":"overview","semantic_rule":"Present the most important source-supported outcome, decisions and unresolved constraints for this profile in a compact scan."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."},{"section_key":"risks_blockers","semantic_rule":"Separate risks from blockers and preserve each item's typed state and relation; never collapse a concern into a blocker."},{"section_key":"open_questions","semantic_rule":"Include materially unanswered questions or decisions still required; exclude questions answered or superseded later."},{"section_key":"topic_summary","semantic_rule":"Summarize supported topic outcomes rather than turns, preserving material disagreement, correction and open state."}],"section_order":["overview","decisions","actions","risks_blockers","open_questions","topic_summary"],"sensitive_class_allowlist":[]},"profile_contract_hash":"8696fda26835f6c585203562d93544fd1c93627f6e499ae7c314e6425e0731ca","profile_key":"general_summary","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","fact","feedback","hypothesis","interview_exchange","question","requirement","topic"],"allowed_relation_set":["answers","interview_answer","interview_question","rationale_for"],"auto_policy_row_hash":"9f755ca514aa740474bc78b9fb32c187043976755cf6b41f6195d4dce1b3d92e","budget_policy_key":"B1","default_detail_level":"detailed","empty_state_section_keys":[],"forbidden_inference_clause_ids":["MP-PRF-INT-DIA-001","MP-PRF-INT-HIR-001"],"master_clause_ids":["MP-PRF-INT-DIA-001","MP-PRF-INT-HIR-001","MP-PRO-001"],"profile_key":"hiring_interview","profile_semantic_rule":"Preserve evidence-backed questions, answers, examples, explicit interviewer concerns and information gaps for an authorized hiring review; never infer sensitive traits, personality, a score or a hiring recommendation.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["feedback:*","interview_exchange:*","question:*","requirement:*"],"required_relation_types":["interview_answer","interview_question"],"required_trusted_role_groups":["hiring_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["no_hiring_recommendation","no_personality_or_sensitive_trait_inference"],"schema_version":1,"section_contracts":[{"section_key":"question_competency","semantic_rule":"Pair each interview question with the explicitly targeted competency only when that competency is supplied by the authorized rubric or source."},{"section_key":"answer_examples","semantic_rule":"Pair each interview answer with only the concrete examples actually supplied by the interviewee."},{"section_key":"evidence","semantic_rule":"Include the factual evidence and examples explicitly supplied for the relevant claim; do not add interpretation or recommendation."},{"section_key":"explicit_concerns","semantic_rule":"Include only concerns explicitly expressed by authorized interview participants and preserve uncertainty; add no score or recommendation."},{"section_key":"information_gaps","semantic_rule":"Include information required for the profile that is absent, contradictory or unreliable; never fill the gap with inference."}],"section_order":["question_competency","answer_examples","evidence","explicit_concerns","information_gaps"],"sensitive_class_allowlist":[]},"profile_contract_hash":"1e35f627c4b9cc903039b64d01d74f93b9a9779cdb18fb8a1f83e2fd5c5e528e","profile_key":"hiring_interview","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","hypothesis","metric","question","risk","topic"],"allowed_relation_set":["blocks","cancels","causes","contributes_to","depends_on","mitigates","precedes","resolves","supersedes"],"auto_policy_row_hash":"fd3641af0451a0cc28c22f3119fcb1ae29abe6f029879809f5269a85f0126772","budget_policy_key":"B1","default_detail_level":"detailed","empty_state_section_keys":["corrective_preventive_actions","root_cause"],"forbidden_inference_clause_ids":["MP-PRF-INC-BLM-001","MP-PRF-INC-RCA-001"],"master_clause_ids":["MP-PRF-INC-BLM-001","MP-PRF-INC-RCA-001","MP-PRO-001"],"profile_key":"incident_postmortem","profile_semantic_rule":"Preserve supported impact, status, timeline, detection, mitigation, recovery, confirmed cause or explicit unknown, contributing factors and accepted corrective actions; use blameless language and never promote a hypothesis to root cause.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","blocker:*","correction:*","decision:*","event:*","hypothesis:*","risk:*"],"required_relation_types":["causes","contributes_to","mitigates","precedes"],"required_trusted_role_groups":["incident"],"risk_class":"external_sensitive","safety_caveat_codes":["blameless_language","root_cause_requires_confirmed"],"schema_version":1,"section_contracts":[{"section_key":"impact_status","semantic_rule":"Include source-supported incident impact and current status, separating confirmed scope from estimates and unknowns."},{"section_key":"timeline","semantic_rule":"Include source-supported incident events in evidenced order, preserving unknown, relative or conflicting timestamps."},{"section_key":"detection","semantic_rule":"Include how and when an incident was detected only when source-supported; preserve unknown or conflicting timestamps."},{"section_key":"mitigation_recovery","semantic_rule":"Include mitigation and recovery steps actually taken or accepted, preserving sequence, state and remaining uncertainty."},{"section_key":"root_cause","semantic_rule":"Include a root cause only when confirmed by the source and relations; otherwise state that it is unknown and keep hypotheses separate."},{"section_key":"contributing_factors","semantic_rule":"Include only source-supported factors that contributed to an incident; keep hypotheses typed and separate from confirmed causes."},{"section_key":"corrective_preventive_actions","semantic_rule":"Include accepted corrective or preventive actions with exact state, owner and due condition; exclude generic recommendations."},{"section_key":"unresolved_risk","semantic_rule":"Include incident risks that remain explicitly unresolved after mitigation and recovery, preserving owner or deadline only when evidenced."}],"section_order":["impact_status","timeline","detection","mitigation_recovery","root_cause","contributing_factors","corrective_preventive_actions","unresolved_risk"],"sensitive_class_allowlist":[]},"profile_contract_hash":"0d6294122077ffeb4524d7638f377de592fcce571f89abd31b1439ab5c3f31e4","profile_key":"incident_postmortem","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","feedback","hypothesis","idea","interview_exchange","learning","metric","motion","option","proposal","question","requirement","resolution","risk","topic","tradeoff","vote"],"allowed_relation_set":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["actions","decisions","open_questions"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"meeting_minutes","profile_semantic_rule":"Produce a practical source-faithful internal record of purpose, topics, exact decision states, accepted actions, open questions and verification gaps; never invent quorum, votes, legal status or formal resolutions.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*"],"required_relation_types":["cancels","depends_on","rationale_for","supersedes"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"purpose_context","semantic_rule":"Include the meeting purpose and context only when stated or trusted in metadata, clearly separating unknowns."},{"section_key":"topics","semantic_rule":"Include the material topics actually discussed with their outcome or unresolved state, not a transcript chronology."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."},{"section_key":"open_questions","semantic_rule":"Include materially unanswered questions or decisions still required; exclude questions answered or superseded later."},{"section_key":"verification_gaps","semantic_rule":"Include claims or formal fields that require human verification because evidence is missing, conflicting or unreadable."}],"section_order":["purpose_context","topics","decisions","actions","open_questions","verification_gaps"],"sensitive_class_allowlist":[]},"profile_contract_hash":"be8b85ef1eeeaf0c5e54388cad095b00dc37ac25e2962ec8215866c397beca1f","profile_key":"meeting_minutes","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","decision","fact","feedback","question","requirement","risk","topic"],"allowed_relation_set":["blocks","cancels","depends_on","precedes","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"7e6432c0e5dd82d5c2b2fb8c61b69f677a616662cfca8bd749169d7eff4e2dc7","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["commitments"],"forbidden_inference_clause_ids":["MP-PRF-ONE-PRIV-001"],"master_clause_ids":["MP-PRF-ONE-PRIV-001","MP-PRO-001"],"profile_key":"one_on_one","profile_semantic_rule":"Preserve source-supported themes, mutual feedback, support requests, commitments and development questions for the authorized pair; minimize incidental personal detail and never diagnose personality, psychology or performance.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","feedback:*","question:*","requirement:*"],"required_relation_types":["depends_on"],"required_trusted_role_groups":["one_to_one_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["minimize_personal_details"],"schema_version":1,"section_contracts":[{"section_key":"key_themes","semantic_rule":"Include the materially recurring themes of the conversation without psychological interpretation or unnecessary sensitive detail."},{"section_key":"mutual_feedback","semantic_rule":"Attribute explicit feedback to the correct side, preserve whether it was acknowledged or accepted, and omit diagnosis or inferred intent."},{"section_key":"support_requests","semantic_rule":"Include explicit requests for support and their response state; do not infer need or commitment from discussion alone."},{"section_key":"commitments","semantic_rule":"Include only explicit commitments by either side and preserve which side, owner, condition and due date when evidenced."},{"section_key":"development_goals_open_questions","semantic_rule":"Include development goals explicitly requested or agreed and the open questions attached to them; exclude personality or performance diagnosis."}],"section_order":["key_themes","mutual_feedback","support_requests","commitments","development_goals_open_questions"],"sensitive_class_allowlist":["health_wellbeing","performance_hr","personal_life"]},"profile_contract_hash":"85a6da2d7f28bfa4864298c267df9197b4ce1f1f50a508fb1f147e5e9df5b4a9","profile_key":"one_on_one","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","feedback","hypothesis","idea","interview_exchange","learning","metric","motion","option","proposal","question","requirement","resolution","risk","topic","tradeoff","vote"],"allowed_relation_set":["answers","benefit_of","blocks","cancels","causes","constraint_on","contributes_to","cost_of","depends_on","interview_answer","interview_question","mitigates","motion_for","option_for","precedes","rationale_for","resolves","supersedes","vote_on"],"budget_policy_key":"B1","default_detail_level":"concise","empty_state_section_keys":[],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"outline","profile_semantic_rule":"Organize supported content as a thematic hierarchy with a concise takeaway per theme and linked decisions or actions; exclude line-by-line chronology and unsupported hierarchy.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":[],"required_relation_types":[],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":[],"schema_version":1,"section_contracts":[{"section_key":"outline","semantic_rule":"Organize the supported discussion into a concise hierarchy of themes and subthemes, with no line-by-line chronology or invented taxonomy."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."}],"section_order":["outline","decisions","actions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"29f2492841a98bce9eaba0154235fcb759fa64aef21dbf6a946606868dbdf2bd","profile_key":"outline","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","correction","decision","dependency","fact","hypothesis","metric","option","proposal","question","requirement","risk","topic","tradeoff"],"allowed_relation_set":["benefit_of","cancels","constraint_on","cost_of","depends_on","option_for","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"f2793630e0e74ffab5380b91f0696242aa23dbde4c1ee467be9f1cee72661c72","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["decisions","validations_actions"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"planning_decision","profile_semantic_rule":"Preserve the stated goal, constraints, options, trade-offs and exact decision dispositions, followed by accepted validations, actions and open questions; never manufacture a winner or rationale.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*","option:accepted","option:deferred","option:rejected","option:superseded","option:withdrawn","tradeoff:*"],"required_relation_types":["benefit_of","constraint_on","cost_of","option_for","rationale_for"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"goal_constraints","semantic_rule":"Include the stated goal and explicit constraints, assumptions and success conditions; unknown constraints remain absent."},{"section_key":"options","semantic_rule":"Include options actually considered with exact disposition; do not create alternatives or select a winner."},{"section_key":"tradeoffs","semantic_rule":"Include explicitly discussed benefits, costs and constraints linked to options; do not invent evaluation criteria or preference."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"validations_actions","semantic_rule":"Include accepted validations and actions required before a decision can progress; exclude generic recommendations."},{"section_key":"open_questions","semantic_rule":"Include materially unanswered questions or decisions still required; exclude questions answered or superseded later."}],"section_order":["goal_constraints","options","tradeoffs","decisions","validations_actions","open_questions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"c6b5b3793aa69d8c2b1ce765d9062a85b3606c45fbc812bdf5c836d4ebbf90e9","profile_key":"planning_decision","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","metric","question","requirement","risk","topic"],"allowed_relation_set":["blocks","cancels","depends_on","precedes","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"2cc11db3adbbbe692f116b32d1a0a8fa055fac9be6cd24907550735d0756882e","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["actions","blockers_dependencies"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"project_sync","profile_semantic_rule":"Surface evidenced progress, scope or timeline changes, decisions, actions, blockers, dependencies and open questions; never infer project health, completion percentage or schedule status.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","blocker:*","decision:*","dependency:*"],"required_relation_types":["blocks","depends_on"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"overview","semantic_rule":"Present the most important source-supported outcome, decisions and unresolved constraints for this profile in a compact scan."},{"section_key":"progress","semantic_rule":"Include source-supported movement since the relevant work baseline; do not infer project health, percentage or schedule."},{"section_key":"scope_timeline_changes","semantic_rule":"Include only explicitly accepted or observed scope and timeline changes; proposals and estimates retain their state."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."},{"section_key":"blockers_dependencies","semantic_rule":"Include explicit blockers and dependencies with their typed relations; do not invent dependency direction or impact."},{"section_key":"open_questions","semantic_rule":"Include materially unanswered questions or decisions still required; exclude questions answered or superseded later."}],"section_order":["overview","progress","scope_timeline_changes","decisions","actions","blockers_dependencies","open_questions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"ca9ca9e0e58217924b27c0e584da076d88ebd554d54c57c36a98819ff2dfe8e3","profile_key":"project_sync","profile_version":2},{"profile_contract":{"allowed_kind_set":["action","fact","feedback","hypothesis","interview_exchange","question","requirement","topic"],"allowed_relation_set":["answers","interview_answer","interview_question","rationale_for"],"auto_policy_row_hash":"9d9d17f2d5faaab47d8b7178fc330aa4413c31d92cc66a92c483ca537f4415cd","budget_policy_key":"B1","default_detail_level":"detailed","empty_state_section_keys":[],"forbidden_inference_clause_ids":["MP-PRF-INT-DIA-001"],"master_clause_ids":["MP-PRF-INT-DIA-001","MP-PRO-001"],"profile_key":"research_interview","profile_semantic_rule":"Separate supported observations, needs, workflows, representative quotes and contradictions from hypotheses explicitly stated in the source; never generalize one participant to a population.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["feedback:*","hypothesis:*","interview_exchange:*","requirement:*"],"required_relation_types":["interview_answer","interview_question"],"required_trusted_role_groups":["research_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["no_personality_or_sensitive_trait_inference"],"schema_version":1,"section_contracts":[{"section_key":"research_questions","semantic_rule":"Include the research questions explicitly stated for the session; do not invent a study objective."},{"section_key":"observations","semantic_rule":"Include source-supported observed behavior or statements separately from researcher interpretation and hypotheses."},{"section_key":"needs_pains","semantic_rule":"Include needs and pains explicitly described or evidenced by participant behavior; do not infer market prevalence or severity."},{"section_key":"workflows","semantic_rule":"Include observed or described user workflows in their source-supported sequence, separating current behavior from desired behavior."},{"section_key":"representative_quotes","semantic_rule":"Include only exact, evidence-linked quotes that materially represent a finding; do not paraphrase inside quotation marks."},{"section_key":"contradictions_gaps","semantic_rule":"Include material contradictions, incomplete evidence and unresolved information gaps without selecting an unsupported winner."},{"section_key":"stated_hypotheses","semantic_rule":"Include hypotheses explicitly stated by participants or researchers and label them as hypotheses, never findings."}],"section_order":["research_questions","observations","needs_pains","workflows","representative_quotes","contradictions_gaps","stated_hypotheses"],"sensitive_class_allowlist":[]},"profile_contract_hash":"c13a82ff6bf8cb37d5ec266124de6ccbcda6bdc9b7e733e3ab729447b4b7eaa4","profile_key":"research_interview","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","feedback","learning","proposal","question","risk","topic"],"allowed_relation_set":["blocks","cancels","depends_on","precedes","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"9d342f61b61f4d20d6af168ab0dbeb17d5674a7cf87fcc6f9ca1c43ea2fc489c","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["improvements_actions"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"retrospective","profile_semantic_rule":"Capture what participants explicitly said worked or did not work, stated lessons, start-stop-continue proposals and accepted improvements; use blameless language and never infer owners from who raised a problem.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*","feedback:*","learning:*"],"required_relation_types":["cancels","supersedes"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"worked","semantic_rule":"Include processes or approaches explicitly described as effective, with the source-supported context that made them work."},{"section_key":"did_not_work","semantic_rule":"Include processes or approaches explicitly described as ineffective, preserving context and using blameless language."},{"section_key":"lessons","semantic_rule":"Include lessons explicitly stated or directly resolved from source-supported events; do not invent generalized advice."},{"section_key":"start_stop_continue","semantic_rule":"Include explicitly agreed start, stop and continue changes; suggestions remain proposals until accepted."},{"section_key":"improvements_actions","semantic_rule":"Include only accepted process improvements and resulting actions; proposals remain proposals and blame is excluded."}],"section_order":["worked","did_not_work","lessons","start_stop_continue","improvements_actions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"7e26e7ad6529dfefae57a53b5404a5be48c71df8eea8e1687c34d03145eaff06","profile_key":"retrospective","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","decision","fact","feedback","metric","option","proposal","question","requirement","risk","topic","tradeoff"],"allowed_relation_set":["benefit_of","cancels","constraint_on","cost_of","depends_on","option_for","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"287a334bc8e24ff0b4570814b36fefd038a325bafeb9405e093530e3d341f309","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["commitments","next_step"],"forbidden_inference_clause_ids":["MP-PRF-SAL-EXP-001"],"master_clause_ids":["MP-PRF-SAL-EXP-001","MP-PRO-001"],"profile_key":"sales_discovery_demo","profile_semantic_rule":"Capture explicit customer context, needs, requirements, decision process, objections, pricing or timing, commitments and next step; never infer budget, authority, intent, probability or CRM stage.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","decision:*","feedback:*","proposal:*","question:*","requirement:*"],"required_relation_types":["option_for","rationale_for"],"required_trusted_role_groups":["customer_pair"],"risk_class":"external_sensitive","safety_caveat_codes":["no_audience_widening","sales_explicit_only"],"schema_version":1,"section_contracts":[{"section_key":"customer_context","semantic_rule":"Include customer context explicitly established in the source; do not infer budget, authority, sentiment, intent or CRM stage."},{"section_key":"pains_use_cases","semantic_rule":"Include customer-stated pains and use cases with source context; do not infer priority, urgency, budget or purchase intent."},{"section_key":"requirements","semantic_rule":"Include explicit requirements and constraints, preserving requester, priority or acceptance only when evidenced."},{"section_key":"decision_process","semantic_rule":"Include explicitly stated decision criteria, participants, authority and process; unknown authority or timing remains unknown."},{"section_key":"objections","semantic_rule":"Include objections explicitly raised and their stated disposition; do not infer an objection from hesitation or silence."},{"section_key":"explicit_pricing_timing","semantic_rule":"Include pricing, budget, timing or commercial terms only when explicitly stated, preserving currency, amount, conditions and uncertainty."},{"section_key":"commitments","semantic_rule":"Include only explicit commitments by either side and preserve which side, owner, condition and due date when evidenced."},{"section_key":"next_step","semantic_rule":"Include the single next step or ordered next steps explicitly agreed, preserving responsible side and due condition."}],"section_order":["customer_context","pains_use_cases","requirements","decision_process","objections","explicit_pricing_timing","commitments","next_step"],"sensitive_class_allowlist":[]},"profile_contract_hash":"6e4cbeed1693270e1337d396f9bc5c80d6213171d3bcb0a393a9178e2ce00238","profile_key":"sales_discovery_demo","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","fact","learning","question","requirement","topic"],"allowed_relation_set":["answers","interview_answer","interview_question","rationale_for"],"auto_policy_row_hash":"285387b1eda0a36d152e7478470a044a5fc40018e3a97b3c21ecb7080b10e579","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["unanswered_questions"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"training_qa","profile_semantic_rule":"Retain source-supported learning goals, concepts, examples, explicit questions and answers, provided exercises or resources and unanswered questions; never invent teaching material.","profile_version":1,"provenance":"built_in","required_kind_state_pairs":["action:*","learning:*","question:*"],"required_relation_types":["answers"],"required_trusted_role_groups":["training_pair"],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"learning_goals","semantic_rule":"Include learning goals explicitly stated by the trainer or participants; do not infer competency gaps."},{"section_key":"concepts","semantic_rule":"Include concepts explicitly taught or explained, preserving qualifications and excluding unstated background theory."},{"section_key":"examples","semantic_rule":"Include examples actually given in the source and link them to the concept they illustrate without inventing details."},{"section_key":"q_and_a","semantic_rule":"Pair each explicit question with only its source-supported answer and mark unanswered or partial answers faithfully."},{"section_key":"exercises_resources","semantic_rule":"Include only exercises, resources or assignments explicitly provided or agreed; never invent links or homework."},{"section_key":"unanswered_questions","semantic_rule":"Include questions left unanswered after the complete source, excluding rhetorical or later-resolved questions."}],"section_order":["learning_goals","concepts","examples","q_and_a","exercises_resources","unanswered_questions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"3d8f5bdb5fd576f7990f0c8366d1184f5fd387ca3cf311871cb55873a20535ec","profile_key":"training_qa","profile_version":1},{"profile_contract":{"allowed_kind_set":["action","blocker","correction","decision","dependency","event","fact","metric","question","requirement","risk","topic"],"allowed_relation_set":["blocks","cancels","depends_on","precedes","rationale_for","resolves","supersedes"],"auto_policy_row_hash":"43e06b0c8009ac250ef6ec045ab4dafa270609f65323823d04fe9670c4a741b8","budget_policy_key":"B1","default_detail_level":"standard","empty_state_section_keys":["actions","blockers"],"forbidden_inference_clause_ids":[],"master_clause_ids":["MP-PRO-001"],"profile_key":"weekly_team","profile_semantic_rule":"Align the team on supported highlights, workstream updates, decisions, accepted actions, blockers and announcements or questions; never score people, force per-person reporting or infer ownership.","profile_version":2,"provenance":"built_in","required_kind_state_pairs":["action:*","blocker:*","decision:*"],"required_relation_types":["blocks","depends_on"],"required_trusted_role_groups":[],"risk_class":"ordinary","safety_caveat_codes":["preserve_unknown_owner_date"],"schema_version":1,"section_contracts":[{"section_key":"highlights","semantic_rule":"Include the most material source-supported developments for the selected profile; do not reward positivity or omit critical negative outcomes."},{"section_key":"workstream_updates","semantic_rule":"Group source-supported updates by explicit workstream, preserving progress, blockers and commitments without per-person performance scoring."},{"section_key":"decisions","semantic_rule":"Include only decisions with their exact accepted, preliminary, requires-approval, deferred, cancelled or superseded state and evidence-backed rationale; rejected or withdrawn applies only to a proposal, idea or option."},{"section_key":"actions","semantic_rule":"Include only explicit accepted assignments or personal commitments; preserve unknown owner or due date and exclude suggestions or unaccepted requests."},{"section_key":"blockers","semantic_rule":"Include explicit blockers preventing progress; do not promote ordinary risks, concerns or delays to blockers without source support."},{"section_key":"announcements_questions","semantic_rule":"Include explicit announcements and materially unanswered questions; do not convert discussion topics into announcements."}],"section_order":["highlights","workstream_updates","decisions","actions","blockers","announcements_questions"],"sensitive_class_allowlist":[]},"profile_contract_hash":"2a9066a5698711c81528d467a9cd33fd9de528ca002541146032385feba1632b","profile_key":"weekly_team","profile_version":2}],"schema_version":1}
```

The adjacent `profile_contract_catalog_hash` is
`5f9f9f4f40a1139e033ae3905900f55ef707f288649f5d8d8d9beb8c48a4df59`. Every one of the 20 bindings embeds the complete exact
`ProfileContractV1` body and its externally recomputed hash. The
following digest ledger is a derived conformance vector only:

| Profile key | `profile_contract_hash` |
|---|---|
| `all_hands` | `002c972d51e6bfa233c98069533c144fc1426918506eec39cc617c84d912f876` |
| `auto` | `b37da94da0ebe54af4025864fd24809942c3dcdaba51d3981398bb50a9b672c9` |
| `brainstorm_workshop` | `da325e2d63068e3ffc59eebbc9132c913138574ca2454f551e1ff1e510b79493` |
| `client_status` | `1b0208cabf1cf43ad6595aa920a356e8d1e54551d0f0f0acd88f6b8a7a8be585` |
| `customer_success` | `03483d546246d552783b30a985c709b3c96aa2dccb687392f749955b9cdc3e5b` |
| `executive_board` | `401b0f98ead495feb8aea60fc678e8ead3f6fa096bcc334374986e8b08945acc` |
| `formal_minutes` | `d568f8362cb6d52dbe23ff4081d6b43228cd9cfd0d634bcc3c17505fce89fd29` |
| `general_summary` | `8696fda26835f6c585203562d93544fd1c93627f6e499ae7c314e6425e0731ca` |
| `hiring_interview` | `1e35f627c4b9cc903039b64d01d74f93b9a9779cdb18fb8a1f83e2fd5c5e528e` |
| `incident_postmortem` | `0d6294122077ffeb4524d7638f377de592fcce571f89abd31b1439ab5c3f31e4` |
| `meeting_minutes` | `be8b85ef1eeeaf0c5e54388cad095b00dc37ac25e2962ec8215866c397beca1f` |
| `one_on_one` | `85a6da2d7f28bfa4864298c267df9197b4ce1f1f50a508fb1f147e5e9df5b4a9` |
| `outline` | `29f2492841a98bce9eaba0154235fcb759fa64aef21dbf6a946606868dbdf2bd` |
| `planning_decision` | `c6b5b3793aa69d8c2b1ce765d9062a85b3606c45fbc812bdf5c836d4ebbf90e9` |
| `project_sync` | `ca9ca9e0e58217924b27c0e584da076d88ebd554d54c57c36a98819ff2dfe8e3` |
| `research_interview` | `c13a82ff6bf8cb37d5ec266124de6ccbcda6bdc9b7e733e3ab729447b4b7eaa4` |
| `retrospective` | `7e26e7ad6529dfefae57a53b5404a5be48c71df8eea8e1687c34d03145eaff06` |
| `sales_discovery_demo` | `6e4cbeed1693270e1337d396f9bc5c80d6213171d3bcb0a393a9178e2ce00238` |
| `training_qa` | `3d8f5bdb5fd576f7990f0c8366d1184f5fd387ca3cf311871cb55873a20535ec` |
| `weekly_team` | `2a9066a5698711c81528d467a9cd33fd9de528ca002541146032385feba1632b` |

The bodies contain literal `allowed_kind_set`,
`allowed_relation_set` and complete `section_contracts`.
Former dictionary keys and the section-semantic registry are not runtime
inputs. Conditional `auto_policy_row_hash` is present only for the
16 Auto-eligible profiles and `general_summary` fallback; each
value byte-equals the corresponding row digest above.

### Exact AutoSectionMappingPolicyV1 body

Auto has one stable visible contract even though its evidence assessment may
resolve a different intent profile for different meetings. The following exact
canonical JSON is the only V1 authority that maps a resolved Auto selection to
the Krisp-faithful visible shell:

```json
{"action_items_kind_set":["action"],"empty_state_source":"auto_profile_contract","intent_effect":"eligibility_ranking_criticality_safety_and_key_point_priority_only","key_points_excluded_kind_set":["action"],"policy_version":1,"profile_contract_hash":"b37da94da0ebe54af4025864fd24809942c3dcdaba51d3981398bb50a9b672c9","profile_key":"auto","profile_version":3,"schema_version":1,"section_assignment":"action_items_for_action_else_key_points","section_contract_source":"auto_profile_contract","section_order":["action_items","key_points"],"selected_id_coverage":"exactly_once","template_key":"auto"}
```

```text
auto_section_mapping_policy_hash =
  SHA-256("GRAF-AUTO-SECTION-MAPPING-POLICY\0v1" ||
    uint64be(auto_section_mapping_policy_body_byte_length) ||
    canonical_json(AutoSectionMappingPolicyV1))
```

The adjacent hash is
`8e6e9844ebd1258392e4caa7b3a86ab95b2f94a4d5a6228f56065e99a0775640`.
The referenced Auto profile body is the exact catalog member with
`profile_key=auto`, `profile_version=3` and the hash embedded above; a mutable
catalog lookup, another Auto version or a hash-only profile reference rejects
the run.

The resolved primary/secondary composite remains the semantic authority for
eligibility, ranking, profile criticality, safety constraints and the priority
of non-action key points. After all projection passes are validated, one
deterministic mapper assigns every selected canonical object of kind `action`
to `action_items` and every other selected object to `key_points`. An action is
never duplicated in Key Points, and every selected ID is assigned exactly
once. The mapper changes no selected/omitted set, canonical text, relation,
priority tier, explanation depth, privacy decision, safety constraint or
budget. The projection result's composite-owned `section_key` remains audit
evidence for intent/ranking only; it is not a visible Auto heading.

An empty Auto section is omitted. If both mapped sections would be empty, the
attempt follows the existing `no_supported_content` terminal path and publishes
nothing; Auto never renders an empty heading or filler message.

For `template_key=auto`, presentation synthesis, presentation verification,
deterministic rendering, canonical content and the publication receipt all use
the Auto profile's exact `section_contracts`, `section_order` and empty-state
authority plus this policy body/hash. For every other template the four Auto
mapping fields are forbidden and the composite contract remains the visible
section authority. Mapping is local and creates no GenerationCall, hidden
prompt or additional inference phase.

### Emphasis-only ProfileCompositionPolicyV1

```json
{"budget_merge":"primary_exact","canonical_set_order":"unique_utf8_ascending","duplicate_section_contract":"require_byte_equal","effective_allowed_kind_set":"primary_exact","effective_allowed_relation_set":"primary_exact","empty_state_merge":"primary_exact","policy_version":1,"primary_authority_fields":["allowed_kind_set","allowed_relation_set","empty_state_section_keys","forbidden_inference_clause_ids","master_clause_ids","required_kind_state_pairs","required_relation_types","required_trusted_role_groups","safety_caveat_codes","section_contracts","section_order"],"primary_requirement_handling":"preserve_exact_in_primary_requirements","profile_semantic_rule_order":"primary_then_secondary_emphasis","risk_merge":"maximum_by_risk_order","risk_order":["ordinary","external_sensitive","regulated_record"],"schema_version":1,"secondary_emphasis_selector_fields":["allowed_kind_set","allowed_relation_set","profile_semantic_rule","section_contracts","section_order"],"secondary_empty_state_handling":"forbidden","secondary_no_content_behavior":"omit_secondary_emphasis","secondary_required_criticality_handling":"forbidden","secondary_safety_fields":["forbidden_inference_clause_ids","master_clause_ids","safety_caveat_codes"],"secondary_safety_handling":"apply_constraints_without_eligibility_or_criticality_expansion","secondary_section_handling":"optional_emphasis_only","secondary_selector_kind_handling":"intersection_primary_secondary_allowed_kind_sets","secondary_selector_relation_handling":"intersection_primary_secondary_allowed_relation_sets","section_merge":"primary_order_then_unseen_secondary_emphasis","section_profile_role_mapping":"one_row_per_section_primary_or_secondary_emphasis_or_both","section_role_order":["primary","secondary_emphasis"],"semantic_conflict":"fail_closed","sensitive_class_allowlist_merge":"primary_exact_without_secondary_else_intersection"}
```

```text
profile_composition_policy_hash =
  SHA-256("GRAF-PROFILE-COMPOSITION-POLICY\0v1" ||
    uint64be(profile_composition_policy_body_byte_length) ||
    canonical_json(ProfileCompositionPolicyV1))
```

The adjacent `profile_composition_policy_hash` is
`c6e4abdb3752e93125b39fe8223b81ba59a388d1c5f38583042b5e816df402b5`. An explicit type materializes one primary and no
secondary. Auto may attach only a policy-allowed secondary emphasis. The
secondary never widens eligible kinds or relations, never contributes required
criticality, required kind/state pairs, required relations, required roles or
empty states, and never increases the primary detail budget. It may only rank
primary-eligible objects into optional emphasis sections. Its safety caveats,
forbidden-inference clauses and master clauses still apply as separately
identified secondary-emphasis safety constraints.

`CompositeProfileContractV1` is a closed body with exactly:

- `schema_version=1`, `profile_composition_policy_version` and `profile_composition_policy_hash`;
- `primary_profile_key`, `primary_profile_version`, complete
`primary_profile_contract` and `primary_profile_contract_hash`;
- optional all-or-none `secondary_profile_key`,
`secondary_profile_version`, complete `secondary_profile_contract` and `secondary_profile_contract_hash`;
- `primary_requirements`, optional `secondary_emphasis`,
`effective_sensitive_class_allowlist`, `effective_risk_class`,
`budget_policy_key`, `selected_detail_level` and complete
`detail_budget`;
- `section_order`, `section_contracts`,
`section_profile_roles`, `empty_state_section_keys` and
`profile_semantic_rules`.

`PrimaryRequirementsV1` has exactly `allowed_kind_set`,
`allowed_relation_set`, `required_kind_state_pairs`,
`required_relation_types`, `required_trusted_role_groups`,
`safety_caveat_codes`, `forbidden_inference_clause_ids`,
`master_clause_ids`, `section_order`,
`section_contracts` and `empty_state_section_keys`. Every
value byte-equals the primary profile contract. Criticality expansion reads
this object only.

`SecondaryEmphasisV1` has exactly
`profile_key`, `profile_version`,
`profile_contract_hash`, `selector_kind_set`,
`selector_relation_set`, `section_order`,
`section_contracts`, `profile_semantic_rule`,
`safety_caveat_codes`, `forbidden_inference_clause_ids` and
`master_clause_ids`. Selector sets are exact intersections with the
primary allowed sets. Required kind/state, relation, trusted-role, criticality
and empty-state fields are forbidden.

Composition preserves primary section order, then appends unseen secondary
sections as optional emphasis. A duplicate section is legal only when both
`SectionContractV1` bodies are byte-equal. One ordered
`SectionProfileRoleV1` exists for every section and has exactly
`section_key` and `roles`. Roles are exactly
`["primary"]`, `["secondary_emphasis"]` or
`["primary","secondary_emphasis"]`.
`empty_state_section_keys` byte-equals the primary array.

For Auto, this composite section order remains the internal semantic projection
order only. It is deterministically mapped to `action_items → key_points` by
the exact `AutoSectionMappingPolicyV1` above before presentation synthesis. No
other template may apply that override.

`effective_sensitive_class_allowlist` byte-equals the primary
allowlist without a secondary and otherwise is the unique UTF-8-sorted
intersection. It byte-equals
`PrivacyActionsV1.effective_sensitive_class_allowlist` in every
projection object and is covered by that body/hash. Risk is the policy-ordered
maximum; budget and detail remain primary-exact. An empty selector set yields
no secondary-emphasis items, never secondary requirements.

The composite body excludes its own digest. Its adjacent hash is:

```text
composite_profile_contract_hash =
  SHA-256("GRAF-COMPOSITE-PROFILE-CONTRACT\0v1" ||
    uint64be(composite_profile_contract_body_byte_length) ||
    canonical_json(CompositeProfileContractV1))
```

### Auto resolution and AutoSelectionProofV1

The visible slot remains `template_key=auto`. Model Auto assesses
every policy row but never chooses a key or confidence. The embedded policy
validates evidence, computes eligibility and score, applies near-neighbor
margins and materializes one primary plus at most one emphasis-only secondary.
Low confidence and capacity fallback resolve to `general_summary` without asking the user or changing the slot key.

`AutoSelectionProofV1` is a model-path-only closed body with exactly
`selection_policy_version`, `selection_policy_hash`, `auto_resolver_input_hash`,
`auto_resolver_result_hash`, `assessments_hash`,
`canonical_evidence_coverage_hash`, `ranked_profile_keys`,
`resolved_primary_profile_key`, `confidence_class` and `decision_code`, plus
optional `resolved_secondary_profile_key`. The ranked keys are the complete
policy-defined permutation of `compatible_profile_keys`, with the resolved
primary first. The proof is valid only with exactly one completed
`auto_resolve` call whose validated-result hash equals the proof result hash and
whose immutable request contains the full input matching the input hash. The
deterministic low-confidence, single-compatible-profile and policy-forced
fallback modes have no selection proof; they use the separate
`resolver_noop_proof` and its exact reason code. This is the sole V1 rule for
capacity fallback as well: an over-envelope full view uses deterministic
`resolver_noop_proof`, never a synthetic selection proof.

Names beginning `resolved_` are legal only in this proof. The
materialized `CompositeProfileContractV1`,
`ResolvedRunManifestV1` profile binding and every runtime request use
`primary_profile_*` and optional `secondary_profile_*`.
A runtime body containing resolved names or a proof containing materialized
names is a schema error.

`AutoSelectionProofV1` excludes its own hash. Its adjacent digest is:

```text
auto_selection_proof_hash =
  SHA-256("GRAF-AUTO-SELECTION-PROOF\0v1" ||
    uint64be(auto_selection_proof_body_byte_length) ||
    canonical_json(AutoSelectionProofV1))
```

The complete proof, selected exact profile bodies/hashes and resulting
composite body/hash are embedded in the attempt-owned resolved-run manifest.
Every Auto manifest additionally embeds the complete
`AutoSectionMappingPolicyV1` body/hash and the exact Auto presentation-profile
body/hash; non-Auto manifests forbid all four fields.
Mutable metadata cannot reconstruct historical Auto input, and no profile
choice changes the profile-independent canonical cache.


## Catalog display and ordering V1

`SummaryTypeCatalogEntryV1` is the only selector/catalog display contract. The
2026-08-23 black-box selector evidence establishes this compact built-in order:
Auto, Outline, Meeting Minutes, Project Sync, Weekly Team Meeting, 1 to 1, then
the `All templates` and `New template` action rows. Personal templates precede
those built-ins in their Feature 199 persisted order. The observed full built-in
library order is Auto, Outline, Meeting Minutes, Project Sync, Weekly Team
Meeting, 1 to 1, Client Status Update, Training, Sales Call/Demo, Hiring and All
Hands. Evidence references are opaque and contain no record title or screenshot
path.

V1 freezes these ranks; gaps are intentional so later rows do not renumber the
observed set:

| `template_key` | Group | Category | Quick rank | Full rank | Provenance |
|---|---|---|---:|---:|---|
| `auto` | `built_in` | `general` | 100 | 100 | `observed_reference` |
| `outline` | `built_in` | `general` | 110 | 110 | `observed_reference` |
| `meeting_minutes` | `built_in` | `general` | 120 | 120 | `observed_reference` |
| `project_sync` | `built_in` | `team_project` | 130 | 130 | `observed_reference` |
| `weekly_team` | `built_in` | `team_project` | 140 | 140 | `observed_reference` |
| `one_on_one` | `built_in` | `people_learning` | 150 | 150 | `observed_reference` |
| `client_status` | `built_in` | `customer_revenue` | null | 160 | `observed_reference` |
| `training_qa` | `built_in` | `people_learning` | null | 170 | `observed_reference` |
| `sales_discovery_demo` | `built_in` | `customer_revenue` | null | 180 | `observed_reference` |
| `hiring_interview` | `built_in` | `people_learning` | null | 190 | `observed_reference` |
| `all_hands` | `built_in` | `people_learning` | null | 200 | `observed_reference` |
| `planning_decision` | `additional` | `team_project` | null | 300 | `graf_extension` |
| `brainstorm_workshop` | `additional` | `team_project` | null | 310 | `graf_extension` |
| `retrospective` | `additional` | `team_project` | null | 320 | `graf_extension` |
| `research_interview` | `additional` | `people_learning` | null | 330 | `graf_extension` |
| `customer_success` | `additional` | `customer_revenue` | null | 340 | `graf_extension` |
| `executive_board` | `additional` | `high_stakes` | null | 350 | `graf_extension` |
| `incident_postmortem` | `additional` | `high_stakes` | null | 360 | `graf_extension` |
| `formal_minutes` | `additional` | `high_stakes` | null | 370 | `graf_extension` |

`general_summary` is fallback-only and never catalog-visible. Personal entries
use `catalog_group=personal`, `category=personal`, group rank before built-ins
and unique Feature 199 ranks; overflow remains reachable through `All
templates`. Exact visible descriptions live in versioned localization resources.
Approved functional reference labels and interaction microcopy may be reproduced
literally. Third-party assets, logos, trademarks, slogans and marketing copy
still require recorded rights or an independently authored replacement carrying
deviation code `rights`.
`graf_extension` rows carry the matching deviation code rather than pretending
they were observed in Krisp. A generation badge, retirement, saved state or
async completion never changes rank inside an open catalog snapshot.

## Non-authoritative product copy

Localized selector names and descriptions may explain the exact contract bodies
above, but they are not prompt, compiler, projection or evaluation input. They
may not add a section, order, fallback, exclusion, requirement, empty state or
secondary behavior. Any product-copy claim that cannot be traced to the embedded
profile body is corrected as copy; runtime never chooses between prose and the
hash-bound body. This prevents the former Job/Order/Exclude restatements from
becoming a second semantic authority.

High-stakes profiles may be read on screen without routine approval. External
system-of-record writes, client/legal sends or regulated use require the
workspace's separate human-review policy and a version-bound receipt over exact
`outcome_set_id`, root bundle hash, projection-policy version, profile risk
class, approved audience, intended egress purpose, recipient-or-link scope,
capability class, policy version, reviewer and timestamp. Refresh, changed
recipient/scope/capability, access/policy change or deletion prevents receipt
reuse.

Feature 203 owns a first-class immutable `EgressReviewReceipt` scoped to one
egress intent. Its canonical digest and DB row bind workspace/meeting,
`outcome_set_id`, root plus resolved-run manifest hashes, projection-policy
version, profile risk, approved audience, purpose, exact recipient identity or
link-scope class, capability class, policy/access/deletion epochs, reviewer,
review time, expiry and optional revocation. State is `valid | consumed |
expired | revoked`; a receipt cannot authorize a second artifact.

The authoritative egress transaction locks the meeting/access policy, exact
outcome and receipt, revalidates every bound field plus current epochs and
expiry/revocation, then records the receipt ID/digest in the same grant/artifact
write that pins type and revision. Any TOCTOU change fails without creating an
artifact; a new review is required. Deletion/access loss immediately blocks
consumption even when the immutable receipt row is retained for audit.

## Subject-dependent views and personal formats

Shared built-in outcomes use one `(workspace, meeting, template_key)` slot and
therefore cannot safely mean “my” for different viewers. The product contract
is:

- `Мои действия` on a shared result is an authorized read-time filter over
  canonical actions using authenticated user → trusted participant mapping; it
  creates no outcome revision, prompt call or shared cache entry.
- A personal template may remain in the shared slot only when its generated
  content is identical for every authorized viewer.
- Any generated `private_self`, “my actions”, private coaching or other
  subject-dependent block requires a later subject-scoped slot/receipt schema.
  Its identity must include owner-bound personal template, authenticated
  workspace-user ID, participant-mapping snapshot/hash, mapping policy version
  and access-policy epoch in request/idempotency, manifest, content, receipt,
  cache/slot uniqueness and every read authorization check.
- Transcript/model guesses never establish subject identity. A missing or
  ambiguous trusted mapping produces a read-time empty/ambiguous state or
  generation denial, never another participant's data.

Receipt V1 rejects generated subject-dependent controls. Feature 199 explicitly
rejects them from personal shared-slot formats. Feature 208 alone owns a future
subject-scoped slot/receipt extension and its cross-user/RLS/deletion tests; no
shared-slot shortcut is permitted.

## Closed preregistered profile-clause evaluation plan

`ProfileClauseEvalManifestV1` is an immutable preregistered **plan**, never
qualification proof and never measured evidence. The build creates it from the
exact activated `MasterPromptClauseRegistryV1.phase_bindings`, the exact
`ProfileContractCatalogV1` above and an immutable held-out fixture registry.
No evaluator, prompt result or operator may hand-author applicability after a
candidate has run. `quality-and-evaluation.md` §Closed master-prompt clause
cells is the sole normative wire schema; this section defines its deterministic
phase/cell derivation and does not introduce another closed shape.

The closed phase domain and ordinal are exactly:

```text
0 extract
1 resolve
2 semantic_verify
3 repair
4 post_repair_reverify
5 auto_resolve
6 profile_projection
7 presentation_synthesis
8 presentation_verify
9 deterministic_render
```

The manifest body has exactly the fields listed by that sole wire contract:
`schema_version=1`, `manifest_version=1`, complete immutable
`master_prompt_clause_registry_binding`, `profile_contract_catalog_binding`,
`profile_composition_policy_binding`, `auto_selection_policy_binding`,
`auto_section_mapping_policy_binding`, `fixture_registry_binding`,
`dataset_manifest_binding`,
`split_policy_binding`, complete `phase_bindings` plus
`phase_bindings_hash`, `phase_domain`, `cell_generation_policy`,
`clause_eval_policy_rows` and `cells`. The bindings resolve and rehash the exact
activated bodies above. `phase_bindings_hash` byte-equals the
domain-separated projection derived from the activated registry entries by the
formula in `prompt-pipeline.md`; the manifest cannot carry a hand-authored phase
matrix or recompute bindings from prose. `phase_domain` is the exact ordered
ten-value array above.
`cell_generation_policy` is the complete closed body below; no prose default is
legal:

```json
{"applicable_fixture_roles":["english_or_mixed_language","positive_preservation","russian_language","tempting_violation"],"canonical_cell_order":"profile_key_utf8_profile_version_clause_id_utf8_clause_version_phase_ordinal","cell_cardinality":10200,"eval_requirement_class_policy":{"deferred_none":{"adversarial_fixture_floor":0,"fixture_floor":0,"required_eval_cell_rule":"always_false"},"high_risk":{"adversarial_fixture_floor":5,"fixture_floor":10,"required_eval_cell_rule":"when_applicable"},"negative_rejection":{"adversarial_fixture_floor":0,"fixture_floor":4,"required_eval_cell_rule":"when_applicable"},"standard":{"adversarial_fixture_floor":0,"fixture_floor":4,"required_eval_cell_rule":"when_applicable"}},"not_applicable_fixture_count":0,"phase_count":10,"profile_count":20,"registry_clause_count":51,"result_artifact":"separate_profile_clause_eval_result_set","result_ids_preregistered":true,"schema_version":1}
```

`cells` is the complete Cartesian product of the 20 catalog bindings, all 51
registry entries and all 10 phases: exactly 10,200
`ProfileClauseEvalCellV1` bodies. The builder sorts by
`(profile_key UTF-8, profile_version, clause_id UTF-8, clause_version,
phase_ordinal)` and rejects one missing, extra, duplicate or reordered cell.
Catalog or registry cardinality drift requires a new manifest version; it may
not be hidden by retaining the old 10,200 count.

Each cell has exactly `cell_id`, `result_cell_id`, `profile_key`,
`profile_version`, `profile_contract_hash`, `clause_id`, `clause_version`,
`clause_requirement_hash`, `phase`, `enforcement`, `applicability`,
`applicability_reason_code`, `eval_requirement_class`, `authority_mode`,
`required_eval_cell`, `plan_disposition` and `fixture_bindings`. IDs are
deterministic UTF-8 strings:

```text
cell_id =
  "PCEV1/" + profile_key + "@" + uint32_decimal(profile_version) +
  "/" + clause_id + "@" + uint32_decimal(clause_version) + "/" + phase

result_cell_id =
  "PCRV1/" + profile_key + "@" + uint32_decimal(profile_version) +
  "/" + clause_id + "@" + uint32_decimal(clause_version) + "/" + phase
```

Profile keys, clause IDs and phase names already use closed ASCII grammars;
`/` and `@` are forbidden inside each component, so no escaping or alternate
normalization exists. `profile_contract_hash` and
`clause_requirement_hash` byte-equal the catalog/registry. `phase_binding` is
not a cell or request field. Cell `enforcement` is the exact registry
`phase_bindings` enforcement value for this phase or the literal `absent`; it is
generated from the hash-bound registry projection, never inferred from clause
prose or implementation owner. A request-side `CompiledClauseBindingV1` remains
the separate five-field runtime value defined in `prompt-pipeline.md`.
`eval_requirement_class` byte-equals the registry entry's exact
`required_eval_cells` value and is one of `high_risk | standard |
negative_rejection | deferred_none`; no clause-ID list or evaluator override may
reclassify it.

Applicability is generated in this order:

1. If `enforcement=absent`, use `applicability=not_applicable`,
   `applicability_reason_code=clause_not_bound_to_phase`,
   `required_eval_cell=false` and `plan_disposition=none`.
2. If the registry entry has exact `applicability=profile` and the exact profile contract does
   not list the clause in `master_clause_ids`, use
   `applicability=not_applicable`,
   `applicability_reason_code=profile_clause_not_listed`,
   `required_eval_cell=false` and `plan_disposition=none`.
3. Otherwise use `applicability=applicable` and `required_eval_cell=true`.
   `applicability_reason_code` is `profile_clause_listed_and_bound` for a
   `applicability=profile` entry and `registry_clause_bound` for every other entry;
   `plan_disposition` maps exactly as follows.

| Exact registry phase binding | `plan_disposition` |
|---|---|
| `runtime_prompt` | `model_behavior_eval` |
| `typed_policy` | `typed_policy_conformance` |
| `deterministic_precheck` | `deterministic_conformance` |
| `deterministic_postcheck` | `deterministic_conformance` |
| `deterministic_renderer` | `deterministic_conformance` |
| `negative_rejection` | `negative_rejection_conformance` |

The four applicability reason codes above are the complete V1 enum. Boolean
`required_eval_cell` follows the exact `eval_requirement_class_policy` row:
it is true if and only if `applicability=applicable` for `high_risk`,
`standard` or `negative_rejection`, and is always false for `deferred_none`.
An entry classified `deferred_none` with any phase enforcement, or any other
class with no required cell for an applicable phase, invalidates the manifest.
A
global, canonical, policy, presentation or negative registry entry cannot be
waived by a profile. A deferred entry with no phase binding creates ten explicit
not-applicable cells rather than disappearing. An `applicability=profile` entry
is forbidden from canonical phases by the registry itself; a generated
applicable cell showing otherwise invalidates both manifest and bundle.

Each required eval cell contains at least the number of unique held-out
`EvalFixtureBindingV1` values required by its exact
`eval_requirement_class_policy` row. Each binding has exactly `fixture_id`,
immutable `content_binding`, `split=held_out`, `language_class`,
`challenge_classes`, `fixture_roles` and exactly one of
`expected_invariant_ids` or immutable `human_gold_schema_binding`. Bindings are unique and
sorted by `(fixture_id UTF-8, content_binding.hash)`; every set-valued string
array inside a binding is unique UTF-8 ascending. Collectively the fixtures
cover all four roles frozen in
`cell_generation_policy`; one fixture may cover several roles but is listed
once. A cell with `required_eval_cell=false` has an empty array. Unknown,
unhashed, train-overlap,
post-result-added or duplicate fixtures invalidate preregistration. A
`high_risk` cell therefore has at least ten fixtures and five carrying challenge
class `adversarial`; `standard` and `negative_rejection` cells have at least
four, while `deferred_none` has zero. These are per-cell floors derived from the
registry classification, never an aggregate-profile or hand-maintained
clause-list substitute. Each required cell additionally carries the exact
`required_fixture_counts`, `evaluator_bindings` and `gate_policy` from the sole
wire contract; a non-required cell forbids those fields and has the required
empty fixture array.

The body excludes its own digest. Activation computes:

```text
profile_clause_eval_manifest_hash =
  SHA-256("GRAF-PROFILE-CLAUSE-EVAL-MANIFEST\0v1" ||
    uint64be(profile_clause_eval_manifest_body_byte_length) ||
    canonical_json(ProfileClauseEvalManifestV1))
```

Measured output lives only in a separate immutable
`ProfileClauseEvalResultSetV1` with the exact body/hash from
`quality-and-evaluation.md`: complete pre-call candidate-evaluation authority,
candidate root, manifest binding, calibration bindings and one phase-bound
result for every preregistered `result_cell_id`. It cannot add cells, fixtures
or applicability. The manifest itself records only the preregistered plan; root
qualification requires the complete passing result set and cannot cite the plan
as proof.

Feature 200 reports entailment/recall by criticality and kind, state fidelity,
forbidden inference, critical omission, profile fit, presentation fidelity,
audience leakage, length/redundancy, Russian/English/mixed-language quality,
long-meeting stability, latency, tokens and cost. No aggregate average may hide
a failed applicable cell, profile, phase or high-risk slice. Each profile also
retains at least 60 suitable and 30 unsuitable held-out items, with at least 10
items each for mixed-profile ambiguity, empty critical sections, correction or
supersession, prompt injection, long-meeting handling and mixed-language use.
