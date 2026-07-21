# Contract: Complete Recording Workflows

## Purpose

Define the cross-surface state, command, authorization, and accessibility
contract for feature 121. Existing capture, upload, playback, speaker, export,
and deletion contracts remain authoritative; this contract composes them and
adds summary-template and complete sharing interactions.

## Authority Map

| Concern | Authority | Consumers |
|---|---|---|
| Permissions, Start/Pause/Resume/Stop, source health | Native macOS app | Main window, titlebar HUD, menu bar |
| Local custody, upload retry, purge | Native persisted queue + server ingest responses | Native shell and server projection |
| Processing, transcript, outcomes, playback readiness | Server | Browser and embedded cabinet |
| Templates and accepted summary revision | Server | Browser and embedded cabinet |
| Access, invitations, links, downloads/exports | Server | Browser and embedded cabinet |
| Whole-meeting deletion | Server deletion service | All surfaces and workers |

Embedded web content MUST NOT send capture commands or hide the native Stop
path. Native code MUST NOT make server sharing/export/deletion policy decisions.

## Native Recording Projection

One presentation projection is derived from existing capture and queue state:

```text
RecordingWorkflowViewState
  phase: blocked | ready | detected | starting | active | paused |
         stopping | finalizing | saved_local | queued | uploading |
         retrying | processing | partial | ready | failed
  elapsed_seconds: integer?                 # active/paused only
  microphone: ready | silent | degraded | unavailable | unknown
  system_audio: ready | silent | degraded | unavailable | unknown
  custody: none | local | server_accepted | purge_pending | purged
  primary_action: start | pause | resume | stop | open_settings |
                  retry_finalize | open_meeting | none
  secondary_actions: bounded list
  message_key: localized enum
  technical_reason_code: internal bounded enum, never raw error text
```

Rules:

- `stop` is always primary or persistently adjacent in `starting`, `active`,
  `paused`, and `stopping` when the controller can still accept it.
- `starting` never shows a second Start.
- Silent meter input is not automatically `unavailable`; health evidence owns
  that transition.
- Network/server failure cannot change an active local capture to failed.
- A local meeting row appears after durable finalization even when upload has
  not started.
- Native and server projections may describe different lifecycle dimensions;
  copy must state which one changed.

## Summary Template API

All routes require authenticated principal, device/session context, tenant
scope, CSRF protection for mutation, and deletion/lifecycle checks.

### List Templates

`GET /api/v1/cabinet/summary-templates`

Response:

```json
{
  "default_template_key": "graf-auto-v1",
  "recommended": [
    {
      "template_id": "uuid-or-null-for-built-in",
      "template_key": "graf-auto-v1",
      "kind": "builtin",
      "name": "Автоматически",
      "purpose": "Краткие итоги и действия",
      "sections": ["summary", "key_points", "action_items"],
      "output_language": "ru",
      "detail_level": "standard",
      "version": 1,
      "status": "active",
      "can_edit": false,
      "can_duplicate": true
    }
  ],
  "personal": []
}
```

The list contains no meeting content and returns only caller-visible personal
templates plus current built-ins.

### Create Personal Template

`POST /api/v1/cabinet/summary-templates`

Request:

```json
{
  "name": "Итоги клиентской встречи",
  "purpose": "Решения, риски и следующие шаги",
  "sections": ["summary", "decisions", "risks", "action_items"],
  "output_language": "ru",
  "detail_level": "standard"
}
```

Validation:

- name and purpose bounded and normalized;
- 1–7 unique allowlisted sections;
- allowlisted language/detail only;
- no HTML, executable markup, model/system prompt, secret, or meeting content;
- per-user active-template limit enforced by product policy.

### Update / Archive / Delete / Duplicate

- `PATCH /api/v1/cabinet/summary-templates/{template_id}` creates a new personal version.
- `POST /api/v1/cabinet/summary-templates/{template_id}/duplicate` creates an owned v1 copy.
- `POST /api/v1/cabinet/summary-templates/{template_id}/archive` hides it from new selection.
- `DELETE /api/v1/cabinet/summary-templates/{template_id}` lifecycle-deletes an owned template when policy allows.

Built-ins reject edit/archive/delete with `403 builtin_template_immutable`.

## Summary Generation API

### Request Candidate

