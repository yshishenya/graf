# Contract: canonical verification and outcome publication receipts

## Ownership and rollout boundary

This is a downstream normative contract for Features 194–195. Feature 183 owns
only the per-type slot, private expected-current CAS primitive and one
always-fail-closed model-publication entry point in `ai_service.py`; it has no
successful receipt path or receipt schema migration. Feature 194 owns the
canonical artifact and claim/relation semantics. Feature 195 extends that same
entry point with persisted GenerationCall membership, calibration-registry
storage/lookup, canonical-receipt finalization and the sole successful outcome
publication transaction. It invokes Feature 183's private CAS primitive and
MUST NOT implement a second publisher or CAS path. Feature 200 owns human-grounded manifest creation, production
activation/revocation and promotion eligibility.

Only two receipt kinds exist:

- `CanonicalVerificationReceiptV1`: one immutable receipt per verified
  `MeetingIntelligenceArtifact`; reusable by every compatible summary type.
- `OutcomePublicationReceiptV1`: one immutable receipt per type-specific
  `MeetingOutcomeGenerationAttempt`; created after projection, mandatory
  presentation synthesis/verification and deterministic layout render for one
  exact `MeetingOutcomeSet`.

Neither receipt is a user approval. A canonical receipt alone can never publish
a result. There is no single-receipt, same-attempt or pre-V2 compatibility mode.

Receipt V1 uses owner-row columns, not receipt tables. Feature 194/195 adds
`canonical_verification_receipt_schema_version`,
`canonical_verification_receipt_json`,
`canonical_verification_receipt_digest` and
`canonical_verification_receipt_finalized_at` to the
`MeetingIntelligenceArtifact` row. The existing
`MeetingOutcomeGenerationAttempt` row owns the corresponding
`outcome_publication_receipt_*` columns. The exact `MeetingOutcomeSet` header
repeats the publication schema/digest through the restrictive composite FK.
There is no `canonical_verification_receipts` or
`outcome_publication_receipts` table, reservation row or independently locked
receipt entity in V1. Adding one requires a versioned schema amendment and a
new lock graph.

## Canonical JSON and digest

The persisted wire payload is a JSON object with exactly the required keys
below. Unknown keys, duplicate keys, JSON `null`, floats, NaN/Infinity and
integers outside signed 64-bit range are rejected. Optional fields are omitted,
never set to `null`.

These rules govern every `canonical_json(...)` contract in this Feature 183
program, including prompt, profile, evaluation, promotion and drift artifacts.
All serialized integers are signed-int64; a non-negative counter is therefore
`0..2^63-1` and a positive counter is `1..2^63-1`. Implementations MAY use
arbitrary-precision integers while computing ratios or cross-products, but MUST
range-check before serialization. Required empty collections serialize as `[]`;
conditional members are omitted rather than written as `null`. `byte_length`
always means the length of the final canonical UTF-8 byte string.
`uint16be`/`uint64be` length prefixes are binary digest framing, not JSON
integers; their inputs are byte lengths and must fit the stated unsigned binary
width.

A digest is reconstructible evidence only when the same closed parent contains
the complete hashed body, or when it contains one `ImmutableArtifactBindingV1`
with exactly `artifact_id`, `schema_version`, `artifact_version` and `hash`.
The finalizer MUST fetch that exact immutable typed foreign binding, recompute
its canonical bytes and hash, and reject absence, mutation or schema/version
mismatch. A bare digest, mutable name, label, latest-version lookup or prose
description is not an artifact binding and cannot authorize activation,
qualification or either receipt.

Canonical bytes are produced with Python standard-library semantics equivalent
to:

```python
json.dumps(
    payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
```

All schema keys and enums are ASCII. Strings are exact UTF-8 with no trim,
case-fold or Unicode normalization. UUIDs are lowercase canonical text. Hashes
are exactly 64 lowercase hexadecimal characters. Timestamps are signed 64-bit
UTC Unix microseconds. Lists have semantic order as defined below; callers may
not reorder them after finalization.

Receipt digest V1 is:

```text
SHA-256(domain_prefix || uint64be(payload_byte_length) || canonical_json_bytes)
```

Domain prefixes are exact UTF-8 bytes:

```text
GRAF-RECEIPT\0canonical-verification\0v1
GRAF-RECEIPT\0outcome-publication\0v1
```

The lowercase digest and schema version are stored beside, never inside, the
payload. This prevents self-reference. Publication recomputes both digests.

## Root execution authorities

There is no generic `RootBindingV1`. Production execution and pre-promotion
evaluation have different, closed authority schemas and are never accepted as
substitutes for one another.

`CandidateRootBindingV1` is the cycle-free identity of one not-yet-promoted
bundle. It has exactly `schema_version=1`, `root_name`, positive
`root_version`, immutable `root_artifact_binding` and immutable
`activation_manifest_binding`. Both bindings are complete
`ImmutableArtifactBindingV1` objects and are fetched and rehashed. It contains
no label, qualification, measured evidence or promotion-event member.

`PromotedRootBindingV1` has exactly `schema_version=1`, `root_name`, positive
`root_version`, immutable `root_artifact_binding`, immutable
`activation_manifest_binding` and immutable
`last_successful_promotion_event_binding`. The event binding is resolved and
rehashed to one passing `RootPromotionEventV1` whose target/read-back root and
activation are byte-equal to the first four fields. A bare current label,
event hash or `CandidateRootBindingV1` is not production authority.

`CandidateEvaluationAuthorityV1` is finalized after its preregistered
comparative plan and before the first candidate model call. Its closed body has
exactly:

```text
schema_version=1
authority_version
authority_id
comparative_experiment_plan_binding
candidate_root
promoted_baseline
dataset_manifest_binding
split_manifest_binding
publication_sink="evaluation_only"
allowed_run_ids
issued_at_us
```

The plan, dataset and split fields are complete immutable typed bindings;
`candidate_root` is `CandidateRootBindingV1`; `promoted_baseline` is
`PromotedRootBindingV1`; and `allowed_run_ids` is the complete non-empty unique
UTF-8-sorted set frozen by the plan. The fetched plan must name byte-equal
candidate/baseline/dataset/split bodies. The authority permits only calls owned
by those runs. Such calls MUST NOT be members of a canonical artifact, outcome
attempt, publication receipt or DispatchIntent, and MUST NOT insert, replace or
select a `MeetingOutcomeSet` or summary slot. A production call rejects this
authority; an evaluation call rejects `PromotedRootBindingV1` used alone.

```text
candidate_evaluation_authority_hash =
  SHA-256("GRAF-CANDIDATE-EVALUATION-AUTHORITY\0v1" ||
    uint64be(authority_body_byte_length) ||
    canonical_json(CandidateEvaluationAuthorityV1))
```

## `ResolvedRunManifestV1`

Every type attempt owns one immutable canonical JSON manifest body plus
`resolved_run_manifest_schema_version=1` and its external hash. The body is
written once after Auto/topic resolution is complete and before a candidate can
enter `pending_publication`; it is never reconstructed from mutable meeting or
workspace settings. The top-level object has exactly these required keys:

| Key | Type / rule |
|---|---|
| `schema_version` | integer literal `1` |
| `attempt_id`, `workspace_id`, `meeting_id`, `artifact_id` | canonical lowercase UUIDs; equal the locked attempt/artifact scope |
| `template_key`, `template_version` | 1..120 UTF-8 bytes and positive uint32; exact API/slot/outcome bound |
| `source_basis_hash`, `canonical_payload_hash`, `canonical_verification_receipt_digest` | exact reusable parent identities |
| `bundle_root_name`, `bundle_root_version`, `bundle_root_hash` | exact immutable root Prompt Config identity |
| `activation_manifest_hash`, `extraction_layer_manifest_hash` | exact activated bundle and reusable canonical-layer identities |
| `root_promotion_event_binding` | complete `ImmutableArtifactBindingV1` for the successful `RootPromotionEventV1`; fetched event must have `result=pass`, target/read-back root equal this manifest root and qualification candidate/activation equal this manifest authority |
| `master_prompt_clause_registry_version`, `master_prompt_clause_registry_hash` | exact closed `MasterPromptClauseRegistryV1` bound by activation |
| `gateway_route_binding`, `gateway_route_binding_hash` | complete immutable `GatewayRouteBindingV1` body, including the compiler binding, and its external hash |
| `criticality_policy` | exact `CriticalityPolicyBindingV1` used by canonical verification and profile expansion |
| `canonical_kind_state_matrix`, `canonical_kind_state_matrix_hash` | complete `CanonicalKindStateMatrixV1` body and recomputed hash; exact state authority used by canonical, presentation and renderer validators |
| `subject_scope` | literal `shared` for Receipt V1 |
| `profile_resolution` | exact `ProfileResolutionV1` object below |
| `meeting_intent` | exact `MeetingIntentV1`; unknown is explicit and never reconstructed from a later title edit |
| `controls` | exact `SharedPresentationControlsV1` object below |
| `component_bindings` | exact required set of `RunComponentBindingV1`, sorted by `component_key` UTF-8 bytes |
| `phase_envelopes` | 3..4 `PhaseEnvelopeV1` objects, sorted by outcome-attempt phase ordinal; projection, synthesis and verification are mandatory, Auto is conditional |

Manifest finalization follows `root_promotion_event_binding`, recomputes the
event body/hash and embedded qualification-record hash, and requires
`result=pass`, target/read-back root equality and a qualification candidate root
plus activation binding byte-equal to this manifest. The immutable event needs
no mutable-label lookup or row lock; an absent binding, unknown artifact,
hash/version mismatch, failed event or activation mismatch rejects the manifest
before any type-phase egress.

`ProfileResolutionV1` has exactly `primary_profile_key`,
`primary_profile_version`, `primary_profile_contract_hash`,
`composite_profile_contract`, `composite_profile_contract_hash`,
`profile_composition_policy_version`, `profile_composition_policy_hash`,
`resolution_mode`, `confidence_class`, `resolver_version` and
`resolver_policy_hash`, plus the conditional fields below. Profile keys are
1..120 UTF-8 bytes; versions are positive uint32; secondary
key/version/contract-hash are all present or all absent. The embedded closed
`CompositeProfileContractV1` and external hash recompute from those exact
contracts under the pinned composition policy. `resolution_mode` is one of
`explicit_template`, `deterministic_low_confidence_fallback`,
`single_compatible_profile`, `policy_forced_profile` or `model_resolved`;
`confidence_class` is `not_applicable`, `low`, `medium` or `high`. Non-Auto
uses `explicit_template`, `not_applicable` and omits every Auto field. For Auto,
the conditional names include exactly `secondary_profile_key`,
`secondary_profile_version` and `secondary_profile_contract_hash` when a
secondary exists, plus mandatory `auto_section_mapping_policy`,
`auto_section_mapping_policy_hash`, `auto_presentation_profile_contract` and
`auto_presentation_profile_contract_hash`. No other secondary or Auto field is
legal. The policy/body/hash byte-equal the activated
`AutoSectionMappingPolicyV1` and exact catalog `auto` profile v3 authority; the
policy's embedded profile identity/hash must recompute from that body. Non-Auto
forbids all four mapping/presentation-profile fields. For Auto,
`model_resolved` may use `low | medium | high`, both deterministic fallback
modes use `low`, and `policy_forced_profile` uses `not_applicable`; no other
mode/confidence pairing is legal. Auto always requires one frozen
`auto_input_descriptor` `AutoResolverInputDescriptorV1` plus
`auto_resolver_input_hash`. `model_resolved` additionally requires
`auto_resolver_result_hash` and the complete `auto_selection_proof`
`AutoSelectionProofV1`; deterministic modes omit both and require the separate
receipt-level `resolver_noop_proof`. The model result never supplies the final
profile or confidence: the proof records the exact deterministic policy output.

`SharedPresentationControlsV1` has exactly the required keys `output_language`,
`audience_context`, `privacy_policy`, `focus`, `detail_budget`, `analysis_mode`,
`evidence_presentation_policy`, `fixed_schema`, `follow_up_requested` and
`clarification_policy`, plus conditional `follow_up_tone`. The nested values are the exact `AudienceContextV1`,
`PrivacyPresentationPolicyV1`, `FocusV1`, `DetailBudgetV1` and
`EvidencePresentationPolicyV1` bodies from `prompt-pipeline.md`; evidence
collection is never off and the requested research value must map byte-for-byte
to the policy's closed display mode;
`fixed_schema` is literal false in shared built-in Receipt V1;
`clarification_policy` is the literal `do_not_ask_record_gaps`, and
`follow_up_requested=true` requires one allowlisted `FollowUpDraftV1` tone while
false forbids the tone. The flag controls only deterministic draft assembly.
Receipt V1 permits only
`analysis_mode=facts_only`; model-authored analysis requires a versioned
analysis phase, verifier, manifest/content/receipt schema and is not smuggled
through presentation synthesis.

`GatewayRouteBindingV1` has exactly `binding_version` (positive uint32),
`gateway_id`, `route_alias`, `allowed_targets`,
`request_compiler_binding` and `request_compiler_binding_hash`. The strings are
1..128 ASCII bytes; `route_alias` is `gpt-5.6-luna`. `allowed_targets` is a
non-empty array of unique `{actual_provider,actual_model}` pairs sorted by
provider then model UTF-8 bytes, each value 1..128 bytes.

`LiteLLMRequestCompilerBindingV1` is the embedded closed
`request_compiler_binding`. It has exactly:

| Key | Type / rule |
|---|---|
| `schema_version` | integer literal `1` |
| `binding_version` | positive uint32; a semantic change never reuses a version |
| `endpoint_mode` | `responses` or `chat_completions`; the initial `gpt-5.6-luna` binding is `responses` |
| `adapter_name` | 1..128 ASCII bytes |
| `adapter_version` | positive uint32 |
| `adapter_hash`, `serializer_hash`, `translator_hash` | exact lowercase SHA-256 implementation/configuration identities |
| `reasoning_effort_domain` | non-empty unique subset of `minimal | low | medium | high`, serialized in that fixed order |
| `service_tier_domain` | non-empty unique subset of `auto | default | flex | priority`, serialized in that fixed order |
| `defaults_policy` | literal `preserve_omitted` in V1; no SDK/provider default is materialized invisibly |
| `drop_policy` | literal `reject_unsupported` in V1; `drop_params` and silent omission are forbidden |
| `automatic_summary_policy` | literal `disabled` in V1; no hidden summarization, compaction or message rewrite |

Its external hash is:

```text
SHA-256("GRAF-LITELLM-REQUEST-COMPILER\0v1" ||
        uint64be(compiler_body_byte_length) ||
        canonical_json(LiteLLMRequestCompilerBindingV1))
```

The hash is outside the compiler body and byte-equals
`request_compiler_binding_hash` in the gateway binding. Endpoint, adapter,
serializer/translator, enum-domain or policy changes require a new compiler
binding/version, root activation and production-equivalent evaluation. A
Chat/Responses bridge cannot inherit evidence from another binding merely
because its logical request looks similar.

