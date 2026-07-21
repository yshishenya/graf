# Quickstart Validation: Complete Recording Workflows

## Purpose

Provide runnable, content-safe evidence that each independently testable story
works without weakening existing recording, tenant, export, or deletion truth.
This document is a validation guide, not implementation code.

## Prerequisites

- Branch `121-recording-workflows` after implementation tasks are complete.
- Feature 106 v5 artifact contract accepted or explicitly reconciled.
- Feature 118 playback/timeline regressions available.
- Feature 120 canonical export contract accepted or its integration tasks held.
- Synthetic meeting fixtures only; no private audio, transcript, identity, email,
  token, signed URL, or production secret in committed evidence.
- Disposable PostgreSQL database for migration/RLS/destructive probes.
- External invite and public-link runtime flags disabled unless their gates are
  the explicit scenario under test.
- Langfuse tests use disposable/synthetic metadata and ignored file-backed
  credentials only; no live key or trace payload is printed or committed.

## Core Commands

```sh
swift test --package-path apps/macos --disable-swift-testing
swift run --package-path apps/macos ContractValidation
python -m pytest apps/server/tests/unit apps/server/tests/contract apps/server/tests/integration
infra/scripts/ci-local.sh
```

Use focused test selectors documented by implementation tasks before the full
gate. Do not run destructive RLS or deletion tests against production.

## UX Simplicity Gate

Use the connected 12-state prototype in [ux-ia.md](./ux-ia.md). For every
state, verify that a representative user can identify within three seconds:

1. what is happening;
2. whether the recording is safe;
3. whether GRAF needs an action;
4. the one next action.

Fail the gate if a normal path shows more than one visually primary action, a
permanent lifecycle stepper/right control rail, raw pipeline terminology, a
first-screen sharing capability matrix, healthy source meters/details, or a
plain-Escape shortcut that stops recording.

### Prototype synthetic fixture and assertions

Use only the committed fictional fixture in
`specs/121-recording-workflows/prototype/`: a weekly team meeting on 21 July
2026, fictional participants, `.local`/`.test` addresses, synthetic timestamps,
and invented summary/transcript content. It represents these 12 review states:

1. ready;
2. permission recovery;
3. detected meeting awaiting consent;
4. active recording;
5. paused recording;
6. one degraded source while the other continues;
7. saved locally/offline;
8. partial processing;
9. ready summary;
10. generated format candidate with accepted output preserved;
11. internal Share with invite and revoke;
12. delete confirmation followed by generic unavailable state.

For each state assert one visually primary next action, truthful status copy,
visible keyboard focus, and a safe route back. Reject any prototype state that
contains a countdown/auto-start promise, plain-Escape Stop, permanent pipeline
stepper, permanent right control rail, source diagnostics while healthy,
sharing role/capability matrix, public-link control without a policy gate,
provider jargon, private meeting content, real identity, credentials, or live
URLs/tokens.

## Scenario 1: Permission And Readiness

1. Launch with microphone and Screen/System Audio permission unknown.
2. Confirm neither permission is implied by the other.
3. Deny each permission in turn and verify Start is blocked with a specific
   `Открыть настройки macOS` / `Проверить снова` recovery path.
4. Grant both, relaunch only when macOS requires it, and confirm ready state.
5. Verify source labels and meters do not convert ordinary silence into a false
   unavailable state.

**Pass**: No capture begins before allowed readiness; controls have Russian
accessible names and visible keyboard focus.

## Scenario 2: Detect-And-Ask And Duplicate Start

1. Feed a supported synthetic meeting-detection candidate.
2. Verify the prompt identifies safe app/context data and offers `Начать` and
   `Не сейчас` without countdown, auto-start, or an in-prompt auto-record toggle.
3. Trigger Start from two visible controls nearly simultaneously.
4. Verify one recording session/package identity and no second Start control in
   starting/active state.

**Pass**: One deliberate recording, one local identity, no hidden start.

## Scenario 3: Active, Pause, Resume, Stop

1. Start a synthetic capture with both owned sources.
2. Verify main window/titlebar/menu-bar show active state, elapsed time, sources,
   Pause, and Stop.
3. Pause, wait, resume, and stop.
4. Inspect metadata-only manifest assertions for one privacy interval and one
   shared timeline without fabricated speech/audio.
5. Repeat using keyboard and VoiceOver.

**Pass**: Stop remains one action; Pause covers both owned sources; elapsed time
is not continuously announced.

## Scenario 4: Degraded Source And Device Change

1. Start with both sources ready.
2. Remove/change microphone device and separately revoke or fail system audio.
3. Verify the affected source becomes degraded/unavailable with a recovery
   action while the other source remains truthful.