`POST /api/v1/cabinet/meetings/{meeting_id}/summary-candidates`

Request:

```json
{
  "template_key": "graf-client-update-v1",
  "template_id": null,
  "template_version": 1,
  "expected_current_outcome_set_id": "uuid-or-null"
}
```

Response `202`:

```json
{
  "candidate_id": "uuid",
  "state": "queued",
  "current_outcome_set_id": "uuid-or-null",
  "poll_url": "/api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}"
}
```

Rules:

- caller must own the meeting and be allowed to generate;
- terminal transcript/result revision is pinned at request time;
- same idempotency input reuses the current attempt/candidate;
- deletion, missing transcript, stale template version, or forbidden lifecycle
  fails before dispatch;
- the accepted outcome remains current during generation and on failure.

### Poll Candidate

`GET /api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}`

Returns content only to an authorized owner and only after the candidate is
stored. Processing states return metadata-only status and bounded reason.

### Accept Or Reject

- `POST /api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/accept`
- `POST /api/v1/cabinet/meetings/{meeting_id}/summary-candidates/{candidate_id}/reject`

Accept request includes `expected_current_outcome_set_id` for optimistic
conflict detection. Accepting updates the meeting pointer, candidate state, and
prior accepted state atomically. A conflict returns `409 summary_revision_conflict`
without dropping either revision.

### Langfuse Prompt Config Contract

Langfuse Config is arbitrary JSON, so GRAF validates one of three closed
profiles and explicitly constructs the LiteLLM request. It never forwards
`**prompt.config`. Every prompt body is at most 64 KiB UTF-8; every config is at
most 64 KiB canonical JSON, at most 12 levels deep, and contains at most 256
object keys plus array elements. Unknown keys and every `$ref`/remote reference
are rejected before any model egress.

#### Outcome profile

Required top-level keys are exactly `config_contract_version`, `model`,
`temperature`, `max_completion_tokens`, and `response_format`:

```json
{
  "config_contract_version": 1,
  "model": "gpt-5.6-luna",
  "temperature": 0.2,
  "max_completion_tokens": 4096,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "graf_meeting_outcome_auto_v1",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "category_states": {
            "type": "object",
            "properties": {
              "summary": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "key_points": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "decisions": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "action_items": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "followups": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "risks": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "questions": {"type": "string", "enum": ["available", "not_found", "not_inferable"]},
              "evidence": {"type": "string", "enum": ["available", "not_found", "not_inferable"]}
            },
            "required": ["summary", "key_points", "decisions", "action_items", "followups", "risks", "questions", "evidence"],
            "additionalProperties": false
          },
          "items": {
            "type": "array",
            "maxItems": 100,
            "items": {
              "type": "object",
              "properties": {
                "category": {"type": "string", "enum": ["summary", "key_points", "decisions", "action_items", "followups", "risks", "questions", "evidence"]},
                "sequence": {"type": "integer", "minimum": 0, "maximum": 99},
                "text": {"type": "string", "minLength": 1, "maxLength": 4000},
                "owner_text": {"anyOf": [{"type": "string", "maxLength": 240}, {"type": "null"}]},
                "due_date_text": {"anyOf": [{"type": "string", "maxLength": 120}, {"type": "null"}]},
                "truth_label": {"type": "string", "enum": ["supported"]},
                "source_refs": {
                  "type": "array",
                  "maxItems": 8,
                  "items": {
                    "type": "object",
                    "properties": {
                      "transcript_segment_id": {"type": "string", "format": "uuid"},
                      "sequence": {"type": "integer", "minimum": 0}
                    },
                    "required": ["transcript_segment_id", "sequence"],
                    "additionalProperties": false
                  }
                }
              },
              "required": ["category", "sequence", "text", "owner_text", "due_date_text", "truth_label", "source_refs"],
              "additionalProperties": false
            }
          }
        },
        "required": ["category_states", "items"],
        "additionalProperties": false
      }
    }
  }
}
```

`config_contract_version` is literal integer `1`; `model` is a 1–128 character
deployment-approved LiteLLM alias; `temperature` is required in `0..2`; and
`max_completion_tokens` is required in `1..8192`. Schema name is a
1–64-character identifier and the inlined schema is at most 48 KiB. Local
validation additionally enforces allowed template categories, unique
`(category, sequence)`, valid segment ownership, owner/due fields only where
applicable, deletion/source revision, and the application cost/token ceiling.
Every `available` category must have at least one item and every `not_found` or
`not_inferable` category must have none, preserving existing product truth.
The schema determines structure; it does not grant authorization.

