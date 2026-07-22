# Temporal, Langfuse, And Runtime Requirements Checklist: Complete Recording Workflows

**Purpose**: Validate durable-work, Cloud egress, secret, observability, degraded-state, and deletion requirement quality
**Created**: 2026-07-21
**Feature**: [spec.md](../spec.md)

## Durable Work Boundary

- [x] CHK001 Is the boundary between restart-sensitive external work and direct application/database transactions explicit? [Clarity, Spec §FR-072]
- [x] CHK002 Are deterministic idempotency and duplicate-dispatch requirements defined for committed generation requests? [Completeness, Spec §FR-068, SC-014]
- [x] CHK003 Is the complete plaintext canonical transcript explicitly required in Temporal History without requiring a duplicate full model request/response/result or any codec, encryption, redaction, masking, truncation, or GRAF deletion? [Observability, Spec §FR-056, FR-088]
- [x] CHK004 Are retryable and non-retryable failure classes unambiguous? [Clarity, Spec §FR-069]
- [x] CHK005 Are restart, dependency outage, reconciliation, cancellation, and duplicate-delivery scenarios covered? [Coverage, Spec §US5, Edge Cases, SC-014]
- [x] CHK006 Is deletion authoritative before new inference/publication/acceptance while retained observability remains explicitly outside the meeting purge? [Consistency, Spec §FR-052–FR-054, FR-073]

## Langfuse Cloud Boundary

- [x] CHK007 Is the approved Langfuse Cloud EU destination/private project, no-public-trace rule, and operator-managed role access documented without treating it as owner-controlled storage? [Dependency, Spec §FR-078, Assumptions]
- [x] CHK008 Is sole-publisher delivery kept durably pending until confirmation and separated from model retry, candidate readiness, meeting deletion, and prompt/config authority? [Clarity, Spec §FR-070–FR-073, SC-014]
- [x] CHK009 Are complete plaintext AI-workflow content fields and explicit non-selection of raw audio/runtime credentials defined without a masking pipeline? [Completeness, Spec §FR-071, SC-015]
- [x] CHK010 Are stable trace names, environment, selected/actual model provenance, exact-or-unknown usage/cost, retry, and prompt-version correlation requirements measurable? [Measurability, Spec §FR-032, FR-071, FR-079, SC-015]
- [x] CHK011 Is prompt-management outage limited to an exact integrity-checked export of the same promoted version, with truthful dependency wait when no approved snapshot exists? [Recovery, Spec §FR-077–FR-078]
- [x] CHK012 Is full-content Langfuse AI-workflow observability intentional while unrelated global HTTP/SQL instrumentation stays disabled? [Simplicity, Constitution §III]

## Secrets, Egress, And Deployment

- [x] CHK013 Are Langfuse credentials restricted to ignored operator/runtime secret files and the outcome-capable worker? [Security, Spec §Dependencies]
- [x] CHK014 Are browser, macOS, logs, diagnostics, screenshots, and committed evidence excluded from receiving credentials? [Consistency, Spec §FR-055–FR-056]
- [x] CHK015 Are configured private destination/environment, no-public-trace rule, timeout, durable pending delivery, operator-managed retention/access, and deliberate no-GRAF-delete behavior documented? [Completeness, Constitution §III, Spec §FR-070–FR-078]
- [x] CHK016 Are missing/invalid credentials and Langfuse outages fail-open for candidate readiness, recording, and transcription without repeating model egress? [Exception Flow, Spec §US5, FR-070]

## LiteLLM Gateway Boundary

- [x] CHK021 Is one owner-controlled HTTPS LiteLLM gateway the sole inference destination, with Langfuse separately bounded to observability and no direct upstream credentials in GRAF? [Security, Spec §FR-074]
- [x] CHK022 Is the selected model route, initially `gpt-5.6-luna`, sourced only from pinned Langfuse config while LiteLLM remains the replaceable upstream provider-routing boundary? [Maintainability, Spec §FR-074–FR-075]
- [x] CHK023 Are model/gateway retries disabled and Temporal retry ownership, timeout, and terminal/transient classes explicit? [Reliability, Spec §FR-069, FR-076]
- [x] CHK024 Are strict JSON schema plus local validation and requested/actual provider-model provenance objectively testable? [Correctness, Spec §FR-075–FR-076, SC-016]

## Prompt And Trace Pinning

- [x] CHK025 Is production-label resolution the first Temporal activity and atomically persisted as an exact prompt/config/dependency snapshot/version/hash before model execution? [Consistency, Spec §FR-077]
- [x] CHK026 Are verified promoted-version export, cold-start dependency wait, promotion-hash verification, and no implicit `latest` behavior explicit? [Recovery, Spec §FR-077–FR-078]
- [x] CHK027 Are TraceContext propagation, deterministic trace/observation IDs, transcript snapshot activities, sole-publisher generation with original timestamps, and delivery retry defined without replay/model duplicates? [Observability, Spec §FR-079]
- [x] CHK028 Are full-content Langfuse attributes, durable fail-open delivery, retained parent-independent plaintext Generation Call, complete plaintext transcript History, pre/post-serialization payload ceilings, and truthful no-delete behavior measurable before rollout? [Governance, Spec §FR-078, FR-088–FR-091, SC-017]