The exact external route-binding hash is

```text
SHA-256("GRAF-GATEWAY-ROUTE-BINDING\0v1" ||
        uint64be(canonical_body_byte_length) ||
        canonical_json(GatewayRouteBindingV1))
```

The lowercase digest is not included inside the body. Every phase envelope and
GenerationCall uses this same hash and the embedded compiler hash. Any other
domain, serializer, normalization, field set or target ordering is invalid. The
root `gateway_route_binding` component version equals `binding_version`; its
name identifies the exact activated binding member and its hash equals this
digest. The root also carries one `litellm_request_compiler` component whose
version equals the compiler `binding_version` and whose hash equals
`request_compiler_binding_hash`.

`CriticalityPolicyBindingV1` has exactly `policy_body`, `policy_hash`,
`policy_version`, `canonical_rules_hash`, `profile_expansion_rules_hash` and
`reason_codes_hash`. `policy_body` is the exact `CriticalityPolicyV1` below and
`policy_version` equals its value.

`CriticalityPolicyV1` has exactly `schema_version=1`, positive uint32
`policy_version`, `canonical_rules`, `profile_expansion_rules` and
`reason_codes`:

- `canonical_rules` is `CanonicalCriticalityRulesV1` with exactly
  `schema_version=1`, `rule_ids` and
  `propagation_mode=source_union_then_relation_fixed_point`. `rule_ids` is the
  unique ASCII-sorted array containing exactly
  `accepted_action`, `critical_relation_context`,
  `decision_or_resolution_state`, `explicit_correction_or_conflict`,
  `explicit_due_or_trigger`, `explicit_owner`,
  `meaning_changing_value_or_qualifier`, `motion_vote_or_dissent`,
  `regulated_or_customer_commitment_or_constraint`, and
  `risk_blocker_or_dependency`.
- `profile_expansion_rules` is `ProfileCriticalityExpansionRulesV1` with exactly
  `schema_version=1` and `profiles`. `profiles` contains one entry for every
  activated profile, sorted by `(profile_key UTF-8, profile_version)`. Each entry
  has exactly `profile_key`, positive uint32 `profile_version`,
  `required_kind_state_pairs`, `required_relation_types`,
  `required_trusted_role_groups` and `safety_caveat_codes`; every array is
  unique and sorted by its canonical tuple/string order. The arrays equal the
  corresponding immutable `ProfileContract` fields byte-for-byte.
- `reason_codes` is `CriticalityReasonCodesV1` with exactly
  `schema_version=1` and `entries`. Each entry has exactly `code`,
  `classification=critical|non_critical` and non-empty unique ASCII-sorted
  `populations` from `source_span|candidate|canonical|profile_expansion`.
  Entries sort by code and contain exactly these codes:
  `accepted_action`, `critical_relation_context`,
  `decision_or_resolution_state`, `explicit_correction_or_conflict`,
  `explicit_due_or_trigger`, `explicit_owner`,
  `meaning_changing_value_or_qualifier`, `motion_vote_or_dissent`,
  `regulated_or_customer_commitment_or_constraint`,
  `risk_blocker_or_dependency`, `ordinary_context`, `repetition_without_new_meaning`,
  `social_or_setup`, `unintelligible_or_unsupported`,
  `profile_required_kind_state`, `profile_required_relation`,
  `profile_required_trusted_role`, and `profile_safety_caveat`. The first ten
  and final four `profile_*` codes are `critical`; the four ordinary/repetition/
  social/unintelligible codes are `non_critical`. `profile_*` populations are
  only `profile_expansion`; the other entries cover their applicable source/
  candidate/canonical populations.

The exact subhashes and full hash are:

```text
canonical_rules_hash = SHA-256("GRAF-CRITICALITY-POLICY\0canonical-rules\0v1" ||
  uint64be(byte_length) || canonical_json(canonical_rules))
profile_expansion_rules_hash = SHA-256("GRAF-CRITICALITY-POLICY\0profile-expansion-rules\0v1" ||
  uint64be(byte_length) || canonical_json(profile_expansion_rules))
reason_codes_hash = SHA-256("GRAF-CRITICALITY-POLICY\0reason-codes\0v1" ||
  uint64be(byte_length) || canonical_json(reason_codes))
policy_hash = SHA-256("GRAF-CRITICALITY-POLICY\0body\0v1" ||
  uint64be(byte_length) || canonical_json(policy_body))
```

Each `byte_length` is the length of the immediately following canonical JSON.
The root `criticality_policy` component version equals `policy_version` and its
hash equals `policy_hash`. The
extraction-layer manifest and canonical receipt bind exactly `policy_version`,
`canonical_rules_hash` and `reason_codes_hash`; they do not bind profile
expansion. `ResolvedRunManifestV1`, projection requests and the publication
receipt bind all fields. Any body/hash/profile-contract mismatch fails closed;
missing policy material cannot default to an empty critical set.

`RunComponentBindingV1` has exactly `component_key`, `name`, `version` and `hash`.
`name` is 1..240 UTF-8 bytes, version is positive uint32 and hash is lowercase
SHA-256. The required closed key set is:

```text
auto_selection_policy (Auto only)
auto_section_mapping_policy (Auto only)
auto_resolver_prompt (model-resolved Auto only)
auto_resolver_input_schema (model-resolved Auto only)
auto_resolver_response_schema (model-resolved Auto only)
auto_resolver_reason_codes (model-resolved Auto only)
auto_resolver_validator (model-resolved Auto only)
criticality_policy
gateway_route_binding
litellm_request_compiler
master_prompt_clause_registry
composite_profile_contract
projection_policy
projection_prompt
projection_response_schema
projection_validator
presentation_synthesis_prompt
presentation_synthesis_response_schema
presentation_synthesis_validator
presentation_verify_prompt
presentation_verify_response_schema
presentation_verify_reason_codes
presentation_verify_validator
outcome_content_schema
renderer
```

Every applicable key appears exactly once; no other key is legal. This is the
run-level closure embedded by `ResolvedRunManifestV1`, not the root-level
`RootComponentBindingV1` array in `ActivationManifestV1`. It deliberately binds
the exact root authorities consumed by this run, including registry/policy/
composite hashes, while the root array deliberately excludes authorities already
embedded as complete bodies. The two schemas are never interchangeable.
`composite_profile_contract` uses
`name="graf/composite-profile-contract/v1"`, `version=1` and the exact
`composite_profile_contract_hash`; it is typed run data, not a Langfuse prompt
name or label.
`auto_section_mapping_policy` uses
`name="graf/auto-section-mapping-policy/v1"`, `version=1` and the exact
`auto_section_mapping_policy_hash`; it is present only for Auto and is likewise
typed deterministic config rather than a prompt.

`PhaseEnvelopeV1` is a closed discriminated union with common keys `phase`,
`prompt_name`, `prompt_version`,
`prompt_hash`, `model_route`, `gateway_route_binding_hash`,
`request_compiler_binding_hash`, `request_settings_hash`, `input_schema_version`,
`input_schema_hash`, `output_schema_version`, `output_schema_hash`,
`max_input_tokens`, `max_output_tokens`, `context_window_tokens`,
`protocol_reserve_tokens`, `planned_call_count` and `max_calls`. Numeric fields
are positive uint32 except `planned_call_count`, which is uint32. Each phase has
only its own capacity keys; a generic `batch_capacity` is invalid:

| `phase` | Required capacity keys |
|---|---|
| `auto_resolve` | `max_canonical_profile_view_objects` |
| `profile_projection` | `max_projection_objects` |
| `presentation_synthesis` | `max_synthesis_items`, `max_synthesis_selected_ids` |
| `presentation_verify` | `max_verify_statements`, `max_verify_selected_critical_ids` |

`phase` is one of `auto_resolve`, `profile_projection`,
`presentation_synthesis` or `presentation_verify`; synthesis and verification
are always present, profile projection is always present for a publishable
non-empty result, and Auto is present only when its model call count is non-zero
and no resolver no-op proof is used. `model_route` is
1..128 ASCII bytes and equals the activated LiteLLM route. Settings hash covers
the exact allowlisted canonical request settings from the pinned root. The
compiler hash equals both the embedded gateway binding and the
`litellm_request_compiler` component. Each
derived envelope must satisfy
`max_input_tokens + max_output_tokens + protocol_reserve_tokens <=
context_window_tokens`; every capacity is independently derived from the exact
production tokenizer and maximal phase schema. Exact-fit and one-unit-over
fixtures exist for each capacity; no fixed 4048/4096 ceiling is implied.

Unknown keys, duplicate keys, `null`, a missing/duplicate component, a hash-only
Auto snapshot or a mutable reference to title/participants/duration are
rejected. Optional Auto/secondary/topic fields are omitted when inapplicable.
The manifest hash is:

```text
SHA-256("GRAF-RESOLVED-RUN\0v1" ||
        uint64be(manifest_body_byte_length) ||
        canonical_json(ResolvedRunManifestV1))
```

The durable request/idempotency identity includes the raw typed focus query,
its normalization version/value and authenticated scope before resolution; the
final manifest additionally binds the resolved canonical topic IDs. A
same-request replay may reuse only the exact body/hash. Feature 199 must version
this schema and the slot/receipt identity before any generated
`private_self`/subject-dependent result can bind authenticated subject,
participant-mapping snapshot/hash and access-policy epoch.

## `RequestSettingsV1`

Every model call freezes one closed canonical settings body before provider
serialization. `RequestSettingsV1` has exactly `schema_version=1`, `phase`,
`model_route`, `request_compiler_binding_hash`, `reasoning`, `verbosity`,
`structured_output`, `output_envelope` and `service_tier`:

- `phase` is exactly one of `extract`, `resolve`, `semantic_verify`, `repair`,
  `post_repair_reverify`, `auto_resolve`, `profile_projection`,
  `presentation_synthesis` or `presentation_verify`; `model_route` is the
  activated alias `gpt-5.6-luna`;
- `request_compiler_binding_hash` is the exact compiler hash embedded in the
  activated `GatewayRouteBindingV1`;
- `reasoning` is exactly `{presence:"omitted"}` or
  `{presence:"explicit",effort:"minimal"|"low"|"medium"|"high"}`; an
  explicit value must also occur in the binding's `reasoning_effort_domain`;
- `verbosity` is exactly `{presence:"omitted"}` or
  `{presence:"explicit",value:"low"|"medium"|"high"}`;
- `structured_output` has exactly `mode="json_schema"`, `strict=true`,
  `schema_name`, positive `schema_version` and `schema_hash`;
- `output_envelope` is exactly
  `{presence:"omitted",basis_hash}` or
  `{presence:"explicit",max_output_tokens,basis_hash}`. An explicit value is the
  route/schema-derived envelope, never a global 4048/4096 constant;
- `service_tier` is exactly `{presence:"omitted"}` or
  `{presence:"explicit",value:"auto"|"default"|"flex"|"priority"}`; an
  explicit value must also occur in the binding's `service_tier_domain`.

No temperature, top-p, seed, stop or unknown provider-facing inference setting
is legal in V1; supporting one requires a settings-schema upgrade and new bundle
evaluation. The compiler must preserve each omitted presence object, reject an
unsupported value/parameter and keep automatic summarization disabled. It may
not silently insert a route/provider default or drop a value. Canonical JSON
preserves the explicit presence objects, so omitted defaults never hash like
explicit values. The external phase-separated hash is:

```text
request_settings_hash = SHA-256(
  "GRAF-REQUEST-SETTINGS\0v1" ||
  uint16be(phase_utf8_byte_length) || phase_utf8 ||
  uint64be(settings_body_byte_length) ||
  canonical_json(RequestSettingsV1)
)
```

The body and hash are immutable GenerationCall fields, and the full body is also
inside `logical_request_json`. The finalizer recomputes the hash, requires phase
and route/compiler equality with the call/manifest and rejects settings accepted
only by SDK defaulting, parameter dropping, automatic summarization or mutable
metadata.

## GenerationCall binding V1

Feature 195 adds normalized immutable ownership fields to `generation_calls`:

| Field | Type | Rule |
|---|---|---|
| `execution_scope` | enum | `production` or `candidate_evaluation`; immutable before prepare completes |
| `owner_kind` | enum | `canonical_artifact` or `outcome_attempt`; nullable only for legacy calls |
| `canonical_artifact_id` | UUID | Required only for canonical owner |
| `outcome_generation_attempt_id` | UUID | Required only for attempt owner |
| `evaluation_run_id` | string/UUID | Required only for candidate-evaluation scope; one of the authority's frozen allowed run IDs |
| `phase` | enum | Allowed phase for the selected owner |
| `phase_sequence` | uint32 | Unique and gap-free inside `(owner, phase)` |
| `model_route` | string 1..128 | Exact activated route alias |
| `gateway_route_binding_hash` | hash | Exact activated gateway binding |
| `request_compiler_binding_hash` | hash | Exact embedded `LiteLLMRequestCompilerBindingV1` |
| `root_promotion_event_id`, `root_promotion_event_schema_version`, `root_promotion_event_version`, `root_promotion_event_hash` | UUID + uint32 + uint32 + hash | Required only for production; four normalized immutable members of the request's complete `root_promotion_event_binding` |
| `candidate_evaluation_authority_id`, `candidate_evaluation_authority_version`, `candidate_evaluation_authority_hash` | UUID + uint32 + hash | Required only for candidate-evaluation; reconstructs the complete pre-call `CandidateEvaluationAuthorityV1` body/hash |
| `request_settings_json`, `request_settings_hash` | canonical JSON + hash | Exact closed `RequestSettingsV1`; immutable before egress |
| `trace_id` | fixed string | W3C 32-lowercase-nonzero-hex trace bound to one Workflow ID/Run ID |
| `observation_id`, `parent_observation_id`, `root_observation_id` | fixed strings | W3C 16-lowercase-nonzero-hex span identities, immutable before export |

Every model call also has a durable invocation machine separate from Langfuse
delivery. Its normalized fields are `invocation_state`, positive
`invocation_state_version`, immutable `provider_correlation_id`, conditional
`invoke_attempt_id`, `sending_started_at_us`, `raw_response_body` plus
`raw_response_hash`, complete `no_provider_egress_proof` plus its hash and
complete ambiguity/reconciliation evidence. The state graph is exactly:

```text
prepared → sending → response_recorded
                   → failed_pre_egress
                   → ambiguous
ambiguous → response_recorded | failed_pre_egress
```

The retryable/idempotent prepare Activity writes the complete logical request,
settings, route/authority bindings and correlation ID and may perform no
gateway/provider I/O. The invoke Activity has Temporal
`maximum_attempts=1`; SDK, HTTP, LiteLLM and provider retries are all zero. It
must CAS `prepared → sending`, freeze one `invoke_attempt_id`, and commit before
the first operation capable of gateway/provider egress. Losing that CAS or
observing any state other than `prepared` permits zero egress. A repeated
Activity execution therefore re-reads `sending|response_recorded|
failed_pre_egress|ambiguous` and returns the durable state without sending.