#### GEPA reflection profile

Prompt `graf/prompt-optimization/reflection` is a self-contained text prompt
using GEPA's supported reflection template and native proposal delimiter. Its
config has exactly four keys:

```json
{"config_contract_version":1,"model":"gpt-5.6-luna","temperature":0.2,"max_completion_tokens":4096}
```

The text body must contain GEPA 0.1.4 tokens `<curr_param>` and `<side_info>`
exactly once each and no legacy placeholder. It requires the smallest targeted
edit, preservation of variables/output schema/safety rules, and no copied
names/transcript fragments/examples. The response contract is exactly one
unlabelled triple-backtick fenced block containing only the updated prompt;
text outside the block, a missing/extra fence, or changed placeholders is a
configuration/proposal failure. A structured response format is intentionally
absent because adding one would require a custom proposer that duplicates
GEPA's native parser.

#### Judge profile

The three chat prompts are `graf/evaluation/meeting-outcome-faithfulness`,
`graf/evaluation/meeting-outcome-action-items`, and
`graf/evaluation/meeting-outcome-completeness`. Each has exactly the outcome
profile's five top-level keys, uses `temperature: 0` and
`max_completion_tokens: 2048` (within the v1 `1..8192` range). This is the full
canonical faithfulness config; the other two change only schema `name`:

```json
{
  "config_contract_version": 1,
  "model": "gpt-5.6-luna",
  "temperature": 0,
  "max_completion_tokens": 2048,
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "graf_meeting_outcome_faithfulness_judge_v1",
      "strict": true,
      "schema": {
        "type": "object",
        "properties": {
          "score": {"type": "number", "minimum": 0, "maximum": 1},
          "verdict": {"type": "string", "enum": ["pass", "fail"]},
          "feedback": {"type": "string", "maxLength": 4000}
        },
        "required": ["score", "verdict", "feedback"],
        "additionalProperties": false
      }
    }
  }
}
```

Faithfulness and action-item bodies contain exactly
`{{source_segments_json}}` and `{{candidate_outcome_json}}`; completeness also
contains exactly `{{required_categories_json}}`. Each rubric is static inside
its own prompt—there is no arbitrary rubric variable. Missing/extra variables
fail before egress. Human calibration labels/expected output are never included
in the judge task; the calibration evaluator compares them only after the judge
returns. GRAF also validates metric-specific verdict consistency. Dataset
labels, expected output, aggregate annotations, and GEPA side information stay
owner-controlled and never enter Temporal History or Langfuse. The exact raw
feedback returned by an actual synthetic judge call is part of that call's one
content-bearing Langfuse generation output, not a dataset or annotation export.

#### Control-prompt promotion

Reflection and judge versions use the same exact-version candidate and
production-label process as outcome prompts but never share their calibration
gate. Reflection must pass placeholder/fence/native-parser, schema-variable
preservation, anti-copy, and bounded-cost synthetic smokes. Each judge must
pass a frozen human-labelled synthetic calibration set, report invalid outputs,
meet its versioned agreement threshold, and receive deployment-operator
approval. Existing optimization runs remain pinned. Protected-label capability
and the sole mutation credential/path are verified before any control prompt is
first promoted.

#### Projection and forbidden fields

GRAF sends only the validated `model`, `temperature`,
`max_completion_tokens`, and profile-specific `response_format`. A capability
smoke must prove the selected LiteLLM route supports the exact parameters and
strict schema. No hidden request setting comes from code. Adding `top_p`,
reasoning/verbosity, penalties, seed, stop sequences, tools, or vendor-specific
parameters requires config contract v2 and a new reviewed capability test.

Base URL, credentials, headers, provider/upstream routing, retry/fallback,
timeout, tracing policy, optimizer budget/concurrency, promotion thresholds,
dataset content/references, and user/meeting identity are always forbidden in
Langfuse Config. These remain deployment/application safety policy.

`graf/meeting-outcome/auto` is a direct conservative prompt; it does not
classify and dispatch. Every built-in format has a self-contained outcome
prompt, while bounded personal templates reuse one self-contained custom
prompt.