4. Stop and finalize.

**Pass**: Usable material is preserved; result never claims complete capture;
no automatic hot-switch claim is made without proof.

## Scenario 5: Crash, Offline, And Local Custody

1. Record while server/network is unavailable.
2. Simulate exit at active, stopping/finalizing, saved-local, and uploading
   boundaries using test fixtures.
3. Relaunch and reconcile.
4. Restore network and allow upload/finalize retry.

**Pass**: Every durable fixture is finalized/recovered or remains with one
truthful recovery state; exactly one server meeting is accepted; no last usable
copy is deleted.

## Scenario 6: Artifact-Independent Processing

1. Create states where playback is ready but transcript/summary are processing,
   transcript is ready but playback is unavailable, and summary generation
   fails while prior summary remains accepted.
2. Open browser and embedded meeting detail.

**Pass**: Each artifact remains independently visible/usable; no generic state
hides ready content; both surfaces show the same server truth.

## Scenario 7: Playback, Transcript, And Speakers

1. Open a representative meeting with overlapping turns, unknown speaker, and
   a confirmed renamed speaker.
2. Play, seek from transcript, seek from speaker timeline, and switch tabs.
3. Run in two tabs and embedded desktop.

**Pass**: Active turn/time remain aligned within one second; speaker identity
truth is not fabricated; no feature-118 regression.

## Scenario 8: Built-In And Personal Templates

1. Open the summary selector and inspect `Авто`, at most four
   recommended/recent formats, and `Все форматы`; verify create/manage is in
   Settings rather than the meeting quick selector.
2. Select each built-in and verify immutable state.
3. Select `Авто` and verify one direct conservative general outcome is generated
   from `graf/meeting-outcome/auto`; no classifier call, hidden format switch,
   or second candidate is created.
4. Duplicate a built-in, edit the personal copy, archive it, and verify the
   historical meeting still renders pinned provenance.
5. Submit unsafe section keys, markup, prompt-like text, oversized name/purpose,
   and stale version.

**Pass**: Original GRAF templates only; invalid content fails with bounded field
errors; every generated category preserves `available`, `not_found`, or
`not_inferable` consistently with its item count; no private meeting content
enters template/audit rows.

## Scenario 9: Candidate Regeneration And Revision Race

1. Keep an accepted outcome set A.
2. Request candidate B with a different template.
3. Fail one generation and verify A remains current.
4. Generate B successfully, then request candidate C in another tab.
5. Accept B using the expected pointer; attempt stale C acceptance.
6. Share/export before, during, and after acceptance.

**Pass**: Acceptance is atomic; stale accept returns conflict; readers use the
accepted pointer; prior output is preserved/superseded, never silently erased.

## Scenario 10: Internal Sharing And Copy Link

1. Open Share for a private meeting.
2. Verify the first surface contains only person/email + Invite, current
   viewers/revoke, and collapsed `Что увидят: только итоги`; no role,
   download/export, or audience matrix appears.
3. Search/add an active workspace user, copy the link from that recipient row,
   open it as the correct and wrong user, then revoke it.
4. Expand `Что увидят`, deliberately select full meeting, and verify the exact
   audio/transcript consequence before saving.

**Pass**: A global invite-only Copy link is absent without a recipient grant;
recipient Copy link never broadens access; wrong user receives generic not
found; revocation blocks on the next request; summary-only cannot reach full
meeting routes.

## Scenario 11: Workspace, Team, And Public Link Gates

1. Attempt workspace/team/link grants while policy is disabled.
2. Enable only the synthetic test policy and verify explicit scope confirmation.
3. Create a short-expiry link, access the narrow projection, rotate the token,
   expire/revoke it, and test rate-limit/invalid-token behavior.
4. Attempt direct playback/transcript/export/private-template URLs.

**Pass**: Disabled policy fails closed; broader scope is confirmed; old/expired/
revoked tokens are generic not found; narrow projection contains none of the
forbidden full-meeting surfaces.

## Scenario 12: External Invitation Lifecycle

1. Keep delivery runtime disabled and verify a bounded unavailable state.
2. In disposable test mode, invite a synthetic address, retry a simulated
   transient delivery failure, accept with a verified matching identity, and
   revoke before/after send.
3. Inspect storage/audit/evidence.

**Pass**: Address is bounded/encrypted where required and absent from audit,
logs, analytics, screenshots, and committed evidence; acceptance resolves to a
normal internal grant; deletion cancels pending work.

## Scenario 13: Export And Deletion Race

1. Verify Export displays only feature-120 canonical availability and existing
   server-mediated downloads.