`response_recorded` is written only by a cancellation-shielded transaction that
persists the exact raw response body/hash and authenticated provider identity
before validation returns to the Workflow. Timeout, disconnect, worker crash or
any outcome not durably classified becomes `ambiguous`; an orphaned `sending`
row is claimed only by the reconciler and never by an invoking worker.
Authoritative exact-correlation read-back may monotonically refine ambiguous to
response-recorded. Absence, list/search, cache state or eventual-consistent 404
does not prove non-egress.

`failed_pre_egress` requires a complete `ProviderNoEgressProofV1` from the
trusted gateway for the exact call/attempt/correlation/request. Its closed body
has exactly `schema_version=1`, `proof_version`, `proof_id`,
`generation_call_id`, `invoke_attempt_id`, `provider_correlation_id`,
`gateway_route_binding_hash`, `gateway_request_hash`, `gateway_receipt_id`,
immutable `gateway_authentication_binding`, `proved_at_us` and one closed
`reason_code` in `route_rejected_before_upstream | capacity_rejected_before_upstream |
transport_failed_before_upstream`. The gateway receipt must authenticate that
zero upstream provider egress occurred; a local guess or transport exception is
invalid. Its hash is:

```text
SHA-256("GRAF-PROVIDER-NO-EGRESS-PROOF\0v1" ||
        uint64be(proof_body_byte_length) ||
        canonical_json(ProviderNoEgressProofV1))
```

Only a terminal `failed_pre_egress` call with that fetched/rehashed proof may
authorize one bounded successor call. The successor has a new
`generation_call_id` and `invoke_attempt_id`, immutable
`predecessor_generation_call_id`, incremented phase retry ordinal and the same
logical-request/route/authority identity. `sending` or `ambiguous` never has a
successor. The owner receipt contains the one response-recorded validated call
for the phase and separately proves the complete predecessor chain; no failed
or ambiguous predecessor can be omitted, reused by another owner or mistaken
for a successful phase.

Exactly one production owner ID is non-null for every new receipt-eligible call.
It carries `PromotedRootBindingV1`/promotion-event authority and forbids every
candidate-evaluation member. A candidate-evaluation call has no artifact/
attempt owner, slot, receipt or DispatchIntent membership; it carries exactly
one allowed evaluation run ID plus the complete fetched/rehashed
`CandidateEvaluationAuthorityV1`, selects either its promoted baseline or
candidate root for the named arm, and forbids all four promotion-event columns
for the candidate arm. Scope/authority exclusivity is a database constraint and
is checked again before invoke. Canonical
phases are `extract`, `resolve`, `semantic_verify`, `repair` and
`post_repair_reverify`. Type-attempt phases are `auto_resolve`,
`profile_projection`, `presentation_synthesis` and `presentation_verify`.
Deterministic no-op phases create no fake GenerationCall.
Every Auto presentation-synthesis and presentation-verify logical request
embeds the complete Auto section-mapping policy and Auto presentation-profile
bodies/hashes byte-equal to its resolved-run manifest. The projection call
retains the hidden intent-composite section assignment; the deterministic
planner maps its selected IDs before synthesis and creates no extra call.
Non-Auto type calls reject any Auto mapping member.
`OutcomePublicationReceiptV1` rejects every continuity call, proof and rendered
section. Feature 207 must introduce a versioned continuity proof and version the
resolved-run manifest, publication receipt and content payload before either a
deterministic or model-based continuity path can publish; a model path must also
add its own GenerationCall phase and numeric envelope.

W3C validation is structural and relational, not a length-only check:

```text
trace_id:                ^(?!0{32}$)[0-9a-f]{32}$
observation/span IDs:    ^(?!0{16}$)[0-9a-f]{16}$
```

The trace row binds exactly one `trace_id` to one Temporal Workflow ID/Run ID and
one `root_observation_id` for the stable `application-root`. The call's
`observation_id` is single-assignment to that GenerationCall and cannot be
reused by another call or another trace. The parent and root must already exist
under the same trace; V1 GenerationCalls are direct root children, so
`parent_observation_id == root_observation_id`, while
`observation_id != parent_observation_id`. Replay reuses the persisted identity
of the same call. Uppercase, zero, wrong-length/non-hex, cross-trace parent/root,
second-root and any post-persistence mutation fail before export and receipt
finalization.

Every completed receipt member freezes this descriptor:

| Key | Type | Cardinality / null rule |
|---|---|---|
| `generation_call_id` | UUID | required |
| `owner_kind` | enum | required |
| `owner_id` | UUID | required; equals the artifact or attempt receipt owner |
| `phase` | enum | required; owner-compatible |
| `phase_sequence` | uint32 | required |
| `request_hash` | hash | required |
| `validated_result_hash` | hash | required |
| `model_route` | string 1..128 | required; byte-equal to owner manifest route |
| `request_settings_hash` | hash | required; recomputed from the immutable phase settings body |
| `gateway_route_binding_hash` | hash | required; byte-equal to the owner manifest and echoed by the gateway pre-egress check |
| `request_compiler_binding_hash` | hash | required; equal to route binding, settings body, root component and gateway echo |
| `root_promotion_event_binding` | `ImmutableArtifactBindingV1` | required; reconstructed from the call's four normalized immutable event fields and byte-equal to the compiled request/owner authority |
| `actual_provider` | string 1..128 | required |
| `actual_model` | string 1..128 | required |
| `provider_request_id` | string 1..240 | optional; omitted when upstream returned none |
| `invocation_state` | enum | required literal `response_recorded` for a receipt member |
| `invoke_attempt_id`, `provider_correlation_id` | UUID/string | required immutable exact invocation identity |
| `raw_response_hash` | hash | required; exact persisted response validated into `validated_result_hash` |
| `predecessor_chain_hash` | hash | required over the complete ordered zero-or-more failed-pre-egress predecessor descriptors/proofs |
| `trace_id` | 32 lowercase nonzero hex | required; exact bound Workflow trace |
| `observation_id` | 16 lowercase nonzero hex | required; unique single assignment |
| `parent_observation_id`, `root_observation_id` | 16 lowercase nonzero hex | required; existing same-trace application root in V1 |

`request_hash` and `validated_result_hash` are never hashes of an SDK object,
raw HTTP bytes or mutable metadata. The ledger persists two strict canonical
JSON bodies before finalization:

- `logical_request_json`: exact compiled system/developer messages, typed model
  input, selected numeric prompt/schema versions, route settings and structured
  output contract after all local assembly but before provider serialization,
  plus the exact applicable master-prompt clause ID/version/requirement-hash/
  disposition bindings from the closed registry and the complete
  `root_promotion_event_binding` reconstructed from the call's normalized event
  fields;
- `validated_result_json`: exact parsed result after strict schema validation
  and deterministic normalization, before any downstream projection or render.

Both bodies use the canonical JSON rules in this contract. Their hashes are
domain- and phase-separated with explicit length framing:

For `profile_projection`, `presentation_synthesis` and `presentation_verify`,
the typed model input is respectively the complete closed
`ProfileProjectionRequestV1`, `PresentationSynthesisRequestV1` or
`PresentationVerifyRequestV1`. Each embeds the same exact
`CompositeProfileContractV1` body/hash and compiled clause bindings. A logical
request that contains only a profile key/hash, fetches `profile/<key>`, or omits
the secondary contract is invalid even if its outer request hash recomputes.

```text
request_hash = SHA-256(
  "GRAF-GENERATION-CALL\0request\0v1" ||
  uint16be(phase_utf8_byte_length) || phase_utf8 ||
  uint64be(logical_request_byte_length) || logical_request_canonical_json
)

validated_result_hash = SHA-256(
  "GRAF-GENERATION-CALL\0validated-result\0v1" ||
  uint16be(phase_utf8_byte_length) || phase_utf8 ||
  uint64be(validated_result_byte_length) || validated_result_canonical_json
)
```

The phase is the exact lowercase enum stored on the call. Prefix, phase length,
payload length and payload bytes are all hashed; concatenated-field ambiguity is
impossible. The finalizer recomputes both from immutable bodies and rejects a
phase/body/hash mismatch. Raw provider response remains retained separately and
cannot replace the validated result. Normative per-phase vectors appear below.

Descriptors are ordered by the owner-specific fixed phase ordinal, then
`phase_sequence`, then UUID bytes. Canonical-artifact ordinals are
`extract=0`, `resolve=1`, `semantic_verify=2`, `repair=3` and
`post_repair_reverify=4`. Outcome-attempt ordinals are `auto_resolve=0`,
`profile_projection=1`, `presentation_synthesis=2` and
`presentation_verify=3`. The exact call-set formula is:

```text
SHA-256("GRAF-CALLSET\0v1" ||
        uint64be(canonical_descriptor_array_byte_length) ||
        canonical_json(complete_descriptor_array))
```

A DB trigger finalizing a
receipt locks each referenced call in the global order defined below, requires
`call_state=completed`, exact
workspace/meeting/owner/phase/value equality, freezes the normalized columns
and rejects an unlisted eligible call for that owner/run. Existing
`actual_provider`, `actual_model` and optional `provider_request_id` columns are
authoritative; mutable metadata JSON cannot substitute for them.
The call is receipt-ineligible unless its route/compiler-binding hashes equal
the pinned descriptor/settings/root components, both gateway echoes match, its
actual provider/model pair is present in the route allowlist and every W3C
identity/parent/root invariant above holds. An alias or syntactically valid span
ID without those checks is insufficient.

Canonical receipts allow 2..1,023 call bindings under the bundle's lower
phase-specific limits. A passing canonical call set has:

- `extract`: 1..511 calls;
- `resolve`: 1..128 calls XOR one `resolve_noop_proof`;
- `semantic_verify`: 1..128 calls whose strict outputs jointly cover every
  canonical claim, every source-catalog span and every source→candidate and
  candidate→canonical omission partition;
- `repair`: zero calls, or 1..128 calls in exactly one repair round;
- `post_repair_reverify`: zero calls when repair is absent, otherwise 1..128
  calls ordered after all repair calls and jointly re-covering the complete
  semantic and two-level omission obligations.

Publication receipts allow 3..385 calls: at most one `auto_resolve`, 1..128
`profile_projection`, 1..128 `presentation_synthesis` and 1..128
`presentation_verify` calls. A published non-empty result always has both
presentation phases and profile projection. An Auto run with no resolver call
requires `resolver_noop_proof`, which is mutually exclusive with an
`auto_resolve` call. V1 has no no-op path for profile projection, presentation
synthesis or presentation verification: the extra branch saved no user-visible
latency because synthesis is mandatory, while it weakened per-profile proof.

## Canonical and Auto deterministic no-op proof schemas

`resolve_noop_proof` is allowed only for a canonical artifact whose complete
validated candidate set needs no model merge or reconciliation. It has exactly
these keys:

| Key | Type / rule |
|---|---|
| `resolver_version` | positive uint32; deterministic canonical resolver pinned by the extraction-layer manifest |
| `resolver_hash` | hash of the exact implementation/configuration identity |
| `candidate_ids_hash` | coverage hash of the complete ordered candidate-ID array |
| `canonical_ids_hash` | coverage hash of the complete ordered canonical-ID array |
| `relation_graph_hash` | exact resulting typed relation graph hash |
| `reason` | `single_partition_no_cross_candidate_relation` or `deterministic_identity_resolution` |

It is mutually exclusive with every `resolve` GenerationCall. The finalizer
reconstructs both ordered ID arrays and the relation graph from the locked
artifact/candidates and rejects a call/proof overlap, missing proof, changed
mapping or a candidate set containing an unresolved cross-partition correction,
conflict, duplicate or relation.

`resolver_noop_proof` has exactly these keys; unknown keys and `null` are
rejected:

| Key | Type / rule |
|---|---|
| `resolver_version` | positive uint32; exact deterministic resolver version pinned by the resolved-run manifest |
| `resolver_policy_hash` | hash; exact resolver policy pinned by the root bundle |
| `auto_resolver_input_hash` | hash of the exact reconstructed `AutoResolverInputV1` payload defined below |
| `resolution_mode` | `deterministic_low_confidence_fallback`, `single_compatible_profile`, or `policy_forced_profile` |
| `reason` | `insufficient_distinctive_evidence`, `complete_view_exceeds_envelope`, `single_compatible_profile`, or `policy_forced_profile` |
| `confidence_class` | `low` for `deterministic_low_confidence_fallback` and `single_compatible_profile`; `not_applicable` for `policy_forced_profile`; equals `ProfileResolutionV1` |
| `resolved_primary_profile_key` | non-empty catalog key; equals the receipt primary profile |
| `resolved_secondary_profile_key` | optional non-empty catalog key; present iff the receipt secondary profile is present and equal |

It is allowed only for `template_key=auto` with no `auto_resolve` call. For a
non-Auto template both the Auto call and this proof are absent.

### Strict Auto input, result and deterministic selection

`AutoResolverInputV1` is the only legal model-Auto input and the authoritative
basis for deterministic Auto no-op proofs. Input and result are deliberately
different schemas: no resolved profile, confidence or resolution mode appears
in the input, and the model result cannot select those values.

The full input has exactly these required keys plus the one explicitly optional
policy key. Unknown keys, duplicate keys and `null` are rejected:

| Key | Type / authoritative source |
|---|---|
| `schema_version` | integer literal `1` |
| `workspace_id`, `meeting_id` | canonical lowercase UUIDs from the locked attempt/meeting scope |
| `source_basis_hash` | exact locked attempt/artifact source basis |
| `canonical_payload_hash`, `canonical_verification_receipt_digest` | exact verified parent identities |
| `resolver_version`, `resolver_policy_hash` | positive uint32 and exact root-bundle selection-policy hash |
| `meeting_metadata` | exact nested `MeetingMetadataForAutoV1` below |
| `meeting_intent` | exact `MeetingIntentV1`; source-supported intent carries canonical refs, never raw agenda/transcript text |
| `compatible_profile_keys` | 1..64 unique catalog keys allowed by the pinned root plus current policy, ascending by exact UTF-8 bytes |
| `fallback_profile_key` | literal `general_summary`, present in `compatible_profile_keys` |
| `policy_forced_profile_key` | optional; present only when locked policy forces one compatible profile |
| `canonical_profile_view` | the complete 0..16,384 ordered `AutoCanonicalObjectV1` array; never a sample |
| `canonical_evidence_index` | complete ordered `AutoClaimEvidenceIndexV1` array binding every claim to its source-segment identities without transcript quotes |
| `canonical_claim_coverage`, `canonical_relation_coverage`, `canonical_evidence_coverage` | exact complete coverage objects recomputed from the view/index and parent artifact |

`AutoCanonicalObjectV1` has exactly required `claim_id`, `kind`, `text`,
`trusted_role_refs`, `relation_refs` and `uncertainty_codes`, plus `state`/
disposition and `effective_time` iff the canonical kind has them. Codes are the
unique ASCII-sorted closed `UncertaintyV1` codes; they carry no free prose.
`text` is the exact 1..800-byte canonical claim text, not transcript prose
or an evidence quote. A trusted role ref has exactly `participant_id` and an
allowlisted role from pinned GRAF metadata; model/self-reported roles are
omitted. A relation ref has exactly `relation_type` and `target_claim_id`.
Objects sort by claim ID; roles by participant ID/role; relations by
relation-type/target ID. Every target exists in the same complete view. Raw
transcript, evidence quotes, agenda text, names without trusted identity and
model-generated role labels are forbidden.