### Durable Generation Contract

After the candidate and generation attempt commit, the server dispatches
`OutcomeGenerationWorkflow` with deterministic workflow ID
`outcome-generation/{candidate_id}`. Dispatch failure does not delete the row;
the existing processing reconciler boundary retries undispatched queued rows.

Temporal workflow start input remains compact:

```json
{
  "candidate_id": "uuid",
  "meeting_id": "uuid",
  "workspace_id": "uuid",
  "source_result_id": "uuid",
  "template_key": "graf-client-update-v1",
  "template_version": 1,
  "prompt_name": "graf/meeting-outcome/client-status-update"
}
```

The complete canonical transcript intentionally enters Temporal History through
normal JSON payloads for internal-MVP debugging. Other workflow/model content
may appear when required for execution or failure debugging, but this contract
does not duplicate the exact full request/response/result into History; those
remain complete in the Generation Call ledger and Langfuse.
Feature 121 adds no PayloadCodec, encoded Failure Converter, application-layer
encryption, redaction, masking, truncation, key ring, or Codec endpoint. Memo
and Search Attributes remain bounded operational indexes rather than transcript
storage.

The workflow executes five externally meaningful activity classes:

1. `resolve-prompt-config` opens tenant scope, verifies candidate/source/template
   lifecycle, resolves the selected format prompt by explicit `production`
   label or an integrity-checked export of that same promoted version, rejects
   unknown/unsafe config fields, and atomically persists the exact uncompiled
   prompt/config, version/hash, selected model route,
   allowlisted request parameters, and strict response schema. If neither
   source is available, the attempt enters bounded `blocked_dependency` and is
   retried by Temporal without model egress.
2. `snapshot-transcript-metadata` pins the canonical transcript hash, plaintext
   byte count, and deterministic chunk count without returning transcript text.
3. `snapshot-transcript-chunk` returns each deterministic plaintext UTF-8 chunk
   exactly once using the default Temporal JSON converter:
   `candidate_id`, `source_result_id`, `snapshot_hash`, `chunk_index`,
   `chunk_count`, and `transcript_utf8`. Plaintext chunks are at most 192 KiB,
   each serialized payload remains at most 256 KiB, and the full snapshot is at
   most 8 MiB. The workflow assembles and validates these activity results one
   chunk at a time and retains only the resulting hash/count for the next
   activity; it never passes the assembled transcript as one activity payload.
   Oversized input fails before model egress.
4. `execute-generation-attempt` reloads the pinned snapshot and authorized
   transcript inside tenant scope, rechecks deletion/source identity, compiles
   variables as untrusted data, sends that transcript to the one allowlisted
   LiteLLM Proxy with the pinned model/settings/schema and no client/gateway
   retry or fallback,
   validates one strict structured result, verifies that the transcript hash
   equals the Temporal snapshot hash, and atomically persists the ready candidate
   plus a retained plaintext `GenerationCall` row before acknowledging the
   response. That row contains the exact logical request, complete transcript,
   raw response, and validated output. A crash after possible egress but
   before response persistence records `ambiguous` and never fabricates output.
5. `publish-observability` is the sole Langfuse `generation` owner. It loads the
   retained Generation Call row, verifies
   source/snapshot/request transcript-hash equality, and publishes the Langfuse
   generation using the original call timestamps. Retry reuses the same
   trace/observation ID and never repeats the model call. Success updates export
   status but does not clear or delete the plaintext row; failure leaves delivery
   durably pending until confirmation and does not change candidate readiness.

LiteLLM URL/key, upstream route/provider secrets, network headers, retry policy,
and security/budget ceilings are deployment/application policy and are never
read from Langfuse Prompt Config. The initial pinned model route is
`gpt-5.6-luna`; a later promoted prompt/config may select another allowlisted
route without workflow or code changes.

Timeout, connection, rate-limit, and transient `5xx` failures are retryable.
Authentication, invalid configuration, missing route, input, budget/policy, deletion,
stale-version, and structured-output errors are non-retryable. Accept/reject
never runs inside the workflow. Prompt-control unavailability with no verified
snapshot is a bounded retryable dependency state, not permission to use a
code-owned model default.

### Langfuse Trace Contract