## Prompt And Generation Quality

- [x] CHK017 Are separate self-contained format prompt/config, schema/adapter, source revision, selected route, and actual provider/model versions all required for reproducibility? [Traceability, Spec §FR-032, FR-067]
- [x] CHK018 Does the spec treat transcript instructions as untrusted data and require strict structured-output validation? [Security, Spec §FR-067]
- [x] CHK019 Are accepted-summary preservation and candidate-only publication consistent across retries, failure, outage, and deletion? [Consistency, Spec §FR-033–FR-034, FR-068, SC-014]
- [x] CHK020 Can the forbidden-content and durability outcomes be objectively verified without storing private evidence? [Measurability, Spec §SC-014–SC-015]

## Model Configuration Authority

- [x] CHK029 Is Langfuse Prompt Config the single editable authority for model route, request-level settings, and response schema? [Consistency, Spec §FR-074–FR-080]
- [x] CHK030 Are allowed config fields/types plus app-owned safety/budget ceilings explicit, with destinations, secrets, headers, arbitrary tools, and retry policy rejected? [Security, Spec §FR-080]
- [x] CHK031 Does each built-in outcome have its own prompt/evaluation lifecycle while personal templates reuse one bounded custom prompt? [Completeness, Spec §FR-067]
- [x] CHK037 Is `Авто` explicitly one direct conservative prompt rather than an unspecified classifier/dispatcher? [Simplicity, Spec §FR-067]
- [x] CHK038 Are the three exact closed Prompt Config profiles testable, including real bounded outcome/judge schemas, native textual reflection, size/depth/count limits, remote-reference rejection, explicit request projection, and model-capability validation? [Measurability, Spec §FR-080, Contract §Langfuse Prompt Config Contract]

## GEPA Optimization And Promotion

- [x] CHK032 Is GEPA an optional offline dependency using the same production inference/validation path without DSPy or a second runtime stack? [Simplicity, Spec §FR-081]
- [x] CHK033 Are Temporal durability, immutable dataset identity, resume/heartbeat, budgets, stale-source handling, and full plaintext optimization History explicit? [Reliability, Spec §FR-082]
- [x] CHK034 Are held-out hard/quality/cost gates required before exact-version publication, with protected-label/sole-credential readiness, deployment-operator approval, serialized expected-source conflict detection, and rollback before production promotion? [Safety, Spec §FR-083, SC-018]
- [x] CHK035 Does the trace contract permit complete plaintext synthetic workflow content while owner-controlled checkpoints remain the resume authority? [Observability, Spec §FR-084]
- [x] CHK036 Is JEPA explicitly excluded as representation/model-training architecture rather than misrepresented as a prompt optimizer? [Scope, Spec §Clarifications]
- [x] CHK039 Are reflection plus three metric-specific judge prompts named, independently versioned/calibrated in Langfuse, pinned per run, and covered by model-setting replacement evidence? [Configuration, Spec §FR-081, FR-085, SC-019]
- [x] CHK040 Is the optimizer trace replay/resume-safe, full-content, attempt-aware, free of masking, and explicit about zero-duration workflow markers? [Observability, Spec §FR-079, FR-086]
- [x] CHK041 Is the project-global production-label boundary restricted to deployment operators rather than workspace/cabinet admins, including plan-dependent protected-label fallback and serialized expected-source promotion? [Authorization, Spec §FR-082–FR-083]
- [x] CHK042 Is feature-121 optimization synthetic-only while real meeting-derived optimization remains a separate product decision? [Scope, Spec §FR-084]
- [x] CHK043 Are GEPA iteration-boundary resume, repeated seed evaluation, immutable hash/schema-verified shared checkpoints, fenced/leased call reservations, ambiguous egress, absolute budget/deadline, and non-throwing callback non-authority explicit? [Durability, Spec §FR-082, FR-086]
- [x] CHK044 Does the candidate receive no manually assigned label, use exact numeric version, match source canonical config hash after re-read, follow held-out, ignore managed `latest`, and use a separate rollback workflow/trace? [Promotion, Spec §FR-083–FR-086]
- [x] CHK045 Do reflection and three judges have exact body-variable/parser contracts plus separate calibration and operator-promotion gates before `production`? [Evaluation, Spec §FR-085, FR-087]
- [x] CHK046 Does the strict outcome schema preserve `available`, `not_found`, and `not_inferable` truth with item-count cross-validation? [Compatibility, Spec §FR-076, Contract §Outcome profile]
- [x] CHK047 Is Langfuse label mutation described as serialized expected-source conflict detection rather than unsupported native CAS, with automated promotion blocked when protected-label/sole-credential readiness is absent? [Correctness, Spec §FR-083]

## Notes

- 47/47 requirement-quality checks re-pass on 2026-07-22 after constitution
  v4.0.0, full-content Langfuse tracing, plaintext Temporal History, retained
  Generation Call storage, and removal of codec/key/delete machinery.
- This checklist validates written requirements. Runtime evidence belongs in
  `quickstart.md` scenarios 15–16 and implementation tasks.