`AutoClaimEvidenceIndexV1` has exactly `claim_id` and
`source_segment_ids`. There is one entry for every object in
`canonical_profile_view`, sorted by claim ID; segment IDs are 1..128-byte stable
UTF-8 identifiers, unique and sorted by exact bytes. The array is reconstructed
from the locked canonical object's validated evidence refs. It contains no quote,
speaker name, transcript text or model-authored diversity flag. A high-stakes
selection counts distinct segments only from the union of this array for the
supporting claim IDs.

Claim coverage hashes the complete ordered object-ID array; relation coverage
hashes the complete ordered `(source_claim_id, relation_type, target_claim_id)`
array; evidence coverage hashes the complete ordered
`(claim_id, source_segment_ids)` array. In all three coverage objects
`covered_count == total_count`; the counts and hashes must equal the locked
parent artifact. The sum of kind counts, a title or a sampled subset cannot
substitute for this view/index.

`AutoResolverInputDescriptorV1`, stored inside `ResolvedRunManifestV1`, has
exactly `schema_version`, `meeting_metadata`, `meeting_intent`, `compatible_profile_keys`,
`fallback_profile_key`, `canonical_claim_coverage` and
`canonical_relation_coverage`, `canonical_evidence_coverage`, plus optional
`policy_forced_profile_key`. The
full view is not duplicated into the attempt row: the finalizer reconstructs it
from the locked immutable canonical artifact and the descriptor, then compares
the separate `auto_resolver_input_hash`. A model path additionally requires the
exact full input in the immutable GenerationCall logical request. Mutable title,
participant, duration, catalog or policy rows are never consulted to recreate
the historical descriptor.

`MeetingMetadataForAutoV1` has exactly required `title` and
`participant_count`, plus optional `duration_us`. `title` is the exact locked
GRAF meeting title as a 0..1,024-byte UTF-8 string; `participant_count` is a
non-negative uint32 count of unique authorized participant identities in the
pinned meeting snapshot; `duration_us`, when the pinned source has a duration,
is its non-negative signed-64-bit microsecond value. No V1 resolver may read
another meeting-metadata field. Adding a field or changing derivation/order
requires a new evidence schema and resolver version.

Allowed canonical kinds are exactly the closed Feature 194 V1 kind enum:
`action`, `blocker`, `correction`, `decision`, `dependency`, `event`, `fact`,
`feedback`, `hypothesis`, `idea`, `interview_exchange`, `learning`, `metric`, `motion`,
`option`, `proposal`, `question`, `requirement`, `resolution`, `risk`, `topic`,
`tradeoff` and `vote`. The finalizer requires the complete view length and claim
coverage count to equal the authoritative canonical-object count.

The full input hash is:

```text
SHA-256("GRAF-AUTO-INPUT\0v1" ||
        uint64be(input_payload_byte_length) ||
        canonical_json(AutoResolverInputV1))
```

`AutoResolverResultV1` has exactly `schema_version=1`, `result=complete`,
`auto_resolver_input_hash`, `reason_code_version=1`, `assessments` and
`overflow_detected=false`. `assessments` contains exactly one
`ProfileAssessmentV1` for every compatible profile, sorted by profile key.
Missing, extra or duplicate profiles reject the call.

`ProfileAssessmentV1` has exactly `profile_key`, `fit_class`, `signals` and
`contraindications`. `fit_class` is `strong`, `plausible`, `weak` or
`contraindicated`. Each signal/contraindication has exactly `reason_code` and
0..32 unique UTF-8-sorted `evidence_claim_ids`; positive signal codes require at
least one ID. Codes use the closed versioned catalog in `prompt-pipeline.md` and
must be allowlisted by that exact profile contract. Every ID must exist in the
input view. The result has no free text, profile selection, confidence, title,
raw transcript or unknown extension. Provider/schema/overflow/failure output is
non-publishable and creates no pass receipt.

`AutoSelectionProofV1` has exactly `selection_policy_version`,
`selection_policy_hash`, `auto_resolver_input_hash`,
`auto_resolver_result_hash`, `assessments_hash`,
`canonical_evidence_coverage_hash`, `ranked_profile_keys`,
`resolved_primary_profile_key`, `confidence_class` and `decision_code`, plus
optional `resolved_secondary_profile_key`. The ranked keys are the exact
serialization defined by `summary-profile-catalog.md`: resolved primary first;
other eligible specialized profiles by descending deterministic score and UTF-8
key only for equal-score serialization; ineligible specialized profiles by
UTF-8 key; then `general_summary` iff it is not primary. The array is a
permutation of `compatible_profile_keys`, and UTF-8 order never breaks a semantic
tie. `decision_code` is `unique_supported_primary`,
`supported_primary_with_secondary` or `low_confidence_general_fallback`. The
proof is valid only with exactly one
completed `auto_resolve` GenerationCall whose validated-result hash equals the
proof result hash and whose immutable logical request contains the full input
matching the input hash. Final selection follows the eligibility, high-stakes,
near-neighbor and fallback rules in `prompt-pipeline.md`; the model cannot
override them. The evidence-coverage hash must equal the reconstructed full input
index; supporting IDs that do not map to the profile's required groups or to the
required number of distinct source segments cannot authorize a specialized
selection.

`assessments_hash` is
`SHA-256("GRAF-AUTO-ASSESSMENTS\0v1" || uint64be(byte_length) ||
canonical_json(assessments))`, recomputed from the strict result. The
`auto_resolver_result_hash` is exactly the call binding's
`validated_result_hash` under the phase-separated GenerationCall formula below;
there is no second result-hash algorithm.

Mode invariants are exact:

- `model_resolved` requires exactly one Auto call plus `AutoSelectionProofV1`,
  forbids `resolver_noop_proof`, and may itself resolve low-confidence
  `general_summary` only through `decision_code=low_confidence_general_fallback`;
- `deterministic_low_confidence_fallback` has no Auto call or selection proof,
  no forced profile or secondary, primary `general_summary`, confidence `low`
  and no-op reason `insufficient_distinctive_evidence` or
  `complete_view_exceeds_envelope`;
- `single_compatible_profile` has no Auto call or selection proof, requires
  `compatible_profile_keys=[general_summary]`, primary `general_summary`, no
  secondary, confidence `low` and reason `single_compatible_profile`;
- `policy_forced_profile` has no Auto call or selection proof, requires the
  forced key to equal primary, forbids a secondary, uses confidence
  `not_applicable` and reason `policy_forced_profile`.

A complete view over the derived Auto envelope uses deterministic low-confidence
with `complete_view_exceeds_envelope` before egress; sampling is forbidden.

The finalize-and-publish transaction reads the frozen descriptor from the
locked attempt, reconstructs the full input from the locked canonical artifact,
recomputes its hash and compares every policy/profile/mode field with the proof,
GenerationCall, resolved-run manifest, artifact and receipt. A caller-supplied
hash without reconstructable authoritative bodies is invalid. Editing current
title, participant mapping, catalog or duration after the snapshot neither
changes nor invalidates historical bytes.

### `AttemptTerminalEvidenceV1`

Zero eligible IDs, zero selected IDs after complete projection, and topic
no-match/ambiguity are terminal `no_supported_content`, not successful empty
publication. Topic-catalog overflow is a terminal `blocked` attempt using the
same non-authorizing evidence shape. The attempt stores one closed evidence body
with exactly:

```text
schema_version = 1
attempt_id + workspace_id + meeting_id + artifact_id
source_basis_hash + canonical_verification_receipt_digest
bundle_root_version/hash + activation_manifest_hash
root_promotion_event_binding = complete ImmutableArtifactBindingV1
extraction_layer_manifest_hash
profile_key/version
controls_request_hash
resolved_focus = optional final FocusV1
reason = no_eligible_items | no_selected_items |
         focus_no_supported_topic | focus_ambiguous |
         focus_topic_catalog_capacity_exceeded
eligible_coverage + selected_coverage + omitted_coverage
projection_call_set_hash = optional, required iff projection calls completed
recovery_capabilities_hash
next_action = switch_type | open_transcript
authorizes_publication = false
```

Unknown/null keys are rejected except the two explicitly optional fields, which
are omitted when inapplicable. The evidence is stored on the terminal attempt,
is not a `CanonicalVerificationReceiptV1` or `OutcomePublicationReceiptV1`, and
cannot satisfy any FK, call-set or finalizer gate. No candidate/content/slot
mutation exists on this path. Its promotion binding must still reconstruct the
same successful event as the attempt's resolved-run authority; terminal truth
cannot be written under an unqualified or hash-only root. Exact zero-eligible,
nonzero-eligible/zero-selected,
topic no-match/ambiguity/catalog-overflow and previous-current preservation
fixtures are mandatory. `recovery_capabilities_hash` binds the frozen authorized
type/transcript/focus-control capabilities used by the public recovery mapper.
Focus no-match/ambiguity/overflow deterministically maps to `open_transcript`;
the normal focus editor remains available when authorized, but `change_focus` is
not a public `next_action`. Zero eligible/selected maps to `switch_type` only
when at least one other available type exists in that snapshot, otherwise
`open_transcript`. This family never emits `wait`, `retry_safe`,
`correct_transcript_language`, bare `retry` or `wait_for_source_change`.

## `SourceVerificationCatalogV1`

The omission universe is compiled before any semantic-verifier call and is never
chosen by a model. The exact catalog body has these keys:

```text
schema_version = 1
source_basis_hash
normalization_version
catalog_compiler_version + catalog_compiler_hash
target_span_max_utf8_bytes
context_before_max_utf8_bytes + context_after_max_utf8_bytes
spans
```

Versions and byte limits are positive uint32 values. `catalog_compiler_hash` is
the lowercase SHA-256 identity of the exact deterministic implementation/config
that is pinned by the extraction-layer manifest and golden split vectors.
`spans` contains 0..32,768 `SourceVerificationSpanV1` objects ordered by
`(source_id UTF-8, segment_id UTF-8, start_utf8_byte, end_utf8_byte)`. Each has
exactly `source_span_id`, `source_id`, `segment_id`, `start_utf8_byte`,
`end_utf8_byte` and `normalization_version`. IDs are 64 lowercase hex characters;
source/segment IDs are 1..128 UTF-8 bytes; ranges are non-empty uint32 values
within the exact normalized segment text.

The canonical verifier planner also receives the complete canonical-claim count
from the locked artifact. It must prove, before any verifier egress,
`ceil(canonical_claim_count / verification_claims_per_call) <= 128` and
`ceil(span_count / verification_spans_per_call) <= 128`, with both per-call
capacities pinned to 256 in the active extraction-layer manifest. It then emits
paired calls in which each claim and each span appears exactly once and neither
population exceeds 256. These planner bounds are part of `capacity_passed`; a
failed bound or an unpaired population is non-publishable.

For each segment with non-empty normalized bytes, its spans start at byte zero,
end at the exact segment byte length and form one gap-free non-overlapping
partition. An empty normalized segment contributes no span. Every span is at
most `target_span_max_utf8_bytes`; split points are produced only by the pinned
compiler and never shifted by a verifier. Adjacent bounded context is request
context only and never changes target identity or coverage. A span ID is:

```text
SHA-256("GRAF-SOURCE-VERIFY-SPAN\0v1" ||
        uint64be(descriptor_byte_length) ||
        canonical_json({source_id,segment_id,start_utf8_byte,
                        end_utf8_byte,normalization_version}))
```

The external catalog hash is:

```text
SHA-256("GRAF-SOURCE-VERIFY-CATALOG\0v1" ||
        uint64be(catalog_body_byte_length) ||
        canonical_json(SourceVerificationCatalogV1))
```

Every passing canonical verification reconstructs the catalog and contains one
`SourceSpanVerdictV1` per catalog span, in the same order, with exactly
`source_span_id`, `classification`, `reason_code`, `mapped_candidate_ids` and
`generation_call_id`. Classification is `critical|non_critical`; reason code is
valid for the source-span population in the pinned policy; candidate IDs are
unique UTF-8 sorted and exist in the authoritative candidate set. A non-critical
verdict has an empty candidate array. A critical verdict with an empty array is
one source→candidate omission; a non-empty array proves only mapping coverage,
not entailment. Unknown/duplicate/reordered/missing verdicts, a changed span,
catalog overflow or more than 128 verifier calls invalidate the artifact rather
than becoming a zero-critical pass.

## Coverage hashes

Every coverage object contains exactly `total_count`, `covered_count` and
`coverage_hash`. Counts are non-negative uint32 and the hash is lowercase
SHA-256. Coverage input arrays are recomputed from authoritative source ranges,
candidate IDs or canonical IDs, not trusted from receipt JSON.

- Source ranges: sorted by `(source_id, start_segment, end_segment)`, non-empty,
  non-overlapping and gap-free for the declared source partition.
- UUID/claim ID sets: unique and sorted by exact UTF-8 bytes.
- Omitted projection entries: unique and sorted by canonical ID, each with one
  closed reason enum: `not_profile_relevant`, `detail_budget`,
  `audience_forbidden`, `superseded`, or `unsupported_relation`.

Each array hash uses
`SHA-256("GRAF-COVERAGE\0v1" || uint64be(byte_length) || canonical_json_bytes)`.
Final pass requires complete source/candidate coverage, an exact disjoint
`selected ∪ omitted = eligible` projection partition, and zero omitted critical
items. Pagination is selected coverage, not omission.

`CriticalityPolicyV1` adds three mandatory reconstructed populations:

- `source_criticality_coverage` covers every exact
  `SourceVerificationCatalogV1` span ID with one `SourceSpanVerdictV1` carrying
  `classification=critical|non_critical` and one closed reason;
- `candidate_criticality_coverage` covers every candidate ID and the
  deterministic union of source classification plus canonical-policy rules;
- `canonical_criticality_coverage` covers every canonical ID and propagates the
  union of all contributing candidate classifications without downgrade.

Each uses the same `{total_count,covered_count,coverage_hash}` shape over the
complete ordered classification objects and requires total=covered. Source total
and hash must equal the reconstructed catalog count/verdict array. Separate
`critical_count` and `critical_ids_hash` fields are recomputed for each
population. A zero critical count is valid only with a complete non-empty or
legitimately empty source partition and complete candidate/canonical coverages;
a missing/partial verifier output cannot serialize as zero. Projection adds the
profile-expansion IDs deterministically and records their count/hash separately;
`non_droppable_ids` equals canonical-critical ∪ profile-expanded IDs after
authorization and relevance rules.

Each `source_to_candidate_omissions` and
`candidate_to_canonical_omissions` value is an exact
`CriticalOmissionFindingV1` object with only these keys:

| Key | Type / rule |
|---|---|
| `missing_count` | non-negative uint32 |
| `missing_ids_hash` | lowercase SHA-256 over the authoritative missing-ID array |

The authoritative array contains unique stable 1..128-byte UTF-8 critical span
or candidate IDs, sorted by exact UTF-8 bytes. It is reconstructed from verifier
coverage, not read from receipt JSON. `missing_ids_hash` uses the same exact
`GRAF-COVERAGE\0v1` length-framed canonical-array algorithm above, and
`missing_count` must equal the reconstructed array length. Unknown keys, `null`,
negative/out-of-range counts, duplicate/out-of-order IDs, count mismatch and
hash mismatch invalidate the receipt. A passing canonical receipt requires both
missing counts to be zero; the empty-array hash is still recomputed.
Any nonzero source→candidate missing count is terminal in V1 and cannot enter
`RepairRequestV1`. Candidate→canonical omissions may enter the one repair round
only through the explicit `missing_candidate_ids` union; post-repair reverify
must reconstruct both omission populations from scratch.

For projection, `eligible_coverage.total_count =
eligible_coverage.covered_count = |eligible|`. Selected and omitted objects both
repeat `total_count = |eligible|`; their `covered_count` values are the sizes of
their respective arrays. Eligible/selected hashes cover ordered canonical-ID
arrays. The omitted hash covers ordered objects with exactly `canonical_id` and
`reason`. Final pass requires selected plus omitted covered counts to equal the
eligible count and the reconstructed sets to be disjoint and exhaustive.

`presentation_statement_coverage` uses the same three-key coverage shape over
the authoritative ordered array of objects with exactly `section_key`,
`item_sequence`, `statement_sequence`, `start_utf8_byte`,
`end_utf8_byte` and `canonical_claim_ids`. Its total and covered counts must
equal the number of `PresentationStatementV1` values in the reconstructed
content payload. Every statement has exactly one strict presentation-verifier
verdict bound to a `presentation_verify` GenerationCall:

```text
statement identity
generation_call_id
entailment = entailed | contradicted | ambiguous | unsupported
numbers_faithful = true | false
negation_faithful = true | false
state_faithful = true | false
effective_date_faithful = true | false
uncertainty_faithful = true | false
language_faithful = true | false
reason_code = one closed versioned presentation-verifier code
```

The receipt stores those entries as `presentation_verdicts`, sorted by
`(section_key UTF-8, item_sequence, statement_sequence, start_utf8_byte,
end_utf8_byte)`. Every entry has exactly the fields shown above plus the
statement's sorted `canonical_claim_ids`; its span and IDs must byte-equal the
authoritative statement descriptor. `presentation_reason_code_version=1` is
mandatory. Its closed reason-code enum is verdict-compatible:

- `entailed`: `faithful_direct_realization`, `faithful_combined_realization`,
  `faithful_translation`;
- `contradicted`: `number_or_unit_changed`, `negation_changed`,
  `state_changed`, `effective_date_changed`, `uncertainty_removed`,
  `attribution_changed`, `meaning_changed_in_translation`;
- `ambiguous`: `ambiguous_realization`, `ambiguous_effective_date`,
  `ambiguous_uncertainty_rendering`, `ambiguous_translation`;
- `unsupported`: `uncited_bridge_claim`, `unsupported_rationale`,
  `unsupported_advice`, `missing_entailing_claim`.

A pass requires `entailed`, one of its compatible codes and all six booleans
true for every statement.
`presentation_claim_coverage` covers the ordered union of canonical claim IDs
across those statements; it must equal `selected_coverage`. The finalizer
separately reconstructs the selected critical-ID subset and requires every ID
to be present. Invalid/missing/duplicate/out-of-order verdicts, a verdict bound
to another owner/phase, an uncovered statement, an unrealized selected ID or an
extra canonical ID reject publication.

## Canonical artifact and rendered outcome hashes

`canonical_payload_hash` is SHA-256 over domain
`GRAF-CANONICAL-ARTIFACT\0v1`, byte length and canonical JSON of the complete
Feature 194 artifact payload. `relation_graph_hash` uses domain
`GRAF-CANONICAL-RELATIONS\0v1` over the ordered typed relation array. The
artifact UUID, receipt and mutable lifecycle timestamps are excluded from those
payloads and bound separately, preventing hash self-reference.

For every new rendered revision, existing `MeetingOutcomeSet.content_hash` and
receipt `outcome_content_hash` are the same lowercase SHA-256 over domain
`GRAF-OUTCOME-CONTENT\0v1`, byte length and the strict canonical JSON payload
below. Every object rejects unknown keys and `null`; optional keys are omitted.

The root has exactly these required keys plus the optional secondary-profile
triple and the conditional Auto-only quartet below:

| Key | Type / rule |
|---|---|
| `template_key` | UTF-8 string 1..120 bytes; byte-equal to slot/attempt/outcome |
| `template_version` | positive uint32 |
| `output_language` | BCP-47 string 1..16 ASCII bytes; byte-equal to the existing outcome/API field and applied only by presentation synthesis |
| `audience_context` | exact shared-slot `AudienceContextV1`; mixed mode uses the bound authorization intersection |
| `privacy_policy` | exact `PrivacyPresentationPolicyV1`; byte-equal to resolved-run controls |
| `focus` | exact `FocusV1` discriminated union below |
| `detail_budget` | exact `DetailBudgetV1`, including total non-critical and overview limits |
| `evidence_presentation_policy` | exact `EvidencePresentationPolicyV1`; requested value/display mode/policy hash equal resolved-run controls and Receipt V1 rejects evidence off |
| `fixed_schema` | literal `false` in shared built-in Receipt V1 |
| `analysis_mode` | literal `facts_only` in Receipt V1 |
| `primary_profile_key`, `primary_profile_version`, `primary_profile_contract_hash` | non-empty catalog key, positive uint32 and exact activated contract hash |
| `secondary_profile_key`, `secondary_profile_version`, `secondary_profile_contract_hash` | optional triple; all present or all absent |
| `composite_profile_contract`, `composite_profile_contract_hash` | complete exact `CompositeProfileContractV1` body and recomputed hash used by projection, presentation and render; byte-equal to `ProfileResolutionV1` |
| `auto_section_mapping_policy`, `auto_section_mapping_policy_hash`, `auto_presentation_profile_contract`, `auto_presentation_profile_contract_hash` | required together iff `template_key=auto`; complete exact `AutoSectionMappingPolicyV1` and catalog Auto profile v3 bodies plus recomputed hashes, byte-equal to `ProfileResolutionV1`; forbidden for every other template |
| `projection_policy_version`, `presentation_schema_version`, `renderer_version` | positive uint32 |
| `sections` | array of 1..256 `SectionV1` values |

`FocusV1` has exactly one of these shapes:

```text
{ "mode": "all_material" | "decisions" | "risks" | "commercial" }

{
  "mode": "topic",
  "focus_query": {
    "kind": "canonical_topic" | "text",
    "value": <1..512 UTF-8 bytes>,
    "normalized_value": <1..512 UTF-8 bytes>,
    "normalization_version": <positive uint32>
  },
  "resolved_canonical_topic_ids": <1..64 unique stable IDs, UTF-8 sorted>
}
```

For non-topic modes, `focus_query` and topic IDs are forbidden. For
`canonical_topic`, normalized value is the exact canonical topic ID and the
resolved array contains it. For `text`, value is untrusted user data;
normalization is deterministic and the resolved IDs are the exact validated
output of profile-projection batch zero over the complete bounded canonical
topic catalog. `FocusRequestV1` is the same union without
`resolved_canonical_topic_ids`; it is the only legal pre-resolution control.
Batch zero binds that request and catalog hash, returns the IDs, and later
projection batches receive final `FocusV1`. No separate or hidden model call is
allowed. More than 64 topics is the separate typed
`focus_topic_catalog_capacity_exceeded` failure; no match or ambiguous match is
a terminal attempt with `AttemptTerminalEvidenceV1`. None may fall back to
`all_material`. The raw typed query, normalized value/version
and resolved IDs are members of durable request identity,
`ResolvedRunManifestV1`, this content payload and the publication receipt.
Changing any one creates a different identity and hash.

`my_actions` is not a generated shared-slot focus. Receipt V1 rejects it,
`private_self` and every subject-dependent generated format. Feature 183 defines
no positive read-time `my_actions` behavior: Feature 205 must first own canonical
actions and trusted subject↔participant mapping, after which Feature 196 may add
an authenticated zero-inference read filter with no model call or shared
revision. Feature 199 rejects generated private output; Feature 208 must first
add an owner-bound personal template plus a subject-scoped slot/receipt version
before any such output.

`SectionV1` has exactly `section_key` (1..128 UTF-8 bytes),
`section_sequence` (uint32), `pages` (0..16,384 `PageV1` values) and conditional
`empty_state_code`. Section sequences start at zero and are gap-free across the
rendered sections; keys are unique and preserve the relative order of the
applicable profile's `section_order`. `PageV1` has exactly `page_sequence`
(gap-free uint32 inside the section), `has_more` (boolean) and `items`
(1..16,384 `VisibleItemV1` values). `has_more` is true iff another page for that
section follows; the last page is false. An empty section is legal only as
`pages=[]` plus `empty_state_code="not_recorded"`, only when its key is present
in the applicable primary profile's `empty_state_section_keys`; every other
empty section is omitted. A non-empty section has 1..16,384 pages and forbids
`empty_state_code`; empty pages are never serialized. The complete payload
contains at most 16,384 visible items.

For non-Auto content, section keys/order/contracts come from the complete
composite profile. For Auto they are exactly `action_items`, then `key_points`,
from the embedded Auto profile v3 body and mapping policy. Auto v3 has
`empty_state_section_keys=[]`, so either section is omitted when it has no items
and at least one non-empty section is required. Every visible item
whose canonical category is `action` occurs only in `action_items`; every other
visible item occurs only in `key_points`. The union equals the receipt's exact
selected canonical-ID set with no duplicate or omission. The dynamic resolved
intent composite remains present for eligibility, ranking, criticality and
safety but cannot contribute a third visible Auto section.

`VisibleItemV1` has these exact keys:

| Key | Type / rule |
|---|---|
| `category` | `decision`, `action`, `question`, `option`, `tradeoff`, `event`, `metric`, `motion`, `vote`, `resolution`, `interview_exchange`, `risk`, `blocker`, `dependency`, `fact`, `proposal`, `hypothesis`, `idea`, `requirement`, `feedback`, `learning`, `correction`, or `topic` |
| `sequence` | uint32; starts at zero and is gap-free across all pages in its section |
| `state` | conditional non-empty 1..64 ASCII key: required iff every supporting canonical claim's kind/state/disposition projection has one compatible visible value; forbidden for stateless kinds |
| `text` | visible UTF-8 text 1..4,096 bytes and within the pinned profile/detail budget |
| `owner_text`, `due_date_text`, `effective_date_text` | optional visible UTF-8 strings 1..512 bytes; omitted when unsupported and each date preserves its evidenced expression/normalization |
| `uncertainties` | 0..32 closed `UncertaintyV1` values, sorted by `(code, subject_field, evidence refs)` and byte-equal to the selected canonical projection |
| `needs_confirmation` | boolean; exact OR of the item's material uncertainty flags, never a prompt to interrupt routine generation |
| `truth_label` | literal `canonical_fact` in Receipt V1 |
| `canonical_claim_ids` | 1..256 unique stable IDs, sorted by exact UTF-8 bytes |
| `evidence_refs` | 1..1,024 unique `EvidenceRefV1` values in the order below |
| `presentation_statements` | 1..64 ordered `PresentationStatementV1` span descriptors covering the synthesized text |

`PresentationStatementV1` has exactly `statement_sequence` (gap-free
uint32), `start_utf8_byte`, `end_utf8_byte` and
`canonical_claim_ids`. Ranges are ordered, non-overlapping, non-empty and
jointly cover every non-whitespace byte of `text`; claim IDs are unique,
UTF-8 sorted and a subset of the item's IDs. The same canonical ID may support
multiple statements. This is the authoritative unit for presentation
verification; prose sentence-boundary guessing is not used at publication.

The content validator derives state/disposition presence, effective-date fields
and uncertainties from the pinned canonical kind/state matrix and selected
claim IDs. A missing required state, invented
state on `fact`, `metric`, `topic`, `hypothesis` or another stateless kind, or a
single visible item that merges incompatible states fails before hashing.
Dropping/changing an uncertainty, inventing an effective date, or setting
`needs_confirmation` inconsistently likewise fails before hashing.

`EvidenceRefV1` has exactly `source_id` and `segment_id` (each 1..128 stable
UTF-8 bytes), `start_utf8_byte` and `end_utf8_byte` (uint32 with end greater
than start), and positive uint32 `normalization_version`. Evidence refs are
sorted by `(source_id UTF-8, segment_id UTF-8, start_utf8_byte,
end_utf8_byte, normalization_version)`. Receipt V1 has no analysis item. A later
analysis mode requires its own versioned phase/schema/verifier/manifest/content/
receipt and policy contract before it can produce any visible text.

Presentation synthesis may formulate and translate only the selected canonical
IDs. Presentation verification compares every statement with those canonical
objects/evidence and returns strict verdicts for entailment, numbers, negation,
decision/action state and requested-language fidelity. It also checks that
every selected critical canonical ID appears in at least one statement.
Deterministic rendering supplies only section order, pagination, headings,
owner/date formatting, evidence controls and UI markup; it cannot invent or
rewrite prose.

The payload excludes `outcome_set_id`, attempt/receipt digests, database
timestamps and lifecycle/provenance columns, all of which are bound separately.
The publication finalizer reconstructs it from locked normalized rows, checks
all ordering/cardinality invariants, and never trusts a supplied hash.

## `CanonicalVerificationReceiptV1`

Required top-level keys, in semantic groups:

| Keys | Type / rule |
|---|---|
| `schema_version`, `receipt_kind` | integer `1`; literal `canonical_verification` |
| `artifact_id`, `workspace_id`, `meeting_id` | UUID; exact artifact scope |
| `source_basis_hash`, `extraction_layer_manifest_hash` | hash; exact reusable identity |
| `source_verification_catalog_schema_version`, `source_verification_catalog_hash` | literal `1` and exact reconstructed catalog hash |
| `source_catalog_compiler_version`, `source_catalog_compiler_hash` | exact extraction-manifest compiler identity |
| `canonical_schema_version` | positive uint32 |
| `canonical_payload_hash`, `relation_graph_hash` | hash; frozen artifact payload and typed relation graph |
| `canonical_kind_state_matrix`, `canonical_kind_state_matrix_hash` | complete `CanonicalKindStateMatrixV1` body and recomputed hash; exact activation/resolved-run authority used by every kind/state validator |
| `bundle_root_name`, `bundle_root_version`, `bundle_root_hash`, `activation_manifest_hash` | exact pinned global bundle identity |
| `root_promotion_event_binding` | complete immutable typed binding to the successful promotion event authorizing that exact root/activation pair |
| `master_prompt_clause_registry_version`, `master_prompt_clause_registry_hash` | exact closed runtime/eval clause registry |
| `gateway_route_binding_hash` | exact activated gateway binding shared by every canonical call |
| `request_compiler_binding_hash` | exact compiler binding shared by root, settings and every canonical call |
| `calibration_manifest_binding` | immutable typed binding to the exact authoritative `VerifierCalibrationManifestV1` |
| `calibration_status_snapshot`, `calibration_status_snapshot_hash` | complete locked active-head snapshot and recomputed hash |
| `call_bindings`, `call_set_hash` | complete canonical GenerationCall set and recomputed hash |
| `resolve_noop_proof` | required iff no `resolve` call exists; forbidden otherwise |
| `source_coverage`, `candidate_coverage` | `{total_count, covered_count, coverage_hash}`; counts equal on pass |
| `criticality_policy_version`, `canonical_criticality_rules_hash`, `criticality_reason_codes_hash` | exact extraction-layer `CriticalityPolicyV1` binding |
| `source_criticality_coverage`, `candidate_criticality_coverage`, `canonical_criticality_coverage` | complete classification coverage plus reconstructed critical counts/hashes |
| `source_span_verdicts` | exactly one ordered `SourceSpanVerdictV1` for every catalog span |
| `semantic_reason_code_version` | literal positive uint32 `1` for this schema |
| `semantic_verdicts` | exactly canonical-claim-count ordered entries |
| `source_to_candidate_omissions`, `candidate_to_canonical_omissions` | `{missing_count, missing_ids_hash}`; zero missing critical IDs on pass |
| `repair_rounds` | integer `0` or `1` |
| `post_repair_reverified` | boolean; must be true when `repair_rounds=1` |
| `final_status` | literal `pass` |
| `issued_at_us` | signed 64-bit UTC Unix microseconds |

Every canonical claim, critical or non-critical, has exactly one semantic
verdict entry:

```text
claim_id: non-empty stable canonical ID
verdict: entailed | contradicted | ambiguous | unsupported
reason_code: closed versioned verifier reason enum
generation_call_id: UUID naming its semantic_verify or post_repair_reverify call
```

Entries are unique and sorted by exact `claim_id` UTF-8 bytes. Reason-code enum
V1 is closed and verdict-compatible:

- `entailed`: `direct_explicit_statement`, `explicit_commitment`,
  `explicit_assignment`, `accepted_request`, `cross_segment_entailment`,
  `later_explicit_correction`, `typed_relation_entailment`;
- `contradicted`: `later_explicit_contradiction`,
  `state_or_speech_act_contradiction`, `attribution_contradiction`;
- `ambiguous`: `conflicting_evidence`, `ambiguous_attribution`,
  `ambiguous_speech_act`, `ambiguous_temporal_scope`;
- `unsupported`: `missing_entailing_span`, `unsupported_inference`,
  `evidence_scope_mismatch`, `unresolved_reference`.

An unknown code, wrong verdict/code pair, duplicate/out-of-order claim or call
owned by another artifact/phase invalidates the receipt. Verifier outage or
invalid verifier output does not invent a verdict; it prevents a passing
receipt.

`pass` requires the exact phase matrix above, every canonical-claim verdict
`entailed`, both critical omission gates passing,
complete coverage, valid relations, the required post-repair full reverify and
the bound successful promotion event re-fetched/rehashed through its immutable
binding, plus an active calibration manifest with a locked, complete and fresh five-run
activation-cohort or weekly-drift evidence body at
`issued_at_us`. The artifact logical identity
and `extraction_layer_manifest_hash` include that exact calibration manifest
binding, so a replacement calibration creates a different reservable parent;
the immutable receipt is never rewritten. Revocation or expiry later
blocks new projection/publication without rewriting historical bytes.

Only pass receipts exist. Schema, verifier, omission, repair, dependency or
capacity failure remains immutable evidence on the artifact lifecycle,
GenerationCalls and attempt records; it does not finalize a receipt-shaped
failure object.

The artifact stores payload, schema version, digest and finalized timestamp in
the owner-row columns named above. A single guarded `NULL → final value`
transition is allowed; afterward they are immutable. The digest itself is not
an artifact identity field until finalization succeeds.

## `OutcomePublicationReceiptV1`

Required top-level keys:

| Keys | Type / rule |
|---|---|
| `schema_version`, `receipt_kind` | integer `1`; literal `outcome_publication` |
| `attempt_id`, `workspace_id`, `meeting_id` | UUID; exact type-attempt scope |
| `template_key`, `template_version`, `source_basis_hash` | non-empty stable key, positive uint32, hash |
| `artifact_id`, `canonical_payload_hash`, `canonical_verification_receipt_digest` | exact reusable parent and canonical receipt |
| `bundle_root_name`, `bundle_root_version`, `bundle_root_hash` | exact pinned root |
| `activation_manifest_hash`, `resolved_run_manifest_hash`, `extraction_layer_manifest_hash` | exact global/run/extraction identities |
| `root_promotion_event_binding` | complete immutable typed binding; byte-equal to the resolved-run manifest, every attempt-owned call and the canonical receipt, and rehashed to a passing event for this exact root/activation |
| `master_prompt_clause_registry_version`, `master_prompt_clause_registry_hash` | exact resolved-run runtime/eval clause registry |
| `gateway_route_binding_hash` | exact resolved-run binding shared by every attempt-owned call |
| `request_compiler_binding_hash` | exact compiler binding shared by root, settings and every attempt-owned call |
| `calibration_manifest_binding` | byte-equal to the canonical receipt's immutable manifest binding |
| `calibration_status_snapshot`, `calibration_status_snapshot_hash` | complete current locked active-head snapshot and recomputed hash |
| `primary_profile_key`, `primary_profile_version`, `primary_profile_contract_hash` | non-empty catalog key, positive uint32 and exact activated contract hash |
| `secondary_profile_key`, `secondary_profile_version`, `secondary_profile_contract_hash` | optional compatible triple; all present or absent |
| `profile_composition_policy_version`, `profile_composition_policy_hash`, `composite_profile_contract`, `composite_profile_contract_hash` | exact resolved-run composition identities and complete composite body; byte-equal to the manifest and content payload and independently rehashed |
| `auto_section_mapping_policy`, `auto_section_mapping_policy_hash`, `auto_presentation_profile_contract`, `auto_presentation_profile_contract_hash` | required together only for Auto; exact bodies/hashes byte-equal across activation, resolved run, synthesis, presentation verification, renderer and content; forbidden for non-Auto |
| `projection_policy_version`, `projection_policy_hash` | positive uint32 and exact version/hash of the resolved-run `projection_policy` component binding |
| `criticality_policy_version`, `criticality_policy_hash`, `canonical_criticality_rules_hash`, `profile_expansion_rules_hash`, `criticality_reason_codes_hash` | exact resolved-run `CriticalityPolicyV1` binding; all hashes recompute from its embedded body |
| `canonical_kind_state_matrix`, `canonical_kind_state_matrix_hash` | complete body/hash byte-equal to activation, resolved run, canonical receipt and content validator authority |
| `output_language`, `audience_context`, `privacy_policy`, `focus`, `detail_budget`, `evidence_presentation_policy`, `fixed_schema`, `analysis_mode` | exact closed controls used by the content payload; evidence is never off, fixed schema is false and analysis is facts-only |
| `presentation_schema_version` | positive uint32 equal to the content payload and the resolved-run `outcome_content_schema` component-binding version |
| `renderer_input_hash`, `renderer_result_hash` | exact external hashes of the immutable `RendererInputV1` and `RenderedOutcomeV1` bodies; both are recomputed and byte-bound to this receipt |
| `call_bindings`, `call_set_hash` | complete attempt-owned Auto-resolver, projection, presentation-synthesis and presentation-verify call set |
| `resolver_noop_proof` | required for an Auto run with no `auto_resolve` call; exact input hash and deterministic reason |
| `auto_selection_proof` | required iff an `auto_resolve` call exists; byte-equal to the resolved-run proof and bound to that call's validated-result hash |
| `eligible_coverage`, `selected_coverage`, `omitted_coverage` | exact `{total_count, covered_count, coverage_hash}` objects defined above |
| `profile_expanded_critical_count`, `profile_expanded_critical_ids_hash` | exact deterministic profile-only expansion before union with canonical critical IDs |
| `relation_closure_passed`, `authorization_passed`, `critical_retention_passed`, `capacity_passed` | booleans; all true for pass |
| `presentation_reason_code_version` | literal positive uint32 `1` for this schema |
| `presentation_statement_coverage` | complete coverage over ordered section/item/statement descriptors |
| `presentation_claim_coverage` | exact selected canonical-ID coverage realized by presentation statements |
| `auto_section_mapping_passed` | required literal `true` iff Auto and forbidden otherwise; finalizer recomputes action/non-action assignment and exactly-once selected-ID coverage from canonical objects, projection passes and rendered sections |
| `presentation_verdicts` | one exact ordered verdict per presentation statement, using the closed versioned schema above |
| `presentation_entailment_passed`, `numeric_fidelity_passed`, `negation_fidelity_passed`, `state_fidelity_passed`, `translation_fidelity_passed`, `presentation_critical_retention_passed` | booleans; all true |
| `renderer_version` | positive uint32 equal to the resolved-run `renderer` component-binding version; deterministic layout/markup renderer only |
| `outcome_set_id`, `outcome_content_hash` | exact frozen revision UUID and canonical content hash |
| `final_status` | literal `pass` |
| `issued_at_us` | signed 64-bit UTC Unix microseconds |

The attempt stores payload, schema version, digest and finalized timestamp in
the owner-row columns named above. They permit one guarded `NULL → final value`
transition in the slot-publication transaction and are immutable afterward.
The outcome header repeats schema/digest through the complete composite FK and
provenance fingerprint. `pass` requires the exact canonical digest, the bound
successful promotion event byte-equal across the canonical receipt,
resolved-run manifest and every call, current active calibration head, the
complete type phase matrix, projection partition,
statement and selected-claim presentation coverage, one verifier verdict for
every presentation statement, allowed call ownership, renderer/content equality
and every final gate true. Every call must also share the pinned gateway route
and request-compiler bindings and use an allowlisted actual provider/model pair.
The locked calibration snapshot must select a complete hash-valid five-run PASS
whose hard freshness deadline is after `issued_at_us`. Auto model
call/selection proof and deterministic
resolver proof are mutually exclusive; a non-Auto type has neither. Missing,
malformed or non-passing presentation
verification leaves failure evidence on the attempt/calls and finalizes no
publication receipt.

Both finalizers resolve and rehash the immutable promotion event before their
owner-row receipt transition. It is not a mutable lock class and adds no receipt
or reservation table; failure to reconstruct the typed binding leaves the
owner receipt null and the prior current slot untouched.

## Finalize-and-publish lock order

Canonical receipt finalization and outcome finalize-and-publish share one
global relative row-lock order. A transaction that touches only a subset still
follows this order and never acquires an earlier class after a later one:

```text
meeting deletion fence
→ current canonical-source pointer
→ transcript-regeneration job when touched
→ target summary slot(s), sorted by template key then UUID
→ outcome generation attempt
→ dispatch intent
→ candidate outcome set
→ parent canonical artifact
→ GenerationCall rows in deterministic order
→ mutable verifier-calibration status-head row(s), sorted by manifest UUID
→ prior current outcome set
```

The meeting deletion fence is the authoritative
`meetings(id, workspace_id)` row. Canonical and publication finalizers acquire
it with PostgreSQL `FOR SHARE`; the deletion-state/epoch writer acquires that
same row first with `FOR UPDATE`. Shared finalizer locks therefore allow
different type work to proceed while conflicting with deletion. A finalizer
then locks `MeetingCanonicalSourcePointer` `FOR SHARE`; Feature 197 source
replacement locks it `FOR UPDATE`, so source movement cannot race after a
finalizer's source check. A transcript-regeneration job, when touched, follows
that pointer and precedes every summary slot. Multi-slot source replacement
locks slots in `(template_key UTF-8 bytes, slot UUID bytes)` order. A finalizer
locks each relevant mutable calibration-head row with `FOR SHARE`; activation,
atomic weekly-PASS refresh, drift-breach revocation, expiry materialization and
manual revocation acquire the same row with `FOR UPDATE`.
Immutable calibration-manifest bodies need no row lock after their digest/FK is
verified. If more than one calibration head is required, rows are locked by
manifest UUID bytes. Target slot, attempt, dispatch, candidate, artifact,
GenerationCalls and prior current outcome use `FOR UPDATE` when the transaction
can freeze or mutate them.

There is no receipt-row lock in this graph: locking the parent artifact locks
the canonical receipt columns, and locking the attempt locks the publication
receipt columns. When more than one GenerationCall is touched, rows are acquired
in ascending `(owner_kind ordinal canonical_artifact=0/outcome_attempt=1,
owner_id UUID bytes, phase ordinal, phase_sequence, generation_call_id UUID
bytes)` order regardless of caller input order. Every call-freeze trigger,
receipt finalizer, dispatch reconciler and publisher that touches another class
uses this same order; a transaction that holds a GenerationCall may not then
lock its artifact, attempt or dispatch owner.

Feature 197's source-replacement transaction follows the same graph:
deletion fence → source pointer → transcript job → sorted saved slots → sorted
coalesced DispatchIntents. It skips untouched attempt/candidate/artifact/call/
calibration classes and never acquires the source pointer after a slot. Race
fixtures cover source replacement versus canonical finalization and versus
same-/different-type publication in both linearization orders.

### Fresh database-time linearization

Neither receipt may use `CURRENT_TIMESTAMP`, `transaction_timestamp()`,
`statement_timestamp()`, a Workflow/Activity time or a caller-supplied time as
freshness authority. PostgreSQL transaction time can precede a long lock wait
and would allow a receipt to cross the hard deadline with an old timestamp.

After every mutable row in the applicable lock graph, including the prior
current outcome when present, is locked and revalidated, the finalizer performs
one last conditional data-modifying SQL statement. That statement obtains
`clock_timestamp()` exactly once inside a materialized one-row CTE, converts it
to signed-int64 UTC Unix microseconds and uses that exact value as
`issued_at_us`. A versioned database finalizer injects the value into the
otherwise complete receipt body, emits the normative canonical JSON bytes and
SHA-256 digest, and the statement both checks
`issued_at_us < freshness_deadline_us` and writes the owner-row transition.
`RETURNING` yields the exact issued time, receipt bytes and digest that were
stored; the application never substitutes or pre-hashes another time.

Canonical finalization conditionally updates only the artifact owner row.
Outcome finalize-and-publish uses one data-modifying CTE statement for the
attempt receipt, candidate completion, prior-current supersession, slot CAS and
DispatchIntent terminal write, so no later write can cross the checked deadline.
The database canonicalizer is covered by the same P1–P4 and mutation vectors as
the application reconstruction; byte disagreement fails before either
transition. A zero-row freshness/CAS result rolls back. No earlier timestamp,
including one read from `clock_timestamp()` in a preceding statement,
authorizes the write.