The Temporal client registers the stable official
`temporalio.contrib.opentelemetry.TracingInterceptor` once through a minimal
subclass that injects/extracts `TraceContextTextMapPropagator` only. W3C baggage
is not written to Temporal headers. Temporal and Langfuse use the same provider;
Langfuse exports the explicit outcome/optimization workflow tree plus its
Langfuse observations. Global HTTP,
FastAPI, SQL, object-store, and unrelated workflow spans are not exported.

One deterministic trace ID derived from
`outcome-generation/<candidate_id>` is reused by every Temporal delivery. Each
real activity execution adds its retry-numbered tree:

```text
generate-meeting-outcome                         # seeded dispatch observation
├── StartWorkflow:OutcomeGenerationWorkflow
├── RunWorkflow:OutcomeGenerationWorkflow        # zero-duration marker
├── StartActivity:resolve-prompt-config           # marker
│   └── RunActivity:resolve-prompt-config
│       └── resolve-prompt-config
├── StartActivity:snapshot-transcript-metadata
├── StartActivity:snapshot-transcript-chunk[*]    # plaintext in History
├── StartActivity:execute-generation-attempt      # marker
│   └── RunActivity:execute-generation-attempt    # duration, attempt=N
│       ├── load-context
│       ├── call-outcome-model                    # provider egress; no generation
│       ├── validate-outcome
│       └── persist-candidate
├── StartActivity:publish-observability           # sole generation owner; retry only
└── CompleteWorkflow:OutcomeGenerationWorkflow    # zero-duration marker
```

The trace ID is `create_trace_id(seed="outcome-generation/<candidate_id>")`.
Use stable action names and propagate Langfuse v4 `environment`, `user_id`,
`session_id`, feature tags, prompt version, selected/actual model provenance,
retry attempt, and status across observations. Token usage is the exact
normalized LiteLLM/provider value when returned and otherwise `unknown`; cost is
an exact returned value or Langfuse's configured model-price calculation and
otherwise remains `unknown`. AI workflow observations may contain complete
plaintext meeting/model content. The publisher
creates exactly one `generation` with the original model-call timestamps; the
inference activity creates none. Publication retry reuses that observation and
does not create a second generation or cost record.

Generation content uses canonical UTF-8 JSON with stable key ordering:

```json
{
  "input": {
    "request": {
      "model": "gpt-5.6-luna",
      "messages": [
        {"role": "system", "content": "<compiled instructions>"},
        {"role": "user", "content": "<canonical transcript appears here once>"}
      ],
      "temperature": 0.2,
      "max_completion_tokens": 4096,
      "response_format": {"type": "json_schema", "json_schema": {}}
    }
  },
  "output": {
    "raw_response": {"<literal parsed LiteLLM response JSON>": true},
    "validated_result": {"<normalized pinned-schema result JSON>": true}
  }
}
```

The values above illustrate types; canonical serialization of stored `request`
is identical to canonical serialization of the validated body sent to LiteLLM.
Only fields from the pinned closed Config profile are present. The transcript
appears exactly once, inside the request message/variable where it was sent;
there is no duplicate top-level transcript field. URL, headers, credentials,
transport retry state, and provider secrets are not part of the logical
request because the exporter explicitly selects model/request fields. No
redaction or masking step changes the canonical transcript, including
credential-like meeting speech.

Every observed actual LiteLLM call creates one distinct generation observation
tagged with `activity.info().attempt`. Temporal workflow replay, duplicate
start, and idempotent activity short-circuit create no generation/cost
observation. The durable generation-attempt ledger—not fail-open telemetry—is
the accounting authority because a process may crash before exporter flush.
Raw audio and runtime credentials are not deliberately selected as observation
attributes. Langfuse export is asynchronous and fail-open for candidate
readiness. Missing credentials, timeout, SDK/export failure, or outage updates
the background export status; durable retry publishes the same observation
without repeating model egress. Langfuse does not own meeting, acceptance, or
deletion truth.

Internal production sends Langfuse traffic only to
`https://cloud.langfuse.com` using the configured project and environment.
Retention and access are operator-managed. GRAF stores trace IDs for correlation
but does not delete, redact, mask, truncate, or encrypt Langfuse content.

### Temporal Plaintext Transcript Payload Contract