2. Begin a revision-pinned export, then request whole-meeting deletion.
3. Race deletion with summary generation/accept, share creation, invitation
   delivery, link resolution, playback, and export fetch.
4. Open deletion report.

**Pass**: Deletion wins all new publication/egress; access blocks immediately;
report distinguishes controlled purge, local/backup/dependency limits, and
previous external copies; no duplicate formatter or worker appears.

## Scenario 14: Accessibility And Responsive Matrix

Validate the full path at:

- macOS `1280×760` and `1040×680`;
- browser wide and compact/mobile widths;
- embedded desktop wide and narrow;
- dark full path and light proofs for ready, active, detail, Share, and delete;
- keyboard only, VoiceOver, Reduce Motion, and Increased Contrast.

Required connected prototype path:

```text
permission → ready → detected/start → active → pause → resume → stop
→ degraded-source recovery → saved local/offline → partial processing
→ ready summary → template candidate/accept → share/revoke → delete/denied
```

**Pass**: No focus escape, unlabeled control, color-only state, hidden Stop,
horizontal modal scroll, clipped warning, or English/debug implementation copy.

## Scenario 15: Plaintext Temporal History And Full-Content Langfuse Tracing

1. Commit one synthetic queued candidate and interrupt dispatch before Temporal
   accepts it; run reconciliation and confirm one deterministic workflow.
2. Restart the worker before, during, and after the provider activity; repeat
   activity delivery and confirm at most one publishable candidate.
3. Exercise timeout, `429`, and transient `5xx`, then auth/configuration,
   malformed structured output, stale source/template, and deletion.
4. Promote a synthetic format prompt whose config first selects
   `gpt-5.6-luna`, then a compatible fake model route and changed allowlisted
   generation parameters; separately remap one selected route between two fake
   providers. Confirm no GRAF code/workflow-schema change, strict local schema
   validation, zero client retry, exact config pinning, and distinct actual
   provenance.
5. Disable Langfuse export after storing the synthetic model result. Confirm the
   candidate remains ready and the retained plaintext Generation Call row stays
   durably pending; restore export and verify the same
   deterministic trace/observation is confirmed without a second model call. Separately prove
   promoted-export fallback and cold-start `blocked_dependency`; recording and
   transcription remain unaffected.
6. Put a clearly synthetic credential-like marker inside the canonical
   transcript. Retrieve the Langfuse observation and prove the complete request,
   transcript, raw response, validated result, and marker remain readable and
   verbatim without masking or truncation. Confirm raw audio and an unrelated
   runtime Authorization credential were never selected as observation fields.
7. Verify the configured private Langfuse destination/environment, absence of
   public trace publishing, operator-managed project access, prompt linkage,
   propagated user/session/tags, model/provider, retry attempt, and prompt/config
   hash. Verify exact returned token usage/cost when supplied, Langfuse-configured
   price calculation when applicable, and explicit `unknown` rather than a
   fabricated value otherwise.
8. Inspect raw Temporal History and prove every transcript chunk is plaintext,
   complete, at most 192 KiB before serialization and 256 KiB after
   serialization, with total snapshot at most 8 MiB. Reconstruct and hash the
   exact transcript; reject missing, duplicate, reordered, invalid UTF-8, and
   oversized chunks before model egress.
9. Delete the synthetic meeting. Verify product access/publication is blocked
   and pending pre-egress workflow work is cancelled, while delivery of any
   completed retained Generation Call continues until Langfuse confirmation and
   the Generation Call row, Langfuse observation, and Temporal History remain
   readable. Verify the deletion report names these three retained observability
   copies and does not report them as failed purge artifacts.

**Pass**: workflow IDs are deterministic; transient failures retry with bounded
backoff; terminal failures do not retry; accepted notes are never replaced;
deletion prevents new candidate publication/acceptance; raw Temporal Service
History contains the exact complete plaintext transcript, while Generation Call
storage and Langfuse contain the exact complete plaintext model-call content.
The trace is named `generate-meeting-outcome` and contains
the actual Temporal
`StartWorkflow`/`RunWorkflow`, `StartActivity`/`RunActivity`, and
`CompleteWorkflow` markers around `resolve-prompt-config`, bounded transcript
snapshot chunks, retry-numbered `execute-generation-attempt`, `load-context`,
actual-call-only `call-outcome-model`, `validate-outcome`,
`persist-candidate`, and `publish-observability`. Workflow
markers may be zero-duration; durable workflow/DB timestamps prove E2E latency.
It uses the explicit test environment, reuses one seeded trace context across
retries, propagates Langfuse v4 attributes, creates no generation on
replay/idempotent short-circuit, and performs no encryption, masking,
truncation, or observability deletion. The durable attempt ledger remains
business/accounting truth; operator-managed Langfuse and Temporal retention
remain visible as an intentional MVP tradeoff.