Canonical artifact finalization is a separate Feature 195 transaction before
projection. It locks the meeting fence and current-source pointer `FOR SHARE`,
then the parent artifact, its
canonical GenerationCalls in the order above and the calibration head
`FOR SHARE`; snapshots the head, resolves and rehashes the kind-tagged complete
activation cohort or weekly-drift evidence and verifies the hard freshness
deadline, then reconstructs the canonical payload;
and performs the artifact owner-row receipt columns' one allowed finalization.
It does not lock or create a summary slot. Outcome finalize-and-publish later
extends the existing Feature 183 fail-closed `ai_service.py` entry point, locks the applicable full sequence above,
requires those canonical columns to
be final and immutable, reconstructs and compares the canonical receipt, then
reconstructs the publication receipt and rendered content. Feature 195 is the
owner of this first positive path: it finalizes the
attempt owner-row receipt columns, moves the slot CAS and finalizes the exact
DispatchIntent in that same transaction. The final conditional SQL write's
single `clock_timestamp()` supplies each receipt's exact `issued_at_us`. Any
mismatch rolls back the publication receipt transition,
dispatch transition and slot movement, leaving the prior slot unchanged.

Race/deadlock fixtures cover deletion writer versus canonical finalization,
deletion writer versus publication, canonical finalization versus first publication,
publication versus call/dispatch reconciliation, reversed input ordering for
multiple calls, calibration activation/revocation on both sides of the
linearization point, day-7/day-8 PASS refresh, breach/expiry/outage and stale
drift writers against both finalizers, same-type writers and cross-type writers.
A test must prove
bounded completion or one documented serialization winner, never a deadlock,
partial receipt, finalized dispatch without publication or published slot with
an unfinished dispatch.

## Calibration registry

Feature 195 creates one owner-controlled `VerifierCalibrationManifest` registry
with immutable manifest bodies, one mutable monotonic status-head row keyed by
manifest ID and append-only status events. A manifest covers the exact canonical
semantic/omission verifier and presentation verifier identities used by the
activated bundle. An incomplete scope cannot authorize either receipt. Changing
an evaluator, prompt, route, actual-target set, compiler, mapping, schema,
request setting or validator creates a new verifier/calibration identity,
requires new blinded human calibration and cannot rewrite or reactivate an old
manifest.

`VerifierIdentityV1` is an immutable closed object with exactly
`schema_version=1`, `verifier_key`, `decision_unit`, `evaluator_binding`,
complete `evaluator_readback` plus `evaluator_readback_hash`, immutable
`prompt_binding`, complete `model_route` plus `model_route_hash`, immutable
`gateway_route_binding`, immutable `request_compiler_binding`, complete
`variable_mapping` plus `variable_mapping_hash`, immutable
`input_contract_binding`, immutable `output_schema_binding`, immutable
`reason_code_binding`, complete `request_settings` plus `request_settings_hash`,
`calibrated_actual_targets` and immutable `local_validator_binding`.
Every immutable field is an `ImmutableArtifactBindingV1`; every local hash has
its complete sibling body. `request_settings` includes exact
`reasoning.effort`, verbosity, structured-output mode and output envelope, with
omitted defaults distinct from explicit values.

`calibrated_actual_targets` is the non-empty unique provider/model array from
the fetched route binding for which the manifest contains required per-target
calibration evidence; a runtime verifier call must observe one exact pair.
`decision_unit` is one of
`canonical_claim_entailment | source_span_criticality |
source_to_candidate_omission | candidate_to_canonical_omission |
presentation_statement_fidelity | presentation_critical_id_omission`.
All typed foreign bindings are fetched and rehashed; the compiler/route/settings
bindings must equal every verifier GenerationCall.

`evaluator_binding` has exactly `id` and `numeric_version`. `id` is the exact
1..128-byte ASCII Langfuse evaluator identifier, never its display name;
`numeric_version` is positive uint32 and never implicit `latest`. Before and
after calibration, every stability repetition and every weekly drift run, the
owner adapter fetches that exact ID/version and canonicalizes one closed
`LangfuseEvaluatorReadbackV1` with exactly `id`, `numeric_version`,
`target_observation_name`, immutable `prompt_binding`, complete `model_route`
plus `model_route_hash`, immutable `gateway_route_binding`, immutable
`request_compiler_binding`, complete `variable_mapping` plus
`variable_mapping_hash`, immutable `input_contract_binding`, immutable
`output_schema_binding`, immutable `reason_code_binding`, complete
`request_settings` plus `request_settings_hash`. Every field must byte-equal the
surrounding identity. Its external hash is:

```text
SHA-256("GRAF-LANGFUSE-EVALUATOR-READBACK\0v1" ||
        uint64be(readback_body_byte_length) ||
        canonical_json(LangfuseEvaluatorReadbackV1))
```

That digest equals `evaluator_readback_hash` and is itself covered by the
VerifierIdentity hash. A same-name new version, changed response under the same
ID/version, pre/post read-back mismatch, unavailable exact-version API or SDK
fallback to latest invalidates the run before it can become evidence. No display
name, mutable Langfuse label or SDK default is identity.
Its external hash is:

```text
SHA-256("GRAF-VERIFIER-IDENTITY\0v1" ||
        uint64be(identity_body_byte_length) ||
        canonical_json(VerifierIdentityV1))
```

`VerifierCalibrationManifestV1` is an immutable closed body with exactly:

```text
schema_version=1
manifest_version
manifest_id
identity_entries
master_prompt_clause_registry_binding
profile_clause_eval_manifest_binding
human_gold_dataset_manifest_binding
human_gold_split_manifest_binding
class_definition_binding
class_count_rows
threshold_rows
measured_metric_rows
calibration_execution_plans
calibration_execution_plans_hash
judge_stability_cohort
judge_stability_cohort_hash
valid_from_us
valid_until_us
```

Each `identity_entry` has exactly complete `verifier_identity` plus its
recomputed `verifier_identity_hash`, uniquely sorted by
`(decision_unit,verifier_key)`. Count, threshold and measured-metric arrays have
one complete row per decision-unit/verifier/actual-target/class tuple and contain
raw counts, exact rational thresholds and conservative confidence values. The
count/threshold rows byte-equal the plan-time calibration requirements.
`measured_metric_rows` is a deterministic, gate-free projection of the complete
judge-stability cohort: the finalizer recomputes it from nested run confusion
rows and rejects any mismatch. It is not a second verdict and cannot override a
failed nested gate.

`calibration_execution_plans` is the complete non-empty array of entries, each
with exactly one complete `JudgeCalibrationExecutionPlanV1` body and its
adjacent recomputed hash. Entries are unique and UTF-8 sorted by the nested
`(decision_unit, verifier_key, actual_provider, actual_model)` identity. There
is exactly one entry for every cohort identity × calibrated-target pair and no
other entry. Its dataset/split, classes, verifier/target/settings, computation,
thresholds and five run/item/invocation plans byte-equal the corresponding
evidence entry. The array hashes as:

```text
calibration_execution_plans_hash =
  SHA-256("GRAF-JUDGE-CALIBRATION-EXECUTION-PLANS\0v1" ||
    uint64be(plans_array_byte_length) ||
    canonical_json(calibration_execution_plans))
```

The manifest finalizer rejects a missing/extra plan, a post-output seal time, a
run/invocation not present in the sealed plan or any plan/evidence mismatch. The
registry/eval immutable bindings cover every applicable profile cell,
including `MP-SPK-001`, `MP-SID-001`, `MP-NUM-001`, `MP-DAT-001`,
`MP-PRO-001`, every applicable profile-safety clause, `MP-RPT-ACT-001`,
`MP-PRI-001`, `MP-EVP-001`, `MP-HRV-001`, `MP-STR-001` and `MP-QAL-001`;
missing cells or model-self-review-only evidence cannot activate.

`CalibrationClassCountRowV1` has exactly `decision_unit`, `verifier_key`,
`actual_provider`, `actual_model`, `class_code`, non-negative signed-int64
`positive_count` and `negative_count`. `CalibrationThresholdRowV1` adds the same
tuple to the exact `JudgeThresholdRowV1` metric/comparison/threshold/confidence
fields. `CalibrationMeasuredMetricRowV1` has the same tuple, `run_ordinal`,
`metric_code`, signed-int64 numerator, positive denominator, conservative ppm
and pass state. Arrays are sorted by tuple, class, metric and run; cardinality is
the full Cartesian set required by the plan, never sparse.

`JudgeStabilityCohortV1` is the only activation-quality authority and has
exactly `schema_version=1`, `cohort_version=1`, `cohort_id`,
`calibration_manifest_id`, `completed_at_us` and `entries`. Each entry has
exactly complete `judge_stability_evidence` plus its adjacent
`judge_stability_evidence_hash`. Entries are unique and sorted by
`(decision_unit,verifier_key,actual_provider,actual_model)`. There is exactly one
entry for every identity × calibrated-target pair and no others; each entry's
manifest ID equals the surrounding manifest ID and every nested gate passes.

```text
judge_stability_cohort_hash =
  SHA-256("GRAF-JUDGE-STABILITY-COHORT\0v1" ||
    uint64be(cohort_body_byte_length) ||
    canonical_json(JudgeStabilityCohortV1))
```

The cohort is embedded in the manifest and its adjacent hash recomputes from the
complete body. Acyclic build order is fixed:

```text
ProfileClauseEvalManifestV1 plan
→ preallocate VerifierCalibrationManifestV1 UUID
→ VerifierIdentityV1 + CalibrationRequirementPolicyV1
→ sealed JudgeCalibrationExecutionPlanV1 bodies/hashes
→ JudgeStabilityEvidenceV1 bodies (manifest UUID only, no manifest hash)
→ JudgeStabilityCohortV1
→ VerifierCalibrationManifestV1/hash embedding the exact plan set and cohort
→ ProfileClauseEvalResultSetV1 and RootQualificationRecordV1
```

The finalized manifest must satisfy every plan-time calibration requirement.
No `ProfileClauseEvalManifestV1` evaluator binding contains the manifest ID or
hash; only measured profile-clause evidence binds the finalized manifest used.
This removes both hash directions and leaves one computable graph.

`valid_until_us > valid_from_us` and the interval is at most 90 days. Status,
revocation data and mutable display metadata are forbidden. The external hash is:

```text
SHA-256("GRAF-VERIFIER-CALIBRATION\0v1" ||
        uint64be(manifest_body_byte_length) ||
        canonical_json(VerifierCalibrationManifestV1))
```

Weekly judge drift is durable evidence, not a mutable dashboard cell and not an
activation authority. Before its first call, one append-only
`VerifierDriftPlanV1` is sealed. Its closed body has exactly
`schema_version=1`, `plan_version`, `plan_id`, immutable `manifest_binding`,
positive `intended_drift_epoch`, positive `expected_status_epoch`, immutable
`expected_previous_freshness_evidence_binding`, complete
`sentinel_dataset_manifest` plus hash, complete `sentinel_split_manifest` plus
hash, complete `identity_entries` plus hash, complete `computation_policy` plus
hash, complete `threshold_rows`, complete `run_plan_rows`, `sealed_at_us` and
`must_commit_before_us`.

The expected epochs/binding byte-equal the active status head observed at seal
time; intended drift epoch is current plus one and `must_commit_before_us`
equals the current hard deadline. Each of exactly five ordered
`VerifierDriftRunPlanV1` rows has exactly `ordinal`, preallocated distinct
`run_id`, exact distinct `run_name=<plan-id>-r0<ordinal>`, complete sorted
`sentinel_item_ids` plus hash and complete one-to-one preallocated
`invocation_ids`. The external hash is:

```text
SHA-256("GRAF-VERIFIER-DRIFT-PLAN\0v1" ||
        uint64be(plan_body_byte_length) ||
        canonical_json(VerifierDriftPlanV1))
```

No call may contribute to a status mutation without the complete sealed plan
body/hash and an exact run/invocation tuple. A stale expected head or any
plan/result mismatch is non-authorizing attempt evidence only.

`VerifierDriftRunEvidenceV1` has exactly `ordinal`,
`run_id`, complete `run_manifest` plus `run_manifest_hash`, complete
`run_result` plus `run_result_hash`, complete `metric_rows` plus
`metric_rows_hash`, complete `disagreement_item_ids` plus
`disagreement_item_ids_hash`, `gate_rows` and `gate_result`. Ordinals are exactly
`1..5`; IDs are distinct; result bodies contain exact item outputs, raw confusion
counts and evaluator read-backs. A missing body is not a run entry.
`VerifierDriftRunManifestV1` has exactly `schema_version=1`, `ordinal`,
`run_name`, complete sentinel item-ID array/hash, complete verifier-identity/
actual-target rows, complete request-settings rows and invocation IDs.
`VerifierDriftRunResultV1` has exactly the matching manifest hash, complete
sorted item-result array/hash, complete raw confusion rows/hash and closed
failure codes. Every tuple in the manifest occurs once in the result.

The append-only `VerifierDriftEvidenceV1` body has exactly
`schema_version=1`, `evidence_version`, `evidence_id`, immutable
`manifest_binding`, complete `drift_plan` plus `drift_plan_hash`,
`evidence_kind="weekly"`, positive `drift_epoch`, complete
`sentinel_dataset_manifest` plus hash, complete `identity_entries` plus hash,
complete `computation_policy` plus hash, `started_at_us`, `completed_at_us`,
`runs`, complete `aggregate_metric_rows` plus hash, complete
`critical_disagreement_item_ids` plus hash, `gate_rows`, `result=pass|breach`
and one closed `reason_code`. The sentinel, identities and policy equal the
manifest cohort except for the explicitly versioned weekly dataset. `runs`
contains exactly five rows in ordinal order. Aggregate rows and disagreement IDs
are reconstructed from complete runs; one failed run/class cannot be averaged
away. `evidence_kind=activation` is schema-invalid. The evidence hash is:

`identity_entries` byte-equals the manifest identity array. Each of the five
runs covers every identity × calibrated-target × sentinel-item tuple exactly
once. `aggregate_metric_rows` contains exactly one row per
identity/target/class/metric tuple and embeds the five source run metric rows;
`gate_rows` contains every structural, threshold, agreement, kappa and spread
gate from `JudgeMetricComputationPolicyV1` exactly once. Missing, extra,
duplicate or reordered tuple coverage makes the attempt inconclusive rather than
creating PASS/breach evidence.

The embedded plan is sealed before every nested call. Its manifest, intended
epoch, expected status/freshness head, dataset/split, identities, computation,
thresholds and five run IDs/names/item/invocation arrays byte-equal the evidence
and the head used by the final status transaction. Evidence assembled from
unplanned calls or a cherry-picked subset is schema-invalid.

```text
SHA-256("GRAF-VERIFIER-DRIFT-EVIDENCE\0v1" ||
        uint64be(evidence_body_byte_length) ||
        canonical_json(VerifierDriftEvidenceV1))
```