Temporal uses the default JSON/Pydantic converter. Each transcript chunk is a
plain typed payload:

```json
{
  "candidate_id": "uuid",
  "source_result_id": "uuid",
  "snapshot_hash": "sha256",
  "chunk_index": 0,
  "chunk_count": 4,
  "transcript_utf8": "<verbatim transcript chunk>"
}
```

`transcript_utf8` is no larger than 192 KiB; canonical serialized payload is no
larger than 256 KiB; the complete snapshot is no larger than 8 MiB. The
assembler verifies stable identity, equal hash/count, contiguous zero-based
indices, no duplicates, valid UTF-8, and final SHA-256 before model execution.
Any mismatch or oversize input fails before model egress and never returns a
partial transcript. No encode/decode HTTP route or key lifecycle exists.

Meeting deletion cancels open work before model egress and blocks candidate
publication/acceptance. If a completed Generation Call row already exists, its
observability delivery continues until Langfuse confirmation. GRAF does not
delete closed or cancelled Temporal History. The deletion report names
the retained plaintext Generation Call ledger, Langfuse observations, and
Temporal History as observability copies under operator-managed retention.

### Prompt Optimization Contract

An authenticated deployment-operator command, unavailable to ordinary cabinet
and workspace-admin APIs, creates a deployment-scoped `PromptOptimizationRun` and starts
`PromptOptimizationWorkflow` with deterministic ID
`prompt-optimization/{run_id}`. Workflow input/history may contain the complete
plaintext synthetic dataset inputs, outputs, reflection, judge feedback, and
optimizer state required for debugging, along with prompt/run IDs, exact
versions/hashes, budget, and rollback version.

Approve/reject arrives as a Temporal Update containing only an opaque,
single-use audit-action ID. `approval_expires_at` is deterministically persisted
when the candidate becomes ready and is no later than seven days afterward. Its workflow
validator checks state/expiry only; an activity loads the action, rechecks
deployment-operator authorization, records consumption, and returns bounded
status. Actor identity and credentials never enter workflow history.

Feature 121 accepts only immutable synthetic manifests. One synchronous
heartbeat activity on a dedicated concurrency-one task queue runs
`gepa==0.1.4` with `raise_on_exception=True` and the same zero-retry
LiteLLM/strict-validation path used by production. It restores and snapshots
GEPA state through existing owner-controlled object storage (or a separately
proven shared persistent volume), because worker-local `run_dir` is not durable.
A checkpoint is an immutable server-generated object under a fixed run prefix;
the worker verifies object key, schema/optimizer version, canonical manifest
hash, and payload checksum before restore, then atomically advances the DB
pointer only after a complete upload. Operator-supplied paths/objects are never
loaded, including unsafe pickle from outside that prefix.
A custom stopper reads a durable absolute deadline and call/token/cost budget;
callbacks are non-throwing/sanitizing, may emit allowlisted scalar aggregates,
but never own cancellation, budget or durability and never export raw
candidates/inputs/outputs/trajectories/prompts or exception strings.

GEPA checkpoints at iteration boundaries and re-runs seed validation before
loading resumed state. Therefore an application-owned call ledger reserves each
task/reflection/judge call before egress and stores status
`reserved|succeeded|ambiguous|failed`, lease expiry and activity fence, exact prompt/config/model versions,
bounded usage and an opaque result-artifact reference. Durable success is
reused; an ambiguous crash is conservatively charged and requires bounded retry
or operator resolution. A new activity attempt atomically fences the old lease;
an expired reservation becomes `ambiguous`, and an old worker cannot persist
success after its fence is replaced. This guarantees at most one stored result
after durable success, not impossible exactly-once provider egress.

Held-out data is unavailable to GEPA/reflection and is evaluated once after
finalist selection while the finalist remains only in owner-controlled
artifacts. Only a passing finalist creates an exact numeric Langfuse prompt
version. It receives no manually assigned candidate/staging/production label;
Langfuse-managed `latest` is ignored. The candidate copies the source config,
is re-read by exact version, and must match the source canonical JSON SHA-256.

