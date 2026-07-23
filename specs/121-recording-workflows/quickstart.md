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

The live exercise is production/operator-only. Start the operations-only
container explicitly; never enable the optimizer flag on
`rec-processing-worker`:

```sh
docker compose --profile operations run --rm \
  -e TWOBRAIN_PROMPT_OPTIMIZATION_ENABLED=true \
  rec-prompt-optimization-worker \
  python -m twobrain_rec_server.cli.prompt_optimization <command> ...
```

1. Create immutable synthetic train/development/held-out manifests in approved
   owner-controlled test storage and start one deployment-operator-authorized
   `PromptOptimizationWorkflow` from the Compose `operations` profile, pinned to the current production prompt/config
   plus exact `graf/prompt-optimization/reflection` and three
   `graf/evaluation/meeting-outcome-*` prompt/config versions. Prove a workspace
   admin and ordinary cabinet request cannot start or approve it.
2. Run two eligible operations-only workers (never the normal recording worker), crash one after a model call and during a GEPA
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

## Implementation Evidence — 2026-07-22

This section records the metadata-safe implementation and release receipt for
Feature 121, merged through PRs
[#4235](https://github.com/yshishenya/crisp/pull/4235),
[#4242](https://github.com/yshishenya/crisp/pull/4242), and
[#4243](https://github.com/yshishenya/crisp/pull/4243), then released as
[`v2026.07.22.4`](https://github.com/yshishenya/crisp/releases/tag/v2026.07.22.4)
at exact SHA `3724b596bfc80a19d1dbef000f44c97d56fff7eb`. It deliberately
does not embed transcript text, model responses, credentials, raw audio,
invitation tokens, or private user identity.

### Scenario coverage

| Scenarios | Result | Evidence |
|---|---|---|
| 1–2 | PASS | Native readiness, separate permission recovery, idempotent manual Start, and detect-and-ask without countdown/autostart are covered by `CaptureControlV5Tests`, `SystemAudioPermissionUXTests`, `AppControlAccessibilityTests`, and `MeetingDetectionPolicyTests`. |
| 3–5 | PASS | Pause/resume/one-action Stop, degraded-source truth, crash/finalize/upload custody, and v5 manifest privacy are covered by `CaptureIndicatorTests`, `AppControlAccessibilityTests`, `DesktopUploadQueueV5Tests`, and `CanonicalRecordingManifestTests`. |
| 5–6 | PASS | Native and server projections preserve one artifact-specific custody/processing lifecycle without a second queue. |
| 7 | PASS | Browser and embedded desktop use one authorized two-tab meeting workspace with persistent playback, synchronized transcript/speaker behavior, and fail-closed denied/deleting states. |
| 8–9 | LIVE PASS | Nine immutable built-ins plus bounded personal templates, one direct `Авто`, per-format prompt/config pinning, candidate failure/retry, and accepted-revision conflict behavior pass automated tests. A production LiteLLM call through `gpt-5.6-luna` also completed and retained its exact Generation Call/Langfuse/Temporal evidence. |
| 10–12 | PASS with rollout flags off | Internal summary-only sharing, token rotation/revocation, fail-closed workspace/team/public policy, external invitation lifecycle, at-most-once Postal fence, enumeration resistance, and focus return pass. Public links and external invitations stay disabled for rollout. |
| 13 | PASS | Feature-120 export composition and deletion races block new inference/publication/acceptance, preserve retained observability truth, and expose one contextual More surface. |
| 14 | PASS | The connected 12-state prototype, narrow native window, keyboard/focus, reduced-motion, increased-contrast, two-tab, modal/listbox, Russian-copy, and clean-room checks pass. Visual artifacts are in `prototype/design-qa*.png`; no real meeting or identity content is present. |
| 15 | LIVE PASS | Production read-back confirmed one exact plaintext transcript across the retained Generation Call, Langfuse generation, and Temporal History; exact input/output, usage, cost, privacy, release, and correlation checks passed. The abandoned reconciler child completed and the response-bearing backlog returned to zero. |
| 16 | LIVE PASS | Optional GEPA `0.1.4` adapter, immutable synthetic manifests, persisted fenced ledger, checkpoint restore, budget/deadline, held-out gating, exact unlabelled candidate, operator promotion, rollback, cancellation reconciliation, and bounded purge pass focused tests. The owner-approved production exercise used the private Langfuse prompt `graf/meeting-outcome/t057-synthetic` v3, immutable train/development/held-out manifests (one example each; hashes are recorded below), two operations-only workers, and the configured LiteLLM route. Combined run `9912c9b8-5433-4678-afb9-8446792b18ce` reached candidate v5 (development 0.8, held-out minimum 1.0), checkpoint revision 4, then killed `t057-worker-r` with exit 137; the surviving `t057-worker-s` completed approve → promote → rollback to v3. Separate run `b772ab2e-c021-4a33-8ce1-4796ba019197` proves in-flight activity retry/fencing: after checkpoint 1, the killed worker resumed at activity attempt 2 and advanced to revision 5; its held-out 0.83 was rejected by the immutable 0.9 gate (fail-closed). The earlier `da6ac03b-470a-4612-87fb-4210bc646706` independently records a successful v4 promotion/rollback. All three runs retain complete plaintext model-call content in Langfuse and complete plaintext `transcript_utf8` activity results in Temporal History; no transcript text is printed in this evidence. The stable-interceptor limitation remains documented, and no JEPA/DSPy dependency is present. |

### T057 live receipt (metadata-only)

- Source prompt: `graf/meeting-outcome/t057-synthetic` production v3;
  production config hash `561c8c7323561a1009442255f94130c1536433e531e15db873dec3f669360aec`.
- Immutable synthetic manifests (one example per split): train
  `f7580ad9daadd918b9b5ae31917531ba3e3e0a6a95efe83b60674698ebdaa650`,
  development `7bf2f1b2b8840cd399461e5e6cae392b58673483c59c46419dd386feda5e66db`,
  held-out `5e958a9964e77387d936caa2f6bb4ba9ffe35fc438335e653405301932287960`.
- Successful run `da6ac03b-470a-4612-87fb-4210bc646706`: checkpoint revision 3,
  checkpoint hash `dd1ed99612c19ce58c2cfeb53d5d52a8c6de56a48ccd3ad745a49c6a47cf89b7`,
  23 succeeded ledger calls, candidate v4, development 1.0, held-out minimum
  0.9, then operator approval, promotion, and rollback.
- Forced-crash run `b772ab2e-c021-4a33-8ce1-4796ba019197`: worker
  `t057-worker-l` exit 137; checkpoint revisions advanced 1 → 5 and resumed
  ledger rows reached activity attempt 2. Held-out minimum 0.83 was rejected by
  the immutable 0.9 gate, leaving no candidate to promote.
- Combined crash/promotion/rollback run `9912c9b8-5433-4678-afb9-8446792b18ce`:
  checkpoint revision 4, checkpoint hash
  `6884deb5c4257fb7052f0e554331d5e66a5a50c14d598fb1ea20f4bd8a601a99`, 12
  succeeded ledger calls, candidate v5, development 0.8, held-out minimum 1.0.
  Worker `t057-worker-r` exited 137 after the checkpoint; `t057-worker-s`
  completed the gated approve → promote → rollback sequence. The production
  label was read back as v3 with the recorded config hash.
- Langfuse trace IDs are `cfa0f784c0fa6674a1fb79b206b0ade7` (successful) and
  `bb7ab4bd1f893daffc3d6d710e2badc5` (crash recovery). The traces contain 23
  and 33 generation observations respectively; every generation has non-empty
  input and output, prompt/config metadata, and usage fields. Content is retained
  in the private project but intentionally omitted from this receipt.
- Combined run Langfuse trace `cf2d0039497de44871811dfd02cbbab7` contains 25
  observations, including 12 generations; all 12 have non-empty input, output,
  model, usage details, prompt/config metadata, and run correlation metadata.
- Temporal optimization histories contain 78 and 59 events respectively. Each
  has three plaintext activity results with the `transcript_utf8` field: evolution
  chunks plus held-out, with decoded plaintext byte counts (successful:
  196608+8417+35793; crash recovery: 196608+52001+35163). This is a read-back
  of the default Temporal converter, not an encrypted or redacted artifact.
- Combined run Temporal History contains 74 events and two plaintext activity
  results with `transcript_utf8` (decoded byte lengths `74683+35265`), read back
  through the default converter without printing content.
- The operator CLI does not purge these runs: per the MVP observability policy,
  Langfuse and Temporal plaintext history is retained and no GRAF-owned evidence
  was deleted during closeout.
- Closeout validation after the live exercise: 608 macOS tests, ContractValidation
  PASS, 2206 server tests passed / 1 skipped, strict PostgreSQL/RLS 41 passed /
  1 skipped, collection digest
  `6ee1a51dc6d0ecdad7a93c789a728f0e77fb978255ed28ec192507fa6b24116d`, Ruff,
  compile, Compose, and deployment-evidence scan PASS. The local destructive RLS
  probe remained correctly blocked because no disposable `RLS_TEST_DATABASE_URL`
  was supplied; the production RLS/readiness gate passed during deployment.

### Accepted-summary pointer hotfix — T096 / #4253 (2026-07-23)

The production-shaped regression where a format selection returned `409
summary_revision_conflict` was traced to legacy extractive outcomes with a
missing `Meeting.current_outcome_set_id`. The additive migration
`0032_outcome_pointer` ranks only active, non-deleting legacy extractive rows,
sets the pointer atomically, marks the selected row accepted, and is safe to
run twice; it leaves template provenance fields unset. Runtime baseline
generation now takes the Meeting lock before outcome mutation, and AI candidate
reservation, completion, and accept/reject use the same Meeting → attempt lock
order as deletion.

The regression contract covers the complete user path: rendered
`data-current-outcome-set-id` remains the accepted CAS token, selecting a
non-Auto built-in starts exactly one Temporal workflow with the requested
template, and a newer processing result makes summary/combined export missing
with reason `stored_summary_revision_stale`. A malicious mixed-revision export
returns 409, records a denial, and emits no attachment or content bytes. The
two-session deletion test proves generation waits for and then observes a
committed deletion state.

Validation evidence: focused PostgreSQL suite `45 passed`; canonical
`infra/scripts/ci-local.sh` passed with 608 macOS tests, 2198 server tests / 1
skip, strict PostgreSQL/RLS 41 tests / 1 skip, collection digest
`02702796e56ab9e65a5a69a5f89720c4b512b4e25a5ca6ab6602780bf3bbdae1`, Ruff,
compile, Compose, and deployment-evidence scan. Production deploy used source
SHA `c013bdab27a8be1f705f4727f4bfca2c926c5e9a`, backup
`/opt/projects/2brain-rec/backups/20260723T011346Z`, and migration head
`0032_outcome_pointer`; RLS, runtime identity, Temporal/worker readiness,
smoke/cleanup, automatic dispatch, and public live/ready all passed. The
post-deploy pointer inventory was `legacy_outcomes_with_null_pointer=0`,
`active_accepted_pointer_count=32`, `invalid_pointer_count=0`; no summary
candidate 409 was observed after deployment.

### Langfuse receipt

Read-only prompt verification against the configured private production project
returned the ten outcome prompts (`auto`, `outline`, `meeting-minutes`,
`project-sync`, `weekly-team-meeting`, `one-to-one`, `client-status-update`,
`interview`, `sales-discovery`, and `custom`) at verified production version 2.
The reflection and three judge prompts exist at version 1 and correctly remain
`control-gate-required`; they were not promoted without calibration evidence.

A synthetic private trace was re-read from Langfuse without printing its
content:

- trace `a03a989e4897dbddcfc74ca51edf522f`, name
  `generate-meeting-outcome`, environment `production`, `public=false`;
- root chain observation `34b6a360749bbcde` and sole generation observation
  `b2307bd949bda2dd`;
- input keys are exactly `request` and `transcript`, 305 canonical JSON bytes,
  SHA-256 `95784f39bca15dc360f39b5fdc9b76e521898f19843a0f85525eaf5a6b20d095`;
- output keys are exactly `raw_response` and `validated_result`, 243 canonical
  JSON bytes, SHA-256
  `0ad6f21bec3d8c5f0028725c5c73da2649d4863f610e0a00faf01c961748ef7f`.

This initial synthetic receipt proves the configured private destination, trace shape, explicit
full-content field selection, sole generation publisher, environment, and
non-public state. The production receipt below adds the end-to-end LiteLLM and
three-store read-back required by T050/T089.

### Focused and canonical validation

- Final prompt-optimization cancellation/idempotency suite after adversarial
  remediation: 116 passed; independent re-review suite: 69 passed; Ruff and
  diff checks passed.
- Post-Ponytail focused server regression across prompt optimization, outcome
  generation, sharing, Langfuse, and UI contracts: 89 passed with two external
  dependency warnings and no failures.
- Canonical `infra/scripts/ci-local.sh` after the observability reconciler:
  macOS 608 passed; native `ContractValidation: PASS`; server parallel 2191
  passed, 1 skipped; strict PostgreSQL/RLS 41 passed, 1 skipped; collection
  digest `e17b34f99664a8cca403c031fd70343b5cbb27cc86952cf19db56a298cfa4673`;
  Ruff, Python compile, production Compose rendering, deployment evidence scan,
  and final `ci_local_result=pass` all passed.
- The local RLS helper truthfully reported `live_production_probe=not_attempted`;
  production RLS/health evidence belongs to the post-merge deployment receipt,
  not this local gate.

### Review and simplification

Correctness/security review iterated through failure finalization, infinite
Temporal retries, plaintext chunking, durable GEPA checkpoints, usage/cost
provenance, prompt variables, held-out isolation, object-first purge,
materialization certificates, cancellation quiescence, Langfuse label mutation
reconciliation, DB commit/AsyncSession exit/engine disposal, and rollback child
cancellation. The final independent verdict found no P0/P1/P2 issue.

Ponytail review removed production-unused settings and helpers, duplicate
share-writer and response-provenance paths, test-only runtime ledgers/checkpoint
formats, a no-op optimizer callback, a self-comparison guard, and dead workflow
chunk/observability helpers. Deliberate Temporal sandbox fallbacks, semantic
workflow result types, per-activity transaction scopes, and the explicit WebKit
dialog focus boundary remain because they enforce tested runtime contracts.
The final repeated Ponytail verdict was `Lean already. Ship.`.

Post-implementation `$speckit-analyze` rechecked 111 explicit FR/SC entries,
95 dependency-ordered tasks, the constitution v4.0.0 gates, terminology,
paths, and open-gate truth. Requirement coverage remains complete and the
finding count is CRITICAL/HIGH/MEDIUM/LOW `0/0/0/0`. T050 and T089 now have
production evidence; T057 remains an intentional external evidence gate rather
than an uncovered requirement. The mandatory repository issue-canon validator
passed after tracker closeout; 90 of 91 Feature-121 issues are complete and
only T057/#4177 remains open.

### Native local-purge hotfix

Pre-install inspection found a production-shaped `403 csrf_token_missing` loop
for native local-purge acknowledgement and recursively growing retry reasons.
PR [#4242](https://github.com/yshishenya/crisp/pull/4242) moved native requests
from browser cookies to redacted `X-Auth-Session`, explicitly disabled the
URLSession cookie jar, preserved cookie-only browser CSRF rejection, bounded
retry reasons, and added a lock-protected 4 MiB log rotation with one retained
backup. Focused native/server regressions passed, the full canonical gate above
passed, and the repeated independent review verdict was `CLEAN`.

### Production, release, and installed-app closeout

- Exact-tag deploy from `v2026.07.22.4` passed with
  `deployed_sha=runtime_sha=3724b596bfc80a19d1dbef000f44c97d56fff7eb`,
  backup `/opt/projects/2brain-rec/backups/20260722T073804Z`, restore rehearsal,
  Alembic head `0031_recording_workflows`, runtime identities, Temporal and
  processing/media worker readiness, automatic dispatch, smoke, and cleanup
  of 37 database records plus 3 object keys.
- Public `live` and `ready` returned HTTP 200. The six GitHub Release assets,
  signed appcast, ZIP, PKG, checksums, notes, and Keychain attestation were
  published; strict public re-fetch matched local SHA-256 values and passed ZIP
  plus owner-only update validation. The appcast was replaced last and now
  advertises `2026.07.22.4`; `.3` is marked superseded.
- `/Applications/GRAF.app` was replaced only while idle and now reports
  version `2026.07.22.4`, bundle id `pro.2brain.graf`, the unchanged designated
  signing requirement, a running process, and retained microphone plus
  Screen/System Audio grants. Post-launch queue refresh produced no
  `csrf_token_missing`, recursive local-purge retry, or repeated stable retry;
  the legacy 8.6 MiB log rotated to a bounded 4 MiB backup and a small current
  log. This is post-launch negative evidence, not a fabricated positive
  pending-task acknowledgement; the positive boundary is covered by the native
  request and server CSRF integration regressions. The prior bundle remains in
  a recoverable temporary backup.

### Production AI observability closeout

PR [#4250](https://github.com/yshishenya/crisp/pull/4250) merged the
response-attempt reconciler at `22771cde`. Production runs the content-equivalent
overlay `3a1cfbdcdde5250ec447fc00f8d98a41cf34784a`; a pre-deploy drain found no
old open outcome workflow and no response-bearing pending Generation Call.
Because the new Temporal history records the patch marker and abandoned child,
rollback is forward-fix only while that history is retained: do not deploy code
that removes the marker or child command.

The metadata-only live receipt is:

- candidate `b2c573a8-439f-4611-80d1-9351d7b51032`, Generation Call
  `674dba1f-af5a-4b3e-b019-f7064dd98534`, parent run
  `019f8a8b-92cd-7aa2-8657-52b6421611cb`;
- child `outcome-observability/b2c573a8-439f-4611-80d1-9351d7b51032`
  completed; response-bearing pending backlog after reconciliation: `0`;
- private Langfuse trace `2d56118a47376212493fed5be9ff16a9`, generation
  observation `da595959984a7fe7`, prompt version `2`, prompt SHA-256
  `cb3532ffae9b5cc5c789de33d64ad079cb4d05d34829c768483247d77738a795`,
  model `gpt-5.6-luna`;
- retained transcript: `720` UTF-8 bytes, SHA-256
  `acb88b372519b4a6bcc6dc4cd1a7f7b28656c1fd6a8ef345e0a5a6a9e0d046e8`;
  Temporal parent History: `36` events and one plaintext chunk;
- exact Langfuse input/output, returned usage, cost presence, private state,
  runtime release, and Temporal correlation: `PASS`; ledger hashes: `PASS`;
  disposable source rows were cleaned while the retained Generation Call,
  Langfuse trace, and Temporal History remained available.

The expanded zero-leak scan read all `21` active Compose secret files (`20`
unique values) without printing them. Content and secret matches were `0` in
ordinary logs, the application database outside `generation_calls`, and
tracked repository content. The server-side AI-only proof created `0` audio
rows, `0` runtime screenshots, and `0` diagnostic bundles; the desktop path
was not executed, product analytics was disabled, and no analytics event path
was invoked. This closes T050 and T089 with metadata-only committed evidence.

### Open external rollout gate

- **T057**: immutable owner-approved synthetic train/development/held-out
  manifests, the human-labelled calibration pack, and a real two-worker
  forced-crash GEPA promotion/rollback exercise are absent. Automated GEPA
  contracts pass, but production prompt optimization remains disabled and no
  live promotion/rollback claim is made.

Production outcome generation is configured and passed the live LiteLLM proof.
Prompt optimization, public-link, team, and external-invitation rollout remain
false until their explicit gates are satisfied.

T095 is satisfied by the owner's explicit advance approval in this task for
commit, push, PR, merge, production deploy, release, and installed-app
replacement after validation and review.