`pass` requires five independently passing runs, exact critical 5/5 agreement
and every stability/threshold gate. `breach` uses only `threshold_breach`,
`critical_disagreement` or `verifier_identity_mismatch` and revokes immediately.
Transport outage, dataset/evaluator read-back failure or fewer than five valid
runs creates only append-only `VerifierDriftAttemptEventV1` with exactly
`schema_version=1`, `event_version`, `attempt_id`, `event_id`, immutable
`manifest_binding`, complete `drift_plan` plus `drift_plan_hash`, intended
`drift_epoch`, `started_at_us`, `ended_at_us`,
complete `finished_runs` body/hash array and one closed `failure_reason_code`.
It contains no `result` or aggregate verdict and cannot refresh freshness.

`VerifierCalibrationStatusHeadV1` is the separate mutable row with exactly
`manifest_id`, positive signed-int64 `status_epoch`, immutable
`status_event_binding`, `status=draft|active|expired|revoked`, non-negative
signed-int64 `drift_epoch` and conditional `last_freshness_pass_at_us`,
`freshness_deadline_us`, `freshness_evidence_kind` and immutable
`freshness_evidence_binding`. Draft omits the four freshness members. Active
requires them. Expired/revoked retains them after activation.
`freshness_evidence_kind` is
`activation_judge_stability_cohort | weekly_drift`; the binding points
respectively to the exact embedded cohort artifact or one
`VerifierDriftEvidenceV1`. There is never an untyped ID/hash pointer.
For an activation cohort the binding is exactly
`{artifact_id=cohort_id,schema_version=1,artifact_version=cohort_version,
hash=judge_stability_cohort_hash}` and is resolved only inside the head's exact
manifest binding. For weekly drift it is exactly
`{artifact_id=evidence_id,schema_version=1,artifact_version=evidence_version,
hash=verifier_drift_evidence_hash}` in the append-only drift registry.

`VerifierCalibrationStatusSnapshotV1`, persisted inside each passing receipt,
has exactly immutable `manifest_binding`, `status_epoch`, immutable
`status_event_binding`, `status="active"`, `drift_epoch`,
`last_freshness_pass_at_us`, `freshness_deadline_us`,
`freshness_evidence_kind` and immutable `freshness_evidence_binding`. It is
byte-equal to the head read under `FOR SHARE` and hashes as:

```text
SHA-256("GRAF-VERIFIER-CALIBRATION-STATUS-SNAPSHOT\0v1" ||
  uint64be(snapshot_body_byte_length) ||
  canonical_json(VerifierCalibrationStatusSnapshotV1))
```

Before finalization the owner fetches the complete selected cohort/drift body
through the snapshot's immutable binding and rehashes it. The body remains in
its immutable manifest/drift registry; the reconstructible typed binding is
persisted inside the receipt snapshot. Thus neither a mutable head pointer nor a
bare digest can authorize publication, without copying a large five-run corpus
into every receipt.

Every immutable append-only `VerifierCalibrationStatusEventV1` has exactly
`schema_version=1`, `event_version`, `event_id`, `manifest_id`, `status_epoch`,
`previous_status`, `new_status`, `occurred_at_us`, one closed `reason_code` and
conditional `event_evidence_kind` plus immutable `event_evidence_binding`. The
pair is required for
`activation_judge_stability_pass`, `weekly_drift_pass` and a complete weekly
breach; its kind is respectively `activation_judge_stability_cohort` or
`weekly_drift`. Other reasons forbid it. A breach event may point to breach
evidence but never replaces the head's last passing freshness binding. The head
equals the latest event.
`previous_status=none` is legal only for initial draft; `active → active` only
for `weekly_drift_pass`; revoked/expired are terminal.

Activation verifies the exact complete cohort embedded by the manifest and then
commits `draft → active` with `drift_epoch=0`,
`last_freshness_pass_at_us=cohort.completed_at_us`,
`freshness_evidence_kind=activation_judge_stability_cohort` and the cohort's
immutable binding. It creates no `VerifierDriftEvidenceV1`. The hard
`freshness_deadline_us` is the earlier of manifest `valid_until_us` or cohort
completion + `8 × 24h`; soft weekly due is completion + `7 × 24h`. Both are UTC
microseconds and half-open.

A weekly PASS is one transaction: lock the head `FOR UPDATE`; require active,
unexpired manifest and fresh old deadline; require the sealed plan's expected
status/drift epochs and previous freshness binding to match that exact head;
verify all five complete planned runs,
identities, raw counts, metrics and evidence hash; insert the append-only weekly
evidence; append `active → active`; increment status/drift epochs; and replace
all four freshness members with the weekly-drift binding/time/deadline. A
complete breach inserts weekly evidence and commits `active → revoked` without
changing the last PASS pointer. An outage changes no head field. At the hard
deadline finalization fails immediately; an expiry writer materializes
`active → expired` under `FOR UPDATE`.

Both canonical finalization and outcome finalize-and-publish lock this exact
head row `FOR SHARE`, verify `status=active`, manifest interval and
`issued_at_us < freshness_deadline_us`, create/hash the complete status snapshot,
fetch the kind-tagged freshness binding, and rehash its complete body. For
`activation_judge_stability_cohort`, the body byte-equals the manifest's cohort;
for `weekly_drift`, it is a PASS for the same manifest and drift epoch. The
snapshot with its immutable selected-evidence binding is embedded in the
receipt. PASS refresh, breach, expiry and either finalizer therefore serialize
without a second activation verdict or retroactive freshness.

The exact calibration manifest binding is a member of
`extraction_layer_manifest_hash` and therefore of canonical artifact logical
identity and its active/verified partial-unique key. Expired/revoked parents keep
immutable historical receipts but are ineligible for new projection/publication.
A replacement active calibration has a new ID/hash, produces a different
extraction identity and may reserve/finalize its own parent without retiring or
rewriting the historical row. V1 deliberately reruns the canonical layer on a
calibration change; splitting canonical and presentation calibration identities
is allowed only in a future schema after measured need. Expiry-before-reserve,
expiry-between-finalizers, day-7 PASS, day-8 grace/PASS/deadline, stale PASS
writer versus each finalizer, threshold/critical breach, dependency outage,
renewal, revocation and concurrent old/new-manifest fixtures must prove one
bounded outcome and no uniqueness dead-end.
Langfuse scores or labels are evidence imported into this registry, never the
runtime source of publication truth. Feature 195 integration tests may load
isolated synthetic manifests, but production has no `active` manifest until
Feature 200 creates and activates one from approved human-grounded evidence.

## Feature 195 conformance gate

Feature 183 intentionally contains no receipt-vector artifact. An earlier
schema-invalid checksum draft was removed so neither review tooling nor future
implementation can mistake compact illustrative bodies for positive publication
evidence. Feature 195 MUST create one machine-readable conformance set from
scratch whose bodies validate against the frozen closed schemas below, then
independently recompute every dependent hash, manifest, call set and receipt
before implementation may pass. The names P1–P4 are reserved for positive
members of that future schema-valid corpus; they do not identify existing
fixtures.

### Required Feature 195 conformance inventory

The Feature 195 conformance corpus MUST contain all of the following:

- authoritative source/candidate/eligible/selected/omitted/missing arrays and
  their length-framed coverage hashes;
- complete `CriticalityPolicyV1` bodies/hashes plus source, candidate, canonical
  and profile-expansion classification arrays for non-empty, legitimate-zero and
  adversarial non-empty→empty cases, with every closed reason code covered;
- exact `SourceVerificationCatalogV1` body/span/catalog hashes, gap-free split
  vectors, one `SourceSpanVerdictV1` per span, 32,768 exact-fit/one-over and
  boundary-context mutations;
- complete `GatewayRouteBindingV1`, embedded
  `LiteLLMRequestCompilerBindingV1` and `CriticalityPolicyV1`
  body/subhash/full-hash positive and one-field/ordering/domain mutation vectors;
- complete `RootQualificationRecordV1`, passing `RootPromotionEventV1` and
  `ImmutableArtifactBindingV1` vectors, with unknown event ID, schema/event
  version, body/hash, qualification, target/read-back root, activation and
  cross-call/manifest/receipt substitution mutations rejected at their first
  authority boundary;
- complete per-phase `RequestSettingsV1` bodies/hashes proving omitted versus
  explicit settings, every closed phase/effort/service-tier enum,
  route/compiler/phase separation and schema-derived output envelopes; endpoint,
  adapter/serializer/translator, defaults/drop and automatic-summary mutations
  must fail in route, call and `VerifierIdentityV1` bindings;
- exact `MasterPromptClauseRegistryV1` version/hash, complete gap-free source
  provenance spans, every requirement-unit body/hash/disposition and per-call
  applicable clause bindings, including
  `MP-SPK-001`, `MP-SID-001`, `MP-NUM-001`, `MP-DAT-001`, `MP-PRO-001`, every
  applicable profile-safety clause, `MP-RPT-ACT-001`, `MP-PRI-001`,
  `MP-EVP-001`, `MP-HRV-001`, `MP-STR-001` and `MP-QAL-001` runtime/eval cells;
- complete `MeetingIntentV1`, single/mixed `AudienceContextV1`, every closed
  privacy matrix action, `EvidencePresentationPolicyV1`, `DetailBudgetV1`,
  disposition/effective-date/`UncertaintyV1` and deterministic `FollowUpDraftV1`
  positive/boundary/rejection vectors;
- every `ProfileContractV1` and legal/illegal primary-secondary composition,
  including section merge, risk max, unioned prohibitions/criticality, unchanged
  primary budget and one-field `composite_profile_contract_hash` mutations;
- canonical semantic-verdict arrays proving one entailed verdict for every
  canonical claim, including non-critical claims and rejection of a missing
  non-critical verdict;
- every legal `FocusRequestV1 → FocusV1` path: deterministic non-topic,
  deterministic canonical topic and text resolution only in projection batch
  zero over the complete ≤64-topic catalog, with later-batch immutability and
  no-match/ambiguity/catalog-overflow rejection;
- strict `AttemptTerminalEvidenceV1` vectors for zero eligible, zero selected,
  topic no-match and topic ambiguity, proving no synthesis/verification call,
  candidate/content/publication receipt or slot mutation and preserving any
  previous current result, plus the same exact passing promotion-event binding
  as the resolved-run authority;
- exact `logical_request` and `validated_result` bodies plus recomputed hashes
  for all nine phases: `extract`, `resolve`, `semantic_verify`, `repair`,
  `post_repair_reverify`, `auto_resolve`, `profile_projection`,
  `presentation_synthesis` and `presentation_verify`;
- GenerationCall W3C vectors with 32-lowercase-nonzero-hex trace IDs,
  16-lowercase-nonzero-hex observation/parent/root IDs, same-trace root/parent
  bindings and executable uppercase/zero/length/non-hex/reuse/cross-trace
  mutations;
- exact project-profile request/result bodies for the P2/P3 projection,
  synthesis and presentation-verification calls;
- a complete canonical receipt and digest;
- complete `AutoResolverInputV1`, frozen
  `AutoResolverInputDescriptorV1`, `AutoResolverResultV1`, assessments hash,
  deterministic no-op proof, model-call descriptor and
  `AutoSelectionProofV1`;
- exact Auto-section-mapping positive vectors for action-only, key-points-only,
  mixed and empty-section cases, plus rejection vectors for a duplicated,
  omitted, wrong-kind, third-section, changed-policy/profile and non-Auto
  mapping member;
- positive resolved-run manifests and publication receipts covering every legal
  resolver mode (`explicit_template`, `model_resolved`,
  `deterministic_low_confidence_fallback`, `single_compatible_profile`,
  `policy_forced_profile`), each with mandatory profile projection; P1–P4 remain
  reserved named positive members of that corpus;
- deterministic content, statement-coverage and mutation vectors;
- positive and negative conditional item-`state` vectors proving it is required
  exactly for compatible stateful kinds and forbidden for stateless kinds;
- schema-valid full English and full Russian payloads for all nine phases,
  both owner-row receipts and publication content, plus mandatory Auto/schema/phase
  negative vectors expressed as executable base-vector + RFC 6901 JSON Pointer
  operation/value + expected rejection stage/reason, never prose-only mutations;
- independently derived exact-fit and one-over vectors for Auto objects,
  projection objects, synthesis items/selected IDs and verifier statements/
  critical IDs using the route tokenizer and combined-context formula;
- positive and mutation vectors for the complete `GatewayRouteBindingV1`, its
  domain-separated hash, pre-egress echo and actual provider/model allowlist;
- calibration vectors for active/expired/revoked manifests and replacement
  manifest identity; exact evaluator `{id,numeric_version}` read-back/hash
  mutations; activation from the manifest-embedded sorted judge-stability
  cohort with no activation drift artifact; append-only weekly five-run drift
  bodies/hashes/per-run raw confusion and aggregate metrics; atomic kind-tagged
  PASS freshness updates; and day-7/day-8, stale-writer, breach, outage,
  expiry-before-reserve, expiry-between-finalizers, renewal, concurrent old/new
  writer and no-uniqueness-dead-end outcomes;
- Langfuse publisher vectors proving claim-while-pending, immediate pre-egress
  `sending` CAS, claim-owner-only terminal writes, stale publisher rejection,
  every crash window, expired-sending ambiguity and exact authoritative
  reconciliation without blind export;
- one positive PostgreSQL integration corpus that reconstructs the complete
  bodies from owner rows, validates P1–P4/all ten mode cells, executes canonical
  finalization followed by publication through the sole Feature 183 entry point,
  and runs every required race/deadlock case with no partial receipt, slot or
  DispatchIntent state.

The Feature 195 finalizer rebuilds every body from locked authoritative rows before
comparison. A printed hash, descriptor-only reconstruction, mutable title or
catalog lookup, SDK object, provider bytes or Langfuse observation cannot
substitute for the exact persisted canonical bodies.

### Reserved positive names and mandatory rejection behavior

The future P1–P4 members and every negative case are executable only when the
Feature 195 corpus supplies complete closed-schema base bodies and exact RFC 6901
JSON Pointer mutations. At minimum, those tests must prove:

- hash-only or mutable reconstruction, incomplete/oversized sampled views and
  input/view/coverage mismatch fail before model egress or publication;
- missing, extra, duplicate or out-of-order assessments, unknown evidence IDs,
  evidence-free positive signals, cross-profile reason codes and ranked
  non-permutations reject the result/proof;
- model-authored selected profile, confidence or free text, unknown keys,
  `null`, overflow/non-complete output and any proof hash/policy/rank mismatch
  produce no pass receipt;
- high-stakes incomplete evidence and equally ranked near-neighbors cannot
  publish a specialized result;
- call/proof absence or overlap for Auto/projection rejects the phase matrix;
- focus, coverage partition, verdict ordering/code compatibility, continuity,
  provider/model, calibration, outcome or content mismatches reject even when a
  syntactically valid digest can be computed.

Changing one byte, semantic list order, omitted-vs-null form, actual
provider/model, request/result body, coverage, calibration head, outcome ID or
content changes the relevant hash chain. Serialization success never overrides
schema or semantic invalidity.