Promotion uses per-prompt DB/advisory serialization, re-fetches the expected
production version, updates the label, clears local cache, and post-verifies.
This detects conflicts but is not represented as native compare-and-swap.
Production rollout requires a protected `production` label, human prompt
editors limited to a role that cannot move it, and the sole admin/owner mutation
credential restricted to the deployment service. Without that capability,
automated promotion stays disabled. Rollback is a separate idempotent
`PromptRollbackWorkflow` and trace linked by run/version IDs. GEPA and judges
cannot approve or promote.

The optimization trace ID is
`create_trace_id(seed="prompt-optimization/<run_id>")`. The bounded initial
trace topology is:

```text
optimize-meeting-prompt
└── run-prompt-optimization-workflow
    ├── resolve-optimization-contract
    ├── evolve-prompt
    │   ├── restore-checkpoint
    │   ├── call-task-model               # generation per actual rollout
    │   ├── call-metric-judge              # one of three pinned judges
    │   ├── reflect-candidate              # generation per actual proposal
    │   └── persist-checkpoint
    ├── validate-heldout
    ├── publish-prompt-candidate
    └── approve-reject-or-promote          # only after operator command
```

The long operator-approval wait is workflow state, not an open Langfuse span. Resume restores
the shared checkpoint and reuses durable-success ledger entries; a raw callback
is never telemetry. The optimization execution uses one bounded trace;
promotion can join it only while still within the active run, while later
rollback always uses its own linked trace.

The operator `purge` command for a synthetic run removes only GRAF-owned run
rows, optimizer call-ledger rows, and shared checkpoints. It does not delete or
claim to delete the run's Langfuse observations or Temporal History; those
remain complete plaintext observability copies under platform retention.

The stable Temporal `TracingInterceptor` is chosen even though the newer plugin
is recommended for accurate workflow durations, because the plugin API is still
experimental in SDK 1.30.0. Workflow correlation spans may be zero-duration;
durable workflow/DB timestamps and activity/generation spans own latency.
Switching requires a stable plugin API plus replay, privacy and trace-shape
evidence.

## Sharing API

### Recipient Search

`GET /api/v1/cabinet/share-recipients?query={text}`

Returns only active users visible within the current workspace. Empty, short,
or cross-workspace queries return no private identity data. The response is
bounded and contains stable user ID plus safe display label; email visibility
follows workspace policy.

### Create Or Update Internal Grant

Extend the existing route:

`POST /api/v1/cabinet/meetings/{meeting_id}/shares`

```json
{
  "audience_type": "user",
  "audience_id": "uuid",
  "content_scope": "summary_only",
  "can_download": false,
  "can_export": false,
  "expires_at": null
}
```

Allowed `audience_type`: `user`, `workspace`, `team`, `link`.

Rules:

- default is user + summary-only + no download/export;
- workspace/team/link require matching policy and explicit confirmation token
  from the HTML flow;
- `team` requires same-workspace team ID;
- `link` requires expiry when workspace policy says so and returns a raw token
  once; only its hash is stored;
- duplicate active grants update deterministically or return the current grant;
- deletion/revocation policy is checked before commit.

### Revoke / Rotate Link

- Existing `DELETE /api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}` revokes any grant type.
- `POST /api/v1/cabinet/meetings/{meeting_id}/shares/{grant_id}/rotate` rotates active link token and invalidates the old token in one transaction.

### External Email Invitation

`POST /api/v1/cabinet/meetings/{meeting_id}/share-invitations`

```json
{
  "address": "recipient@example.test",
  "content_scope": "summary_only",
  "can_download": false,
  "can_export": false
}
```

The server normalizes and validates the address, stores only a bounded encrypted
delivery value plus lookup hash, starts a durable delivery lifecycle, and
returns a content-free invitation state. Responses never reveal whether an
unrelated private account exists.

`DELETE /api/v1/cabinet/meetings/{meeting_id}/share-invitations/{invitation_id}`
revokes a pending/sent invitation.

External invitation endpoints remain disabled until SMTP/delivery, identity,
retention, RLS, abuse, and deletion gates pass.

### Resolve Share

- Authenticated user/token share continues through the current cabinet route.
- A link audience uses a dedicated narrow resolver and response projection.
- Summary-only projection contains only safe meeting label/date/duration,
  accepted summary sections, and bounded share metadata; it excludes transcript,
  playback, speakers, participants, source metadata, downloads, exports, private
  templates, and internal activity.