## Scenario 16: GEPA Candidate, Operator Promotion, And Rollback

1. Create immutable synthetic train/development/held-out manifests in approved
   owner-controlled test storage and start one deployment-operator-authorized
   `PromptOptimizationWorkflow` pinned to the current production prompt/config
   plus exact `graf/prompt-optimization/reflection` and three
   `graf/evaluation/meeting-outcome-*` prompt/config versions. Prove a workspace
   admin and ordinary cabinet request cannot start or approve it.
2. Run two eligible workers, crash one after a model call and during a GEPA
   iteration, then confirm hash/schema/prefix-verified restore of the latest
   complete server-generated checkpoint on the other worker. Verify the new
   activity fence blocks a stale worker write, durable-success entries are
   reused, expired reservations become conservatively charged ambiguous calls,
   and the immutable deadline is preserved. Confirm Temporal History retains
   complete plaintext synthetic optimizer inputs, outputs, and state.
3. Exercise hard JSON-schema/privacy failures, unsupported-claim and
   action-item feedback, format-specific completeness, and latency/token/cost
   ceilings; verify the same zero-retry LiteLLM/validator path as production.
4. Keep the selected finalist only in owner-controlled artifacts, run held-out
   once, and reject a regression. For a pass, create one exact numeric Langfuse
   version with no manually assigned candidate/staging/production label, re-read
   it, and prove canonical config SHA-256 equality; managed `latest` is ignored.
5. Require protected `production`, human editors unable to move it, and the
   sole mutation credential held by the deployment service; otherwise prove
   automated promotion is disabled. With operator approval, serialize per
   prompt, recheck expected production, update, clear cache and post-verify.
   Treat out-of-band change as detected conflict, not native CAS. Execute
   rollback through a separate durable workflow and linked trace.
6. Before promoting changed reflection/judge settings, run the reflection
   placeholder/fence/native-parser/preservation/anti-copy/cost gates and each
   judge's frozen human-labelled calibration, invalid-output report and
   agreement threshold. Verify the next run uses the approved versions while
   an existing run remains pinned.
7. Inspect the detailed optimization and separate rollback traces, Temporal
   history, dependency lock, call ledger, checkpoint manifest, and
   owner-controlled artifacts. Verify Langfuse and Temporal retain the complete
   plaintext synthetic task/reflection/judge inputs, outputs, feedback, and run
   state. Confirm `gepa==0.1.4` is optional, datasets are synthetic only, and no
   DSPy or JEPA dependency was added.
8. Purge the synthetic run through the operator CLI. Verify only GRAF-owned run
   rows, optimizer call-ledger rows, and shared checkpoints are removed while
   the Langfuse observations and Temporal History remain readable and retained.

**Pass**: optimization survives two-worker failover and is bounded by durable
reservations/deadline; only synthetic owner-controlled content is used;
candidate canonical config hash equals source and publication follows held-out;
hard/held-out and control-prompt calibration gates precede operator
approval; a separate rollback workflow restores the exact prior version;
observed actual calls are attempt-numbered without duplicates after durable
success; ambiguous pre-persist egress is reported rather than mislabeled
exactly-once; GRAF purge leaves external observability retained; no
optimizer/judge auto-promotes; JEPA is absent because it is not a prompt
optimizer.

## Security / Privacy Negative Gate

Search all generated evidence, fixtures, logs, diagnostics, screenshots, and
test artifacts for:

- raw audio or transcript/summary text outside the approved Langfuse AI
  observations, plaintext Temporal History, retained Generation Call ledger,
  and explicitly synthetic test assertions;
- real names/emails or user screenshot identity;
- runtime/transport credentials, tokens, signed URLs, passwords, or live secret
  paths outside the explicitly asserted verbatim synthetic transcript field;
- object keys/internal provider payloads;
- raw audio or runtime credentials deliberately attached to Langfuse or Temporal
  observability attributes outside verbatim meeting/model content;
- public link raw token persisted outside the one-time response fixture.

Any match outside the explicitly approved observability stores is a failure and
must be removed before commit or PR. Approved transcript/model content must not
be redacted or masked.

## Completion Evidence

Record only:

- exact commit/build/test version;
- test command and counts;
- metadata-only scenario/result identifiers;
- migration head and rollback receipt;
- policy flags used for public/invite test gates;
- synthetic screenshot paths and accessibility findings;
- unresolved release-only gates.

Passing local scenarios does not claim signed app, production deployment,
notarization, public-link launch, external email delivery, or user rollout.