- Full-meeting projection still checks every route capability independently.
- Anonymous link resolution is rate-limited, returns generic not-found on
  invalid/revoked/expired/deleted state, and never redirects into the internal
  owner cabinet response.

## Export And Deletion Composition

- `Экспорт` reads feature 120's canonical availability response; no browser or
  feature-121 formatter constructs transcript/summary files.
- Existing audio download and package export remain server-mediated and
  independently policy-gated.
- Once deletion begins, template generation/accept, grant/invite creation,
  link resolution, playback, export, download, and outcome publication all
  fail closed with the lifecycle reason.
- Deletion UI uses the bounded GRAF copy and offers the existing report route.
- The report states that the retained plaintext Generation Call ledger,
  Langfuse observations, and Temporal History are not deleted with the meeting;
  they remain observability copies under operator-managed retention.

## HTML / HTMX Interaction Contract

Existing meeting detail remains the owning page. Add focused server-rendered
fragments rather than new top-level routes:

| Interaction | Fragment/state |
|---|---|
| Open format selector | `Авто`, at most four recommended/recent rows, selected state, `Все форматы…` |
| Open personal-format settings | Name, supported sections, detail, validation; outside meeting detail |
| Request regeneration | Start candidate while accepted result remains current; no up-front replacement modal |
| Candidate ready | `Новый вариант готов` plus `Использовать`; dismissal keeps current |
| Open Share | Recipient combobox + Invite, current viewers/revoke, collapsed `Что увидят: только итоги` |
| Open recipient row | Content scope and recipient-bound Copy link; no role matrix |
| Broaden audience | Scope confirmation before grant mutation |
| Revoke/rotate | Inline pending/success/error without losing dialog context |
| Open More | Export, audio download, meeting information, deletion actions allowed for the viewer |
| Open Export | Canonical feature-120 artifact/format availability only |
| Delete | Bounded confirmation, deleting progress, report link |

Controls use existing classes/tokens and progressive enhancement. The server API
remains complete without JavaScript; HTMX enhances fragments and focus restore.

## Accessibility Contract

- Format selector is a labelled button with current selection; its popover
  uses a listbox/menu pattern appropriate to actual interaction, not mixed roles.
- Share, personal-format editor, broader-scope confirmation, and deletion
  confirmation are modal dialogs with labelled title, focus containment, Escape
  close when non-destructive, and focus return to opener. Plain Escape never
  stops recording.
- Initial focus: recipient input for Share; name input in personal-format
  settings; static warning/title for broader scope/delete when reading
  consequences first matters.
- Tab and Shift+Tab cycle inside a modal; no positive tabindex.
- Status updates use polite live regions once per transition. Elapsed capture
  time is not continuously announced.
- Error summary receives focus and fields reference specific errors.
- State is never communicated only by color; all icons have text or accessible
  names; decorative icons are hidden from assistive technology.
- Narrow layouts keep primary action and scope warning visible and do not create
  horizontal scrolling inside the modal.

## Problem Detail Codes

| Code | Status | Meaning |
|---|---:|---|
| `template_not_found` | 404 | No caller-visible active template. |
| `builtin_template_immutable` | 403 | Built-in mutation attempted. |
| `template_version_conflict` | 409 | Stale personal template edit/selection. |
| `summary_source_unavailable` | 409 | No eligible transcript/result revision. |
| `summary_generation_in_progress` | 409 | Equivalent generation already active. |
| `summary_revision_conflict` | 409 | Accepted pointer changed before accept. |
| `share_policy_denied` | 403 | Audience/content/capability prohibited. |
| `share_recipient_not_found` | 404 | Generic unavailable recipient result. |
| `share_link_expired` | 404 | Generic expired/invalid link result. |
| `share_invitation_disabled` | 503 | Delivery gate is not enabled. |
| `meeting_deleting` | 409 | Mutation/egress blocked by deletion. |
| `meeting_not_found` | 404 | Generic unauthorized/deleted/not-found response. |
| `summary_transcript_too_large` | 413 | Complete plaintext transcript exceeds the bounded Temporal History contract. |
| `summary_transcript_snapshot_invalid` | 422 | Plaintext chunks fail identity, order, count, UTF-8, or final-hash validation. |

Problem details never include meeting title/content, email, token, object key,
signed URL, provider payload, or secret path.
